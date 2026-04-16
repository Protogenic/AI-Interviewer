from __future__ import annotations

import argparse
import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List

import chromadb
from dotenv import load_dotenv
from openai import OpenAI, BadRequestError
from sentence_transformers import SentenceTransformer

LOG = logging.getLogger("test_llm_chroma_cases_templates")

MAX_OUTPUT_TOKENS = 120
TOP_K = 8
TEMPLATE_TOP = 5
TEMPS = [0.7]

LLM_BASE_URL= "http://localhost:11434/v1"
LLM_API_KEY="ollama"
LLM_MODEL="qwen2.5:7b-instruct"


os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")
os.environ.setdefault("CHROMA_TELEMETRY", "False")

CAP_NAME_RE = re.compile(r"\b[А-ЯЁ][а-яё]+(?:\s+[А-ЯЁ][а-яё]+){0,2}\b")
NUM_RE = re.compile(r"\b\d+(?:[.,]\d+)?\b")
LAT_CAP_RE = re.compile(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2}\b")


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


def dump_debug_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def query_text_from_test(test_text: str) -> str:
    t = test_text.strip()
    return t[-900:] if len(t) > 900 else t


def to_skeleton(q: str) -> str:
    q0 = q.replace("  ", " ").strip()
    toks = q0.split()
    if len(toks) <= 6:
        return q0 if q0.endswith("?") else (q0 + "?")
    head = " ".join(toks[:5])
    return (head + " ...?").strip()


def infer_pressure(text: str) -> str:
    t = text.lower()
    provocative = ["офиг", "жесть", "стыдно", "тебе норм"]
    pushy = ["то есть", "в смысле", "подожди", "получается", "но", "ты же", "а есть такая проблема", "реально", "серьёзно", "правда"]
    soft = ["если можно", "можешь", "давай попробуем", "попробуем", "чуть-чуть", "можно уточнить", "расскажи", "хочется"]

    if any(m in t for m in provocative):
        return "provocative"
    if any(m in t for m in pushy):
        return "pushy"
    if any(m in t for m in soft):
        return "soft"
    return "neutral"



def skeletonize_with_llm(client: OpenAI, questions: List[str], *, model: str) -> List[Dict[str, str]]:
    qs = [q.strip() for q in questions if str(q).strip()]
    qs = qs[:TEMPLATE_TOP]

    system = (
        "Ты - лингвист-редактор. "
        "Тебе дают вопросы интервьюера. "
        "Твоя задача: для каждого вопроса сделать КАРКАС (skeleton): "
        "убрать смысловую начинку (имена, конкретные объекты, уникальные детали) "
        "и оставить только общую конструкцию, частицы, связки и ритм. "
        "Скелет должен звучать по-русски и быть пригодным как шаблон, "
        "поэтому вместо удалённых смысловых слов ставь '...'. "
        "Нельзя добавлять новые факты. Не меняй общий стиль/частицы."
    )

    user = (
            "Список вопросов (в исходном виде):\n"
            + "\n".join([f"{i + 1}) {q}" for i, q in enumerate(qs)])
            + "\n\n"
            "Верни строго JSON-массив, такой длины, как список. Каждый элемент:\n"
            "{\n"
            '  "original": "исходный вопрос без изменений",\n'
            '  "skeleton": "каркас с ... вместо смысловой начинки"\n'
            "}\n\n"
            "Правила каркаса:\n"
            "- Сохраняй порядок слов, пунктуацию, междометия, эмоции, заикания.\n"
            "- Имена/места/числа/уникальные объекты заменяй на '...'.\n"
            "- Замени смысловые части и слова на ..., т.е. то, что зависит от контекста. Нужно выделить структуру из общих слов.\n"
            "- Не упускай ничего лишнего, ничего не придумывай и не добавляй от себя.\n"
            "- Не делай список внутри skeleton; это должен быть один вопрос или несколько предложений и вопрос, если так в оригинале.\n"
            "- Заменяй на '...' только смысловые сущности: людей/роли/профессии/фильмы/проекты/предметы/места/события/конкретные ситуации.\n"
            "- Старайся оставить как можно больше исходной конструкции, меняй минимум, чтобы шаблон оставался узнаваемым.\n"
    )

    raw = responses_create_safe(
        client,
        model=model,
        input=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=0.0,
        max_output_tokens=600,
    )

    try:
        data = json.loads(raw)
        out: List[Dict[str, str]] = []
        if isinstance(data, list):
            for item in data:
                if not isinstance(item, dict):
                    continue
                o = str(item.get("original", "")).strip()
                s = str(item.get("skeleton", "")).strip()
                if o and s:
                    out.append({"original": o, "skeleton": s})
        if len(out) == len(qs):
            return out
    except Exception:
        pass

    return [{"original": q, "skeleton": to_skeleton(q)} for q in qs]


def build_template_candidates(next_questions: List[str], client: OpenAI, *, model: str, limit: int = TEMPLATE_TOP) -> List[Dict[str, Any]]:
    seen: set[str] = set()
    uniq: List[str] = []
    for q in next_questions:
        q = str(q).strip()
        if not q or q in seen:
            continue
        seen.add(q)
        uniq.append(q)
        if len(uniq) >= limit:
            break

    pairs = skeletonize_with_llm(client, uniq, model=model)

    out: List[Dict[str, Any]] = []
    for p in pairs:
        orig = str(p.get("original", "")).strip()
        sk = str(p.get("skeleton", "")).strip()
        if not orig or not sk:
            continue
        out.append(
            {
                "original_next_question": orig,
                "skeleton": sk,
                "pressure_level": infer_pressure(sk),
            }
        )

    if not out:
        out = [{"original_next_question": "", "source_next_question": "", "skeleton": "Почему ...?", "pressure_level": "neutral"}]
    return out




def build_planner_prompt(test_text: str, templates: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    system = (
        "Ты - аналитик интервью. Выбери подходящий КАРКАС вопроса (template skeleton) "
        "и спланируй следующий вопрос интервьюера. Не придумывай факты. Каркас никак не менять."
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
        '  "template_choice": template number,\n'
        '  "pressure_level": "soft|neutral|pushy|provocative",\n'
        '  "target_entity_type": "на русском: что именно ты уточняешь (3-7 слов), не списком",\n'
        '  "anchor_keywords": "2-6 слов по смыслу из последнего ответа гостя, без прямой цитаты"\n'
        "}\n\n"
        "Правила:\n"
        "- Выбранный каркас должен подходит для генерации вопроса для госят из test_text, учитывай это. \n"
        "- template_choice должен быть номером из списка шаблонов.\n"
        "- anchor_keywords - ТОЛЬКО из последнего ответа гостя; НЕ цитируй длинно.\n"
        "- pressure_level должен совпадать с выбранным шаблоном (если сомневаешься - бери шаблонный).\n"
        "- Если ни один шаблон не подходит, то верни 'Почему ...?'"
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
        "- Сохрани каркас; немного поменяй, если нужно это сделать под смысл вопроса; можно менять форму, пол, падеж, если это необходимо; заполни '...' смыслом из ТЕСТОВЫЙ ФРАГМЕНТ.\n"
        "- На месте '...' может быть 1-6 слов, не больше. \n"
        "- Конкретизируй target_entity_type.\n"
        "- Учитывай пол того, кому задают вопрос по тестовому фрагменту. И учитывай, обращаться на 'ты' или на 'вы' исходя из контекста. (ОБЯЗАТЕЛЬНО)\n"
        "- Если не знаешь имени гостя, то просто убери обращение из предложения (если оно есть в КАРКАС).\n"
        "- В сгенерированном вопросе не должно быть '...' и ошибок в структуре предложения (которые не связаны со стилем). Если ты видишь, что предложение не логичное - каркас можно немного поменять.\n"
        "- Если в каркасе нет '...', то добавь к вопросу максимум 1-6 слов."
        "- Если каркас не подходит для генерации вопроса - используй только стилистические черты из него, такие как междометия, частицы и т.д."
        "Сгенерируй вопрос. Проверь результат на 'человечность' и понятность - если не удовлетворительно, то исправь что-нибудь. В ОСТАЛЬНЫХ СЛУЧАЯХ НИЧЕГО НЕ МЕНЯЙ."
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def main() -> None:
    load_dotenv()
    ap = argparse.ArgumentParser()
    ap.add_argument("tests_dir", type=Path)
    ap.add_argument("persist_dir", type=Path)
    ap.add_argument("collection_hint", type=str, help="e.g. dud_cases_w2_e5_large or dud_cases_w2_e5_base")
    ap.add_argument("results_dir", type=Path)
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    args.results_dir.mkdir(parents=True, exist_ok=True)
    debug_dir = args.results_dir / "debug_rag"
    debug_dir.mkdir(parents=True, exist_ok=True)

    hint = args.collection_hint
    suffix = "e5_large" if "e5_large" in hint or hint.endswith("_large") else "e5_base"
    base = hint.replace("_e5_large", "").replace("_e5_base", "")

    embed_model = "intfloat/multilingual-e5-large" if suffix == "e5_large" else "intfloat/multilingual-e5-base"
    embedder = SentenceTransformer(embed_model)

    client = OpenAI(base_url=LLM_BASE_URL, api_key=(LLM_API_KEY or "EMPTY")) if LLM_BASE_URL else OpenAI()
    chroma_client = chromadb.PersistentClient(path=str(args.persist_dir))
    col_state = chroma_client.get_collection(name=f"{base}_state_{suffix}")
    col_q = chroma_client.get_collection(name=f"{base}_q_{suffix}")

    files = sorted([p for p in args.tests_dir.glob("*.txt") if p.is_file()])
    if not files:
        LOG.warning("No tests in %s", args.tests_dir)
        return

    for temp in TEMPS:
        out_rows: List[Dict[str, Any]] = []
        out_path = args.results_dir / f"chroma_cases_templates_temp_{str(temp).replace('.', '_')}.jsonl"
        LOG.info("=== temp=%s -> %s ===", temp, out_path)

        for fp in files:
            test_text = fp.read_text(encoding="utf-8", errors="replace")
            qtext = query_text_from_test(test_text)
            q_emb = embedder.encode([qtext], show_progress_bar=False, convert_to_numpy=True).astype("float32")

            res_a = col_state.query(query_embeddings=q_emb.tolist(), n_results=TOP_K, include=["documents", "metadatas", "distances"])
            res_b = col_q.query(query_embeddings=q_emb.tolist(), n_results=TOP_K, include=["documents", "metadatas", "distances"])

            docs_a = (res_a.get("documents") or [[]])[0]
            docs_b = (res_b.get("documents") or [[]])[0]
            dists_a = (res_a.get("distances") or [[]])[0]
            dists_b = (res_b.get("distances") or [[]])[0]
            metas_a = (res_a.get("metadatas") or [[]])[0]
            metas_b = (res_b.get("metadatas") or [[]])[0]

            state_hits: List[Dict[str, Any]] = []
            for i in range(min(len(docs_a), len(metas_a), len(dists_a))):
                m = metas_a[i] or {}
                state_hits.append({"rank": i + 1, "distance": dists_a[i], "document": docs_a[i], "metadata": m, "next_question": m.get("next_question")})

            question_hits: List[Dict[str, Any]] = []
            for i in range(min(len(docs_b), len(metas_b), len(dists_b))):
                m = metas_b[i] or {}
                question_hits.append({"rank": i + 1, "distance": dists_b[i], "document": docs_b[i], "metadata": m, "next_question": m.get("next_question")})

            found_nextq: List[str] = []
            for h in state_hits:
                nq = h.get("next_question")
                if nq:
                    found_nextq.append(str(nq))
            for h in question_hits:
                nq = h.get("next_question")
                if nq:
                    found_nextq.append(str(nq))

            template_candidates = build_template_candidates(found_nextq, client, model=LLM_MODEL, limit=TEMPLATE_TOP)

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
                    "collection_base": base,
                    "suffix": suffix,
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
                    "method": "rag_chroma_cases_templates",
                    "llm_model": LLM_MODEL,
                    "temperature": temp,
                    "top_k": TOP_K,
                    "embed_model": embed_model,
                    "collection_base": base,
                    "suffix": suffix,
                    "plan_json": plan,
                    "chosen_template": chosen_template.get("skeleton"),
                    "generated_question": q,
                }
            )
            LOG.info("OK %s -> %s", fp.name, q)

        with out_path.open("w", encoding="utf-8") as f:
            for r in out_rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        LOG.info("Wrote %s (%d rows)", out_path, len(out_rows))


if __name__ == "__main__":
    main()
