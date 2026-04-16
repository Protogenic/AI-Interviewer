from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Any, Dict, List

from dotenv import load_dotenv
from openai import OpenAI
from openai import BadRequestError

LOG = logging.getLogger("test_only_llm")

LLM_BASE_URL= "http://localhost:11434/v1"
LLM_API_KEY="ollama"
LLM_MODEL="qwen2.5:7b-instruct"
MAX_OUTPUT_TOKENS = 120
TEMPERATURE = 0.7


def responses_create_safe(client: OpenAI, **kwargs: Any) -> str:
    try:
        resp = client.responses.create(**kwargs)
        return (getattr(resp, "output_text", "") or "").strip()
    except BadRequestError as e:
        msg = str(e)
        if "Unsupported parameter" in msg:
            kwargs.pop("temperature", None)
            kwargs.pop("top_p", None)
            resp = client.responses.create(**kwargs)
            return (getattr(resp, "output_text", "") or "").strip()
    except Exception:
        pass

    model = kwargs.get("model")
    messages = kwargs.get("input")
    temperature = kwargs.get("temperature")
    max_tokens = kwargs.get("max_output_tokens") or kwargs.get("max_tokens")

    chat_kwargs = {"model": model, "messages": messages}
    if temperature is not None:
        chat_kwargs["temperature"] = temperature
    if max_tokens is not None:
        chat_kwargs["max_tokens"] = max_tokens

    try:
        chat = client.chat.completions.create(**chat_kwargs)
        return (chat.choices[0].message.content or "").strip()
    except BadRequestError as e:
        msg = str(e)
        if "Unsupported parameter" in msg:
            chat_kwargs.pop("temperature", None)
            chat = client.chat.completions.create(**chat_kwargs)
            return (chat.choices[0].message.content or "").strip()
        raise

def build_messages(test_text: str) -> List[Dict[str, str]]:
    system = (
        "Ты - интервьюер в стиле Юрия Дудя (Yotube канал: вДудь). "
        "Твоя задача: по данному фрагменту (две пары вопрос-ответ) задать СЛЕДУЮЩИЙ вопрос в стиле Дудя. "
        "Правила:"
        "1) Логично продолжай ПОСЛЕДНИЙ ответ гостя в стиле Дудя."
        "2) Ровно одна строка."
        "3) Повтори структуру и длину вопросов как у Дудя."
        "4) Выяви и учитывай уровень эмоциональности Дудя."
        "5) Никаких ииподобных предложений и слов, никаких списков."
        "6) Никаких общих вопросов без конкретики, никаких пояснений."
        "7) Учитывай пол гостя по предыдущим вопросам и ответам"
        "8) Учитывай логику того, как задаёт вопросы Дудь"
        "9) Разрешен свободный, разговорный стиль вопроса."
    )
    user = (
        "Вот фрагмент интервью (2 пары вопрос-ответ). Прочитай и задай следующий вопрос, "
        "максимально копируя стиль интервьюера из фрагмента:\n\n"
        f"{test_text.strip()}\n"
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def write_jsonl(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(description="Control: GPT only (no RAG) for tests/*.txt")
    parser.add_argument("tests_dir", type=Path)
    parser.add_argument("out_jsonl", type=Path)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    tests_dir: Path = args.tests_dir
    out_jsonl: Path = args.out_jsonl

    files = sorted([p for p in tests_dir.glob("*.txt") if p.is_file()])
    if not files:
        LOG.warning("No .txt tests found in %s", tests_dir)
        return

    client = OpenAI(base_url=LLM_BASE_URL, api_key=(LLM_API_KEY or "EMPTY")) if LLM_BASE_URL else OpenAI()

    results: List[Dict[str, Any]] = []
    for fp in files:
        test_text = fp.read_text(encoding="utf-8", errors="replace")
        messages = build_messages(test_text)

        out = responses_create_safe(
            client,
            model=LLM_MODEL,
            input=messages,
            temperature=TEMPERATURE,
            max_output_tokens=MAX_OUTPUT_TOKENS,
        )

        q = " ".join(out.splitlines()).strip()
        if q and not q.endswith("?"):
            q = q.rstrip(".") + "?"

        results.append(
            {
                "test_file": fp.name,
                "method": "llm_only",
                "llm_model": LLM_MODEL,
                "temperature": TEMPERATURE,
                "generated_question": q,
            }
        )
        LOG.info("OK %s to %s", fp.name, q)

    write_jsonl(out_jsonl, results)
    LOG.info("Wrote %s (%d rows)", out_jsonl, len(results))


if __name__ == "__main__":
    main()
