from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
from app.api.routes import chat, aerospace, health, download, auth
from app.db.vector_store import vector_store
from app.utils.pdf_loader import load_documents
from app.core.config import settings
import os


@asynccontextmanager
async def lifespan(app: FastAPI):
    knowledge_base_candidates = [
        os.path.abspath(os.path.join(os.path.dirname(__file__), "../../knowledge_base")),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../knowledge_base")),
    ]
    base_path = next((path for path in knowledge_base_candidates if os.path.exists(path)), knowledge_base_candidates[0])
    print("Knowledge base path:", base_path)
    print(f"LLM Provider: {settings.LLM_PROVIDER}")

    from app.utils.chunker import chunk_text

    raw_documents = load_documents(base_path)
    print(f"Knowledge base documents loaded: {len(raw_documents)}")

    if not raw_documents:
        file_count = 0
        for _, _, files in os.walk(base_path):
            file_count += len(files)
        print(f"Knowledge base files discovered: {file_count}")

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

def resolve_frontend_path() -> str | None:
    frontend_candidates = [
        os.getenv("FRONTEND_DIR", ""),
        "/app/frontend",
        os.path.abspath(os.path.join(os.path.dirname(__file__), "../../frontend")),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../frontend")),
    ]
    filtered_candidates = [path for path in frontend_candidates if path]
    return next((path for path in filtered_candidates if os.path.exists(path)), None)


frontend_path = resolve_frontend_path()
print(f"Frontend path: {frontend_path}")

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


if frontend_path:
    assets_path = os.path.join(frontend_path, "assets")
    css_path = os.path.join(frontend_path, "css")
    js_path = os.path.join(frontend_path, "js")

    if os.path.exists(assets_path):
        app.mount("/assets", StaticFiles(directory=assets_path), name="assets")
    if os.path.exists(css_path):
        app.mount("/css", StaticFiles(directory=css_path), name="css")
    if os.path.exists(js_path):
        app.mount("/js", StaticFiles(directory=js_path), name="js")


@app.get("/auth-success.html")
def auth_success_page():
    resolved_frontend_path = resolve_frontend_path()
    if resolved_frontend_path:
        return FileResponse(os.path.join(resolved_frontend_path, "auth-success.html"))
    return {"message": "Frontend not bundled"}


@app.get("/auth-error.html")
def auth_error_page():
    resolved_frontend_path = resolve_frontend_path()
    if resolved_frontend_path:
        return FileResponse(os.path.join(resolved_frontend_path, "auth-error.html"))
    return {"message": "Frontend not bundled"}


@app.get("/auth-access-denied.html")
def auth_access_denied_page():
    resolved_frontend_path = resolve_frontend_path()
    if resolved_frontend_path:
        return FileResponse(os.path.join(resolved_frontend_path, "auth-access-denied.html"))
    return {"message": "Frontend not bundled"}


@app.get("/auth-access-granted.html")
def auth_access_granted_page():
    resolved_frontend_path = resolve_frontend_path()
    if resolved_frontend_path:
        return FileResponse(os.path.join(resolved_frontend_path, "auth-access-granted.html"))
    return {"message": "Frontend not bundled"}


@app.get("/favicon.ico")
def favicon():
    resolved_frontend_path = resolve_frontend_path()
    if resolved_frontend_path:
        favicon_path = os.path.join(resolved_frontend_path, "assets", "favicon.svg")
        if os.path.exists(favicon_path):
            return FileResponse(favicon_path, media_type="image/svg+xml")
    return {"message": "Favicon not found"}


@app.get("/")
def root():
    resolved_frontend_path = resolve_frontend_path()
    if resolved_frontend_path:
        return FileResponse(os.path.join(resolved_frontend_path, "index.html"))
    return {"message": "Airbot API running"}


@app.get("/index.html")
def index_fallback():
    return root()
