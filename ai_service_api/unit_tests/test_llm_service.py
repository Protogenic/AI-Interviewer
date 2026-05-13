import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from ai_service.services.llm_service import (
    _assemble_from_json,
    OpenAILLMClient,
    OpenRouterLLMClient,
    OllamaLLMClient,
)
from ai_service.exeptions.generation_error import LLMResponseError


class TestAssembleFromJson:
    def test_valid_json_single_part(self):
        raw = json.dumps({"parts": [{"role": "question", "content": "Как так вышло?"}]})
        assert _assemble_from_json(raw) == "Как так вышло?"

    def test_valid_json_multiple_parts(self):
        raw = json.dumps({
            "parts": [
                {"role": "acknowledgment", "content": "Понимаю."},
                {"role": "question", "content": "А что дальше?"},
            ]
        })
        result = _assemble_from_json(raw)
        assert "Понимаю." in result
        assert "А что дальше?" in result

    def test_strips_markdown_code_block(self):
        raw = "```json\n" + json.dumps({"parts": [{"role": "question", "content": "Вопрос?"}]}) + "\n```"
        result = _assemble_from_json(raw)
        assert "Вопрос?" in result


class TestOpenAILLMClient:
    @pytest.mark.asyncio
    async def test_generate_question_returns_string(self):
        client = OpenAILLMClient(api_key="fake-key")
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content=json.dumps({
            "parts": [{"role": "question", "content": "Почему вы здесь?"}]
        })))]

        with patch.object(client._client.chat.completions, "create", new=AsyncMock(return_value=mock_response)):
            result = await client.generate_question("system prompt", "user prompt")
        assert result == "Почему вы здесь?"

    @pytest.mark.asyncio
    async def test_raises_llm_response_error_on_empty_content(self):
        client = OpenAILLMClient(api_key="fake-key")
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content=""))]

        with patch.object(client._client.chat.completions, "create", new=AsyncMock(return_value=mock_response)):
            with pytest.raises(LLMResponseError):
                await client.generate_question("sys", "usr")

    @pytest.mark.asyncio
    async def test_raises_llm_response_error_on_generic_exception(self):
        client = OpenAILLMClient(api_key="fake-key")
        with patch.object(
            client._client.chat.completions, "create",
            new=AsyncMock(side_effect=RuntimeError("network error"))
        ):
            with pytest.raises(LLMResponseError):
                await client.generate_question("sys", "usr")


class TestOpenRouterLLMClient:
    @pytest.mark.asyncio
    async def test_generate_question_returns_string(self):
        client = OpenRouterLLMClient(api_key="fake-key")
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content=json.dumps({
            "parts": [{"role": "question", "content": "Почему вы здесь?"}]
        })))]

        with patch.object(client._client.chat.completions, "create", new=AsyncMock(return_value=mock_response)):
            result = await client.generate_question("system prompt", "user prompt")
        assert result == "Почему вы здесь?"

    @pytest.mark.asyncio
    async def test_raises_llm_response_error_on_empty_content(self):
        client = OpenRouterLLMClient(api_key="fake-key")
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content=""))]

        with patch.object(client._client.chat.completions, "create", new=AsyncMock(return_value=mock_response)):
            with pytest.raises(LLMResponseError):
                await client.generate_question("sys", "usr")

    @pytest.mark.asyncio
    async def test_raises_llm_response_error_on_generic_exception(self):
        client = OpenRouterLLMClient(api_key="fake-key")
        with patch.object(
            client._client.chat.completions, "create",
            new=AsyncMock(side_effect=RuntimeError("network error"))
        ):
            with pytest.raises(LLMResponseError):
                await client.generate_question("sys", "usr")


class TestOllamaLLMClient:
    @pytest.mark.asyncio
    async def test_generate_question_returns_string(self):
        client = OllamaLLMClient()
        response_data = {"message": {"content": json.dumps({
            "parts": [{"role": "question", "content": "Как вы к этому пришли?"}]
        })}}

        mock_response = MagicMock()
        mock_response.json.return_value = response_data
        mock_response.raise_for_status = MagicMock()

        mock_http_client = AsyncMock()
        mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
        mock_http_client.__aexit__ = AsyncMock(return_value=False)
        mock_http_client.post = AsyncMock(return_value=mock_response)

        with patch("ai_service.services.llm_service.httpx.AsyncClient", return_value=mock_http_client):
            result = await client.generate_question("sys", "usr")
        assert result == "Как вы к этому пришли?"

    @pytest.mark.asyncio
    async def test_raises_on_missing_message_content(self):
        client = OllamaLLMClient()
        response_data = {"message": {}}

        mock_response = MagicMock()
        mock_response.json.return_value = response_data
        mock_response.raise_for_status = MagicMock()

        mock_http_client = AsyncMock()
        mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
        mock_http_client.__aexit__ = AsyncMock(return_value=False)
        mock_http_client.post = AsyncMock(return_value=mock_response)

        with patch("ai_service.services.llm_service.httpx.AsyncClient", return_value=mock_http_client):
            with pytest.raises(LLMResponseError):
                await client.generate_question("sys", "usr")