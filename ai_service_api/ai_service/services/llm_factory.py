from ai_service.core import settings
from ai_service.services.llm_service import (
    OpenAILLMClient,
    OllamaLLMClient,
    OpenRouterLLMClient,
)
from ai_service.exeptions.generation_error import LLMConfigurationError


def create_llm_client():
    if settings.LLM_PROVIDER == "openai":
        if not settings.OPENAI_API_KEY:
            raise LLMConfigurationError(
                provider=f"{settings.LLM_PROVIDER} (missing env OPENROUTER_API_KEY)"
            )
        return OpenAILLMClient(
            api_key=settings.OPENAI_API_KEY,
            model=settings.OPENAI_MODEL,
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS,
        )

    if settings.LLM_PROVIDER == "ollama":
        return OllamaLLMClient(
            model=settings.OLLAMA_MODEL,
            base_url=settings.OLLAMA_BASE_URL,
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS,
        )

    if settings.LLM_PROVIDER == "openrouter":
        if not settings.OPENROUTER_API_KEY:
            raise LLMConfigurationError(
                provider=f"{settings.LLM_PROVIDER} (missing env OPENROUTER_API_KEY)"
            )
        return OpenRouterLLMClient(
            api_key=settings.OPENROUTER_API_KEY,
            base_url=settings.OPENROUTER_BASE_URL,
            model=settings.OPENROUTER_MODEL,
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS,
        )

    raise LLMConfigurationError(provider=settings.LLM_PROVIDER)