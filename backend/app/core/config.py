from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    # App Configuration
    APP_NAME: str = "Airbot"
    DEBUG: bool = True
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours

    # LLM Provider: "cloud" for Groq, "local" for Ollama
    LLM_PROVIDER: str = "local"
    PRIVACY_MODE: str = "standard"  # standard | local_only

    # Groq Configuration (Cloud LLM)
    GROQ_API_KEY: Optional[str] = None
    GROQ_MODEL_TEST_CASE: str = "llama-3.3-70b-versatile"
    GROQ_MODEL_GENERAL_CHAT: str = "llama-3.1-8b-instant"

    # Google OAuth
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None

    # URLs
    FRONTEND_URL: str = "http://localhost:5500"
    BACKEND_URL: str = "http://localhost:8000"

    # Legacy (optional)
    OPENAI_API_KEY: Optional[str] = None
    MONGO_URI: str = "mongodb://localhost:27017"
    SQLITE_DB_PATH: str = "./airbot.db"
    RAG_CACHE_DIR: str = "./cache"
    RAG_CACHE_ENABLED: bool = True
    RAG_REQUIRE_PREBUILT: bool = False

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings():
    return Settings()


settings = get_settings()
