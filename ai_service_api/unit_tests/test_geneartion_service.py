import pytest
from typing import cast
from unittest.mock import AsyncMock, MagicMock

from ai_service.services.generation_service import GenerateQuestionService
from ai_service.services.llm_service import BaseLLMClient
from ai_service.models.generation import GenerationRequest, GenerationResponse, InterviewPart
from ai_service.models.build_profile import Template
from ai_service.models.selection import ActionSelection, TemplateSelection
from ai_service.offline_pipeline.categories import Action, Technique


def make_template(action=Action.QUESTION, structure="question"):
    return Template(
        structure=structure,
        frequency=10,
        action=action.value,
        question_openness="open_question",
        emotion="neutral",
        techniques=[Technique.WHY_QUESTION],
        avg_position=0.5,
        reactivity=[],
        examples=["Как?"],
    )


@pytest.fixture
def mock_llm_client() -> AsyncMock:
    client = AsyncMock(spec=BaseLLMClient)
    client.generate_question = AsyncMock(return_value="Как вы к этому пришли?")
    return client


@pytest.fixture
def mock_profile_repository(interviewer_profile):
    repo = MagicMock()
    repo.get_profile = MagicMock(return_value=interviewer_profile)
    return repo


@pytest.fixture
def mock_action_selector():
    selector = MagicMock()
    selector.select = MagicMock(
        return_value=ActionSelection(
            action=Action.QUESTION,
            reason="sampled_from_reactivity_matrix",
            distribution={"question": 1.0},
        )
    )
    return selector


@pytest.fixture
def mock_template_selector():
    selector = MagicMock()
    selector.select_template = MagicMock(
        return_value=TemplateSelection(
            template=make_template(Action.QUESTION, "question"),
            candidates_count=3,
            reason="selected_by_compatibility_position_frequency",
        )
    )
    return selector


@pytest.fixture
def mock_rag_service(rag_examples):
    service = MagicMock()
    service.search = MagicMock(return_value=rag_examples)
    return service


@pytest.fixture
def service(mock_llm_client, mock_profile_repository, mock_action_selector, mock_template_selector, mock_rag_service):
    return GenerateQuestionService(
        llm_client=cast(BaseLLMClient, mock_llm_client),
        profile_repository=mock_profile_repository,
        action_selector=mock_action_selector,
        template_selector=mock_template_selector,
        max_number_question=20,
        rag_service=mock_rag_service,
    )


class TestGenerateQuestion:
    @pytest.mark.asyncio
    async def test_returns_generation_response(self, service, simple_generation_request):
        result = await service.generate_question(simple_generation_request)
        assert isinstance(result, GenerationResponse)

    @pytest.mark.asyncio
    async def test_question_field_from_llm(self, service, simple_generation_request):
        result = await service.generate_question(simple_generation_request)
        assert result.question == "Как вы к этому пришли?"

    @pytest.mark.asyncio
    async def test_used_profile_matches_character_id(self, service, simple_generation_request):
        result = await service.generate_question(simple_generation_request)
        assert result.used_profile == "dud"

    @pytest.mark.asyncio
    async def test_profile_repository_called_with_character_id(self, service, simple_generation_request, mock_profile_repository):
        await service.generate_question(simple_generation_request)
        mock_profile_repository.get_profile.assert_called_once_with("dud")

    @pytest.mark.asyncio
    async def test_action_selector_called(self, service, simple_generation_request, mock_action_selector):
        await service.generate_question(simple_generation_request)
        mock_action_selector.select.assert_called_once()

    @pytest.mark.asyncio
    async def test_template_selector_called(self, service, simple_generation_request, mock_template_selector):
        await service.generate_question(simple_generation_request)
        mock_template_selector.select_template.assert_called_once()

    @pytest.mark.asyncio
    async def test_rag_service_called(self, service, simple_generation_request, mock_rag_service):
        await service.generate_question(simple_generation_request)
        mock_rag_service.search.assert_called_once()

    @pytest.mark.asyncio
    async def test_llm_client_called(self, service, simple_generation_request, mock_llm_client):
        await service.generate_question(simple_generation_request)
        mock_llm_client.generate_question.assert_called_once()


class TestExtractInterviewPosition:
    def test_zero_phrase_id_gives_zero(self, service):
        request = GenerationRequest(
            session_id="s", character_id="dud", user_name="X", user_info="X",
            last_answer="", full_interview_history=[], max_number_questions=20, phrase_id=0,
        )
        position = service.extract_interview_position(request)
        assert position == 0.0

    def test_mid_phrase_gives_mid_position(self, service):
        request = GenerationRequest(
            session_id="s", character_id="dud", user_name="X", user_info="X",
            last_answer="", full_interview_history=[], max_number_questions=20, phrase_id=10,
        )
        position = service.extract_interview_position(request)
        assert position == pytest.approx(0.5)

    def test_phrase_id_beyond_max_capped_at_one(self, service):
        request = GenerationRequest(
            session_id="s", character_id="dud", user_name="X", user_info="X",
            last_answer="", full_interview_history=[], max_number_questions=20, phrase_id=100,
        )
        position = service.extract_interview_position(request)
        assert position == 1.0

    def test_zero_max_number_returns_zero(self):
        svc = GenerateQuestionService(
            llm_client=cast(BaseLLMClient, AsyncMock()),
            profile_repository=MagicMock(),
            action_selector=MagicMock(),
            template_selector=MagicMock(),
            max_number_question=0,
            rag_service=MagicMock(),
        )
        request = GenerationRequest(
            session_id="s", character_id="dud", user_name="X", user_info="X",
            last_answer="", full_interview_history=[], max_number_questions=0, phrase_id=5,
        )
        position = svc.extract_interview_position(request)
        assert position == 0.0


class TestUpdateConsecutiveFollowups:
    def test_transition_resets_to_zero(self, service):
        result = service.update_consecutive_followups(3, Action.TRANSITION)
        assert result == 0

    def test_back_channel_resets_to_zero(self, service):
        result = service.update_consecutive_followups(2, Action.BACK_CHANNEL)
        assert result == 0

    def test_acknowledgment_resets_to_zero(self, service):
        result = service.update_consecutive_followups(1, Action.ACKNOWLEDGMENT)
        assert result == 0

    def test_question_increments(self, service):
        result = service.update_consecutive_followups(2, Action.QUESTION)
        assert result == 3

    def test_clarification_increments(self, service):
        result = service.update_consecutive_followups(0, Action.CLARIFICATION)
        assert result == 1


class TestExtractLastQuestion:
    def test_returns_last_interviewer_question_before_guest(self, service):
        history = [
            InterviewPart(role="interviewer", text="Первый вопрос?"),
            InterviewPart(role="guest", text="Первый ответ."),
            InterviewPart(role="interviewer", text="Второй вопрос?"),
            InterviewPart(role="guest", text="Второй ответ."),
        ]
        result = service.extract_last_question(history)
        assert result == "Второй вопрос?"

    @pytest.mark.asyncio
    async def test_consecutive_followups_reset_on_transition(
        self, mock_llm_client, mock_profile_repository, mock_rag_service, simple_generation_request
    ):
        transition_action_selector = MagicMock()
        transition_action_selector.select = MagicMock(
            return_value=ActionSelection(
                action=Action.TRANSITION,
                reason="forced",
                distribution={"transition": 1.0},
            )
        )
        transition_template_selector = MagicMock()
        transition_template_selector.select_template = MagicMock(
            return_value=TemplateSelection(
                template=make_template(Action.TRANSITION, "bridge+question"),
                candidates_count=1,
                reason="r",
            )
        )
        svc = GenerateQuestionService(
            llm_client=cast(BaseLLMClient, mock_llm_client),
            profile_repository=mock_profile_repository,
            action_selector=transition_action_selector,
            template_selector=transition_template_selector,
            max_number_question=20,
            rag_service=mock_rag_service,
        )
        request = simple_generation_request.model_copy(update={"consecutive_followups": 5})
        result = await svc.generate_question(request)
        assert result.consecutive_followups == 0
