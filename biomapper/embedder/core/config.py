"""Configuration utilities for the Biomapper Embedder module."""

import os
from typing import Optional
from pydantic import BaseModel, Field


class EmbedderConfig(BaseModel):
    """Configuration for the Embedder module."""

    # Embedding model settings
    embedding_model: str = Field(
        default="all-MiniLM-L6-v2", description="Default embedding model name"
    )
    embedding_dimension: int = Field(
        default=384, description="Dimension of the embedding vectors"
    )

    # Storage settings
    storage_dir: str = Field(
        default=os.path.expanduser("~/.biomapper/embeddings"),
        description="Directory for storing embedding indices and metadata",
    )

    # Processing settings
    batch_size: int = Field(default=32, description="Default batch size for processing")
    max_tokens: int = Field(
        default=512, description="Maximum number of tokens for the embedding model"
    )

    # Performance settings
    cache_dir: Optional[str] = Field(
        default=None, description="Cache directory for models"
    )

    # Advanced settings
    device: Optional[str] = Field(
        default=None, description="Device to use for the embedding model (cpu, cuda)"
    )

    class Config:
        """Pydantic config."""

        extra = "allow"  # Allow extra fields


def load_config() -> EmbedderConfig:
    """Load configuration from environment or defaults.

    Returns:
        EmbedderConfig object
    """
    # Load from environment variables or use defaults
    config_dict = {}

    # Check environment variables
    if "BIOMAPPER_EMBEDDING_MODEL" in os.environ:
        config_dict["embedding_model"] = os.environ["BIOMAPPER_EMBEDDING_MODEL"]

    if "BIOMAPPER_STORAGE_DIR" in os.environ:
        config_dict["storage_dir"] = os.environ["BIOMAPPER_STORAGE_DIR"]

    if "BIOMAPPER_EMBEDDING_BATCH_SIZE" in os.environ:
        config_dict["batch_size"] = int(os.environ["BIOMAPPER_EMBEDDING_BATCH_SIZE"])

    if "BIOMAPPER_EMBEDDING_DEVICE" in os.environ:
        config_dict["device"] = os.environ["BIOMAPPER_EMBEDDING_DEVICE"]

    # Create storage directory if it doesn't exist
    config = EmbedderConfig(**config_dict)
    os.makedirs(config.storage_dir, exist_ok=True)

    if config.cache_dir:
        os.makedirs(config.cache_dir, exist_ok=True)

    return config


# Default configuration instance
default_config = load_config()
