"""Configuration utilities for biomapper."""

import os
from typing import Optional
from dotenv import load_dotenv

from ..core.base_spoke import SPOKEConfig


def get_spoke_config(config_path: Optional[str] = None) -> SPOKEConfig:
    """Get SPOKE configuration from environment or file.
    
    Args:
        config_path: Optional path to configuration file
        
    Returns:
        SPOKEConfig instance
    """
    # Load environment variables from .env file if it exists
    if config_path and os.path.exists(config_path):
        load_dotenv(config_path)
    else:
        load_dotenv()  # Try default .env file

    return SPOKEConfig(
        base_url=os.getenv("SPOKE_BASE_URL", "https://spoke.rbvi.ucsf.edu/api/v1"),
        timeout=int(os.getenv("SPOKE_TIMEOUT", "30")),
        max_retries=int(os.getenv("SPOKE_MAX_RETRIES", "3")),
        backoff_factor=float(os.getenv("SPOKE_BACKOFF_FACTOR", "0.5"))
    )
