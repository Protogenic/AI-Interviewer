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


@router.post("/generate_question", response_model=GenerationResponse, status_code=status.HTTP_200_OK)
async def get_generate_question(input_data: GenerationRequest) -> GenerationResponse:
    ch_id = input_data.character_id
    max_number_q = input_data.max_number_questions

    if input_data.character_id not in INTERVIEW_CHARACTERS:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    try:
        rag_config = RagIndexConfig.for_character(character_id=input_data.character_id)
        rag_service = OnlineRagSearchService(config=rag_config)
        action_selector = ActionSelector(profile_repository.get_reactivity_matrix(ch_id), 2, 42)
        template_selector = TemplateSelector(profile_repository.get_templates(ch_id), 3, 42)

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