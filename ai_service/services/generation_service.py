from ai_service.pydantic_schemas.generation import GenerationRequest, GenerationResponse
from ai_service.services.llm_service import DummyLLMClient
from ai_service.services.build_prompt_service import BuildPromptService
from ai_service.exeptions.generation_error import CharacterNotFound

class GenerateQuestionService:
    def __init__(self, llm_client: DummyLLMClient, interview_characters: set[str]) -> None:
        self.__llm_client = llm_client
        self.__interview_characters = interview_characters


    async def generate_question(self, input_data: GenerationRequest):
        if input_data.character_id not in self.__interview_characters:
            raise CharacterNotFound(input_data.character_id)

        prompt_builder = BuildPromptService()
        prompt = prompt_builder.build_prompt(input_data)
        generate_question = await self.__llm_client.generate_question(prompt)

        output_response = GenerationResponse(question=generate_question, used_profile=input_data.character_id)

        return  output_response