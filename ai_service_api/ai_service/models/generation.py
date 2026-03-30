from pydantic import BaseModel

class InterviewPart(BaseModel):
    role: str
    text: str


class GenerationRequest(BaseModel):
    session_id: str
    character_id: str
    user_name: str
    user_info: str
    last_answer: str
    full_interview_history: list[InterviewPart]


class GenerationResponse(BaseModel):
    question: str
    used_profile: str
