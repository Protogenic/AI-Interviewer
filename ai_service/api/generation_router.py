from fastapi import APIRouter

from ai_service.pydantic_schemas.generation import GenerationRequest, GenerationResponse


router = APIRouter(
    prefix = "/generation",
    tags = ["generation"]
)


@router.post("/generation") #response_model=GenerationResponse
async def generate_question(input_data: GenerationRequest) -> str: #GenerationResponse
    #generation_service = get_generation_service()
    #generated_question = await generation_service.generate(input_data)
    generated_question = "str"
    return generated_question