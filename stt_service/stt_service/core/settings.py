from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEFAULT_WHISPER_PROMPT = (
    "Пример: Здравствуйте, я готов ответить на вопросы. "
    "Короткие фразы — с запятыми; длинные — с точками. "
    "Вопросы заканчиваются знаком вопроса? Восклицания — восклицательным знаком!"
)


class SttSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    proj_name: str = "AI-Interviewer-STT"

    app_host: str = "0.0.0.0"
    app_port: int = 8010

    whisper_model: str = "small"
    whisper_compute_type: str = "int8"
    whisper_initial_prompt: str = Field(default=_DEFAULT_WHISPER_PROMPT)
    whisper_vad_filter: bool = True
    whisper_vad_min_silence_duration_ms: int = 350
    whisper_beam_size: int = 2
    whisper_best_of: int = 2
    whisper_condition_on_previous_text: bool = False
    whisper_temperature: float = 0.0


@lru_cache
def get_settings() -> SttSettings:
    return SttSettings()
