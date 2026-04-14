import faiss
import numpy as np
import json
import os
from app.services.embedding_service import embedding_service
from loguru import logger


class VectorStore:
    def __init__(self):
        self.index = None
        self.documents = []

    def build_index(self, documents):
        logger.info("Building FAISS index...")

        self.documents = documents
        embeddings = embedding_service.embed_documents(documents)
        embeddings = np.array(embeddings).astype("float32")

        dimension = embeddings.shape[1]
        self.index = faiss.IndexFlatL2(dimension)
        self.index.add(embeddings)

        logger.info("FAISS index built successfully.")

    def save_cache(self, cache_dir: str, signature: str):
        if self.index is None:
            raise ValueError("Cannot save cache without an initialized index.")
        if not signature:
            raise ValueError("Cache signature is required.")

        os.makedirs(cache_dir, exist_ok=True)
        index_path = os.path.join(cache_dir, "faiss.index")
        metadata_path = os.path.join(cache_dir, "metadata.json")

        faiss.write_index(self.index, index_path)
        metadata = {
            "signature": signature,
            "documents": self.documents,
            "document_count": len(self.documents),
        }
        with open(metadata_path, "w", encoding="utf-8") as file:
            json.dump(metadata, file)

        logger.info(f"RAG cache saved: {index_path}")

    def load_cache(self, cache_dir: str, signature: str) -> bool:
        if not signature:
            return False

        index_path = os.path.join(cache_dir, "faiss.index")
        metadata_path = os.path.join(cache_dir, "metadata.json")

        if not (os.path.exists(index_path) and os.path.exists(metadata_path)):
            return False

        with open(metadata_path, "r", encoding="utf-8") as file:
            metadata = json.load(file)

        cached_signature = metadata.get("signature")
        documents = metadata.get("documents")
        document_count = metadata.get("document_count")

        if cached_signature != signature:
            return False
        if not isinstance(documents, list):
            return False
        if document_count != len(documents):
            return False

        index = faiss.read_index(index_path)
        if index.ntotal != len(documents):
            logger.warning("RAG cache mismatch: index vectors and documents differ. Ignoring cache.")
            return False

        self.index = index
        self.documents = documents
        logger.info(f"RAG cache loaded: {index_path}")
        return True

    def search(self, query, top_k=3):
        if self.index is None:
            raise ValueError("Vector index not initialized. No documents loaded.")

        query_embedding = embedding_service.embed_query(query)
        query_embedding = np.array([query_embedding]).astype("float32")

        distances, indices = self.index.search(query_embedding, top_k)
        results = [
            self.documents[i]
            for i in indices[0]
            if 0 <= i < len(self.documents)
        ]
        return results



vector_store = VectorStore()
