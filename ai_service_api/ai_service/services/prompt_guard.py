"""Базовая защита от prompt injection в пользовательских полях."""

import logging
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Iterable

logger = logging.getLogger(__name__)

MAX_NAME_LEN = 100
MAX_INFO_LEN = 1000
MAX_TOPIC_LEN = 255
MAX_ANSWER_LEN = 4000


_INJECTION_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("override_instructions", re.compile(
        r"\b(ignore|disregard|forget|override|bypass)\b.{0,30}\b(previous|prior|above|all|earlier|system)\b.{0,30}\b(instructions?|prompts?|rules?|directives?)\b",
        re.IGNORECASE,
    )),
    ("override_instructions_ru", re.compile(
        r"\b(игнорируй|забудь|отмени|не\s+слушай|перепиши)\b.{0,40}\b(предыдущ|выше|систем|инструкц|правил|промпт)",
        re.IGNORECASE,
    )),
    ("role_injection", re.compile(
        r"\b(system|assistant|developer)\s*:\s*",
        re.IGNORECASE,
    )),
    ("fake_section_header", re.compile(
        r"^\s*#\s*(система|инструкци|систем|роль|правил|формат\s+вывода|тема\s+интервью|персона|маркер)",
        re.IGNORECASE | re.MULTILINE,
    )),
    ("reveal_prompt", re.compile(
        r"\b(reveal|show|print|output|display|repeat).{0,30}\b(system\s+prompt|your\s+prompt|instructions?)\b",
        re.IGNORECASE,
    )),
    ("reveal_prompt_ru", re.compile(
        r"\b(покажи|выведи|напечатай|повтори|расскажи)\b.{0,40}\b(систем|промпт|инструкц)",
        re.IGNORECASE,
    )),
    ("fenced_code", re.compile(r"```", re.IGNORECASE)),
    ("jailbreak_persona", re.compile(
        r"\b(do\s+anything\s+now|DAN|developer\s+mode|jailbreak)\b",
        re.IGNORECASE,
    )),
]


USER_INPUT_OPEN = "<<<USER_INPUT⟪"
USER_INPUT_CLOSE = "⟫USER_INPUT>>>"


@dataclass
class GuardReport:
    """Результат проверки одного поля."""

    field_name: str
    original_length: int
    sanitized_length: int
    truncated: bool = False
    matched_patterns: list[str] = field(default_factory=list)

    @property
    def is_suspicious(self) -> bool:
        return bool(self.matched_patterns)


def _strip_controls(text: str) -> str:
    """Удаляет управляющие символы, кроме \\n и \\t."""
    out: list[str] = []
    for ch in text:
        if ch in ("\n", "\t"):
            out.append(ch)
            continue
        category = unicodedata.category(ch)
        if category.startswith("C"):
            continue
        out.append(ch)
    return "".join(out)


def _collapse_whitespace(text: str) -> str:
    """Схлопывает множественные пробелы и подряд идущие переводы строк."""
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def _detect(text: str) -> list[str]:
    """Возвращает список имён сработавших паттернов."""
    return [name for name, pattern in _INJECTION_PATTERNS if pattern.search(text)]


def _neutralize(text: str) -> str:
    """Нейтрализует найденные injection-паттерны без удаления текста."""
    text = re.sub(r"\b(ignore|disregard|forget|override)\b", r"[\1]", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(игнорируй|забудь|отмени)\b", r"[\1]", text, flags=re.IGNORECASE)

    text = re.sub(r"\b(system|assistant|developer)\s*:", r"\1​:", text, flags=re.IGNORECASE)

    text = text.replace("```", "`` `")

    text = re.sub(
        r"^(\s*)#(\s*)",
        r"\1​#\2",
        text,
        flags=re.MULTILINE,
    )
    return text


def sanitize_field(
    text: str | None,
    field_name: str,
    max_length: int,
) -> tuple[str, GuardReport]:
    """Возвращает очищенный текст и отчёт с метаданными для логирования."""
    if text is None:
        return "", GuardReport(field_name=field_name, original_length=0, sanitized_length=0)

    original_length = len(text)

    text = _strip_controls(text)
    text = _collapse_whitespace(text).strip()

    matched = _detect(text)
    if matched:
        text = _neutralize(text)

    truncated = False
    if len(text) > max_length:
        text = text[:max_length].rstrip() + "…"
        truncated = True

    report = GuardReport(
        field_name=field_name,
        original_length=original_length,
        sanitized_length=len(text),
        truncated=truncated,
        matched_patterns=matched,
    )

    if matched:
        logger.warning(
            "prompt_guard: suspicious patterns in field=%s patterns=%s preview=%r",
            field_name, matched, text[:200],
        )
    if truncated:
        logger.info(
            "prompt_guard: truncated field=%s from %d to %d",
            field_name, original_length, len(text),
        )

    return text, report


def wrap_user_input(text: str) -> str:
    """Оборачивает текст в разделители, чтобы LLM отличала его от инструкций."""
    return f"{USER_INPUT_OPEN}{text}{USER_INPUT_CLOSE}"


@dataclass
class GuardedInput:
    """Уже санитизированные поля пользователя для передачи в строитель промпта."""

    user_name: str
    user_info: str
    interview_topic: str
    last_answer: str
    history_texts: list[str]
    reports: list[GuardReport] = field(default_factory=list)

    @property
    def any_suspicious(self) -> bool:
        return any(r.is_suspicious for r in self.reports)


def guard_generation_input(
    user_name: str | None,
    user_info: str | None,
    interview_topic: str | None,
    last_answer: str | None,
    history_texts: Iterable[str] | None,
) -> GuardedInput:
    """Точка входа: чистит все пользовательские поля одного запроса генерации."""
    reports: list[GuardReport] = []

    name, r = sanitize_field(user_name, "user_name", MAX_NAME_LEN)
    reports.append(r)
    info, r = sanitize_field(user_info, "user_info", MAX_INFO_LEN)
    reports.append(r)
    topic, r = sanitize_field(interview_topic, "interview_topic", MAX_TOPIC_LEN)
    reports.append(r)
    answer, r = sanitize_field(last_answer, "last_answer", MAX_ANSWER_LEN)
    reports.append(r)

    cleaned_history: list[str] = []
    for idx, raw in enumerate(history_texts or []):
        cleaned, hr = sanitize_field(raw, f"history[{idx}]", MAX_ANSWER_LEN)
        reports.append(hr)
        cleaned_history.append(cleaned)

    return GuardedInput(
        user_name=name,
        user_info=info,
        interview_topic=topic,
        last_answer=answer,
        history_texts=cleaned_history,
        reports=reports,
    )
