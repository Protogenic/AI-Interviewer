from typing import Dict, List

from ai_service.models.build_profile import InterviewerProfile, Template


class InMemoryProfileRepository:
    def __init__(self) -> None:
        self.__profiles: dict[str, InterviewerProfile] = {}

    def get_profile(self, character_id: str, profile: InterviewerProfile) -> None:
        self.__profiles[character_id] = profile

    def get_reactivity_matrix(self) -> Dict[str, Dict[str, int]]:
        rm :  Dict[str, Dict[str, int]] = []
        return rm

    def get_templates(self) -> list[Template]:
        return []