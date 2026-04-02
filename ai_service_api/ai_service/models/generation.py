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
    last_answer: str
    full_interview_history: List[InterviewPart]


class GenerationResponse(BaseModel):
    question: str
    used_profile: str


class BuildPromptResult(BaseModel):
    prompt: str
    style_instruction: List[str]
    example_used: int
