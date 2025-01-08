"""Fixtures for RAG component tests."""
import os
import pytest
from pathlib import Path
import json
from typing import Dict, Any, Generator

from biomapper.schemas.store_schema import VectorStoreConfig
from biomapper.mapping.rag.store import ChromaCompoundStore
from biomapper.mapping.rag.prompts import PromptManager
from chromadb import Settings as ChromaSettings
from pytest import TempPathFactory


@pytest.fixture(scope="session", autouse=True)
def setup_chroma_env() -> None:
    """Set up ChromaDB environment variables."""
    os.environ["ALLOW_RESET"] = "TRUE"


@pytest.fixture(scope="session")
def chroma_settings() -> ChromaSettings:
    """Get ChromaDB settings for testing."""
    return ChromaSettings()


@pytest.fixture
def temp_vector_store(
    tmp_path_factory: TempPathFactory,
    chroma_settings: ChromaSettings,
) -> Generator[ChromaCompoundStore, None, None]:
    """Create a temporary vector store."""
    # Create a temporary directory for the test
    test_dir = tmp_path_factory.mktemp("test_store")
    config = VectorStoreConfig(
        collection_name="test_collection",
        persist_directory=test_dir,
    )

    # Create store with test settings
    store = ChromaCompoundStore(config, settings=chroma_settings)
    yield store

    # Clean up
    if os.path.exists(str(test_dir)):
        store.client.reset()


@pytest.fixture
def sample_prompts() -> Dict[str, Dict[str, Any]]:
    """Sample prompts for testing."""
    return {
        "test_prompt": {
            "template": "Test template with {placeholder}",
            "version": "1.0",
            "metrics": {"accuracy": 0.9},
        }
    }


@pytest.fixture
def prompt_manager(
    tmp_path: Path, sample_prompts: Dict[str, Dict[str, Any]]
) -> PromptManager:
    """Create a PromptManager with sample prompts."""
    # Create temp prompts file
    prompts_file = tmp_path / "default_prompts.json"
    with open(prompts_file, "w") as f:
        json.dump(sample_prompts, f)

    # Patch the DEFAULT_PROMPTS path
    PromptManager.DEFAULT_PROMPTS = prompts_file
    return PromptManager()
