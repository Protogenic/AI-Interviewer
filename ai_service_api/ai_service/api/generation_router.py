from fastapi import APIRouter, HTTPException, status

from ai_service.models.generation import GenerationRequest, GenerationResponse
from ai_service.services.generation_service import GenerateQuestionService
from ai_service_api.ai_service.services.profile_repository import GetProfileInfo
from ai_service_api.ai_service.services.llm_factory import create_llm_client
from ai_service_api.ai_service.selection.template_selector import TemplateSelector
from ai_service_api.ai_service.selection.action_selector import ActionSelector
from ai_service.exeptions.generation_error import CharacterNotFound


router = APIRouter(
    prefix = "/generation",
    tags = ["generation"]
)

llm_client = create_llm_client()
profile_repository = GetProfileInfo()


@router.post("/generate_question", response_model=GenerationResponse, status_code=status.HTTP_200_OK)
async def get_generate_question(input_data: GenerationRequest) -> GenerationResponse:
    ch_id = input_data.character_id
    max_number_q = input_data.max_number_questions

    action_selector = ActionSelector(profile_repository.get_reactivity_matrix(ch_id), 3, 42)
    template_selector = TemplateSelector(profile_repository.get_templates(ch_id), 3, 42)

    generation_service = GenerateQuestionService(
        llm_client=llm_client,
        interview_characters={"dud", "sobchak", "pozner"},
        profile_repository=profile_repository,
        action_selector=action_selector,
        template_selector=template_selector,
        max_number_question=max_number_q
    )

    try:
        generated_question = await generation_service.generate_question(input_data)
    except CharacterNotFound as chnf:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(chnf)) from chnf
    return generated_question