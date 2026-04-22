from pydantic import BaseModel
from typing import List


class InterviewPart(BaseModel):
    role: str
    text: str


class GenerationRequest(BaseModel):
    session_id: str
    character_id: str
    user_name: str
    user_info: str
    last_answer: str = ""
    full_interview_history: List[InterviewPart]
    max_number_questions: int
    phrase_id: int = 1
    previous_template_id: str | None = None
    consecutive_followups: int = 0


class GenerationResponse(BaseModel):
    question: str
    used_profile: str
    used_template_id: str
    consecutive_followups: int


class BuildPromptResult(BaseModel):
    prompt: str
    style_instruction: List[str]

