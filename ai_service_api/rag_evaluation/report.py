import json
from dataclasses import asdict
from pathlib import Path

from rag_evaluation.index_builder import IndexBuildStats
from rag_evaluation.runner import BenchmarkResult


def save_json(
    results: list[tuple[BenchmarkResult, IndexBuildStats]],
    out_path: Path,
) -> None:
    payload = [
        {"benchmark": asdict(r), "build": asdict(b)}
        for r, b in results
    ]
    out_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def save_markdown(
    results: list[tuple[BenchmarkResult, IndexBuildStats]],
    out_path: Path,
    character_id: str,
    chunks_count: int,
    holdout_size: int,
) -> None:
    if not results:
        out_path.write_text("# Сравнение моделей эмбеддингов\n\nНет результатов.\n", encoding="utf-8")
        return

    k_values = results[0][0].k_values

    lines: list[str] = []
    lines.append("# Сравнение моделей эмбеддингов для RAG")
    lines.append("")
    lines.append(f"**Персонаж**: `{character_id}` | **Чанков в индексе**: {chunks_count} | **Hold-out**: {holdout_size}")
    lines.append("")
    lines.append(
        "Релевантность: чанк считается релевантным, если у него тот же `interview_id`, "
        "что и у holdout-запроса. Self-hit исключается. Замеры латентности — после прогрева."
    )
    lines.append("")

    lines.append("## Качество поиска (recall@K)")
    lines.append("")
    header = "| Модель | dim | " + " | ".join(f"recall@{k}" for k in k_values) + " | mean top-1 dist |"
    sep = "|" + "|".join(["---"] * (3 + len(k_values))) + "|"
    lines.append(header)
    lines.append(sep)
    for r, _ in results:
        row = (
            f"| `{r.model_name}` | {r.embedding_dim} | "
            + " | ".join(f"{r.recall_at_k[k]:.3f}" for k in k_values)
            + f" | {r.mean_top1_distance:.4f} |"
        )
        lines.append(row)
    lines.append("")

    lines.append("## Латентность retrieval (мс на запрос, после прогрева)")
    lines.append("")
    lines.append("| Модель | embed p50 | embed p95 | search p50 | search p95 | total p50 | total p95 |")
    lines.append("|---|---|---|---|---|---|---|")
    for r, _ in results:
        lines.append(
            f"| `{r.model_name}` | "
            f"{r.embed_latency_p50_ms:.1f} | {r.embed_latency_p95_ms:.1f} | "
            f"{r.search_latency_p50_ms:.1f} | {r.search_latency_p95_ms:.1f} | "
            f"{r.total_latency_p50_ms:.1f} | {r.total_latency_p95_ms:.1f} |"
        )
    lines.append("")

    lines.append("## Стоимость построения индекса")
    lines.append("")
    lines.append("| Модель | загрузка модели (с) | эмбеддинг (с) | upsert в Chroma (с) | всего (с) |")
    lines.append("|---|---|---|---|---|")
    for _, b in results:
        lines.append(
            f"| `{b.model_name}` | "
            f"{b.model_load_seconds:.1f} | {b.embed_seconds:.1f} | "
            f"{b.upsert_seconds:.1f} | {b.total_seconds:.1f} |"
        )
    lines.append("")

    lines.append("## Конфигурация")
    lines.append("")
    lines.append(f"- Векторное хранилище: ChromaDB (cosine, HNSW)")
    lines.append(f"- K-значения: {', '.join(str(k) for k in k_values)}")
    lines.append("- Все модели запускались на CPU")
    lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")
