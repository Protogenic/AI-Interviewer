import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import chromadb
import logging
from collections import Counter

from ai_service.models.rag import RagIndexConfig
from ai_service.offline_pipeline.indexing.chunking import Chunking
from ai_service.offline_pipeline.indexing.embedding import E5SentenceTransformerEmbedder
from ai_service.exeptions.generation_error import (
    DataDirectoryNotFoundError,
    DuplicateChunkError,
    IndexBuildError,
    IndexStorageError,
)

logger = logging.getLogger(__name__)

def load_replicas_from_file(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return []

    replicas: list[dict[str, Any]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            replicas.append(json.loads(line))
        except json.JSONDecodeError as e:
            raise IndexBuildError(
                character_id=str(path),
                reason=f"invalid JSON on line {line} of '{path}': {e}",
            ) from e
    return replicas


class OfflineRagIndexBuilder:
    def __init__(self, config: RagIndexConfig, batch_size: int = 256) -> None:
        self.config = config
        self.batch_size = batch_size
        self.embedder = E5SentenceTransformerEmbedder(model_name=config.model_name)
        self.chunking = Chunking()

    def build(self) -> None:
        self._validate_dirs()

        self.config.persist_dir.mkdir(parents=True, exist_ok=True)
        self.config.manifest_path.parent.mkdir(parents=True, exist_ok=True)

        client = chromadb.PersistentClient(path=str(self.config.persist_dir))

        try:
            client.delete_collection(name=self.config.collection_name)
        except Exception:
            pass

        collection = client.get_or_create_collection(
            name=self.config.collection_name,
            metadata={"hnsw:space": "cosine"},
        )

        chunks = self._load_all_chunks(self.config.data_dir)
        if not chunks:
            self._write_manifest(chunks_count=0)
            return

        logger.info(f"Total chunks: {len(chunks)}")

        for batch in self.chunking.batched(chunks, self.batch_size):
            ids = [self._make_id(c.interview_id, c.source_file, c.question_replica_id) for c in batch]
            documents = [c.passage_text for c in batch]
            metadatas = [
                {
                    "interview_id": c.interview_id,
                    "source_file": c.source_file,
                    "question_replica_id": c.question_replica_id,
                    "question_text": c.question_text,
                    "answer_text": c.answer_text or "",
                }
                for c in batch
            ]

            embeddings = self.embedder.embed_passages(documents)

            c = Counter(ids)
            dups = [k for k, v in c.items() if v > 1]
            if dups:
                for d in dups[:5]:
                    idxs = [i for i, x in enumerate(ids) if x == d]
                    for pos in idxs:
                        ch = batch[pos]
                        logger.error("  chunk: %s %s %s", ch.interview_id, ch.source_file, ch.question_replica_id)
                raise DuplicateChunkError(duplicate_ids=dups)

            try:
                collection.upsert(
                    ids=ids,
                    documents=documents,
                    metadatas=metadatas,
                    embeddings=embeddings,
                )
            except Exception as e:
                raise IndexStorageError(
                    character_id=self.config.character_id,
                    reason=str(e),
                ) from e

        self._write_manifest(chunks_count=len(chunks))

    def _validate_dirs(self) -> None:
        if not self.config.data_dir.exists():
            raise DataDirectoryNotFoundError(path=str(self.config.data_dir))

    def _load_all_chunks(self, data_dir: Path):
        chunks = []
        for p in sorted(data_dir.glob("**/*")):
            if p.is_dir():
                continue
            if p.suffix.lower() not in {".json", ".jsonl"}:
                continue
            replicas = load_replicas_from_file(p)
            chunks.extend(self.chunking.build_qa_chunks(replicas))
        return chunks

    @staticmethod
    def _make_id(interview_id: str, source_file: str, replica_id: int) -> str:
        return f"{interview_id}::{source_file}::{replica_id}"

    def _write_manifest(self, chunks_count: int) -> None:
        manifest = {
            "character_id": self.config.character_id,
            "collection_name": self.config.collection_name,
            "model_name": self.config.model_name,
            "data_dir": str(self.config.data_dir),
            "persist_dir": str(self.config.persist_dir),
            "chunks_count": chunks_count,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self.config.manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )