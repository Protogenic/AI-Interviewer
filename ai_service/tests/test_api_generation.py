import pytest
from httpx import ASGITransport, AsyncClient

from ai_service.main import app

@pytest.mark.asyncio
async def test_generate_question_success() -> None:
    transport_app = ASGITransport(app=app)

    async with AsyncClient(transport=transport_app, base_url="http://test") as client:
        response = await client.post(
            "/api/generation/generate_question",
            json={
                "session_id": "session_001",
                "character_id": "dud",
                "user_name": "Иван",
                "user_info": "работаю программистом",
                "last_answer": "я программист",
                "full_interview_history": []
            }
        )

    assert response.status_code == 200
    data = response.json()
    assert "question" in data
    assert data["used_profile"] == "dud"


@pytest.mark.asyncio
async def test_generate_question_404() -> None:
    transport_app = ASGITransport(app=app)

    async with AsyncClient(transport=transport_app, base_url="http://test") as client:
        response = await client.post(
            "/api/generation/generate_question",
            json={
                "session_id": "session_001",
                "character_id": "pozner",
                "user_name": "Иван",
                "user_info": "работаю программистом",
                "last_answer": "я программист",
                "full_interview_history": []
            }
        )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_generate_question_422() -> None:
    transport_app = ASGITransport(app=app)

    async with AsyncClient(transport=transport_app, base_url="http://test") as client:
        response = await client.post(
            "/api/generation/generate_question",
            json={
                "session_id": "session_001",
                "character_id": "pozner",
                "user_name": "Иван",
                "user_info": None,
                "last_answer": "я программист",
                "full_interview_history": []
            }
        )

    assert response.status_code == 422