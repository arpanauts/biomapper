import psutil
from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict

# Base directory of the project
BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    """Application settings with defaults and environment variable integration."""

    # General settings
    PROJECT_NAME: str = "Biomapper API"
    DEBUG: bool = False

    # API settings
    API_V1_PREFIX: str = "/api"

    # CORS settings
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",  # React frontend default
        "http://localhost:5173",  # Vite development server
        "http://localhost:5174",  # Vite may use this port too
        "http://localhost:8000",  # Same origin for development
        "*",  # Allow all origins during development (remove in production)
    ]

    # File handling
    UPLOAD_DIR: Path = BASE_DIR / "data" / "uploads"
    # Dynamically set max upload size to half of available system memory
    # Default to 1GB if we can't determine memory
    MAX_UPLOAD_SIZE: int = (
        int(psutil.virtual_memory().available / 2)
        if hasattr(psutil, "virtual_memory")
        else 1024 * 1024 * 1024
    )

    # Session management
    SESSION_EXPIRY_HOURS: int = 24

    # Mapping settings
    MAPPING_RESULTS_DIR: Path = BASE_DIR / "data" / "results"
    STRATEGIES_DIR: Path = BASE_DIR.parent / "configs"

    # Database settings
    DATABASE_URL: str = "sqlite+aiosqlite:///./biomapper.db"
    DATABASE_ECHO: bool = False

    # Storage settings
    CHECKPOINT_DIR: Path = BASE_DIR / "data" / "checkpoints"
    EXTERNAL_STORAGE_DIR: Path = BASE_DIR / "data" / "storage"
    MAX_INLINE_STORAGE_SIZE: int = 100 * 1024  # 100KB

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="allow"
    )

    def __init__(self, **data):
        super().__init__(**data)

        # Create necessary directories
        self.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        self.MAPPING_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        self.CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
        self.EXTERNAL_STORAGE_DIR.mkdir(parents=True, exist_ok=True)


# Global settings instance
settings = Settings()
