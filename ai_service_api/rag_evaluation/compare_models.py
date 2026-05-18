import argparse
import logging
import re
from pathlib import Path

from rag_evaluation.dataset import load_all_chunks, sample_holdout
from rag_evaluation.index_builder import BenchmarkIndexBuilder, IndexBuildStats
from rag_evaluation.report import save_json, save_markdown
from rag_evaluation.runner import BenchmarkResult, run_benchmark

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("rag_evaluation")

DEFAULT_CHARACTER = "dud"
DEFAULT_CLEANED_ROOT = Path("ai_service/data/cleaned")
DEFAULT_OUTPUT_DIR = Path("rag_evaluation/results")
DEFAULT_TEST_DATA_DIR = Path("rag_evaluation/test_data")

DEFAULT_MODELS = [
    "intfloat/multilingual-e5-small",
    "intfloat/multilingual-e5-base",
    "intfloat/multilingual-e5-large",
    "BAAI/bge-m3",
    "deepvk/USER-bge-m3",
    "ai-forever/ru-en-RoSBERTa",
]


def _safe_dir_name(model_name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]+", "__", model_name)


def main() -> None:
    parser = argparse.ArgumentParser(description="Сравнение моделей эмбеддингов на одном персонаже")
    parser.add_argument("--character", default=DEFAULT_CHARACTER,
                        help="Идентификатор персонажа (по умолчанию dud)")
    parser.add_argument("--holdout", type=int, default=50,
                        help="Размер hold-out выборки")
    parser.add_argument("--seed", type=int, default=42,
                        help="Seed для воспроизводимости hold-out")
    parser.add_argument("--models", nargs="+", default=DEFAULT_MODELS,
                        help="Список моделей HuggingFace для сравнения")
    parser.add_argument("--k-values", type=int, nargs="+", default=[1, 3, 5, 10],
                        help="Какие K считать для recall@K")
    parser.add_argument("--cleaned-root", type=Path, default=DEFAULT_CLEANED_ROOT)
    parser.add_argument("--test-data-dir", type=Path, default=DEFAULT_TEST_DATA_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--warmup", type=int, default=2,
                        help="Сколько warmup-запросов перед замером")
    parser.add_argument("--skip-existing", action="store_true",
                        help="Не пересобирать индекс, если его папка уже существует")
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.test_data_dir.mkdir(parents=True, exist_ok=True)

    cleaned_dir = args.cleaned_root / args.character
    if not cleaned_dir.exists():
        raise FileNotFoundError(f"cleaned dir not found: {cleaned_dir}")

    logger.info("loading all chunks from %s", cleaned_dir)
    all_chunks = load_all_chunks(cleaned_dir)
    logger.info("loaded %d chunks", len(all_chunks))

    holdout = sample_holdout(all_chunks, args.holdout, seed=args.seed)
    logger.info("sampled holdout of %d queries (seed=%d)", len(holdout), args.seed)

    results: list[tuple[BenchmarkResult, IndexBuildStats]] = []

    for model_name in args.models:
        safe_name = _safe_dir_name(model_name)
        persist_dir = args.test_data_dir / safe_name
        collection_name = f"{args.character}_rag"

        index_exists = (persist_dir / "chroma.sqlite3").exists() or any(persist_dir.glob("**/*"))
        if args.skip_existing and index_exists:
            logger.info("[%s] index already exists, skipping build", model_name)
            build_stats = IndexBuildStats(
                model_name=model_name, chunks_count=len(all_chunks),
                embed_seconds=0.0, upsert_seconds=0.0,
                total_seconds=0.0, model_load_seconds=0.0,
            )
        else:
            logger.info("[%s] building index at %s", model_name, persist_dir)
            builder = BenchmarkIndexBuilder(
                model_name=model_name,
                persist_dir=persist_dir,
                collection_name=collection_name,
            )
            build_stats = builder.build(all_chunks)
            logger.info(
                "[%s] index built: %d chunks, %.1fs (load %.1fs, embed %.1fs, upsert %.1fs)",
                model_name, build_stats.chunks_count, build_stats.total_seconds,
                build_stats.model_load_seconds, build_stats.embed_seconds, build_stats.upsert_seconds,
            )

        logger.info("[%s] running benchmark", model_name)
        bench = run_benchmark(
            model_name=model_name,
            persist_dir=persist_dir,
            collection_name=collection_name,
            holdout=holdout,
            k_values=tuple(args.k_values),
            warmup_queries=args.warmup,
        )
        logger.info(
            "[%s] recall@1=%.3f recall@5=%.3f recall@10=%.3f total_p50=%.1fms total_p95=%.1fms",
            model_name,
            bench.recall_at_k.get(1, 0.0),
            bench.recall_at_k.get(5, 0.0),
            bench.recall_at_k.get(10, 0.0),
            bench.total_latency_p50_ms,
            bench.total_latency_p95_ms,
        )

        results.append((bench, build_stats))

    save_json(results, args.output_dir / "comparison.json")
    save_markdown(
        results,
        args.output_dir / "comparison.md",
        character_id=args.character,
        chunks_count=len(all_chunks),
        holdout_size=len(holdout),
    )
    logger.info("saved comparison to %s", args.output_dir)


if __name__ == "__main__":
    main()
