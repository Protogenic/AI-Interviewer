from fastapi import APIRouter, HTTPException, status

from ai_service.pydantic_schemas.generation import GenerationRequest, GenerationResponse
from ai_service.services.generation_service import GenerateQuestionService
from ai_service.services.llm_service import DummyLLMClient
from ai_service.exeptions.generation_error import CharacterNotFound


router = APIRouter(
    prefix = "/generation",
    tags = ["generation"]
)


@router.post("/generate_question", response_model=GenerationResponse, status_code=status.HTTP_200_OK)
async def get_generate_question(input_data: GenerationRequest) -> GenerationResponse:
    generation_service = GenerateQuestionService(DummyLLMClient(), {"dud", "sobchak"})
    try:
        generated_question = await generation_service.generate_question(input_data)
    except CharacterNotFound as chnf:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(chnf)) from chnf
    return generated_question