from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.api.routes import chat, aerospace, health, download, auth
from app.db.vector_store import vector_store
from app.utils.pdf_loader import load_documents
from app.core.config import settings
import os


@asynccontextmanager
async def lifespan(app: FastAPI):
    knowledge_base_candidates = [
        os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../knowledge_base")),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "../../knowledge_base")),
    ]
    base_path = next((path for path in knowledge_base_candidates if os.path.exists(path)), knowledge_base_candidates[0])
    print("Knowledge base path:", base_path)
    print(f"LLM Provider: {settings.LLM_PROVIDER}")

    from app.utils.chunker import chunk_text

    raw_documents = load_documents(base_path)

    documents = []
    for doc in raw_documents:
        chunks = chunk_text(doc)
        documents.extend(chunks)

    if documents:
        try:
            vector_store.build_index(documents)
        except Exception as error:
            print(f"⚠ Vector index build failed. Continuing without RAG index: {error}")
    else:
        print("⚠ No documents found in knowledge base.")

    yield

    print("Shutting down Airbot...")


app = FastAPI(title="Airbot API", lifespan=lifespan)

# CORS configuration
allowed_origins = [
    "http://localhost:5500",
    "http://127.0.0.1:5500",
    "http://localhost:3000",
    "null",
    settings.FRONTEND_URL
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Routes
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(chat.router, prefix="/chat", tags=["Chat"])
app.include_router(download.router, prefix="/download", tags=["Download"])
app.include_router(aerospace.router, prefix="/aerospace", tags=["Aerospace"])
app.include_router(health.router, prefix="/health", tags=["Health"])


@app.get("/")
def root():
    return {"message": "Airbot API running"}
