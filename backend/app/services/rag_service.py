from app.db.vector_store import vector_store


class RAGService:
    def retrieve_context(self, query: str):
        results = vector_store.search(query)
        return "\n\n".join(results)


rag_service = RAGService()
