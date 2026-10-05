from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment or .env file."""
    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parent.parent.parent / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Google Gemini AI settings
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.8-flash"

    # Embeddings
    EMBEDDING_MODEL: str = "gemini-embedding-001"
    EMBEDDING_PROVIDER: str = "local"  # "local" or "gemini"

    # Storage paths
    CHROMA_PERSIST_DIR: str = "./data/chroma"
    SQLITE_DB_PATH: str = "./data/db/remind.db"
    PHOTO_DIR: str = "./data/photos"

    # Search and Refinement limits
    MAX_CANDIDATES: int = 20
    MAX_REFINEMENT_TURNS: int = 5

    # Server settings
    LOG_LEVEL: str = "INFO"
    PORT: int = 8000
    HOST: str = "0.0.0.0"


settings = Settings()
