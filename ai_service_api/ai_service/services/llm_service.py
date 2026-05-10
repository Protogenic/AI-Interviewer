from openai import AsyncOpenAI, BadRequestError
from typing import Protocol
import httpx
import json
import logging

from ai_service.exeptions.generation_error import GenerationError, LLMResponseError

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)

logger = logging.getLogger("app")


def _assemble_from_json(raw: str) -> str:
    text = (raw or "").strip()

    if text.startswith("```"):
        text = text.strip("`").strip()
        if text.lower().startswith("json"):
            text = text[4:].strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return raw.strip()

    parts = data.get("parts") if isinstance(data, dict) else None
    if not isinstance(parts, list):
        return raw.strip()

    pieces = []
    for p in parts:
        if isinstance(p, dict):
            content = p.get("content")
            if isinstance(content, str) and content.strip():
                pieces.append(content.strip())

    return " ".join(pieces) if pieces else raw.strip()


class BaseLLMClient(Protocol):
    async def generate_question(self, system_prompt: str, user_prompt: str) -> str:
        ...

class OpenAILLMClient:
    def __init__(
        self,
        api_key: str | None = None,
        model: str = "gpt-4o-mini",
        temperature: float = 0.7,
        max_tokens: int = 500,
    ) -> None:
        if api_key:
            self.__client = AsyncOpenAI(api_key=api_key)
        else:
            self.__client = AsyncOpenAI()

        self.__model = model
        self.__temperature = temperature
        self.__max_tokens = max_tokens


    async def generate_question(self, system_prompt: str, user_prompt: str) -> str:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        logger.info("PROMPT: %s", messages)
        logger.info("MODEL: %s", self.__model)
        logger.info("TEMP: %s", self.__temperature)

        try:
            response = await self.__client.chat.completions.create(
                model=self.__model,
                messages=messages,
                temperature=self.__temperature,
                response_format={"type": "json_object"},
            )
            raw_question = response.choices[0].message.content or ""
            question =  _assemble_from_json(raw_question)
            return question
        except LLMResponseError:
            raise
        except BadRequestError as e:
            raise GenerationError(f"OpenAI bad request: {e}") from e
        except Exception as e:
            raise LLMResponseError(f"OpenAI generation failed: {e}") from e


class OllamaLLMClient:
    def __init__(self,
                 model: str = "qwen2.5:7b-instruct",
                 base_url: str = "http://localhost:11434/v1",
                 temperature: float = 0.7,
                 max_tokens: int = 150,
                 ) -> None:
        self.__model = model
        self.__base_url = base_url.rstrip("/")
        self.__temperature = temperature
        self.__max_tokens = max_tokens

    async def generate_question(self, system_prompt: str, user_prompt: str) -> str:
        url = f"{self.__base_url}/api/chat"

        payload = {
            "model": self.__model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "format": "json",
            "options": {
                "temperature": self.__temperature,
                "num_predict": self.__max_tokens,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
            raw = data["message"]["content"].strip()
            return _assemble_from_json(raw)

        except httpx.HTTPStatusError as e:
            raise GenerationError(
                f"Ollama HTTP error: {e.response.status_code} {e.response.text}"
            ) from e
        except Exception as e:
            raise LLMResponseError(f"Ollama generation failed: {e}") from e


class OpenRouterLLMClient:
    def __init__(
        self,
        api_key: str,
        model: str = "deepseek/deepseek-chat:free",
        base_url: str = "https://openrouter.ai/api/v1",
        temperature: float = 0.7,
        max_tokens: int = 500,
    ) -> None:
        self.__client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
        )
        self.__model = model
        self.__temperature = temperature
        self.__max_tokens = max_tokens

    async def generate_question(self, system_prompt: str, user_prompt: str) -> str:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        logger.info("PROVIDER: openrouter")
        logger.info("MODEL: %s", self.__model)
        logger.info("TEMP: %s", self.__temperature)

        request_kwargs: dict = {
            "model": self.__model,
            "messages": messages,
            "temperature": self.__temperature,
            "max_tokens": self.__max_tokens,
            "response_format": {"type": "json_object"},
        }

        try:
            response = await self.__client.chat.completions.create(**request_kwargs)
            raw_question = response.choices[0].message.content or ""
            if not raw_question.strip():
                raise LLMResponseError("OpenRouter returned an empty message content")
            return _assemble_from_json(raw_question)
        except LLMResponseError:
            raise
        except BadRequestError as e:
            raise GenerationError(f"OpenRouter bad request: {e}") from e
        except Exception as e:
            raise LLMResponseError(f"OpenRouter generation failed: {e}") from e