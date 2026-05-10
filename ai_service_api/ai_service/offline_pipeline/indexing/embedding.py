from abc import ABC, abstractmethod
import os
import numpy as np
from sentence_transformers import SentenceTransformer

from ai_service.exeptions.generation_error import EmbeddingModelError

EMBEDDING_MODEL_PATH = os.getenv(
    "EMBEDDING_MODEL_PATH",
   "/app/models/multilingual-e5-small",
)
#EMBEDDING_MODEL_PATH = "intfloat/multilingual-e5-small"


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
        try:
            self.model = SentenceTransformer(EMBEDDING_MODEL_PATH)
        except Exception as e:
            raise EmbeddingModelError(
                model_name=EMBEDDING_MODEL_PATH,
                reason=str(e)
            ) from e

    def embed_passages(self, passages: list[str]) -> list[list[float]]:
        try:
            texts = [f"passage: {t}" for t in passages]
            emb = self.model.encode(texts, normalize_embeddings=True, batch_size=64)
            return np.asarray(emb, dtype=np.float32).tolist()
        except Exception as e:
            raise EmbeddingModelError(
                model_name=self.model_name,
                reason=f"embed_passages failed: {e}",
            ) from e


    def embed_queries(self, queries: list[str]) -> list[list[float]]:
        try:
            texts = [f"query: {t}" for t in queries]
            emb = self.model.encode(texts, normalize_embeddings=True, batch_size=64)
            return np.asarray(emb, dtype=np.float32).tolist()
        except Exception as e:
            raise EmbeddingModelError(
                model_name=self.model_name,
                reason=f"embed_queries failed: {e}",
            ) from e