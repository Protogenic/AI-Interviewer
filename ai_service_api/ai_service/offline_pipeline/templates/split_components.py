import re
from typing import List, Tuple

from ai_service.offline_pipeline.categories import ComponentType
from ai_service.offline_pipeline.templates.markers import ComponentMarkers
from ai_service.models.build_profile import Component

class ComponentSeparator:
    def split_into_components(self, text: str) -> Tuple[List[Component], str]:
        phrases = [s.strip() for s in re.split(r"(?<=[.?!])\s+", text.strip()) if s.strip()]
        components: List[Component] = []

        for phrase in phrases:
            component_type = self._classify_component(phrase)
            components.append(Component(type=component_type, text= phrase))

        pattern = " + ".join(component.type.value for component in components)
        return components, pattern

    def _classify_component(self, phrase: str) -> ComponentType:
        low_phrase = phrase.lower().strip()
        markers = ComponentMarkers()

        if any(marker in low_phrase for marker in markers.ACK_MARKERS):
            return ComponentType.ACKNOWLEDGMENT

        if any(marker in low_phrase for marker in markers.EMPATHY_MARKERS):
            return ComponentType.EMPATHY

        if any(marker in low_phrase for marker in markers.BRIDGE_MARKERS):
            return ComponentType.BRIDGE

        if any(marker in low_phrase for marker in markers.REQUEST_MARKERS):
            return ComponentType.REQUEST

        if any(marker in low_phrase for marker in markers.PARAPHRASE_MARKERS):
            return ComponentType.PARAPHRASE

        if "?" in low_phrase:
            return ComponentType.QUESTION

        return ComponentType.TEXT
