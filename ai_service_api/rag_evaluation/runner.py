import logging
import statistics
import time
from dataclasses import dataclass, field
from pathlib import Path

import chromadb
import numpy as np
from sentence_transformers import SentenceTransformer

from rag_evaluation.dataset import RagQuery

logger = logging.getLogger(__name__)


@dataclass
class QueryResult:
    query_chunk_id: str
    expected_interview_id: str
    hits_per_k: dict[int, bool]
    top1_distance: float
    returned_interview_ids: list[str]
    embed_latency_ms: float
    search_latency_ms: float
    total_latency_ms: float


@dataclass
class BenchmarkResult:
    model_name: str
    embedding_dim: int
    holdout_size: int
    k_values: list[int]
    recall_at_k: dict[int, float] = field(default_factory=dict)
    mean_top1_distance: float = 0.0
    embed_latency_p50_ms: float = 0.0
    embed_latency_p95_ms: float = 0.0
    search_latency_p50_ms: float = 0.0
    search_latency_p95_ms: float = 0.0
    total_latency_p50_ms: float = 0.0
    total_latency_p95_ms: float = 0.0
    per_query_results: list[QueryResult] = field(default_factory=list)


def _percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    k = (len(s) - 1) * p
    f = int(k)
    c = min(f + 1, len(s) - 1)
    if f == c:
        return s[f]
    return s[f] + (s[c] - s[f]) * (k - f)


def run_benchmark(
    model_name: str,
    persist_dir: Path,
    collection_name: str,
    holdout: list[RagQuery],
    k_values: tuple[int, ...] = (1, 3, 5, 10),
    warmup_queries: int = 2,
) -> BenchmarkResult:
    logger.info("[%s] loading model for query phase", model_name)
    model = SentenceTransformer(model_name)
    client = chromadb.PersistentClient(path=str(persist_dir))
    collection = client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )

    max_k = max(k_values)
    n_request = max_k + 1

    if warmup_queries > 0:
        warmup_text = holdout[0].question_text if holdout else "warmup"
        for _ in range(warmup_queries):
            emb = model.encode([f"query: {warmup_text}"], normalize_embeddings=True)
            collection.query(query_embeddings=np.asarray(emb).tolist(), n_results=1)

    per_query: list[QueryResult] = []

    for q in holdout:
        t0 = time.perf_counter()
        emb = model.encode([f"query: {q.question_text}"], normalize_embeddings=True)
        emb_list = np.asarray(emb, dtype=np.float32).tolist()
        t1 = time.perf_counter()
        res = collection.query(
            query_embeddings=emb_list,
            n_results=n_request,
            include=["metadatas", "distances"],
        )
        t2 = time.perf_counter()

        ids_row = (res.get("ids") or [[]])[0]
        metadatas = (res.get("metadatas") or [[]])[0]
        distances = (res.get("distances") or [[]])[0]

        filtered: list[tuple[str, str, float]] = []
        for rid, md, dist in zip(ids_row, metadatas, distances):
            if rid == q.chunk_id:
                continue
            filtered.append((rid, str(md.get("interview_id", "")), float(dist)))
            if len(filtered) >= max_k:
                break

        returned_interview_ids = [iv for _, iv, _ in filtered]
        top1_distance = filtered[0][2] if filtered else 0.0

        hits_per_k = {
            k: any(iv == q.interview_id for iv in returned_interview_ids[:k])
            for k in k_values
        }

        per_query.append(QueryResult(
            query_chunk_id=q.chunk_id,
            expected_interview_id=q.interview_id,
            hits_per_k=hits_per_k,
            top1_distance=top1_distance,
            returned_interview_ids=returned_interview_ids,
            embed_latency_ms=(t1 - t0) * 1000.0,
            search_latency_ms=(t2 - t1) * 1000.0,
            total_latency_ms=(t2 - t0) * 1000.0,
        ))

    recall_at_k = {
        k: sum(1 for r in per_query if r.hits_per_k[k]) / len(per_query)
        for k in k_values
    }
    top1_dists = [r.top1_distance for r in per_query if r.top1_distance]
    mean_top1 = statistics.mean(top1_dists) if top1_dists else 0.0

    embed_lat = [r.embed_latency_ms for r in per_query]
    search_lat = [r.search_latency_ms for r in per_query]
    total_lat = [r.total_latency_ms for r in per_query]

    embedding_dim = int(model.get_embedding_dimension() or 0)

    return BenchmarkResult(
        model_name=model_name,
        embedding_dim=embedding_dim,
        holdout_size=len(holdout),
        k_values=list(k_values),
        recall_at_k=recall_at_k,
        mean_top1_distance=mean_top1,
        embed_latency_p50_ms=_percentile(embed_lat, 0.5),
        embed_latency_p95_ms=_percentile(embed_lat, 0.95),
        search_latency_p50_ms=_percentile(search_lat, 0.5),
        search_latency_p95_ms=_percentile(search_lat, 0.95),
        total_latency_p50_ms=_percentile(total_lat, 0.5),
        total_latency_p95_ms=_percentile(total_lat, 0.95),
        per_query_results=per_query,
    )
