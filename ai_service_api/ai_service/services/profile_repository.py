import json
from typing import Dict, List
from pathlib import Path
from ai_service.exeptions.generation_error import CharacterNotFound

from ai_service.models.build_profile import InterviewerProfile, Template, LinguisticProfile


class GetProfileInfo:
    def __init__(self, profile_dir: str = "ai_service/data/profiles") -> None:
        self.__profiles_dir = Path(profile_dir)
        self.__profiles: dict[str, InterviewerProfile] = {}

    def load_profile(self, character_id:str) -> InterviewerProfile:
        if character_id in self.__profiles:
            return self.__profiles[character_id]

        profile_path = self.__profiles_dir / f"{character_id}_profile.json"

        if not profile_path.exists():
            print("ERROR: profile_path")
            raise CharacterNotFound(character_id=character_id)

        with profile_path.open("r", encoding="utf-8") as f:
            raw_profile = json.load(f)

        profile = self.__parse_profile(raw_profile)
        self.__profiles[character_id] = profile
        return profile


    def get_profile(self, character_id: str) -> InterviewerProfile:
        if character_id not in self.__profiles:
            return self.load_profile(character_id)
        return self.__profiles[character_id]

    def get_reactivity_matrix(self, character_id: str) -> Dict[str, Dict[str, int]]:
        return self.get_profile(character_id).reactivity_matrix

    def get_templates(self, character_id: str) -> list[Template]:
        return self.get_profile(character_id).templates

    def __parse_profile(self, raw_data: dict) -> InterviewerProfile:
        linguistic_raw = raw_data.get("linguistic_profile", {})
        templates_raw = raw_data.get("templates", [])

        linguistic_profile = LinguisticProfile(
            empathy_density=linguistic_raw.get("empathy_density", 0.0),
            hedging_density=linguistic_raw.get("hedging_density", 0.0),
            pressure_density=linguistic_raw.get("pressure_density", 0.0),
            filler_density=linguistic_raw.get("filler_density", 0.0),
            formal_density=linguistic_raw.get("formal_density", 0.0),
            provocation_density=linguistic_raw.get("provocation_density", 0.0),
            avg_question_length=linguistic_raw.get("avg_question_length", 0.0),
            avg_phrase_length=linguistic_raw.get("avg_phrase_length", 0.0),
            multi_sentence_ratio=linguistic_raw.get("multi_sentence_ratio", 0.0),
            number_of_questions=linguistic_raw.get("number_of_questions", 0.0),
        )

        templates: List[Template] = []
        for idx, template_raw in  enumerate(templates_raw):
            template = Template(
                structure=template_raw.get("structure", ""),
                frequency=template_raw.get("frequency", 0),
                action=template_raw.get("action", ""),
                question_openness=template_raw.get("question_openness", ""),
                emotion= template_raw.get("emotion", ""),
                techniques=template_raw.get("techniques", []),
                avg_position=template_raw.get("avg_position", 0.0),
                reactivity=template_raw.get("reactivity", []),
                examples=template_raw.get("examples", []),
            )
            templates.append(template)

        return InterviewerProfile(
            interviewer_id=raw_data.get("interviewer_id", ""),
            linguistic_profile=linguistic_profile,
            reactivity_matrix=raw_data.get("reactivity_matrix", {}),
            templates=templates,
            characteristic_phrases=raw_data.get("characteristic_phrases", []),
        )