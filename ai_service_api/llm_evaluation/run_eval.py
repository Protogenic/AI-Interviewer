import argparse
import asyncio
import logging
import sys

from llm_evaluation.config import ALL_PROVIDERS, JUDGE_API_KEY, RESULTS_DIR
from llm_evaluation.judge import LLMJudge, scores_to_dict
from llm_evaluation.report import save_reports
from llm_evaluation.runner import (
    run_all_providers,
    save_raw_results,
    load_raw_results,
)
from llm_evaluation.style_scorer import StyleScorer, add_style_scores
from llm_evaluation.test_cases import TEST_CASES

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def _filter_providers(labels: str | None):
    if not labels:
        return ALL_PROVIDERS
    wanted = {l.strip().lower() for l in labels.split(",")}
    filtered = [p for p in ALL_PROVIDERS if any(w in p.label.lower() for w in wanted)]
    if not filtered:
        logger.error("No providers matched: %s", labels)
        sys.exit(1)
    return filtered


async def _run_judge(results: list[dict]) -> list[dict]:
    if not JUDGE_API_KEY:
        logger.warning("OPENAI_API_KEY not set — skipping judge evaluation.")
        return results

    judge = LLMJudge(api_key=JUDGE_API_KEY)
    case_map = {tc.id: tc for tc in TEST_CASES}

    items = []
    indices = []
    for i, r in enumerate(results):
        raw = r.get("metrics", {}).get("raw_response", "")
        tc = case_map.get(r["case_id"])
        if raw and tc:
            items.append((tc, raw, r.get("last_answer", "")))
            indices.append(i)

    logger.info("Running judge on %d responses …", len(items))
    scores_list = await judge.evaluate_batch(items, concurrency=5)

    for idx, scores in zip(indices, scores_list):
        results[idx]["judge"] = scores_to_dict(scores)

    return results


async def main(args: argparse.Namespace) -> None:
    if args.judge_only:
        logger.info("Judge-only mode: loading raw_results.json …")
        results = load_raw_results()
        results = await _run_judge(results)
        try:
            scorer = StyleScorer()
            results = add_style_scores(results, scorer)
        except ImportError:
            logger.warning("sentence-transformers not installed — skipping style cosine.")
        save_raw_results(results, "raw_results.json")
        save_reports(results)
        return

    providers = _filter_providers(args.providers)
    active = [p for p in providers if p.api_key]
    skipped = [p for p in providers if not p.api_key]

    if skipped:
        logger.warning("Skipped (no API key): %s", ", ".join(p.label for p in skipped))
    if not active:
        logger.error("No providers with API keys. Set the required env vars.")
        sys.exit(1)

    logger.info(
        "Starting evaluation: %d providers × %d test cases = %d LLM calls",
        len(active), len(TEST_CASES), len(active) * len(TEST_CASES),
    )

    results = await run_all_providers(active, TEST_CASES)
    save_raw_results(results)

    if not args.skip_judge:
        results = await _run_judge(results)

    logger.info("Computing style cosine similarity …")
    try:
        scorer = StyleScorer()
        results = add_style_scores(results, scorer)
    except ImportError:
        logger.warning("sentence-transformers not installed — skipping style cosine. "
                       "Install with: pip install sentence-transformers")

    save_raw_results(results, "raw_results.json")
    save_reports(results)
    logger.info("Done.")


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="LLM evaluation pipeline")
    p.add_argument(
        "--providers",
        default=None,
        help="Comma-separated provider labels to test, e.g. 'openai,deepseek'. "
             "Default: all configured providers.",
    )
    p.add_argument(
        "--skip-judge",
        action="store_true",
        help="Skip GPT-4o judge evaluation (objective metrics only).",
    )
    p.add_argument(
        "--judge-only",
        action="store_true",
        help="Re-run judge on previously saved raw_results.json.",
    )
    return p.parse_args()


if __name__ == "__main__":
    asyncio.run(main(_parse_args()))
