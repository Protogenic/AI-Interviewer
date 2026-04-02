from openai import AsyncOpenAI, BadRequestError
from typing import Protocol

from ai_service.exeptions.generation_error import GenerationError


class BaseLLMClient(Protocol):
    async def generate_question(self, prompt: str) -> str:
        ...


class DummyLLMClient:
    async def generate_question(self, prompt: str) -> str:
        return "Как давно ты занимаешься программированием?"


class OpenAILLMClient:
    def __init__(self,
                 api_key: str | None = None,
                 model: str = "gpt-4o-mini",
                 temperature: float = 0.7,
                 max_tokens: int = 150,
                 ) -> None:
        if api_key:
            self.__client = AsyncOpenAI(api_key=api_key)
        else:
            self.__client = AsyncOpenAI()

        self.__model = model
        self.__temperature = temperature
        self.__max_tokens = max_tokens


    async def generate_question(self, prompt: str) -> str:
        messages = [
            {
                "role": "system",
                "content": (
                    "Ты - интервьюер Юрий Дудь."
                    "Сгенерируй ровно одно естественное высказывание (или вопрос) "
                    "в стиле Юрия Дудя для интервью с пользователем."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ]

        try:
            response = await self.__client.responses.create(
                model=self.__model,
                input=messages,
                temperature=self.__temperature,
                max_output_tokens=self.__max_tokens,
            )
            return response.output_text.strip()

        except BadRequestError as e:
            raise GenerationError(f"OpenAI bad request: {e}") from e
        except Exception as e:
            raise GenerationError(f"OpenAI generation failed: {e}") from e


class OllamaLLMClient:
    def __init__(self,
                 api_key: str = "ollama",
                 model: str = "qwen2.5:7b-instruct",
                 base_url: str = "http://localhost:11434/v1",
                 temperature: float = 0.7,
                 max_tokens: int = 150,
                 ) -> None:
        self.__client = AsyncOpenAI(
            base_url=base_url,
            api_key=api_key,
        )
        self.__model = model
        self.__temperature = temperature
        self.__max_tokens = max_tokens


    async def generate_question(self, prompt: str) -> str:
        messages = [
            {
                "role": "system",
                "content": (
                    "Ты - интервьюер Юрий Дудь."
                    "Сгенерируй ровно одно естественное высказывание (или вопрос) "
                    "в стиле Юрия Дудя для интервью с пользователем."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ]

        try:
            response = await self.__client.responses.create(
                model=self.__model,
                input=messages,
                temperature=self.__temperature,
                max_output_tokens=self.__max_tokens,
            )
            return response.output_text.strip()

        except BadRequestError as e:
            raise GenerationError(f"OpenAI bad request: {e}") from e
        except Exception as e:
            raise GenerationError(f"OpenAI generation failed: {e}") from e


