import numpy as np
from loguru import logger
from app.core.config import settings
import re
import hashlib


class EmbeddingService:
    EMBEDDING_DIM = 384

    def __init__(self):
        self.provider = settings.LLM_PROVIDER
        self.ollama_client = None

        if self.provider == "local":
            try:
                import ollama
                self.ollama_client = ollama
                logger.info("Using Ollama nomic-embed-text for embeddings...")
            except Exception:
                logger.warning("Ollama unavailable. Falling back to hash embeddings.")
        else:
            logger.info("Using hash embeddings for cloud deployment (no Ollama dependency).")

    def _hash_embedding(self, text: str) -> np.ndarray:
        vector = np.zeros(self.EMBEDDING_DIM, dtype="float32")
        tokens = re.findall(r"[a-zA-Z0-9]+", (text or "").lower())

        if not tokens:
            return vector

        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.EMBEDDING_DIM
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign

        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm

        return vector.astype("float32")

    def embed_documents(self, texts):
        if self.ollama_client is None:
            return np.array([self._hash_embedding(text) for text in texts]).astype("float32")

        embeddings = []
        for text in texts:
            response = self.ollama_client.embeddings(
                model="nomic-embed-text",
                prompt=text
            )
            embeddings.append(response["embedding"])
        return np.array(embeddings).astype("float32")

    def embed_query(self, text):
        if self.ollama_client is None:
            return self._hash_embedding(text)

        response = self.ollama_client.embeddings(
            model="nomic-embed-text",
            prompt=text
        )
        return np.array(response["embedding"]).astype("float32")


embedding_service = EmbeddingService()
