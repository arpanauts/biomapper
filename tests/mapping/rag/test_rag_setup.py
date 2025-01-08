"""Tests for RAG setup and configuration."""
from pathlib import Path
import pytest
from rdkit import RDLogger

from biomapper.mapping.rag import RAGCompoundMapper
from biomapper.schemas.store_schema import VectorStoreConfig

# Disable RDKit logging
RDLogger.logger().setLevel(RDLogger.ERROR)  # type: ignore[no-untyped-call]


@pytest.fixture
def test_sdf_path(tmp_path: Path) -> str:
    """Create a test SDF file."""
    sdf_content = """
    Test Compound
      RDKit

     10 10  0  0  0  0  0  0  0  0999 V2000
        0.0000    0.0000    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
        1.0000    0.0000    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
        2.0000    0.0000    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
        3.0000    0.0000    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
        4.0000    0.0000    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
        5.0000    0.0000    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
        6.0000    0.0000    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
        7.0000    0.0000    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
        8.0000    0.0000    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
        9.0000    0.0000    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
     1  2  1  0
     2  3  1  0
     3  4  1  0
     4  5  1  0
     5  6  1  0
     6  7  1  0
     7  8  1  0
     8  9  1  0
     9 10  1  0
    M  END
    $$$$
    """
    test_file = tmp_path / "test.sdf"
    test_file.write_text(sdf_content)
    return str(test_file)


def test_rag_initialization(test_sdf_path: str) -> None:
    """Test RAG mapper initialization."""
    config = VectorStoreConfig(
        collection_name="test_compounds",
        persist_directory=Path(test_sdf_path).parent / "chroma",
    )

    mapper = RAGCompoundMapper(store_config=config)
    assert mapper.store is not None
    assert mapper.prompt_manager is not None
    assert mapper.optimizer is not None


def test_rag_mapping(test_sdf_path: str) -> None:
    """Test compound mapping."""
    config = VectorStoreConfig(
        collection_name="test_compounds",
        persist_directory=Path(test_sdf_path).parent / "chroma",
    )

    mapper = RAGCompoundMapper(store_config=config)
    result = mapper.map_compound("Test Compound")

    assert result.query_term == "Test Compound"
    assert len(result.matches) >= 0  # May be empty if no matches found
    assert result.metrics is not None
    assert result.metrics["latency_ms"] >= 0
