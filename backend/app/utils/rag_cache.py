import hashlib
import os

from app.utils.chunker import chunk_text
from app.utils.pdf_loader import load_documents


def resolve_knowledge_base_path() -> str:
    knowledge_base_candidates = [
        os.getenv("KNOWLEDGE_BASE_DIR", ""),
        "/app/knowledge_base",
        os.path.abspath(os.path.join(os.path.dirname(__file__), "../../knowledge_base")),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../knowledge_base")),
    ]
    filtered_candidates = [path for path in knowledge_base_candidates if path]
    return next((path for path in filtered_candidates if os.path.exists(path)), filtered_candidates[0])


def get_knowledge_base_signature(base_path: str) -> str:
    parts: list[str] = []
    for root, _, files in os.walk(base_path):
        for file_name in sorted(files):
            if not (file_name.endswith(".pdf") or file_name.endswith(".txt")):
                continue
            file_path = os.path.join(root, file_name)
            try:
                stats = os.stat(file_path)
            except OSError:
                continue
            relative_path = os.path.relpath(file_path, base_path)
            parts.append(f"{relative_path}|{stats.st_size}|{int(stats.st_mtime)}")
    digest = hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()
    return digest


def prepare_chunked_documents(base_path: str) -> list[str]:
    raw_documents = load_documents(base_path)
    print(f"Knowledge base documents loaded: {len(raw_documents)}")

    if not raw_documents:
        file_count = 0
        for _, _, files in os.walk(base_path):
            file_count += len(files)
        print(f"Knowledge base files discovered: {file_count}")

    documents: list[str] = []
    for doc in raw_documents:
        documents.extend(chunk_text(doc))
    return documents
