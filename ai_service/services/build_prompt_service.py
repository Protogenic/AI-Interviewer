from ai_service.pydantic_schemas.generation import GenerationRequest
from ai_service.services.llm_service import DummyLLMClient

class BuildPromptService:

    def build_prompt(self, input_data: GenerationRequest):
        # Будет прописана логика формирования промпта
        prompt = f"Character: {input_data.character_id}, History: {input_data.full_interview_history}"
        return prompt