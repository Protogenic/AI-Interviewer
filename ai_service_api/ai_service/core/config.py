"""Настройки FastAPI-приложения через pydantic-settings."""

from pydantic_settings import BaseSettings
from functools import lru_cache


class ProjectSettings(BaseSettings):
    proj_name: str = "AI-Interviewer"
    profiles_dir: str = "data/profiles"


@lru_cache
def get_proj_settings() -> ProjectSettings:
    return ProjectSettings()