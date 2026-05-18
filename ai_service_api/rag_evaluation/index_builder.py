import logging
import time
from dataclasses import dataclass
from pathlib import Path

import chromadb
import numpy as np
from sentence_transformers import SentenceTransformer

from ai_service.models.rag import RagChunk

logger = logging.getLogger(__name__)


@dataclass
class IndexBuildStats:
    model_name: str
    chunks_count: int
    embed_seconds: float
    upsert_seconds: float
    total_seconds: float
    model_load_seconds: float


class BenchmarkIndexBuilder:
    def __init__(
        self,
        model_name: str,
        persist_dir: Path,
        collection_name: str = "dud_rag",
        batch_size: int = 256,
    ) -> None:
        self.model_name = model_name
        self.persist_dir = persist_dir
        self.collection_name = collection_name
        self.batch_size = batch_size

    def build(self, chunks: list[RagChunk]) -> IndexBuildStats:
        t_start = time.perf_counter()
        self.persist_dir.mkdir(parents=True, exist_ok=True)

        logger.info("[%s] loading model", self.model_name)
        t_model = time.perf_counter()
        model = SentenceTransformer(self.model_name)
        model_load_seconds = time.perf_counter() - t_model

        client = chromadb.PersistentClient(path=str(self.persist_dir))
        try:
            client.delete_collection(name=self.collection_name)
        except Exception:
            pass
        collection = client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )

        seen_ids: set[str] = set()

        embed_seconds = 0.0
        upsert_seconds = 0.0

        for start in range(0, len(chunks), self.batch_size):
            batch = chunks[start: start + self.batch_size]
            ids: list[str] = []
            documents: list[str] = []
            metadatas: list[dict] = []
            for c in batch:
                cid = f"{c.interview_id}::{c.source_file}::{c.question_replica_id}"
                if cid in seen_ids:
                    continue
                seen_ids.add(cid)
                ids.append(cid)
                documents.append(c.passage_text)
                metadatas.append({
                    "interview_id": c.interview_id,
                    "source_file": c.source_file,
                    "question_replica_id": c.question_replica_id,
                    "question_text": c.question_text,
                    "answer_text": c.answer_text or "",
                })
            if not ids:
                continue

            t1 = time.perf_counter()
            texts = [f"passage: {d}" for d in documents]
            emb = model.encode(texts, normalize_embeddings=True, batch_size=64)
            emb_list = np.asarray(emb, dtype=np.float32).tolist()
            t2 = time.perf_counter()
            embed_seconds += (t2 - t1)

            collection.upsert(ids=ids, documents=documents, metadatas=metadatas, embeddings=emb_list)
            t3 = time.perf_counter()
            upsert_seconds += (t3 - t2)

        total = time.perf_counter() - t_start
        return IndexBuildStats(
            model_name=self.model_name,
            chunks_count=len(seen_ids),
            embed_seconds=embed_seconds,
            upsert_seconds=upsert_seconds,
            total_seconds=total,
            model_load_seconds=model_load_seconds,
        )
