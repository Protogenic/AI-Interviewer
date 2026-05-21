"""Pydantic-модели для запросов и ответов генерации вопросов интервью."""

from pydantic import BaseModel
from typing import List


class InterviewPart(BaseModel):
    """Реплика в формате: роль (interviewer / guest) и текст."""

    role: str
    text: str


class GenerationRequest(BaseModel):
    """Входные данные для генерации очередного вопроса интервьюера."""

    session_id: str
    character_id: str
    user_name: str
    user_info: str
    interview_topic: str = ""
    last_answer: str = ""
    full_interview_history: List[InterviewPart]
    max_number_questions: int
    phrase_id: int = 1
    previous_template_id: str | None = None
    consecutive_followups: int = 0


class GenerationResponse(BaseModel):
    """Результат генерации: вопрос и данные о выборе шаблона."""

    question: str
    used_profile: str
    used_template_id: str
    consecutive_followups: int


class BuildPromptResult(BaseModel):
    """Результат сборки промпта: текст и список инструкций по стилю."""

    prompt: str
    style_instruction: List[str]

