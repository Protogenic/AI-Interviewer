import pytest
from httpx import ASGITransport, AsyncClient
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

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
    assert data["used_profile"] == "dud"


@pytest.mark.asyncio
async def test_generate_question_404() -> None:
    transport_app = ASGITransport(app=app)

    async with AsyncClient(transport=transport_app, base_url="http://test") as client:
        response = await client.post(
            "/api/generation/generate_question",
            json={
                "session_id": "session_001",
                "character_id": "sobchaki",
                "user_name": "Иван",
                "user_info": "работаю программистом",
                "last_answer": "я программист",
                "full_interview_history": [],
                "max_number_questions": 20
            }
        )

    #print(response.status_code)
    print(response.json())

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
                "full_interview_history": [],
                "max_number_questions": 20
            }
        )

    #print(response.status_code)
    print(response.json())

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_generate_question_consecutive() -> None:
    transport_app = ASGITransport(app=app)

    async with AsyncClient(transport=transport_app, base_url="http://test") as client:
        response = await client.post(
            "/api/generation/generate_question",
            json={
                "session_id": "session_001",
                "character_id": "dud",
                "user_name": "Иван",
                "user_info": "работаю тестироващиком",
                "last_answer": "я программист",
                "full_interview_history": [],
                "max_number_questions": 20,
                "phrase_id": 1,
                "previous_template_id": "text",
                "consecutive_followups": 1
            }
        )

    #print(response.status_code)
    print(response.json())

    assert response.status_code == 200
    data = response.json()
    assert "question" in data
    assert data["consecutive_followups"] == 2


@pytest.mark.asyncio
async def test_generate_question_rag() -> None:
    transport_app = ASGITransport(app=app)

    async with AsyncClient(transport=transport_app, base_url="http://test") as client:
        response = await client.post(
            "/api/generation/generate_question",
            json={
                "session_id": "session_001",
                "character_id": "dud",
                "user_name": "Катя",
                "user_info": "работаю тестироващиком",
                "last_answer": "словила выгорание недавно",
                "full_interview_history": [
                    {
                      "role": "interviewer",
                      "text": "Как давно вы работаете программистом?."
                    },
                    {
                      "role": "user",
                      "text": "Я занимаюсь разработкой больше 10 лет."
                    },
                    {
                      "role": "interviewer",
                      "text": "Работа ещё не надоела?"
                    },
                    {
                        "role": "user",
                        "text": "Словила выгорание недавно"
                    }
                ],
                "max_number_questions": 20,
                "phrase_id": 1,
                "previous_template_id": "text",
                "consecutive_followups": 1
            }
        )

    #print(response.status_code)
    print(response.json())

    assert response.status_code == 200
    data = response.json()
    assert "question" in data


@pytest.mark.asyncio
async def test_generate_question_2() -> None:
    transport_app = ASGITransport(app=app)

    async with AsyncClient(transport=transport_app, base_url="http://test") as client:
        response = await client.post(
            "/api/generation/generate_question",
            json={
                "session_id": "session_001",
                "character_id": "dud",
                "user_name": "Иван",
                "user_info": "Я пишу музыку",
                "last_answer": "т",
                "full_interview_history": [],
                "max_number_questions": 5,
                "phrase_id": 1,
                "previous_template_id": "",
                "consecutive_followups": 0
            }
        )

    #print(response.status_code)
    print(response.json())

    assert response.status_code == 200
    data = response.json()
    assert "question" in data