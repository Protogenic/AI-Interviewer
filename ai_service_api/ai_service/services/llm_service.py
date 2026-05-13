from openai import AsyncOpenAI, BadRequestError
from typing import Protocol
import asyncio
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
    import re

    text = (raw or "").strip()

    if text.startswith("```"):
        text = text.strip("`").strip()
        if text.lower().startswith("json"):
            text = text[4:].strip()

    try:
        data = json.loads(text)
        parts = data.get("parts") if isinstance(data, dict) else None
        if isinstance(parts, list):
            pieces = [
                p["content"].strip()
                for p in parts
                if isinstance(p, dict)
                and isinstance(p.get("content"), str)
                and p["content"].strip()
            ]
            if pieces:
                return " ".join(pieces)
        return raw.strip()
    except json.JSONDecodeError:
        pass

    matches = re.findall(r'"content"\s*:\s*"((?:[^"\\]|\\.)*)"', text)
    if matches:
        return " ".join(m.strip() for m in matches if m.strip())

    return raw.strip()


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
            self._client = AsyncOpenAI(api_key=api_key)
        else:
            self._client = AsyncOpenAI()

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
            response = await self._client.chat.completions.create(
                model=self.__model,
                messages=messages,
                temperature=self.__temperature,
                response_format={"type": "json_object"},
            )
            raw_question = response.choices[0].message.content or ""
            if not raw_question.strip():
                raise LLMResponseError("OpenAI returned empty message content")
            question = _assemble_from_json(raw_question)
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
        model: str = "mistralai/mistral-small-3.1-24b-instruct",
        base_url: str = "https://openrouter.ai/api/v1",
        temperature: float = 0.7,
        max_tokens: int = 500,
        max_retries: int = 3,
        retry_base_delay: float = 1.0,
    ) -> None:
        self._client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
        )
        self.__model = model
        self.__temperature = temperature
        self.__max_tokens = max_tokens
        self.__max_retries = max_retries
        self.__retry_base_delay = retry_base_delay

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

        last_exc: Exception | None = None

        for attempt in range(self.__max_retries + 1):
            try:
                response = await self._client.chat.completions.create(**request_kwargs)
                raw_question = response.choices[0].message.content or ""
                if not raw_question.strip():
                    raise LLMResponseError("OpenRouter returned an empty message content")
                return _assemble_from_json(raw_question)
            except BadRequestError as e:
                raise GenerationError(f"OpenRouter bad request: {e}") from e
            except Exception as e:
                last_exc = e
                if attempt < self.__max_retries:
                    delay = self.__retry_base_delay * (2 ** attempt)
                    logger.warning(
                        "OpenRouter attempt %d/%d failed, retrying in %.1fs: %s",
                        attempt + 1, self.__max_retries + 1, delay, e,
                    )
                    await asyncio.sleep(delay)

        if isinstance(last_exc, GenerationError):
            raise last_exc
        raise LLMResponseError(
            f"OpenRouter generation failed after {self.__max_retries + 1} attempts: {last_exc}"
        ) from last_exc