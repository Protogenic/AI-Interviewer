from pydantic_settings import BaseSettings
from functools import lru_cache

class ProjectSettings(BaseSettings):
    proj_name: str = "AI-Interviewer"

    llm_url: str = "http://localhost:11434/v1"
    llm_api_key: str = "ollama"
    llm_model: str = "qwen2.5:7b-instruct"

    profiles_dir: str = "data/profiles"


@lru_cache
def get_proj_settings() -> ProjectSettings:
    return ProjectSettings()