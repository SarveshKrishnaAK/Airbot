import faiss
import numpy as np
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

    def search(self, query, top_k=3):
        if self.index is None:
            raise ValueError("Vector index not initialized. No documents loaded.")

        query_embedding = embedding_service.embed_query(query)
        query_embedding = np.array([query_embedding]).astype("float32")

        distances, indices = self.index.search(query_embedding, top_k)

        results = [self.documents[i] for i in indices[0]]
        return results



vector_store = VectorStore()
