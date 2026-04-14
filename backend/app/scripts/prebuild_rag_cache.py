from app.core.config import settings
from app.db.vector_store import vector_store
from app.utils.rag_cache import (
    resolve_knowledge_base_path,
    get_knowledge_base_signature,
    prepare_chunked_documents,
)
import os


def main():
    base_path = resolve_knowledge_base_path()
    cache_dir = os.path.abspath(settings.RAG_CACHE_DIR)
    signature = get_knowledge_base_signature(base_path)

    print(f"Knowledge base path: {base_path}")
    print(f"RAG cache directory: {cache_dir}")

    documents = prepare_chunked_documents(base_path)
    if not documents:
        print("No knowledge base content found. Cache not built.")
        return

    vector_store.build_index(documents)
    vector_store.save_cache(cache_dir, signature)
    print(f"RAG cache built successfully with {len(documents)} chunks.")


if __name__ == "__main__":
    main()
