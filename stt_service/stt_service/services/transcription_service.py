from __future__ import annotations

import re
from typing import Any, Optional

from faster_whisper import WhisperModel

from stt_service.core.settings import get_settings

_model: WhisperModel | None = None


def get_whisper_model() -> WhisperModel:
    global _model
    if _model is None:
        s = get_settings()
        _model = WhisperModel(
            s.whisper_model,
            device="cpu",
            compute_type=s.whisper_compute_type,
        )
    return _model


def _polish_russian_text(text: str) -> str:
    """Нормализует пробелы, заглавные после конца предложения, точку в конце при необходимости."""
    t = " ".join(text.split()).strip()
    if not t:
        return t
    t = t[0].upper() + t[1:] if len(t) > 1 else t.upper()

    def _cap_after(m: re.Match[str]) -> str:
        punct, letter, tail = m.group(1), m.group(2), m.group(3) or ""
        return f"{punct} {letter.upper()}{tail}"

    t = re.sub(
        r"([.!?…])\s+([а-яёa-z])([^\s.!?…]*)",
        _cap_after,
        t,
        flags=re.IGNORECASE,
    )
    if t[-1] not in ".!?…":
        t += "."
    return t


def transcribe_file(tmp_path: str, language: Optional[str]) -> dict[str, Any]:
    s = get_settings()
    model = get_whisper_model()

    transcribe_kw: dict[str, Any] = dict(
        language=language or None,
        beam_size=1,
        best_of=1,
        condition_on_previous_text=False,
        initial_prompt=s.whisper_initial_prompt,
    )
    if s.whisper_vad_filter:
        transcribe_kw["vad_filter"] = True
        transcribe_kw["vad_parameters"] = dict(min_silence_duration_ms=500)
    else:
        transcribe_kw["vad_filter"] = False

    segments, info = model.transcribe(tmp_path, **transcribe_kw)
    parts = [seg.text.strip() for seg in segments if seg.text and seg.text.strip()]
    text = " ".join(parts).strip()
    if text:
        text = _polish_russian_text(text)

    return {
        "text": text,
        "language": info.language,
        "duration": info.duration,
    }
