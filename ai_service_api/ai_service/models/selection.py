from pydantic import BaseModel
from typing import Dict

from ai_service.offline_pipeline.categories import Action
from ai_service.models.build_profile import Template


class ActionSelection(BaseModel):
    action: Action
    reason: str
    distribution: Dict[str, float]


class TemplateSelection(BaseModel):
    template: Template
    candidates_count: int
    reason: str
