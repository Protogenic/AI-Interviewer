import pytest
from pathlib import Path
from typing import cast

from ai_service.services.profile_repository import GetProfileInfo
from ai_service.selection.action_selector import ActionSelector
from ai_service.selection.template_selector import TemplateSelector
from ai_service.services.build_prompt_service import BuildUserPromptService, BuildSystemPromptService
from ai_service.offline_pipeline.categories import Action, AnswerType
from ai_service.models.generation import GenerationRequest, InterviewPart
from ai_service.models.rag import RagExample

PROFILES_DIR = Path(__file__).parent.parent / "ai_service" / "data" / "profiles"
ALL_CHARACTERS = ["dud", "pozner", "sobchak"]


@pytest.fixture(scope="module")
def repo():
    return GetProfileInfo(profile_dir=str(PROFILES_DIR))


@pytest.fixture(scope="module")
def dud_profile(repo):
    return repo.load_profile("dud")


@pytest.fixture(scope="module")
def pozner_profile(repo):
    return repo.load_profile("pozner")


@pytest.fixture(scope="module")
def sobchak_profile(repo):
    return repo.load_profile("sobchak")


class TestRealProfileLoading:
    def test_all_characters_load(self, repo):
        for cid in ALL_CHARACTERS:
            p = repo.load_profile(cid)
            assert p.interviewer_id == cid

    def test_profiles_are_cached(self, repo):
        p1 = repo.load_profile("dud")
        p2 = repo.load_profile("dud")
        assert p1 is p2

    def test_dud_reactivity_matrix_covers_main_answer_types(self, dud_profile):
        matrix = dud_profile.reactivity_matrix
        for answer_type in {"back_channel", "agreement", "uncertain", "refusal", "explanation"}:
            assert answer_type in matrix, f"missing answer type: {answer_type}"

    def test_all_templates_have_required_fields(self, dud_profile):
        for tpl in dud_profile.templates:
            assert tpl.action, "template missing action"
            assert tpl.structure, "template missing structure"
            assert isinstance(tpl.frequency, int)
            assert 0.0 <= tpl.avg_position <= 1.0

    def test_all_characters_have_non_empty_templates(self, repo):
        for cid in ALL_CHARACTERS:
            p = repo.load_profile(cid)
            assert len(p.templates) > 0, f"{cid} has no templates"

    def test_all_characters_have_characteristic_phrases(self, repo):
        for cid in ALL_CHARACTERS:
            p = repo.load_profile(cid)
            assert len(p.characteristic_phrases) > 0


class TestActionSelectorRealData:
    @pytest.fixture
    def selector(self, dud_profile):
        return ActionSelector(
            reactivity_matrix=dud_profile.reactivity_matrix,
            max_followups_in_row=2,
            random_seed=42,
        )

    def test_distribution_sums_to_one_for_all_answer_types(self, selector):
        for answer_type in AnswerType:
            dist = selector._get_distribution(cast(AnswerType, answer_type))
            assert abs(sum(dist.values()) - 1.0) < 1e-9, f"dist doesn't sum to 1 for {answer_type}"

    def test_select_returns_valid_action_for_all_answer_types(self, selector):
        for answer_type in AnswerType:
            result = selector.select(
                answer_type=cast(AnswerType, answer_type),
                interview_position=0.5,
                consecutive_followups=0,
            )
            assert isinstance(result.action, Action), f"invalid action for {answer_type}: {result.action}"

    def test_explanation_never_produces_question_via_matrix(self, dud_profile):
        sampled_actions = set()
        for seed in range(20):
            sel = ActionSelector(
                reactivity_matrix=dud_profile.reactivity_matrix,
                max_followups_in_row=10,
                random_seed=seed,
            )
            result = sel.select(AnswerType.EXPLANATION, interview_position=0.5, consecutive_followups=0)
            sampled_actions.add(result.action)
        assert Action.QUESTION not in sampled_actions

    @pytest.mark.parametrize("character_id", ALL_CHARACTERS)
    def test_all_characters_selector_works(self, repo, character_id):
        profile = repo.load_profile(character_id)
        selector = ActionSelector(reactivity_matrix=profile.reactivity_matrix, random_seed=0)
        result = selector.select(AnswerType.AGREEMENT, 0.5, 0)
        assert isinstance(result.action, Action)

class TestTemplateSelectorRealData:
    @pytest.fixture
    def selector(self, dud_profile):
        return TemplateSelector(templates=dud_profile.templates, top_n=5, random_seed=42)

    def test_can_select_question_template(self, selector):
        result = selector.select_template(Action.QUESTION, 0.5)
        assert result.template.action == Action.QUESTION.value

    def test_can_select_transition_template(self, selector):
        result = selector.select_template(Action.TRANSITION, 0.5)
        assert result.template.action == Action.TRANSITION.value

    def test_can_select_back_channel_template(self, selector):
        result = selector.select_template(Action.BACK_CHANNEL, 0.5)
        assert result.template.action == Action.BACK_CHANNEL.value

    def test_can_select_acknowledgment_template(self, selector):
        result = selector.select_template(Action.ACKNOWLEDGMENT, 0.5)
        assert result.template.action == Action.ACKNOWLEDGMENT.value

    def test_can_select_summary_template(self, selector):
        result = selector.select_template(Action.SUMMARY, 0.5)
        assert result.template.action == Action.SUMMARY.value

    def test_can_select_clarification_template(self, selector):
        result = selector.select_template(Action.CLARIFICATION, 0.5)
        assert result.template.action == Action.CLARIFICATION.value

    def test_selected_template_has_examples(self, selector):
        result = selector.select_template(Action.QUESTION, 0.5)
        assert len(result.template.examples) > 0

    @pytest.mark.parametrize("character_id", ALL_CHARACTERS)
    def test_all_characters_can_select_question(self, repo, character_id):
        profile = repo.load_profile(character_id)
        selector = TemplateSelector(templates=profile.templates, top_n=5, random_seed=0)
        result = selector.select_template(Action.QUESTION, 0.5)
        assert result.template.action == Action.QUESTION.value


class TestFullSelectionPipeline:
    @pytest.fixture
    def dud_pipeline(self, dud_profile):
        action_selector = ActionSelector(
            reactivity_matrix=dud_profile.reactivity_matrix,
            max_followups_in_row=2,
            random_seed=42,
        )
        template_selector = TemplateSelector(
            templates=dud_profile.templates,
            top_n=5,
            random_seed=42,
        )
        return dud_profile, action_selector, template_selector

    @pytest.mark.parametrize("answer_type", [
        AnswerType.AGREEMENT,
        AnswerType.EXPLANATION,
        AnswerType.REFUSAL,
        AnswerType.SHORT_FACT,
        AnswerType.STORY_WITH_EXAMPLE,
        AnswerType.UNCERTAIN,
        AnswerType.VAGUE,
    ])
    def test_pipeline_completes_for_common_answer_types(self, dud_pipeline, answer_type):
        profile, action_sel, template_sel = dud_pipeline
        action_result = action_sel.select(
            answer_type=answer_type,
            interview_position=0.5,
            consecutive_followups=0,
        )
        action = Action(action_result.action)
        template_result = template_sel.select_template(action, 0.5)
        assert template_result.template is not None

    def test_user_prompt_built_with_real_template(self, dud_pipeline):
        profile, action_sel, template_sel = dud_pipeline
        action_result = action_sel.select(AnswerType.AGREEMENT, 0.5, 0)
        template_result = template_sel.select_template(Action(action_result.action), 0.5)

        request = GenerationRequest(
            session_id="test-session",
            character_id="dud",
            user_name="Иван",
            user_info="Предприниматель",
            last_answer="Да, я согласен с вами.",
            full_interview_history=[
                InterviewPart(role="interviewer", text="Расскажите о своей работе."),
                InterviewPart(role="guest", text="Да, я согласен с вами."),
            ],
            max_number_questions=20,
            phrase_id=5,
        )
        result = BuildUserPromptService().build_prompt(request, template_result.template, [])
        assert len(result.prompt) > 0
        assert "Иван" in result.prompt

    def test_user_prompt_with_rag_examples(self, dud_pipeline):
        profile, action_sel, template_sel = dud_pipeline
        action_result = action_sel.select(AnswerType.AGREEMENT, 0.5, 0)
        template_result = template_sel.select_template(Action(action_result.action), 0.5)

        request = GenerationRequest(
            session_id="sess",
            character_id="dud",
            user_name="Катя",
            user_info="Журналист",
            last_answer="Мне нравится моя работа.",
            full_interview_history=[],
            max_number_questions=20,
            phrase_id=3,
        )
        rag = [
            RagExample(
                score=0.9,
                interview_id="i1",
                source_file="dud_001.jsonl",
                question_replica_id=1,
                question_text="Как вы к этому пришли?",
                answer_text="Это долгая история.",
            )
        ]
        result = BuildUserPromptService().build_prompt(request, template_result.template, rag)
        assert "Как вы к этому пришли?" in result.prompt

    def test_system_prompt_contains_real_characteristic_phrases(self, dud_pipeline):
        profile, _, template_sel = dud_pipeline
        template_result = template_sel.select_template(Action.QUESTION, 0.5)
        result = BuildSystemPromptService().build_prompt(profile, template_result.template, "dud")
        real_phrases = set(profile.characteristic_phrases)
        assert any(phrase in result.prompt for phrase in real_phrases)

    @pytest.mark.parametrize("character_id", ALL_CHARACTERS)
    def test_full_pipeline_for_all_characters(self, repo, character_id):
        profile = repo.load_profile(character_id)
        action_sel = ActionSelector(reactivity_matrix=profile.reactivity_matrix, random_seed=0)
        template_sel = TemplateSelector(templates=profile.templates, top_n=5, random_seed=0)

        action_result = action_sel.select(AnswerType.AGREEMENT, 0.5, 0)
        template_result = template_sel.select_template(Action(action_result.action), 0.5)

        request = GenerationRequest(
            session_id="s",
            character_id=character_id,
            user_name="Тест",
            user_info="Тестовый пользователь",
            last_answer="Да.",
            full_interview_history=[],
            max_number_questions=20,
            phrase_id=5,
        )
        prompt_result = BuildUserPromptService().build_prompt(request, template_result.template, [])
        assert len(prompt_result.prompt) > 0
