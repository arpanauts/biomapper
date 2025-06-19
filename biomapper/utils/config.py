"""Configuration utilities for biomapper.

This module provides functions to load configurations from environment variables
or .env files, and defines standard paths and database URLs for the application.

DEPRECATION NOTICE:
This module is being deprecated in favor of the centralized configuration
system implemented in biomapper.core.config.Config. The module-level constants
(PROJECT_ROOT, DATA_DIR, CONFIG_DB_URL, CACHE_DB_URL) should be replaced with
the Config class. Please update your code as follows:

    # Old way:
    from biomapper.utils.config import CONFIG_DB_URL, CACHE_DB_URL
    
    # New way:
    from biomapper.core.config import Config
    config = Config.get_instance()
    config_db_url = config.get("database.config_db_url")
    cache_db_url = config.get("database.cache_db_url")

For functions like get_spoke_config(), these will be migrated to use the
central Config system in a future update.
"""

import os
import pathlib
from typing import Optional, Dict
from dotenv import load_dotenv

from ..core.base_spoke import SPOKEConfig


def get_spoke_config(config_path: Optional[str] = None) -> SPOKEConfig:
    """Get SPOKE configuration from environment variables or file.

    Loads configuration from a .env file and/or environment variables,
    with environment variables taking precedence over file-based configuration.

    Args:
        config_path: Optional path to .env configuration file. If None,
                     tries to load from default .env file in current directory.

    Returns:
        SPOKEConfig instance with populated configuration values

    Raises:
        ValueError: If critical configuration values are missing or invalid
    """
    # Load environment variables from .env file if it exists
    if config_path and os.path.exists(config_path):
        load_dotenv(config_path)
    else:
        load_dotenv()  # Try default .env file

    # Get configuration values with defaults
    base_url: str = os.getenv("SPOKE_BASE_URL", "https://spoke.rbvi.ucsf.edu/api/v1")

    # Get numeric values with proper type conversion and error handling
    try:
        timeout: int = int(os.getenv("SPOKE_TIMEOUT", "30"))
        max_retries: int = int(os.getenv("SPOKE_MAX_RETRIES", "3"))
        backoff_factor: float = float(os.getenv("SPOKE_BACKOFF_FACTOR", "0.5"))
    except ValueError as e:
        raise ValueError(f"Invalid configuration value: {e}")

    return SPOKEConfig(
        base_url=base_url,
        timeout=timeout,
        max_retries=max_retries,
        backoff_factor=backoff_factor,
    )


def get_project_paths() -> Dict[str, pathlib.Path]:
    """Get standard project paths.

    Returns:
        Dictionary containing project root, data, log, and other directories
    """
    # Resolve the project root directory based on this file's location
    project_root: pathlib.Path = pathlib.Path(__file__).parent.parent.parent

    paths: Dict[str, pathlib.Path] = {
        "root": project_root,
        "data": project_root / "data",
        "logs": project_root / "logs",
        "cache": project_root / "data" / "cache",
    }

    return paths


# --- Database Configuration ---
# Resolve the project root directory based on this file's location
PROJECT_ROOT: pathlib.Path = pathlib.Path(__file__).parent.parent.parent
DATA_DIR: pathlib.Path = PROJECT_ROOT / "data"
CONFIG_DB_URL: str = f"sqlite+aiosqlite:///{DATA_DIR}/metamapper.db"
CACHE_DB_URL: str = f"sqlite+aiosqlite:///{DATA_DIR}/mapping_cache.db"

# Set up logging for deprecation warnings
import logging
logger = logging.getLogger(__name__)

# Log warning when module is imported
logger.warning(
    "The module-level constants in biomapper.utils.config are deprecated. "
    "Please use biomapper.core.config.Config instead. "
    "See module docstring for migration guidance."
)


# TODO: Implement actual configuration loading (e.g., from env vars or file)
class Config:
    """Placeholder for application configuration."""

    def __init__(self):
        # In a real implementation, this would load config from files/env vars
        self._config = {
            "cache": {},
            "spoke": {},
            "api": {},
            "metadata": {},
            # Add other sections as needed
        }

    def get(self, key, default=None):
        """Provides dictionary-like access to configuration sections."""
        return self._config.get(key, default)


def get_project_root() -> pathlib.Path:
    """Get the project root directory."""
    return pathlib.Path(__file__).parent.parent.parent
