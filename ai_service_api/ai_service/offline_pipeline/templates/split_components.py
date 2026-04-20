import re
from typing import List, Tuple

from ai_service.offline_pipeline.categories import ComponentType
from ai_service.offline_pipeline.templates.markers import ComponentMarkers
from ai_service.models.build_profile import Component


def normalize_text(text: str) -> str:
    text = text.lower().strip()
    text = text.replace("ё", "е")
    text = re.sub(r'[\u200b\u200c\u200d\ufeff]', '', text)
    text = re.sub(r"\s+", " ", text)
    return text


def tokenize(text: str) -> list[str]:
    return re.findall(r"[а-яёa-z0-9-]+", normalize_text(text))


def contains_marker(text: str, marker: str) -> bool:
    text_norm = normalize_text(text)
    marker_norm = normalize_text(marker)

    if " " not in marker_norm:
        return marker_norm in tokenize(text_norm)

    pattern = rf"(?<!\w){re.escape(marker_norm)}(?!\w)"
    return re.search(pattern, text_norm) is not None


def contains_any_marker(text: str, markers) -> bool:
    return any(contains_marker(text, marker) for marker in markers)


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
        low_phrase = normalize_text(phrase)
        markers = ComponentMarkers()

        if contains_any_marker(low_phrase, markers.ACK_MARKERS):
            return ComponentType.ACKNOWLEDGMENT

        if contains_any_marker(low_phrase, markers.EMPATHY_MARKERS):
            return ComponentType.EMPATHY

        if contains_any_marker(low_phrase, markers.BRIDGE_MARKERS):
            return ComponentType.BRIDGE

        if contains_any_marker(low_phrase, markers.REQUEST_MARKERS):
            return ComponentType.REQUEST

        if contains_any_marker(low_phrase, markers.PARAPHRASE_MARKERS):
            return ComponentType.PARAPHRASE

        if "?" in low_phrase:
            return ComponentType.QUESTION

        return ComponentType.TEXT
