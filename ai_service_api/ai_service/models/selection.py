"""Pydantic-модели результатов выбора действия и шаблона."""

from pydantic import BaseModel
from typing import Dict

from ai_service.offline_pipeline.categories import Action
from ai_service.models.build_profile import Template


class ActionSelection(BaseModel):
    """Результат выбора действия интервьюера с распределением вероятностей."""

    action: Action
    reason: str
    distribution: Dict[str, float]


class TemplateSelection(BaseModel):
    """Результат выбора шаблона реплики с количеством рассмотренных кандидатов."""

    template: Template
    candidates_count: int
    reason: str
