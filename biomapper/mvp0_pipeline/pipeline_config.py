"""
Configuration model for the MVP0 Pipeline Orchestrator.

This module defines the PipelineConfig Pydantic model that manages
all configuration settings for the pipeline components, including
Qdrant, PubChem, and LLM settings. Configuration values are loaded
from environment variables with sensible defaults where appropriate.
"""

from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class PipelineConfig(BaseSettings):
    """
    Configuration settings for the MVP0 mapping pipeline.

    This configuration model loads values from environment variables
    and provides defaults where appropriate. Sensitive information
    like API keys must be provided via environment variables.

    Environment variables:
        QDRANT_URL: URL for the Qdrant vector database
        QDRANT_COLLECTION_NAME: Name of the Qdrant collection to search
        QDRANT_API_KEY: Optional API key for Qdrant authentication
        PUBCHEM_MAX_CONCURRENT_REQUESTS: Maximum concurrent PubChem API requests
        LLM_MODEL_NAME: Name of the LLM model to use
        ANTHROPIC_API_KEY: API key for Anthropic Claude (required)
    """

    # Qdrant configuration
    qdrant_url: str = Field(
        default="http://localhost:6333",
        description="URL for the Qdrant vector database",
    )
    qdrant_collection_name: str = Field(
        default="pubchem_embeddings",
        description="Name of the Qdrant collection containing PubChem embeddings",
    )
    qdrant_api_key: Optional[str] = Field(
        default=None, description="Optional API key for Qdrant authentication"
    )

    # PubChem API configuration
    pubchem_max_concurrent_requests: int = Field(
        default=5,
        description="Maximum number of concurrent requests to PubChem API",
        ge=1,
        le=20,
    )

    # LLM configuration
    llm_model_name: str = Field(
        default="claude-3-sonnet-20240229",
        description="Name of the Anthropic Claude model to use for mapping decisions",
    )
    anthropic_api_key: str = Field(
        description="API key for Anthropic Claude (required)",
        # No default - this must be provided via environment variable
    )

    # Additional pipeline settings
    pipeline_batch_size: int = Field(
        default=10,
        description="Number of biochemical names to process in parallel",
        ge=1,
        le=50,
    )
    pipeline_timeout_seconds: int = Field(
        default=300,
        description="Timeout for processing a single biochemical name (seconds)",
        ge=30,
        le=1800,
    )

    class Config:
        """Pydantic configuration for the settings model."""

        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        # Allow extra fields from environment
        extra = "ignore"


# Factory function to create a config instance with validation
def create_pipeline_config(**kwargs) -> PipelineConfig:
    """
    Create a PipelineConfig instance with validation.

    This factory function creates a configuration instance and ensures
    all required settings are present and valid.

    Args:
        **kwargs: Optional overrides for configuration values

    Returns:
        Validated PipelineConfig instance

    Raises:
        ValidationError: If required settings are missing or invalid
    """
    return PipelineConfig(**kwargs)


# Example usage and validation
if __name__ == "__main__":
    import os
    from pydantic import ValidationError

    print("Testing PipelineConfig...")
    print("-" * 60)

    # Test with minimal environment (will fail without ANTHROPIC_API_KEY)
    try:
        # Temporarily set a test API key
        os.environ["ANTHROPIC_API_KEY"] = "test-key-for-validation"

        config = create_pipeline_config()
        print("Configuration loaded successfully!")
        print(f"Qdrant URL: {config.qdrant_url}")
        print(f"Qdrant Collection: {config.qdrant_collection_name}")
        print(f"PubChem Max Concurrent: {config.pubchem_max_concurrent_requests}")
        print(f"LLM Model: {config.llm_model_name}")
        print(f"Pipeline Batch Size: {config.pipeline_batch_size}")
        print(f"Pipeline Timeout: {config.pipeline_timeout_seconds}s")

        # Don't print the actual API key
        print(f"Anthropic API Key: {'*' * 10} (hidden)")

    except ValidationError as e:
        print(f"Configuration validation failed: {e}")
    finally:
        # Clean up test key
        if (
            "ANTHROPIC_API_KEY" in os.environ
            and os.environ["ANTHROPIC_API_KEY"] == "test-key-for-validation"
        ):
            del os.environ["ANTHROPIC_API_KEY"]

    print("\n" + "-" * 60)
    print("Note: Set ANTHROPIC_API_KEY environment variable before using the pipeline.")
