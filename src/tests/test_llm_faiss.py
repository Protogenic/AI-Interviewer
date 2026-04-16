from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Any, Dict, List

import faiss
import numpy as np
from dotenv import load_dotenv
from openai import OpenAI, BadRequestError
from sentence_transformers import SentenceTransformer

LOG = logging.getLogger("test_llm_faiss")

LLM_MODEL = "gpt-4o-mini"
MAX_OUTPUT_TOKENS = 120
TOP_K = 5
TEMPS = (0.3, 0.7)


def l2_normalize(x: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(x, axis=1, keepdims=True)
    norms = np.maximum(norms, 1e-12)
    return x / norms


def read_jsonl_map(path: Path, key: str) -> Dict[int, Dict[str, Any]]:
    out: Dict[int, Dict[str, Any]] = {}
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            out[int(obj[key])] = obj
    return out


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
        "  preferred_patterns: [..]\n"
        "  examples_rewrite_rules: [..]\n\n"
        "4) length_tokens - диапазон, например '4-10' или '6-12' на основе примеров.\n"
        "5) preferred_patterns - 8–12 шаблонов \n"
        "6) Не обобщай, все поля должны содержать конкретные правила, которые получились из ARCHIVE_QUESTIONS. Не придумывай."
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
        "6) Учитывай пол гостя по тестовому фрагменту.(ОБЯЗАТЕЛЬНО, ОЧЕНЬ ВАЖНО)\n"
        "7) Иногда используй частицы/междометия (1–2 слова) из STYLE_CARD.typical_openers или STYLE_CARD.typical_particles."
        "8) 10) Запрещены общие формулировки"
        "Сгенерируй следующий вопрос."
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def build_prompt(test_text: str, context_blocks: List[str]) -> List[Dict[str, str]]:
    system = (
        "интервьюер в стиле Юрия Дудя (Yotube канал: вДудь) "
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

    parser = argparse.ArgumentParser(description="Tests: GPT + RAG(FAISS) with temp sweep.")
    parser.add_argument("tests_dir", type=Path)
    parser.add_argument("faiss_index_dir", type=Path, help="Path to e5_base FAISS folder (contains index.faiss etc.)")
    parser.add_argument("results_dir", type=Path)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    tests_dir: Path = args.tests_dir
    index_dir: Path = args.faiss_index_dir
    results_dir: Path = args.results_dir
    results_dir.mkdir(parents=True, exist_ok=True)

    index_path = index_dir / "index.faiss"
    store_path = index_dir / "store.jsonl"
    config_path = index_dir / "config.json"
    if not index_path.exists() or not store_path.exists() or not config_path.exists():
        raise FileNotFoundError(f"FAISS index folder missing required files: {index_dir}")

    cfg = json.loads(config_path.read_text(encoding="utf-8"))
    embed_model = str(cfg.get("embed_model", "intfloat/multilingual-e5-base"))
    normalize = bool(cfg.get("normalize", True))

    LOG.info("Using FAISS index=%s", index_path)
    LOG.info("Embedding model=%s normalize=%s", embed_model, normalize)

    files = sorted([p for p in tests_dir.glob("*.txt") if p.is_file()])
    if not files:
        LOG.warning("No .txt tests found in %s", tests_dir)
        return

    store = read_jsonl_map(store_path, key="faiss_id")

    embedder = SentenceTransformer(embed_model)
    index = faiss.read_index(str(index_path))
    client = OpenAI()

    for temp in TEMPS:
        out_rows: List[Dict[str, Any]] = []
        out_name = f"faiss_temp_{str(temp).replace('.', '_')}.jsonl"
        out_path = results_dir / out_name

        LOG.info("Temperature=%s in %s", temp, out_path)

        for fp in files:
            test_text = fp.read_text(encoding="utf-8", errors="replace")

            q_emb = embedder.encode([test_text], show_progress_bar=False, convert_to_numpy=True).astype("float32")
            if normalize:
                q_emb = l2_normalize(q_emb)

            D, I = index.search(q_emb, TOP_K)
            idxs = [int(i) for i in I[0] if int(i) >= 0]

            context_blocks: List[str] = []
            for i in idxs:
                txt = str(store.get(i, {}).get("text", "")).strip()
                if txt:
                    context_blocks.append(txt)

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
                    "method": "rag_faiss",
                    "llm_model": LLM_MODEL,
                    "temperature": temp,
                    "top_k": TOP_K,
                    "embed_model": embed_model,
                    "generated_question": q,
                }
            )
            LOG.info("OK %s to %s", fp.name, q)

        write_jsonl(out_path, out_rows)
        LOG.info("Wrote %s (%d rows)", out_path, len(out_rows))

    LOG.info("Done.")


if __name__ == "__main__":
    main()
