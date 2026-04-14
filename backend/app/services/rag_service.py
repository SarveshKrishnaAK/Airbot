from app.db.vector_store import vector_store


class RAGService:
    def retrieve_context(self, query: str, top_k: int = 3):
        try:
            results = vector_store.search(query, top_k=top_k)
            return "\n\n".join(results)
        except ValueError:
            return ""


rag_service = RAGService()
