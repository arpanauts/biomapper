"""Tests for the ChromaCompoundStore."""
import pytest
from biomapper.schemas.rag_schema import CompoundDocument
from biomapper.mapping.rag.store import ChromaCompoundStore


def test_add_documents(temp_vector_store: ChromaCompoundStore) -> None:
    """Test adding documents to the store."""
    docs = [
        CompoundDocument(
            content="Test compound 1", metadata={"id": "1"}, embedding=[0.1] * 768
        ),
        CompoundDocument(
            content="Test compound 2", metadata={"id": "2"}, embedding=[0.2] * 768
        ),
    ]

    temp_vector_store.add_documents(docs)

    # Query should return the documents
    results = temp_vector_store.get_relevant_compounds([0.1] * 768, n_results=2)
    assert len(results) == 2
    assert results[0].content == "Test compound 1"


def test_query_empty_store(temp_vector_store: ChromaCompoundStore) -> None:
    """Test querying an empty store."""
    results = temp_vector_store.get_relevant_compounds([0.1] * 768)
    assert len(results) == 0


def test_add_documents_no_embeddings(temp_vector_store: ChromaCompoundStore) -> None:
    """Test adding documents without embeddings raises error."""
    docs = [
        CompoundDocument(content="Test compound", metadata={"id": "1"}, embedding=None)
    ]

    with pytest.raises(ValueError):
        temp_vector_store.add_documents(docs)
