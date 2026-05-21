"""Онлайн-поиск по RAG-индексу ChromaDB для подбора похожих примеров диалога."""

import json
import chromadb

from ai_service.models.rag import RagExample, RagIndexConfig
from ai_service.offline_pipeline.indexing.embedding import E5SentenceTransformerEmbedder
from ai_service.exeptions.generation_error import (
    RagIndexNotFoundError,
    RagManifestCorruptedError,
    RagSearchError,
    RagStoreUnavailableError,
)


class OnlineRagSearchService:
    """Загружает ChromaDB-индекс интервьюера и выполняет семантический поиск похожих пар."""

    def __init__(self, config: RagIndexConfig) -> None:
        self.config = config
        self.embedder = E5SentenceTransformerEmbedder(model_name=config.model_name)

        if not self.config.manifest_path.exists():
            raise RagIndexNotFoundError(
                character_id=config.character_id,
                missing_path=str(config.manifest_path),
            )
        if not self.config.persist_dir.exists():
            raise RagIndexNotFoundError(
                character_id=config.character_id,
                missing_path=str(config.persist_dir),
            )

        try:
            self._manifest = json.loads(self.config.manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            raise RagManifestCorruptedError(
                character_id=config.character_id,
                manifest_path=str(config.manifest_path),
                reason=str(e),
            ) from e

        try:
            self._client = chromadb.PersistentClient(path=str(self.config.persist_dir))
            self._collection = self._client.get_or_create_collection(
                name=self.config.collection_name,
                metadata={"hnsw:space": "cosine"},
            )
        except Exception as e:
            raise RagStoreUnavailableError(
                character_id=config.character_id,
                persist_dir=str(config.persist_dir),
                reason=str(e),
            ) from e

    def search(self, last_question: str | None, last_answer: str | None, k: int = 2) -> list[RagExample]:
        """Возвращает k наиболее похожих примеров по последнему вопросу и ответу.
        Если оба аргумента пусты, то возвращает пустой список без обращения к индексу."""
        q = (last_question or "").strip()
        a = (last_answer or "").strip()
        if not q and not a:
            return []

        parts = []
        if q:
            parts.append(f"Вопрос интервьюера: {q}")
        if a:
            parts.append(f"Ответ гостя: {a}")
        query_text = "\n".join(parts)

        query_emb = self.embedder.embed_queries([query_text])

        try:
            res = self._collection.query(
                query_embeddings=query_emb,
                n_results=k,
                include=["metadatas", "distances"],
            )
        except Exception as e:
            raise RagSearchError(
                character_id=self.config.character_id,
                reason=str(e),
            ) from e

        metadatas = (res.get("metadatas") or [[]])[0]
        distances = (res.get("distances") or [[]])[0]

        out: list[RagExample] = []
        for md, dist in zip(metadatas, distances):
            score = float(1.0 - float(dist))  # cosine distance -> score
            out.append(
                RagExample(
                    score=score,
                    interview_id=str(md.get("interview_id", "")),
                    source_file=str(md.get("source_file", "")),
                    question_replica_id=int(md.get("question_replica_id", -1)),
                    question_text=str(md.get("question_text", "")),
                    answer_text=(str(md.get("answer_text", "")) or None),
                )
            )
        return out