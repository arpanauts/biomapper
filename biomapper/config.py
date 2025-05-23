import logging
import os
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Define the root directory of the project
# Assuming this file is at /home/ubuntu/biomapper/biomapper/config.py
# PROJECT_ROOT will be /home/ubuntu/biomapper
PROJECT_ROOT = Path(__file__).parent.parent.parent


class Settings(BaseSettings):
    # --- Database Settings ---
    # Metamapper DB URL (config/metadata)
    # Default location: data/metamapper.db relative to project root
    metamapper_db_url: str = f"sqlite+aiosqlite:///{PROJECT_ROOT / 'data' / 'metamapper.db'}"

    # Cache DB URL (runtime results)
    # Default location: data/mapping_cache.db relative to project root
    cache_db_url: str = f"sqlite+aiosqlite:///{PROJECT_ROOT / 'data' / 'mapping_cache.db'}"

    # --- Logging Settings ---
    log_level: str = "INFO"

    # --- File Paths ---
    # Default data directory relative to project root
    data_dir: Path = PROJECT_ROOT / "data"
    # Default output directory relative to project root
    output_dir: Path = PROJECT_ROOT / "output"

    # --- API Keys (Optional - prefer environment variables) ---
    # Example: openai_api_key: str | None = None

    # Pydantic-settings configuration
    model_config = SettingsConfigDict(
        env_file=".env",  # Load .env file if it exists
        env_file_encoding="utf-8",
        case_sensitive=False,  # Environment variables are case-insensitive
        extra="ignore",  # Ignore extra fields from env vars or .env file
    )

    @property
    def numeric_log_level(self) -> int:
        """Return the numeric value of the log level."""
        return logging.getLevelName(self.log_level.upper())


# Singleton instance of the settings
# Use lru_cache(maxsize=None) to ensure it's created only once
@lru_cache(maxsize=None)
def get_settings() -> Settings:
    # Ensure default directories exist
    settings = Settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.output_dir.mkdir(parents=True, exist_ok=True)
    return settings


settings = get_settings()

# Example usage:
# from biomapper.config import settings
# print(settings.metamapper_db_url)
# print(settings.log_level)
