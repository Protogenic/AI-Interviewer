import json
from pathlib import Path
from typing import Dict, List

from tts_service.models.tts import Voice
from tts_service.exeptions.tts_error import VoiceNotFound


class VoiceRepository:
    def __init__(self, voices_dir: str) -> None:
        self.__voices_dir = Path(voices_dir)
        self.__voices: Dict[str, Voice] = {}
        self.__load_all()

    def __load_all(self) -> None:
        if not self.__voices_dir.exists():
            print("ERROR: voices_dir")
            return

        for sub in self.__voices_dir.iterdir():
            if not sub.is_dir():
                continue
            meta_path = sub / "meta.json"
            if not meta_path.exists():
                continue

            with meta_path.open("r", encoding="utf-8") as f:
                raw = json.load(f)

            voice = Voice(
                id=sub.name,
                name=raw.get("name", sub.name),
                description=raw.get("description", ""),
                language=raw.get("language", "ru"),
            )
            self.__voices[voice.id] = voice

    def list(self) -> List[Voice]:
        return list(self.__voices.values())

    def get(self, voice_id: str) -> Voice:
        if voice_id not in self.__voices:
            raise VoiceNotFound(voice_id=voice_id)
        return self.__voices[voice_id]

    def reference_path(self, voice_id: str) -> Path:
        self.get(voice_id)
        return self.__voices_dir / voice_id / "reference.wav"
