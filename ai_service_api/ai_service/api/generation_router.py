"""FastAPI-роутер для эндпоинта генерации вопроса интервьюера."""

from fastapi import APIRouter, HTTPException, status

from ai_service.models.generation import GenerationRequest, GenerationResponse
from ai_service.services.generation_service import GenerateQuestionService
from ai_service.services.profile_repository import GetProfileInfo
from ai_service.services.llm_factory import create_llm_client
from ai_service.selection.template_selector import TemplateSelector
from ai_service.selection.action_selector import ActionSelector
from ai_service.services.rag_service import OnlineRagSearchService
from ai_service.models.rag import RagIndexConfig
from ai_service.exeptions.generation_error import (
    CharacterNotFound,
    ProfileLoadError,
    RagIndexNotFoundError,
    RagSearchError,
    EmbeddingModelError,
    TemplateSelectionError,
    UnknownInterviewerError,
    LLMConfigurationError,
    LLMResponseError,
    GenerationError,
)

router = APIRouter(
    prefix = "/generation",
    tags = ["generation"]
)

llm_client = create_llm_client()
profile_repository = GetProfileInfo()

INTERVIEW_CHARACTERS = {"dud", "sobchak", "pozner"}

_rag_service_cache: dict[str, OnlineRagSearchService] = {}
_action_selector_cache: dict[str, ActionSelector] = {}
_template_selector_cache: dict[str, TemplateSelector] = {}


def _get_rag_service(character_id: str) -> OnlineRagSearchService:
    if character_id not in _rag_service_cache:
        rag_config = RagIndexConfig.for_character(character_id=character_id)
        _rag_service_cache[character_id] = OnlineRagSearchService(config=rag_config)
    return _rag_service_cache[character_id]


def _get_action_selector(character_id: str) -> ActionSelector:
    if character_id not in _action_selector_cache:
        _action_selector_cache[character_id] = ActionSelector(
            profile_repository.get_reactivity_matrix(character_id), 2, 42
        )
    return _action_selector_cache[character_id]


def _get_template_selector(character_id: str) -> TemplateSelector:
    if character_id not in _template_selector_cache:
        _template_selector_cache[character_id] = TemplateSelector(
            profile_repository.get_templates(character_id), 3, 42
        )
    return _template_selector_cache[character_id]


@router.post("/generate_question", response_model=GenerationResponse, status_code=status.HTTP_200_OK)
async def get_generate_question(input_data: GenerationRequest) -> GenerationResponse:
    """Генерирует следующий вопрос интервьюера по истории диалога и профилю персонажа."""
    ch_id = input_data.character_id
    max_number_q = input_data.max_number_questions

    if input_data.character_id not in INTERVIEW_CHARACTERS:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    try:
        rag_service = _get_rag_service(ch_id)
        action_selector = _get_action_selector(ch_id)
        template_selector = _get_template_selector(ch_id)

        generation_service = GenerateQuestionService(
            llm_client=llm_client,
            profile_repository=profile_repository,
            action_selector=action_selector,
            template_selector=template_selector,
            max_number_question=max_number_q,
            rag_service=rag_service
        )

        generated_question = await generation_service.generate_question(input_data)
    except CharacterNotFound as chnf:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(chnf)) from chnf
    except (RagIndexNotFoundError, EmbeddingModelError) as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e)) from e
    except LLMConfigurationError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)) from e
    except LLMResponseError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e)) from e
    except (RagSearchError, TemplateSelectionError, UnknownInterviewerError, ProfileLoadError) as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)) from e
    except GenerationError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)) from e
    return generated_question