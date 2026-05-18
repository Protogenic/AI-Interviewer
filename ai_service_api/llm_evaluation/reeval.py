import argparse
import asyncio
import csv
import json
import logging
import sys
import time
from collections import defaultdict
from pathlib import Path

from openai import AsyncOpenAI, BadRequestError

from llm_evaluation.config import ALL_PROVIDERS, JUDGE_API_KEY, EVAL_MAX_TOKENS
from llm_evaluation.judge import LLMJudge, scores_to_dict
from llm_evaluation.metrics import compute, metrics_to_dict
from llm_evaluation.style_scorer import StyleScorer, add_style_scores
from llm_evaluation.test_cases import TEST_CASES

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("reeval")

DEFAULT_PROVIDERS = [
    "openai/gpt-4o-mini",
    "or/mistral-small-3.1",
    "or/deepseek-chat",
    "or/gemini-2.0-flash",
    "or/llama-3.1-8b",
]

REEVAL_TEMPERATURE = 0.7
DEFAULT_REPEATS = 5

BOOL_METRICS = ["json_valid", "parts_count_correct", "roles_correct", "no_forbidden_punct", "fully_compliant"]
NUM_METRICS = ["word_count_mae", "latency_s", "cost_usd"]
TOP_LEVEL = ["style_cosine"]
JUDGE_FIELDS = ["style", "language", "emotion", "overall"]


async def _call(client: AsyncOpenAI, model: str, system: str, user: str, use_json_mode: bool):
    kwargs: dict = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": REEVAL_TEMPERATURE,
        "max_tokens": EVAL_MAX_TOKENS,
    }
    if use_json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    try:
        resp = await client.chat.completions.create(**kwargs)
    except BadRequestError as e:
        if use_json_mode and "response_format" in str(e).lower():
            kwargs.pop("response_format", None)
            resp = await client.chat.completions.create(**kwargs)
        else:
            raise
    content = resp.choices[0].message.content or ""
    u = resp.usage
    return content, (u.prompt_tokens if u else 0), (u.completion_tokens if u else 0)


def _last_answer(user_prompt: str) -> str:
    for line in user_prompt.splitlines():
        if line.startswith("# ПОСЛЕДНЯЯ РЕПЛИКА ГОСТЯ:"):
            return line.split(":", 1)[-1].strip()
    return ""


async def run_one_provider(provider, repeats: int) -> list[dict]:
    if not provider.api_key:
        log.warning("Skipping %s (no API key)", provider.label)
        return []
    client_kwargs: dict = {"api_key": provider.api_key}
    if provider.base_url:
        client_kwargs["base_url"] = provider.base_url
    client = AsyncOpenAI(**client_kwargs)

    out: list[dict] = []
    for tc in TEST_CASES:
        for k in range(repeats):
            if provider.request_delay > 0:
                await asyncio.sleep(provider.request_delay)
            log.info("[%s] %s rep %d/%d", provider.label, tc.id, k + 1, repeats)
            t0 = time.perf_counter()
            try:
                raw, in_tok, out_tok = await _call(
                    client, provider.model, tc.system_prompt, tc.user_prompt, provider.use_json_mode
                )
            except Exception as e:
                log.error("FAIL [%s] %s: %s", provider.label, tc.id, e)
                raw, in_tok, out_tok = "", 0, 0
            latency = time.perf_counter() - t0
            m = compute(
                raw_response=raw, test_case=tc, latency_s=latency,
                input_tokens=in_tok, output_tokens=out_tok,
                price_input=provider.price_input, price_output=provider.price_output,
            )
            out.append({
                "provider": provider.label,
                "case_id": tc.id,
                "interviewer": tc.interviewer,
                "emotion": tc.emotion,
                "structure": tc.structure,
                "target_words": tc.target_words,
                "repeat": k,
                "metrics": metrics_to_dict(m),
                "last_answer": _last_answer(tc.user_prompt),
            })
    return out


async def run_judge(results: list[dict]) -> list[dict]:
    if not JUDGE_API_KEY:
        log.warning("OPENAI_API_KEY not set → skip judge")
        return results
    judge = LLMJudge(api_key=JUDGE_API_KEY)
    cmap = {tc.id: tc for tc in TEST_CASES}
    items, idxs = [], []
    for i, r in enumerate(results):
        raw = r["metrics"].get("raw_response", "")
        tc = cmap.get(r["case_id"])
        if raw and tc:
            items.append((tc, raw, r.get("last_answer", "")))
            idxs.append(i)
    log.info("Judge на %d ответах…", len(items))
    scores = await judge.evaluate_batch(items, concurrency=5)
    for i, s in zip(idxs, scores):
        results[i]["judge"] = scores_to_dict(s)
    return results


def _bool_to_float(v) -> float | None:
    if v is True:
        return 1.0
    if v is False:
        return 0.0
    return None


def _extract_value(r: dict, key: str) -> float | None:
    if key in BOOL_METRICS:
        return _bool_to_float(r["metrics"].get(key))
    if key in NUM_METRICS:
        v = r["metrics"].get(key)
        return None if v is None else float(v)
    if key in TOP_LEVEL:
        v = r.get(key)
        return None if v is None else float(v)
    if key.startswith("judge_"):
        sub = key[len("judge_"):]
        v = (r.get("judge") or {}).get(sub)
        return None if v is None else float(v)
    return None


def summarize(results: list[dict], out_dir: Path) -> None:
    keys = BOOL_METRICS + NUM_METRICS + TOP_LEVEL + [f"judge_{j}" for j in JUDGE_FIELDS]

    per_case: dict[str, dict[str, dict[str, list[float]]]] = defaultdict(
        lambda: defaultdict(lambda: defaultdict(list))
    )
    for r in results:
        prov = r["provider"]
        case = r["case_id"]
        for k in keys:
            v = _extract_value(r, k)
            if v is None:
                continue
            per_case[prov][k][case].append(v)

    rows = []
    for prov in sorted(per_case):
        any_metric = next(iter(per_case[prov].values()))
        n_cases = len(any_metric)
        repeats_per_case = [len(v) for v in any_metric.values()]
        mean_repeats = sum(repeats_per_case) / len(repeats_per_case) if repeats_per_case else 0
        row = {
            "provider": prov,
            "n_cases": n_cases,
            "repeats_per_case": f"{mean_repeats:.1f}",
        }
        for k in keys:
            case_map = per_case[prov].get(k, {})
            per_case_means = [sum(vs) / len(vs) for vs in case_map.values() if vs]
            mean = sum(per_case_means) / len(per_case_means) if per_case_means else None
            row[f"{k}_mean"] = "" if mean is None else f"{mean:.4f}"
        rows.append(row)

    fields = ["provider", "n_cases", "repeats_per_case"] + [f"{k}_mean" for k in keys]

    csv_path = out_dir / "reeval_summary.csv"
    md_path = out_dir / "reeval_summary.md"

    with csv_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    with md_path.open("w", encoding="utf-8") as f:
        header = "| Provider | n_cases | repeats | " + " | ".join(keys) + " |"
        sep = "|" + "|".join(["---"] * (len(keys) + 3)) + "|"
        f.write(header + "\n" + sep + "\n")
        for r in rows:
            cells = [r["provider"], str(r["n_cases"]), r["repeats_per_case"]]
            for k in keys:
                cells.append(r.get(f"{k}_mean") or "—")
            f.write("| " + " | ".join(cells) + " |\n")

    log.info("Wrote %s", csv_path)
    log.info("Wrote %s", md_path)


async def amain(args: argparse.Namespace) -> None:
    wanted = {l.strip() for l in args.providers.split(",")} if args.providers else set(DEFAULT_PROVIDERS)
    providers = [p for p in ALL_PROVIDERS if p.label in wanted]
    if not providers:
        log.error("No providers matched: %s", wanted)
        sys.exit(1)
    log.info(
        "Re-eval: %s | repeats=%d | T=%.2f",
        [p.label for p in providers], args.repeats, REEVAL_TEMPERATURE,
    )
    log.info(
        "Всего вызовов LLM: %d моделей × %d кейсов × %d повторов = %d",
        len(providers), len(TEST_CASES), args.repeats,
        len(providers) * len(TEST_CASES) * args.repeats,
    )

    all_results: list[dict] = []
    for p in providers:
        all_results.extend(await run_one_provider(p, args.repeats))

    if not args.skip_judge:
        all_results = await run_judge(all_results)

    log.info("Считаю style cosine…")
    try:
        scorer = StyleScorer()
        all_results = add_style_scores(all_results, scorer)
    except ImportError:
        log.warning("sentence-transformers не установлен → пропускаю style_cosine")

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "raw_results.json").write_text(
        json.dumps(all_results, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    log.info("Saved raw_results.json")
    summarize(all_results, out_dir)


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Re-eval models with averaged repeats.")
    p.add_argument("--providers", default=None,
                   help=f"Comma-separated labels. Default: {','.join(DEFAULT_PROVIDERS)}")
    p.add_argument("--repeats", type=int, default=DEFAULT_REPEATS,
                   help=f"Repeats per test case (default: {DEFAULT_REPEATS})")
    p.add_argument("--out-dir", default="llm_evaluation/results_reeval")
    p.add_argument("--skip-judge", action="store_true")
    return p.parse_args()


if __name__ == "__main__":
    asyncio.run(amain(_parse_args()))
