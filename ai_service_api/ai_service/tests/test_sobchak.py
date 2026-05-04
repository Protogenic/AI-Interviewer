import pytest
from httpx import ASGITransport, AsyncClient
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from ai_service.main import app

@pytest.mark.asyncio
async def test_1() -> None:
    transport_app = ASGITransport(app=app)

    async with AsyncClient(transport=transport_app, base_url="http://test") as client:
        response = await client.post(
            "/api/generation/generate_question",
            json={
                "session_id": "session_001",
                "character_id": "sobchak",
                "user_name": "Иван",
                "user_info": "работаю тестироващиком",
                "full_interview_history": [],
                "max_number_questions": 20,
                "phrase_id": 1,
                "previous_template_id": "text",
                "consecutive_followups": 0
            }
        )

    #print(response.status_code)
    print(response.json())

    assert response.status_code == 200
    data = response.json()
    assert "question" in data
    assert data["used_profile"] == "sobchak"