"""Tests for RAG base classes."""

import pytest
from unittest.mock import Mock, AsyncMock
import numpy as np
from typing import List, Optional

from biomapper.mapping.rag.base_rag import (
    Document,
    BaseVectorStore,
    BaseEmbedder,
    BasePromptManager,
    BaseRAGMapper,
    RAGError,
    EmbeddingError,
    RetrievalError,
    GenerationError,
)
from biomapper.schemas.rag_schema import Match


class MockDocument(Document):
    """Mock document for testing."""

    pass


class MockVectorStore(BaseVectorStore[MockDocument]):
    """Mock vector store for testing."""

    def __init__(self):
        self.docs: List[MockDocument] = []
        self.last_query: Optional[np.ndarray] = None

    async def add_documents(self, documents: List[MockDocument]) -> None:
        self.docs.extend(documents)

    async def get_relevant(
        self, query_embedding: np.ndarray, k: int = 5, threshold: float = 0.0
    ) -> List[MockDocument]:
        self.last_query = query_embedding
        return self.docs[:k]

    async def clear(self) -> None:
        self.docs = []


class MockEmbedder(BaseEmbedder):
    """Mock embedder for testing."""

    def __init__(self, dimension: int = 384):
        self.dimension = dimension
        self.embed_calls: List[str] = []

    async def embed_text(self, text: str) -> np.ndarray:
        self.embed_calls.append(text)
        return np.random.rand(self.dimension)

    async def embed_batch(self, texts: List[str]) -> List[np.ndarray]:
        self.embed_calls.extend(texts)
        return [np.random.rand(self.dimension) for _ in texts]


class MockPromptManager(BasePromptManager):
    """Mock prompt manager for testing."""

    async def get_prompt(self, query: str, context: List[Document], **kwargs) -> str:
        return f"Query: {query}\nContext: {len(context)} documents"


class MockRAGMapper(BaseRAGMapper):
    """Mock RAG mapper for testing."""

    async def _generate_matches(
        self, prompt: str, context: List[Document], **kwargs
    ) -> List[Match]:
        return [
            Match(
                id="test-1",
                name="Test Match 1",
                confidence="0.9",
                reasoning="Test reasoning",
            )
        ]


@pytest.fixture
def vector_store():
    """Create mock vector store."""
    return MockVectorStore()


@pytest.fixture
def embedder():
    """Create mock embedder."""
    return MockEmbedder()


@pytest.fixture
def prompt_manager():
    """Create mock prompt manager."""
    return MockPromptManager()


@pytest.fixture
def metrics():
    """Create mock metrics tracker."""
    return Mock(
        record_metrics=Mock(),
        start_operation=Mock(return_value="trace-123"),
        end_operation=Mock(),
    )


@pytest.fixture
def langfuse():
    """Create mock Langfuse tracker."""
    mock = AsyncMock()
    mock.trace_mapping = AsyncMock(return_value="trace-123")
    mock.record_error = AsyncMock()
    return mock


@pytest.fixture
def mapper(vector_store, embedder, prompt_manager, metrics, langfuse):
    """Create mock RAG mapper."""
    return MockRAGMapper(
        vector_store=vector_store,
        embedder=embedder,
        prompt_manager=prompt_manager,
        metrics=metrics,
        langfuse=langfuse,
    )


@pytest.mark.asyncio
async def test_document_creation():
    """Test document creation."""
    doc = MockDocument(
        content="test content", metadata={"key": "value"}, embedding=np.random.rand(384)
    )
    assert doc.content == "test content"
    assert doc.metadata["key"] == "value"
    assert doc.embedding is not None


@pytest.mark.asyncio
async def test_vector_store_operations(vector_store):
    """Test vector store operations."""
    docs = [
        MockDocument(content=f"doc {i}", metadata={}, embedding=np.random.rand(384))
        for i in range(3)
    ]

    await vector_store.add_documents(docs)
    assert len(vector_store.docs) == 3

    query = np.random.rand(384)
    results = await vector_store.get_relevant(query, k=2)
    assert len(results) == 2
    assert vector_store.last_query is query

    await vector_store.clear()
    assert len(vector_store.docs) == 0


@pytest.mark.asyncio
async def test_embedder_operations(embedder):
    """Test embedder operations."""
    embedding = await embedder.embed_text("test")
    assert embedding.shape == (384,)
    assert "test" in embedder.embed_calls

    embeddings = await embedder.embed_batch(["test1", "test2"])
    assert len(embeddings) == 2
    assert all(e.shape == (384,) for e in embeddings)
    assert "test1" in embedder.embed_calls
    assert "test2" in embedder.embed_calls


@pytest.mark.asyncio
async def test_prompt_manager(prompt_manager):
    """Test prompt manager."""
    docs = [MockDocument(content=f"doc {i}", metadata={}) for i in range(2)]
    prompt = await prompt_manager.get_prompt("test query", docs)
    assert "test query" in prompt
    assert "2 documents" in prompt


@pytest.mark.asyncio
async def test_rag_mapper_success(mapper):
    """Test successful RAG mapping."""
    result = await mapper.map_query("test query")
    assert result.query_term == "test query"
    assert len(result.matches) == 1
    assert result.best_match.id == "test-1"
    assert result.best_match.confidence == "0.9"
    assert not result.error

    # Verify metrics were recorded
    mapper.metrics.record_metrics.assert_called_once()


@pytest.mark.asyncio
async def test_rag_mapper_error_handling(mapper, embedder):
    """Test RAG mapper error handling."""
    # Make embedder fail
    embedder.embed_text = AsyncMock(side_effect=EmbeddingError("Test error"))

    result = await mapper.map_query("test query")
    assert result.error == "Test error"
    assert not result.matches
    assert result.best_match.confidence == "0.0"

    # Verify error was recorded
    mapper.langfuse.record_error.assert_called_once_with("trace-123", "Test error")
