from abc import ABC, abstractmethod
import os
import numpy as np
from sentence_transformers import SentenceTransformer

EMBEDDING_MODEL_PATH = os.getenv(
    "EMBEDDING_MODEL_PATH",
    "/app/models/multilingual-e5-small",  # путь внутри docker
)


class Embedder(ABC):
    @abstractmethod
    def embed_passages(self, passages: list[str]) -> list[list[float]]:
        raise NotImplementedError

    @abstractmethod
    def embed_queries(self, queries: list[str]) -> list[list[float]]:
        raise NotImplementedError


class E5SentenceTransformerEmbedder(Embedder):
    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
        self.model = SentenceTransformer(EMBEDDING_MODEL_PATH)

    def embed_passages(self, passages: list[str]) -> list[list[float]]:
        texts = [f"passage: {t}" for t in passages]
        emb = self.model.encode(texts, normalize_embeddings=True, batch_size=64)
        return np.asarray(emb, dtype=np.float32).tolist()

    def embed_queries(self, queries: list[str]) -> list[list[float]]:
        texts = [f"query: {t}" for t in queries]
        emb = self.model.encode(texts, normalize_embeddings=True, batch_size=64)
        return np.asarray(emb, dtype=np.float32).tolist()