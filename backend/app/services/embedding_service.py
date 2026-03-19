import ollama
import numpy as np
from loguru import logger


class EmbeddingService:
    def __init__(self):
        logger.info("Using Ollama nomic-embed-text for embeddings...")

    def embed_documents(self, texts):
        embeddings = []
        for text in texts:
            response = ollama.embeddings(
                model="nomic-embed-text",
                prompt=text
            )
            embeddings.append(response["embedding"])
        return np.array(embeddings).astype("float32")

    def embed_query(self, text):
        response = ollama.embeddings(
            model="nomic-embed-text",
            prompt=text
        )
        return np.array(response["embedding"]).astype("float32")


embedding_service = EmbeddingService()
