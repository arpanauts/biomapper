"""Tests for ChromaDB vector store."""

import pytest
import numpy as np
from unittest.mock import Mock, patch
from chromadb import Settings as ChromaSettings

from biomapper.mapping.rag.chroma import (
    ChromaVectorStore,
    ChromaDocument,
    RetrievalError,
)
from biomapper.schemas.store_schema import VectorStoreConfig


@pytest.fixture
def mock_collection():
    """Create mock Chroma collection."""
    return Mock(
        add=Mock(),
        query=Mock(
            return_value={
                "documents": [["doc1", "doc2"]],
                "metadatas": [[{"key": "value"}, {"key": "value2"}]],
                "distances": [[0.1, 0.2]],
                "ids": [["1", "2"]],
            }
        ),
        delete=Mock(),
    )


@pytest.fixture
def mock_client():
    """Create mock Chroma client."""
    client = Mock()
    client.get_collection = Mock(return_value=Mock())
    client.create_collection = Mock(return_value=Mock())
    return client


@pytest.fixture
def store(mock_client, mock_collection):
    """Create ChromaVectorStore with mocked client."""
    with patch("chromadb.Client", return_value=mock_client):
        store = ChromaVectorStore(
            config=VectorStoreConfig(
                collection_name="test",
                persist_directory=":memory:",
            ),
            settings=ChromaSettings(),
        )
        store.collection = mock_collection
        return store


@pytest.fixture
def documents():
    """Create test documents."""
    return [
        ChromaDocument(
            content=f"test document {i}",
            metadata={"id": str(i)},
            embedding=np.random.rand(384).astype(np.float32),
        )
        for i in range(3)
    ]


@pytest.mark.asyncio
async def test_add_documents(store, documents, mock_collection):
    """Test adding documents."""
    await store.add_documents(documents)
    mock_collection.add.assert_called_once()
    args = mock_collection.add.call_args[1]
    assert len(args["documents"]) == 3
    assert len(args["metadatas"]) == 3
    assert len(args["embeddings"]) == 3
    assert len(args["ids"]) == 3


@pytest.mark.asyncio
async def test_add_documents_no_embeddings(store):
    """Test adding documents without embeddings."""
    docs = [
        ChromaDocument(
            content="test",
            metadata={},
            embedding=None,
        )
    ]
    with pytest.raises(
        ValueError, match="Cannot add documents with missing embeddings"
    ):
        await store.add_documents(docs)


@pytest.mark.asyncio
async def test_get_relevant(store, mock_collection):
    """Test retrieving relevant documents."""
    query = np.random.rand(384).astype(np.float32)
    results = await store.get_relevant(query, k=2)
    mock_collection.query.assert_called_once()
    assert len(results) == 2
    assert all(isinstance(doc, ChromaDocument) for doc in results)


@pytest.mark.asyncio
async def test_get_relevant_error(store, mock_collection):
    """Test error handling during retrieval."""
    mock_collection.query.side_effect = Exception("Test error")
    with pytest.raises(RetrievalError, match="Failed to retrieve documents"):
        await store.get_relevant(np.random.rand(384))


@pytest.mark.asyncio
async def test_clear(store, mock_collection):
    """Test clearing the store."""
    await store.clear()
    mock_collection.delete.assert_called_once_with(where={})


@pytest.mark.asyncio
async def test_clear_error(store, mock_collection):
    """Test error handling during clear."""
    mock_collection.delete.side_effect = Exception("Test error")
    with pytest.raises(RetrievalError, match="Failed to clear store"):
        await store.clear()
