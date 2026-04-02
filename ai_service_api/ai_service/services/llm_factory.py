from ai_service_api.ai_service.core.settings import (
    LLM_PROVIDER,
    OPENAI_API_KEY,
    OPENAI_MODEL,
    OLLAMA_BASE_URL,
    OLLAMA_API_KEY,
    OLLAMA_MODEL,
    LLM_TEMPERATURE,
    LLM_MAX_TOKENS,
)
from ai_service.services.llm_service import (
    DummyLLMClient,
    OpenAILLMClient,
    OllamaLLMClient,
)


def create_llm_client():
    if LLM_PROVIDER == "openai":
        return OpenAILLMClient(
            api_key=OPENAI_API_KEY,
            model=OPENAI_MODEL,
            temperature=LLM_TEMPERATURE,
            max_tokens=LLM_MAX_TOKENS,
        )

    if LLM_PROVIDER == "ollama":
        return OllamaLLMClient(
            model=OLLAMA_MODEL,
            base_url=OLLAMA_BASE_URL,
            api_key=OLLAMA_API_KEY,
            temperature=LLM_TEMPERATURE,
            max_tokens=LLM_MAX_TOKENS,
        )

    return DummyLLMClient()