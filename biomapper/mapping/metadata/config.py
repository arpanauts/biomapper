"""
Configuration settings for the Metamapper Resource.

This module provides configuration settings for the Metadata 
system, including database paths and connection settings.
"""

import os
from pathlib import Path

# Default paths
BIOMAPPER_ROOT = Path(__file__).parent.parent.parent.parent
DATA_DIR = os.path.join(BIOMAPPER_ROOT, "data")

# Ensure data directory exists
os.makedirs(DATA_DIR, exist_ok=True)

# Database configuration
METADATA_DB_PATH = os.path.join(DATA_DIR, "metamapper.db")
METADATA_DB_URL = f"sqlite:///{METADATA_DB_PATH}"

# Default reference database (for testing and examples)
REFERENCE_DB_PATH = os.path.join(DATA_DIR, "metamapper_reference.db")

# CSV template paths
CSV_TEMPLATE_DIR = os.path.join(DATA_DIR, "templates")

# Performance settings
DEFAULT_CACHE_DURATION = 86400  # 24 hours in seconds
DEFAULT_PATH_REDISCOVERY_DAYS = 7  # Weekly rediscovery for paths
DEFAULT_CONNECTION_TIMEOUT = 30  # Default API timeout in seconds

def get_metadata_db_path() -> str:
    """
    Get the path to the metadata database file.
    
    This function checks environment variables first, then falls back to default.
    
    Returns:
        str: Path to the metadata database file
    """
    return os.environ.get("BIOMAPPER_METADATA_DB", METADATA_DB_PATH)

def get_metadata_db_url() -> str:
    """
    Get the database URL for SQLAlchemy.
    
    Returns:
        str: Database URL
    """
    db_path = get_metadata_db_path()
    return f"sqlite:///{db_path}"
