from pydantic import BaseModel, Field


class Voice(BaseModel):
    id: str
    name: str
    description: str = ""
    language: str = "ru"


class VoicesResponse(BaseModel):
    voices: list[Voice]


class SynthesizeRequest(BaseModel):
    text: str = Field(min_length=1, max_length=5000)
    voice_id: str
