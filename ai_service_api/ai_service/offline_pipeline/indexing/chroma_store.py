from pathlib import Path
from typing import Any

import chromadb


class ChromaStore:
    def __init__(self, persist_dir: str, collection_name: str) -> None:
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)

        self.collection_name = collection_name
        self._client: chromadb.ClientAPI | None = None
        self._collection: chromadb.Collection | None = None

    def ensure_collection(self) -> chromadb.Collection:
        if self._collection is not None:
            return self._collection

        self._client = chromadb.PersistentClient(path=str(self.persist_dir))
        self._collection = self._client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        return self._collection

    def reset_collection(self) -> chromadb.Collection:
        self._client = chromadb.PersistentClient(path=str(self.persist_dir))
        try:
            self._client.delete_collection(name=self.collection_name)
        except Exception:
            pass

        self._collection = self._client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        return self._collection

    def count(self) -> int:
        col = self.ensure_collection()
        return col.count()

    def upsert(
        self,
        ids: list[str],
        documents: list[str],
        metadatas: list[dict[str, Any]],
        embeddings: list[list[float]],
    ) -> None:
        col = self.ensure_collection()
        col.upsert(ids=ids, documents=documents, metadatas=metadatas, embeddings=embeddings)

    def query(
        self,
        query_embeddings: list[list[float]],
        k: int,
    ) -> dict[str, Any]:
        col = self.ensure_collection()
        return col.query(
            query_embeddings=query_embeddings,
            n_results=k,
            include=["metadatas", "distances"],
        )