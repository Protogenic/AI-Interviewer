import random
from dataclasses import dataclass
from pathlib import Path

from ai_service.offline_pipeline.indexing.chunking import Chunking
from ai_service.offline_pipeline.indexing.index_builder import load_replicas_from_file
from ai_service.models.rag import RagChunk


@dataclass
class RagQuery:
    chunk_id: str
    interview_id: str
    question_text: str
    answer_text: str | None


def _make_id(interview_id: str, source_file: str, replica_id: int) -> str:
    return f"{interview_id}::{source_file}::{replica_id}"


def load_all_chunks(cleaned_dir: Path) -> list[RagChunk]:
    chunking = Chunking()
    all_chunks: list[RagChunk] = []
    for p in sorted(cleaned_dir.glob("**/*")):
        if p.is_dir():
            continue
        if p.suffix.lower() not in {".json", ".jsonl"}:
            continue
        replicas = load_replicas_from_file(p)
        all_chunks.extend(chunking.build_qa_chunks(replicas))
    if not all_chunks:
        raise RuntimeError(f"no chunks found in {cleaned_dir}")
    return all_chunks


def sample_holdout(
    all_chunks: list[RagChunk],
    holdout_size: int,
    seed: int = 42,
) -> list[RagQuery]:
    rng = random.Random(seed)
    holdout_size = min(holdout_size, len(all_chunks))
    sampled = rng.sample(all_chunks, holdout_size)
    return [
        RagQuery(
            chunk_id=_make_id(c.interview_id, c.source_file, c.question_replica_id),
            interview_id=c.interview_id,
            question_text=c.question_text,
            answer_text=c.answer_text,
        )
        for c in sampled
    ]
