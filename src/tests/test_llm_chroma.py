from __future__ import annotations

import argparse
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List

import chromadb
from dotenv import load_dotenv
from openai import OpenAI, BadRequestError
from sentence_transformers import SentenceTransformer

LOG = logging.getLogger("test_llm_chroma")

os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")
os.environ.setdefault("CHROMA_TELEMETRY", "False")

LLM_MODEL = "gpt-4o-mini"
MAX_OUTPUT_TOKENS = 120
TOP_K = 5
TEMPS = (0.3, 0.7)

EMBED_MODEL = "intfloat/multilingual-e5-base"


def responses_create_safe(client: OpenAI, **kwargs: Any) -> str:
    try:
        resp = client.responses.create(**kwargs)
        return (resp.output_text or "").strip()
    except BadRequestError as e:
        msg = str(e)
        if "Unsupported parameter" in msg:
            kwargs.pop("temperature", None)
            kwargs.pop("top_p", None)
            resp = client.responses.create(**kwargs)
            return (resp.output_text or "").strip()
        raise


def build_stylecard_prompt(context_blocks: List[str]) -> List[Dict[str, str]]:
    archive_text = "\n".join([cb.strip() for cb in context_blocks if cb.strip()])

    system = (
        "Ты - лингвист-редактор. Твоя задача - извлечь стиль интервьюера из примеров вопросов. "
        "Не придумывай тем, фактов, биографий. Только наблюдения о форме речи. "
        "Пиши кратко и формально, без воды."
        "Ты извлекаешь стиль ТОЛЬКО из текста в < ARCHIVE_QUESTIONS >."
        "Запрещено выдумывать типичные фразы."
        "Можно только:"
        "- копировать короткие стартеры / частицы, которые реально встречаются в примерах,"
        "- либо выбирать из заранее заданного списка допустимых стартеров."
        "Запрещены обобщающие формулировки."
        "Запрещены имена собственные в выводе - заменяй на < ИМЯ > / < МЕСТО > / < БРЕНД >."
    )

    user = (
        "ДАНО: Примеры реплик интервьюера (могут быть с шумом).\n\n"
        "ЗАДАЧА: Сформируй 'STYLE_CARD' - компактный набор правил, которые можно применить для генерации новых вопросов в том же стиле.\n\n"
        "ТРЕБОВАНИЯ:\n"
        "1) Верни строго в формате YAML.\n"
        "2) Поля YAML должны быть ровно такими:\n\n"
        "STYLE_CARD:\n"
        "  voice: ...\n"
        "  length_tokens: ...\n"
        "  tempo: ...\n"
        "  directness: ...\n"
        "  emotionality: ...\n"
        "  typical_openers: [..]\n"
        "  typical_particles: [..]\n"
        "  examples_rewrite_rules: [..]\n\n"
        "4) length_tokens - диапазон, например '4-10' или '6-12' на основе примеров.\n"
        "5) Не обобщай, все поля должны содержать конкретные правила, которые получились из ARCHIVE_QUESTIONS. Не придумывай."
        "Вот примеры:\n"
        "<ARCHIVE_QUESTIONS>\n"
        f"{archive_text}\n"
        "</ARCHIVE_QUESTIONS>\n"
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def build_generation_prompt(test_text: str, style_card_yaml: str) -> List[Dict[str, str]]:
    system = (
        "Ты - интервьюер в стиле Юрия Дудя. "
        "Твоя задача - задать СЛЕДУЮЩИЙ вопрос по тестовому фрагменту (две пары вопрос-ответ). "
        "Ты используешь STYLE_CARD только как настройки стиля. "
        "НЕЛЬЗЯ использовать какие-либо факты/темы вне тестового фрагмента. "
        "Вывод: ровно одна строка - один вопрос."
    )

    user = (
        "STYLE_CARD (настройки стиля):\n"
        f"{style_card_yaml.strip()}\n\n"
        "ТЕСТОВЫЙ ФРАГМЕНТ (2 Q/A):\n"
        f"{test_text.strip()}\n\n"
        "ПРАВИЛА:\n"
        "1) Вопрос должен логично продолжать ПОСЛЕДНИЙ ответ гостя.\n"
        "2) 1 строка. Без 'Интервьюер:' и без кавычек.\n"
        "3) Длина вопроса - строго в диапазоне STYLE_CARD.length_tokens (приблизительно по токенам).\n"
        "4) Запрещены любые фразы/паттерны из STYLE_CARD.taboo_phrases и STYLE_CARD.avoid_patterns.\n"
        "5) Вопрос должен быть конкретным: без абстрактных 'как ты думаешь', 'как тебе кажется', 'что именно помогло'.\n"
        "6) Учитывай пол гостя по тестовому фрагменту.\n"
        "7) Иногда используй различные частицы/междометия (1–2 слова) из STYLE_CARD.typical_openers или STYLE_CARD.typical_particles. Выбирай подходящие под контекст, а не первые попавшиеся."
        "8) Запрещены общие формулировки"
        "9) Строго следуй examples_rewrite_rules, обрати на них очень большое внимание, это важные инструкции. Если в них разрешено дополнять вопрос реакцией - можно написать ещё одно предложение кроме вопроса"
        "10) Старайся максимально опираться на STYLE_CARD, но чтобы это сочеталось с гостем, последним вопросом и ответом и стилем общения из прошлых вопросов."
        "11) Учитывай directness, emotionality из STYLE_CARD. "
        "Сгенерируй следующий вопрос."

    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def build_prompt(test_text: str, context_blocks: List[str]) -> List[Dict[str, str]]:
    system = (
        "Ты - интервьюер в стиле резких, живых русскоязычных интервью. "
        "Твоя задача: по тестовому фрагменту (две пары вопрос-ответ) и по контексту из архива интервью "
        "задать СЛЕДУЮЩИЙ вопрос. "
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
    context = "\n\n---\n\n".join(context_blocks).strip()
    user = (
        "ТЕСТОВЫЙ ФРАГМЕНТ (2 Q/A):\n"
        f"{test_text.strip()}\n\n"
        "КОНТЕКСТ ИЗ АРХИВА ИНТЕРВЬЮ Дудя:\n"
        f"{context}\n\n"
        "Используй контекст из архива интервью ТОЛЬКО для АНАЛИЗА ЕГО СТИЛЯ ВОПРОСОВ, чтобы максимально предуагадать его вопрос"
        "в тестовом фрагменте. Продолжай логику ТЕСТОВОГО ФРАГМЕНТА, а КОНТЕКСТ ИЗ АРХИВА используй только для ВЫЯВЛЕНИЯ "
        "СТИЛИСТИЧЕСКИХ И ЭМОЦИОНАЛЬНЫХ черт вопросов Дудя (в контексте - интервьюер) к гостю."
        "ВАЖНО: не добавлять новый контекст, а сгенерировать вопросы конкретно к тестовому фрагменту. Контекст из архива используй только для анализа стиля речи Дудя."
        "Сгенерируй следующий вопрос Дудя."
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def write_jsonl(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(description="Tests: GPT + RAG(Chroma) with temp sweep.")
    parser.add_argument("tests_dir", type=Path)
    parser.add_argument("persist_dir", type=Path)
    parser.add_argument("collection_name", type=str, help="Collection name for e5_base, e.g. interview_qa700_e5_base")
    parser.add_argument("results_dir", type=Path)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    tests_dir: Path = args.tests_dir
    persist_dir: Path = args.persist_dir
    collection_name: str = args.collection_name
    results_dir: Path = args.results_dir
    results_dir.mkdir(parents=True, exist_ok=True)

    name = collection_name.lower()
    if "e5_large" in name or name.endswith("_large"):
        embed_model = "intfloat/multilingual-e5-large"
    else:
        embed_model = "intfloat/multilingual-e5-base"
    LOG.info("Using embed model for queries: %s", embed_model)
    embedder = SentenceTransformer(embed_model)

    files = sorted([p for p in tests_dir.glob("*.txt") if p.is_file()])
    if not files:
        LOG.warning("No .txt tests found in %s", tests_dir)
        return

    client = OpenAI()
    chroma_client = chromadb.PersistentClient(path=str(persist_dir))
    col = chroma_client.get_collection(name=collection_name)

    for temp in TEMPS:
        out_rows: List[Dict[str, Any]] = []
        out_name = f"chroma_temp_{str(temp).replace('.', '_')}.jsonl"
        out_path = results_dir / out_name

        LOG.info("Temperature=%s in %s", temp, out_path)

        for fp in files:
            test_text = fp.read_text(encoding="utf-8", errors="replace")

            q_emb = embedder.encode([test_text], show_progress_bar=False, convert_to_numpy=True).astype("float32")

            res = col.query(
                query_embeddings=q_emb.tolist(),
                n_results=TOP_K,
                include=["documents", "metadatas", "distances"],
            )
            docs = (res.get("documents") or [[]])[0]
            context_blocks = [str(d).strip() for d in docs if str(d).strip()]

            stylecard_messages = build_stylecard_prompt(context_blocks)
            style_card_yaml = responses_create_safe(
                client,
                model=LLM_MODEL,
                input=stylecard_messages,
                temperature=0.1,
                max_output_tokens=350,
            )
            LOG.info("STYLE_CARD for %s:\n%s", fp.name, style_card_yaml)

            gen_messages = build_generation_prompt(test_text, style_card_yaml)
            out = responses_create_safe(
                client,
                model=LLM_MODEL,
                input=gen_messages,
                temperature=temp,
                max_output_tokens=MAX_OUTPUT_TOKENS,
            )

            q = " ".join(out.splitlines()).strip()
            if q and not q.endswith("?"):
                q = q.rstrip(".") + "?"

            out_rows.append(
                {
                    "test_file": fp.name,
                    "method": "rag_chroma",
                    "llm_model": LLM_MODEL,
                    "temperature": temp,
                    "top_k": TOP_K,
                    "embed_model": EMBED_MODEL,
                    "collection": collection_name,
                    "generated_question": q,
                }
            )
            LOG.info("OK %s to %s", fp.name, q)

        write_jsonl(out_path, out_rows)
        LOG.info("Wrote %s (%d rows)", out_path, len(out_rows))

    LOG.info("Done.")


if __name__ == "__main__":
    main()
