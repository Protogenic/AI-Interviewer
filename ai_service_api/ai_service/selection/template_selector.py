import random
from typing import List, Optional

from ai_service_api.ai_service.selection.compability import ACTION_TECHNIQUE_COMPATIBILITY
from ai_service_api.ai_service.offline_pipeline.categories import DialogueAct, Technique
from ai_service_api.ai_service.models.selection import TemplateSelection
from ai_service_api.ai_service.models.build_profile import Template

class TemplateSelector:
    def __init__(self,
                 templates: List[Template],
                 top_n = 3,
                 random_seed: Optional[int] = None
    ) -> None:
        self.templates = templates
        self.top_n = top_n
        self.random = random.Random(random_seed)


    def select_template(self,
                        action: DialogueAct,
                        interview_position: float,
                        previous_template_id: Optional[str] = None
                        ) -> TemplateSelection:
        compatible_techniques = (self._get_compatible_techniques(action))

        filtered = []

        for template in self.templates:
            if template.technique in compatible_techniques:
                filtered.append(template)

        scored = []
        for template in filtered:
            score = self._score_template(
                template=template,
                interview_position=interview_position,
                previous_template_id=previous_template_id
            )
            scored.append((template, score))

        scored.sort(key=lambda  x: x[1], reverse=True)

        top_candidates = scored[: self.top_n] if scored else []

        templates = [item[0] for item in top_candidates]
        weights = [max(item[1], 0.01) for item in top_candidates]

        selected = self.random.choices(templates, weights=weights, k=1)[0]

        return TemplateSelection(
            template=selected,
            candidates_count=len(filtered),
            reason="selected_by_compatibility_position_frequency"
        )


    def _get_compatible_techniques(self, action: DialogueAct) -> List[Technique]:
        profile_compatibility = ACTION_TECHNIQUE_COMPATIBILITY.get(action.value, [])
        compatible_techniques = []

        for item in profile_compatibility:
            compatible_techniques.append(Technique(item))

        return compatible_techniques


    @staticmethod
    def _position_score(template: Template, interview_position: float) -> float:
        distance = abs(template.avg_position - interview_position)
        return max(0.0, 1.0-distance)

    def _score_template(self,
                        template: Template,
                        interview_position: float,
                        previous_template_id: Optional[str]
                        ) -> float:
        frequency_score = float(getattr(template, "frequency", 1))
        position_score = self._position_score(template, interview_position)

        repeat_penalty = 1.0
        if previous_template_id and getattr(template, "template_id", None) == previous_template_id:
            repeat_penalty = 0.35

        return (0.6 * frequency_score + 0.4 * position_score) * repeat_penalty
