from pydantic import BaseModel
from typing import Any, Dict, List

from ai_service.offline_pipeline.categories import Action, QuestionOpenness, Emotion, AnswerType, Technique, ComponentType

class LinguisticProfile(BaseModel):
    empathy_density: float = 0.0
    hedging_density: float = 0.0
    pressure_density: float = 0.0
    filler_density: float = 0.0
    formal_density: float = 0.0
    provocation_density: float = 0.0

    avg_question_length: float = 0.0
    avg_phrase_length: float = 0.0
    multi_sentence_ratio: float = 0.0
    number_of_questions: float = 0.0


class Phrase(BaseModel):
    role: str
    text: str
    replica_id: int


class AnnotatedPhrase(Phrase):
    action: Action = None
    question_openness: QuestionOpenness = None
    emotion: Emotion = None
    technique: Technique = None
    answer_type: AnswerType = None

    def to_dict(self) -> Dict[str, Any]:
        data = self.model_dump()
        return data


class Component(BaseModel):
    type: ComponentType
    text: str


class Template(BaseModel):
    structure: str
    frequency: int
    action: str
    question_openness: str
    emotion: str
    technique: str
    avg_position: float
    reactivity: List[str]
    examples: List[str]


class InterviewerProfile(BaseModel):
    interviewer_id: str
    linguistic_profile: LinguisticProfile
    reactivity_matrix: Dict[str, Dict[str, int]]
    templates: List[Template]
    characteristic_phrases: List[str]

    def to_dict(self) -> Dict[str, Any]:
        data = self.model_dump()
        return data
