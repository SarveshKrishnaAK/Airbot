from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional
import os
import dotenv 

dotenv.load_dotenv()


class Settings(BaseSettings):
    # App Configuration
    APP_NAME: str = "Airbot"
    DEBUG: bool = True
    SECRET_KEY: str = os.getenv("SECRET_KEY")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours

    # LLM Provider: "cloud" for Groq, "local" for Ollama
    LLM_PROVIDER: str = "cloud"

    # Groq Configuration (Cloud LLM)
    GROQ_API_KEY: Optional[str] = os.getenv("GROQ_API_KEY")
    GROQ_MODEL_TEST_CASE: str = "llama-3.3-70b-versatile"
    GROQ_MODEL_GENERAL_CHAT: str = "llama-3.1-8b-instant"

    # Google OAuth
    GOOGLE_CLIENT_ID: Optional[str] = os.getenv("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET: Optional[str] = os.getenv("GOOGLE_CLIENT_SECRET")

    # URLs
    FRONTEND_URL: str = "https://airbot-production-3f51.up.railway.app/"
    BACKEND_URL: str = "https://airbot-production-3f51.up.railway.app/"

    # Legacy (optional)
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    MONGO_URI: str = "mongodb://localhost:27017"

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings():
    return Settings()


settings = get_settings()
