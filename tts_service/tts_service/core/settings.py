from pathlib import Path
from functools import lru_cache

from pydantic_settings import BaseSettings


class ProjectSettings(BaseSettings):
    proj_name: str = "AI-Interviewer-TTS"

    engine: str = "dummy"
    device: str = "cpu"
    xtts_model: str = "tts_models/multilingual/multi-dataset/xtts_v2"
    voices_dir: str = str(Path(__file__).resolve().parent.parent / "data" / "voices")
    models_dir: str = str(Path(__file__).resolve().parent.parent / "data" / "models")

    sample_rate: int = 22050
    default_voice_id: str = "dud"
    default_language: str = "ru"


@lru_cache
def get_proj_settings() -> ProjectSettings:
    return ProjectSettings()
