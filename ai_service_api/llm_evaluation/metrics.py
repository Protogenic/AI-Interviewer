import json
import re
from dataclasses import dataclass

from llm_evaluation.test_cases import TestCase


@dataclass
class ObjectiveMetrics:
    json_valid: bool = False
    has_parts_key: bool = False
    parts_count_correct: bool = False
    roles_correct: bool = False
    word_count_mae: float | None = None
    no_forbidden_punct: bool = False
    latency_s: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    raw_response: str = ""
    parse_error: str = ""

    @property
    def fully_compliant(self) -> bool:
        return (
            self.json_valid
            and self.has_parts_key
            and self.parts_count_correct
            and self.roles_correct
            and self.no_forbidden_punct
        )


_FORBIDDEN_PUNCT = re.compile(r"—| - | – ")


def compute(
    raw_response: str,
    test_case: TestCase,
    latency_s: float,
    input_tokens: int,
    output_tokens: int,
    price_input: float,
    price_output: float,
) -> ObjectiveMetrics:
    m = ObjectiveMetrics(
        latency_s=latency_s,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        raw_response=raw_response,
    )
    m.cost_usd = (
        input_tokens / 1_000_000 * price_input
        + output_tokens / 1_000_000 * price_output
    )

    text = (raw_response or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text).rstrip("`").strip()
    text_for_parse = text.replace("'", '"')

    try:
        data = json.loads(text_for_parse)
        m.json_valid = True
    except json.JSONDecodeError as e:
        m.parse_error = str(e)
        return m

    parts = data.get("parts") if isinstance(data, dict) else None
    if not isinstance(parts, list):
        m.has_parts_key = False
        return m
    m.has_parts_key = True

    expected_n = len(test_case.expected_roles)
    m.parts_count_correct = len(parts) == expected_n

    actual_roles = [
        p.get("role", "") for p in parts if isinstance(p, dict)
    ]
    m.roles_correct = actual_roles == test_case.expected_roles

    contents = [
        p.get("content", "") for p in parts if isinstance(p, dict)
    ]
    total_words = sum(len(c.split()) for c in contents)
    m.word_count_mae = abs(total_words - test_case.target_words)

    all_text = " ".join(contents)
    m.no_forbidden_punct = not bool(_FORBIDDEN_PUNCT.search(all_text))

    return m


def metrics_to_dict(m: ObjectiveMetrics) -> dict:
    return {
        "json_valid": m.json_valid,
        "has_parts_key": m.has_parts_key,
        "parts_count_correct": m.parts_count_correct,
        "roles_correct": m.roles_correct,
        "word_count_mae": m.word_count_mae,
        "no_forbidden_punct": m.no_forbidden_punct,
        "fully_compliant": m.fully_compliant,
        "latency_s": round(m.latency_s, 3),
        "input_tokens": m.input_tokens,
        "output_tokens": m.output_tokens,
        "cost_usd": round(m.cost_usd, 6),
        "raw_response": m.raw_response,
        "parse_error": m.parse_error,
    }
