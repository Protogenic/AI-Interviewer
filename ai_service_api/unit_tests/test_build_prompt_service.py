import pytest

from ai_service.services.build_prompt_service import (
    BuildUserPromptService,
    BuildSystemPromptService,
    _sample_marker,
)
from ai_service.models.generation import GenerationRequest, InterviewPart, BuildPromptResult
from ai_service.models.build_profile import Template
from ai_service.models.rag import RagExample
from ai_service.exeptions.generation_error import UnknownInterviewerError
from ai_service.offline_pipeline.categories import Technique


@pytest.fixture
def basic_template():
    return Template(
        structure="question",
        frequency=10,
        action="question",
        question_openness="open_question",
        emotion="neutral",
        techniques=[Technique.WHY_QUESTION],
        avg_position=0.5,
        reactivity=[],
        examples=["Как так получилось?"],
    )


@pytest.fixture
def multi_part_template():
    return Template(
        structure="acknowledgment+question",
        frequency=5,
        action="question",
        question_openness="open_question",
        emotion="empathy",
        techniques=[Technique.WHY_QUESTION],
        avg_position=0.4,
        reactivity=[],
        examples=["Понимаю. Почему вы так решили?"],
    )


@pytest.fixture
def basic_request():
    return GenerationRequest(
        session_id="sess-1",
        character_id="dud",
        user_name="Иван",
        user_info="Предприниматель",
        last_answer="Я работаю уже пять лет.",
        full_interview_history=[
            InterviewPart(role="interviewer", text="Расскажите о себе."),
            InterviewPart(role="guest", text="Я работаю уже пять лет."),
        ],
        max_number_questions=20,
        phrase_id=3,
    )


@pytest.fixture
def rag_examples():
    return [
        RagExample(
            score=0.9,
            interview_id="i1",
            source_file="f1.jsonl",
            question_replica_id=1,
            question_text="Как вы к этому пришли?",
            answer_text="Это долгая история.",
        )
    ]


class TestBuildUserPromptService:
    def setup_method(self):
        self.service = BuildUserPromptService()

    def test_returns_build_prompt_result(self, basic_request, basic_template, rag_examples):
        result = self.service.build_prompt(basic_request, basic_template, rag_examples)
        assert isinstance(result, BuildPromptResult)

    def test_prompt_contains_user_name(self, basic_request, basic_template):
        result = self.service.build_prompt(basic_request, basic_template, [])
        assert "Иван" in result.prompt

    def test_prompt_contains_user_info(self, basic_request, basic_template):
        result = self.service.build_prompt(basic_request, basic_template, [])
        assert "Предприниматель" in result.prompt

    def test_prompt_contains_last_answer(self, basic_request, basic_template):
        result = self.service.build_prompt(basic_request, basic_template, [])
        assert "пять лет" in result.prompt

    def test_prompt_contains_history_roles(self, basic_request, basic_template):
        result = self.service.build_prompt(basic_request, basic_template, [])
        assert "interviewer" in result.prompt or "guest" in result.prompt

    def test_rag_examples_included_in_prompt(self, basic_request, basic_template, rag_examples):
        result = self.service.build_prompt(basic_request, basic_template, rag_examples)
        assert "Как вы к этому пришли?" in result.prompt

    def test_empty_rag_examples_no_examples_section(self, basic_request, basic_template):
        result = self.service.build_prompt(basic_request, basic_template, [])
        assert "ПОХОЖИЕ СИТУАЦИИ" not in result.prompt

    def test_empty_history_and_answer_shows_no_history_message(self, basic_template):
        request = GenerationRequest(
            session_id="s",
            character_id="dud",
            user_name="Иван",
            user_info="Х",
            last_answer="",
            full_interview_history=[],
            max_number_questions=10,
        )
        result = self.service.build_prompt(request, basic_template, [])
        assert "начало диалога" in result.prompt

    def test_multi_part_structure_mentions_roles(self, basic_request, multi_part_template):
        result = self.service.build_prompt(basic_request, multi_part_template, [])
        assert "acknowledgment" in result.prompt
        assert "question" in result.prompt

    def test_structure_block_includes_action_description(self, basic_request, basic_template):
        result = self.service.build_prompt(basic_request, basic_template, [])
        assert "STRUCTURE" in result.prompt


class TestBuildSystemPromptService:
    def setup_method(self):
        self.service = BuildSystemPromptService()

    def test_returns_build_prompt_result(self, interviewer_profile, basic_template):
        result = self.service.build_prompt(interviewer_profile, basic_template, "dud")
        assert isinstance(result, BuildPromptResult)

    def test_prompt_is_non_empty_string(self, interviewer_profile, basic_template):
        result = self.service.build_prompt(interviewer_profile, basic_template, "dud")
        assert len(result.prompt.strip()) > 0

    def test_raises_for_unknown_interviewer(self, interviewer_profile, basic_template):
        with pytest.raises(UnknownInterviewerError):
            self.service.build_prompt(interviewer_profile, basic_template, "unknown_id")

    def test_prompt_contains_output_format_section(self, interviewer_profile, basic_template):
        result = self.service.build_prompt(interviewer_profile, basic_template, "dud")
        assert "ФОРМАТ ВЫВОДА" in result.prompt

    def test_style_instruction_is_list_of_strings(self, interviewer_profile, basic_template):
        result = self.service.build_prompt(interviewer_profile, basic_template, "dud")
        assert isinstance(result.style_instruction, list)
        assert all(isinstance(s, str) for s in result.style_instruction)

    def test_characteristic_phrases_in_prompt(self, interviewer_profile, basic_template):
        result = self.service.build_prompt(interviewer_profile, basic_template, "dud")
        assert any(phrase in result.prompt for phrase in ["Подождите", "То есть как?"])

    def test_build_style_block_empty_list(self):
        result = BuildSystemPromptService._build_style_block([])
        assert "Нейтральный стиль" in result

    def test_build_output_constraints_with_structure(self, basic_template):
        result = BuildSystemPromptService._build_output_constraints(basic_template)
        assert "JSON" in result

    def test_build_output_constraints_no_structure(self):
        t = Template(
            structure="",
            frequency=1,
            action="question",
            question_openness="open_question",
            emotion="neutral",
            techniques=[],
            avg_position=0.5,
            reactivity=[],
            examples=[],
        )
        result = BuildSystemPromptService._build_output_constraints(t)
        assert "JSON" in result


class TestSampleMarker:
    def test_returns_false_for_zero_density(self):
        used, text = _sample_marker(0.0, "empathy", "empathy", "dud")
        assert used is False

    def test_high_density_may_return_true(self):
        results = [_sample_marker(1.0, "empathy", "empathy", "dud") for _ in range(20)]
        assert any(used for used, _ in results)
