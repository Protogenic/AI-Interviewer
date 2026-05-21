"""Pydantic-модели профиля интервьюера: лингвистика, шаблоны, персона."""

from pydantic import BaseModel, Field
from typing import Any, Dict, List

from ai_service.offline_pipeline.categories import Action, QuestionOpenness, Emotion, AnswerType, Technique, ComponentType


class LinguisticProfile(BaseModel):
    """Числовые характеристики речевого стиля интервьюера."""

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
    """Реплика диалога с ролью и порядковым номером."""

    role: str
    text: str
    replica_id: int


class AnnotatedPhrase(Phrase):
    """Реплика с разметкой действия, эмоции и типа ответа."""

    interview_id: str
    action: Action = None
    question_openness: QuestionOpenness = None
    emotion: Emotion = None
    techniques: list[Technique] = Field(default_factory=list)
    answer_type: AnswerType = None

    def to_dict(self) -> Dict[str, Any]:
        data = self.model_dump()
        return data


class Component(BaseModel):
    """Компонент составной реплики."""

    type: ComponentType
    text: str


class Template(BaseModel):
    """Шаблон реплики интервьюера с параметрами действия, эмоции и позиции."""

    structure: str
    frequency: int
    action: str
    question_openness: str
    emotion: str
    techniques: List[Technique]
    avg_position: float
    reactivity: List[str]
    examples: List[str]


class InterviewerProfile(BaseModel):
    """Полный профиль интервьюера: лингвистика, матрица реактивности, шаблоны."""

    interviewer_id: str
    linguistic_profile: LinguisticProfile
    reactivity_matrix: Dict[str, Dict[str, int]]
    templates: List[Template]
    characteristic_phrases: List[str]

    def to_dict(self) -> Dict[str, Any]:
        data = self.model_dump()
        return data
