from __future__ import annotations

import argparse
import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List

import faiss
import numpy as np
from dotenv import load_dotenv
from openai import OpenAI, BadRequestError
from sentence_transformers import SentenceTransformer

LOG = logging.getLogger("test_llm_faiss_cases_templates")

LLM_MODEL = "gpt-4o-mini"
MAX_OUTPUT_TOKENS = 120
TOP_K = 8
TEMPLATE_TOP = 5
TEMPS = (0.3, 0.7)

CAP_NAME_RE = re.compile(r"\b[А-ЯЁ][а-яё]+(?:\s+[А-ЯЁ][а-яё]+){0,2}\b")
NUM_RE = re.compile(r"\b\d+(?:[.,]\d+)?\b")
LAT_CAP_RE = re.compile(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2}\b")


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


def dump_debug_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def query_text_from_test(test_text: str) -> str:
    t = test_text.strip()
    return t[-900:] if len(t) > 900 else t


def anonymize_q(text: str) -> str:
    t = str(text).strip()
    t = NUM_RE.sub("<ЧИСЛО>", t)
    t = LAT_CAP_RE.sub("<ИМЯ>", t)
    t = CAP_NAME_RE.sub("<ИМЯ>", t)
    t = re.sub(r"[ \t]+", " ", t).strip()
    return t


def to_skeleton(q: str) -> str:
    q0 = anonymize_q(q).replace("  ", " ").strip()

    m = re.match(r"^(А\s+есть\s+так\w*\s+).*\?$", q0, flags=re.IGNORECASE)
    if m:
        return (m.group(1) + "...?").strip()

    m = re.match(r"^(Да\.\s*А[, ]+\s*).*\?$", q0, flags=re.IGNORECASE)
    if m:
        return (m.group(1) + "...?").strip()

    if "давайте попробуем" in q0.lower() and "расскажите" in q0.lower():
        first = q0.split(".")[0].strip() + "."
        sk = first + " Расскажите о ... ."
        if "желательно" in q0.lower():
            sk += " Желательно ... ."
        return sk.strip()

    m = re.match(r"^(Слушай[, ]+\s*есть\s+ощущение[, ]+\s*что\s+).*\?$", q0, flags=re.IGNORECASE)
    if m:
        return (m.group(1) + "...?").strip()

    toks = q0.split()
    if len(toks) <= 6:
        return q0 if q0.endswith("?") else (q0 + "?")
    head = " ".join(toks[:5])
    return (head + " ...?").strip()


def infer_pressure(text: str) -> str:
    t = text.lower()
    provocative = ["офиг", "жесть", "какого", "стыдно", "тебе норм"]
    pushy = ["то есть", "в смысле", "подожди", "получается", "но", "ты же", "а есть такая проблема", "реально", "серьёзно", "правда"]
    soft = ["если можно", "можешь", "давай попробуем", "попробуем", "чуть-чуть", "можно уточнить", "расскажи", "хочется"]

    if any(m in t for m in provocative):
        return "provocative"
    if any(m in t for m in pushy):
        return "pushy"
    if any(m in t for m in soft):
        return "soft"
    return "neutral"


def build_template_candidates(next_questions: List[str], limit: int = TEMPLATE_TOP) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    seen = set()

    for q in next_questions:
        if not q:
            continue
        q = str(q).strip()
        if not q or q in seen:
            continue
        seen.add(q)

        sk = to_skeleton(q)
        if len(sk.split()) < 2:
            continue

        out.append(
            {
                "source_next_question": anonymize_q(q),
                "skeleton": sk,
                "pressure_level": infer_pressure(sk),
            }
        )
        if len(out) >= limit:
            break

    if not out:
        out = [{"source_next_question": "", "skeleton": "Почему ...?", "pressure_level": "neutral"}]
    return out


def build_planner_prompt(test_text: str, templates: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    system = (
        "Ты - аналитик интервью. Выбери подходящий КАРКАС вопроса (template skeleton) "
        "и спланируй следующий вопрос интервьюера. Не придумывай факты."
    )

    blocks = []
    for i, t in enumerate(templates, start=1):
        blocks.append(f"{i}) skeleton: {t.get('skeleton')}\n   pressure_level: {t.get('pressure_level')}")

    user = (
        "ТЕСТОВЫЙ ФРАГМЕНТ:\n"
        f"{test_text.strip()}\n\n"
        "ШАБЛОНЫ (каркасы) из похожих кейсов:\n"
        + "\n".join(blocks)
        + "\n\n"
        "Верни JSON строго такого вида:\n"
        "{\n"
        '  "template_choice": 1,\n'
        '  "pressure_level": "soft|neutral|pushy|provocative",\n'
        '  "target_entity_type": "на русском: что именно ты уточняешь (3-7 слов), не списком",\n'
        '  "anchor_keywords": "2-6 слов по смыслу из последнего ответа гостя, без прямой цитаты"\n'
        "}\n\n"
        "Правила:\n"
        "- template_choice должен быть номером из списка шаблонов.\n"
        "- anchor_keywords - ТОЛЬКО из последнего ответа гостя; НЕ цитируй длинно.\n"
        "- pressure_level должен совпадать с выбранным шаблоном (если сомневаешься - бери шаблонный).\n"
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def extract_template_choice(plan_text: str, max_choice: int) -> int:
    m = re.search(r'"template_choice"\s*:\s*(\d+)', plan_text)
    if not m:
        return 1
    v = int(m.group(1))
    return max(1, min(v, max_choice))


def build_realizer_prompt(test_text: str, plan_json: str, chosen_template: Dict[str, Any]) -> List[Dict[str, str]]:
    system = (
        "Ты - интервьюер в стиле Юрия Дудя. "
        "Сгенерируй следующий вопрос по тестовому фрагменту. "
        "Используй каркас (skeleton) как основу формулировки. "
        "Не добавляй новые факты/имена/места. Одна строка, один вопрос."
    )
    user = (
        "КАРКАС (skeleton):\n"
        f"{chosen_template.get('skeleton')}\n\n"
        "ПЛАН:\n"
        f"{plan_json.strip()}\n\n"
        "ТЕСТОВЫЙ ФРАГМЕНТ:\n"
        f"{test_text.strip()}\n\n"
        "ОГРАНИЧЕНИЯ:\n"
        "- Сохрани частицы/ритм каркаса, но заполни '...' смыслом из test_text.\n"
        "- Используй anchor_keywords по смыслу (можно склонять/перефразировать), НЕ нужно дословно цитировать гостя.\n"
        "- Конкретизируй target_entity_type.\n"
        "- Учитывай пол того, кому задают вопрос по тестовому фрагменту. (ОБЯЗАТЕЛЬНО)\n"
        "Сгенерируй вопрос."
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def main() -> None:
    load_dotenv()
    ap = argparse.ArgumentParser()
    ap.add_argument("tests_dir", type=Path)
    ap.add_argument("faiss_model_dir", type=Path, help=".../e5_large or .../e5_base")
    ap.add_argument("results_dir", type=Path)
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    args.results_dir.mkdir(parents=True, exist_ok=True)
    debug_dir = args.results_dir / "debug_rag"
    debug_dir.mkdir(parents=True, exist_ok=True)

    state_dir = args.faiss_model_dir / "state"
    q_dir = args.faiss_model_dir / "q"

    def must(p: Path) -> None:
        if not p.exists():
            raise FileNotFoundError(p)

    must(state_dir / "index.faiss")
    must(state_dir / "store.jsonl")
    must(state_dir / "meta.jsonl")
    must(q_dir / "index.faiss")
    must(q_dir / "store.jsonl")
    must(q_dir / "meta.jsonl")

    suffix = args.faiss_model_dir.name
    embed_model = "intfloat/multilingual-e5-large" if "large" in suffix else "intfloat/multilingual-e5-base"
    embedder = SentenceTransformer(embed_model)

    index_state = faiss.read_index(str(state_dir / "index.faiss"))
    index_q = faiss.read_index(str(q_dir / "index.faiss"))

    meta_state = read_jsonl_map(state_dir / "meta.jsonl", "faiss_id")
    meta_q = read_jsonl_map(q_dir / "meta.jsonl", "faiss_id")
    store_state = read_jsonl_map(state_dir / "store.jsonl", "faiss_id")
    store_q = read_jsonl_map(q_dir / "store.jsonl", "faiss_id")

    client = OpenAI()

    files = sorted([p for p in args.tests_dir.glob("*.txt") if p.is_file()])
    if not files:
        LOG.warning("No tests in %s", args.tests_dir)
        return

    for temp in TEMPS:
        out_rows: List[Dict[str, Any]] = []
        out_path = args.results_dir / f"faiss_cases_templates_temp_{str(temp).replace('.', '_')}.jsonl"
        LOG.info("temp=%s in %s", temp, out_path)

        for fp in files:
            test_text = fp.read_text(encoding="utf-8", errors="replace")
            qtext = query_text_from_test(test_text)

            q_emb = embedder.encode([qtext], show_progress_bar=False, convert_to_numpy=True).astype("float32")
            q_emb = l2_normalize(q_emb)

            D1, I1 = index_state.search(q_emb, TOP_K)
            D2, I2 = index_q.search(q_emb, TOP_K)

            state_hits: List[Dict[str, Any]] = []
            for rank, (score, idx) in enumerate(zip(D1[0].tolist(), I1[0].tolist()), start=1):
                idx = int(idx)
                if idx < 0:
                    continue
                m = meta_state.get(idx, {})
                doc = store_state.get(idx, {}).get("text", "")
                state_hits.append({"rank": rank, "score": score, "faiss_id": idx, "document": doc, "metadata": m, "next_question": (m or {}).get("next_question")})

            question_hits: List[Dict[str, Any]] = []
            for rank, (score, idx) in enumerate(zip(D2[0].tolist(), I2[0].tolist()), start=1):
                idx = int(idx)
                if idx < 0:
                    continue
                m = meta_q.get(idx, {})
                doc = store_q.get(idx, {}).get("text", "")
                question_hits.append({"rank": rank, "score": score, "faiss_id": idx, "document": doc, "metadata": m, "next_question": (m or {}).get("next_question")})

            found_nextq: List[str] = []
            for h in state_hits:
                nq = h.get("next_question")
                if nq:
                    found_nextq.append(str(nq))
            for h in question_hits:
                nq = h.get("next_question")
                if nq:
                    found_nextq.append(str(nq))

            template_candidates = build_template_candidates(found_nextq, limit=TEMPLATE_TOP)

            plan_messages = build_planner_prompt(test_text, template_candidates)
            plan = responses_create_safe(client, model=LLM_MODEL, input=plan_messages, temperature=0.1, max_output_tokens=220)

            choice = extract_template_choice(plan, max_choice=len(template_candidates))
            chosen_template = template_candidates[choice - 1]

            gen_messages = build_realizer_prompt(test_text, plan, chosen_template)
            out = responses_create_safe(client, model=LLM_MODEL, input=gen_messages, temperature=temp, max_output_tokens=MAX_OUTPUT_TOKENS)

            q = " ".join(out.splitlines()).strip()
            if q and not q.endswith("?"):
                q = q.rstrip(".") + "?"

            dump_debug_json(
                debug_dir / f"{fp.stem}.debug.json",
                {
                    "test_file": fp.name,
                    "embed_model": embed_model,
                    "top_k": TOP_K,
                    "temperature": temp,
                    "rag_query_text": qtext,
                    "retrieval_raw": {"state_hits": state_hits, "question_hits": question_hits},
                    "template_candidates": template_candidates,
                    "planner_prompt": plan_messages,
                    "plan_raw": plan,
                    "chosen_template": chosen_template,
                    "realizer_prompt": gen_messages,
                    "generated_question": q,
                },
            )

            out_rows.append(
                {
                    "test_file": fp.name,
                    "method": "rag_faiss_cases_templates",
                    "llm_model": LLM_MODEL,
                    "temperature": temp,
                    "top_k": TOP_K,
                    "embed_model": embed_model,
                    "plan_json": plan,
                    "chosen_template": chosen_template.get("skeleton"),
                    "generated_question": q,
                }
            )
            LOG.info("OK %s to %s", fp.name, q)

        with out_path.open("w", encoding="utf-8") as f:
            for r in out_rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        LOG.info("Wrote %s (%d rows)", out_path, len(out_rows))


if __name__ == "__main__":
    main()
