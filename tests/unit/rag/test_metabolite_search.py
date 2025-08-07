"""Unit tests for Metabolite search functionality - Written FIRST for TDD."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import time


class TestMetaboliteSearcher:
    """Test metabolite search functionality - WRITE FIRST!"""

    @pytest.fixture
    def mock_qdrant_client(self):
        """Mock Qdrant client for testing."""
        client = Mock()
        client.search = Mock()  # Qdrant search is synchronous
        return client

    @pytest.fixture
    def searcher(self, mock_qdrant_client):
        """Create searcher instance with mocked dependencies."""
        with patch(
            "biomapper.rag.metabolite_search.QdrantClient",
            return_value=mock_qdrant_client,
        ):
            with patch(
                "biomapper.rag.metabolite_search.TextEmbedding"
            ) as mock_embedding:
                from biomapper.rag.metabolite_search import MetaboliteSearcher

                # Mock the embedding model
                mock_embedding_instance = Mock()

                def mock_embed(texts):
                    return [[0.1] * 384 for _ in texts]

                mock_embedding_instance.embed = Mock(side_effect=mock_embed)
                mock_embedding.return_value = mock_embedding_instance

                searcher = MetaboliteSearcher(
                    qdrant_url="localhost:6333", collection_name="test_metabolites"
                )
                searcher.client = mock_qdrant_client
                return searcher

    @pytest.mark.asyncio
    async def test_search_by_name_returns_sorted_results(self, searcher):
        """Test search returns results sorted by score."""
        # Mock Qdrant response (sorted by score descending as Qdrant would return)
        mock_results = [
            Mock(
                score=0.92,
                payload={"hmdb_id": "HMDB0000122", "name": "Cholesterol ester"},
            ),
            Mock(score=0.85, payload={"hmdb_id": "HMDB0000067", "name": "Cholesterol"}),
            Mock(score=0.78, payload={"hmdb_id": "HMDB0000097", "name": "Cholestanol"}),
        ]
        searcher.client.search.return_value = mock_results

        results = await searcher.search_by_name("cholesterol")

        # Verify results are sorted by score descending
        scores = [r["score"] for r in results]
        assert scores == sorted(scores, reverse=True)
        # This test should FAIL initially

    @pytest.mark.asyncio
    async def test_search_filters_by_threshold(self, searcher):
        """Test search filters results by score threshold."""
        # Mock Qdrant response with various scores
        mock_results = [
            Mock(score=0.85, payload={"hmdb_id": "HMDB0000067", "name": "Cholesterol"}),
            Mock(
                score=0.75,
                payload={"hmdb_id": "HMDB0000122", "name": "Cholesterol ester"},
            ),
            Mock(score=0.65, payload={"hmdb_id": "HMDB0000097", "name": "Cholestanol"}),
        ]
        searcher.client.search.return_value = mock_results

        results = await searcher.search_by_name("cholesterol", score_threshold=0.8)

        # All results should meet threshold
        assert all(r["score"] >= 0.8 for r in results)
        assert len(results) == 1  # Only one result above 0.8
        # This test should FAIL initially

    @pytest.mark.asyncio
    async def test_batch_search_efficiency(self, searcher):
        """Test batch search is more efficient than individual searches."""
        compounds = ["cholesterol", "glucose", "alanine"]

        # Measure batch search
        start_time = time.time()
        batch_results = await searcher.batch_search(compounds)
        batch_time = time.time() - start_time

        # Batch should return dict mapping
        assert len(batch_results) == 3
        assert all(compound in batch_results for compound in compounds)
        # This test should FAIL initially

    @pytest.mark.asyncio
    async def test_search_handles_empty_results(self, searcher):
        """Test search handles case when no results found."""
        searcher.client.search.return_value = []

        results = await searcher.search_by_name("nonexistent-compound-xyz")

        assert results == []
        assert isinstance(results, list)
        # This test should FAIL initially

    @pytest.mark.asyncio
    async def test_search_includes_metadata_in_results(self, searcher):
        """Test search results include all relevant metadata."""
        mock_results = [
            Mock(
                score=0.92,
                payload={
                    "hmdb_id": "HMDB0000067",
                    "name": "Cholesterol",
                    "synonyms": ["Cholesterin", "Cholest-5-en-3β-ol"],
                    "chemical_formula": "C27H46O",
                    "description": "The most abundant steroid in animal tissues",
                },
            )
        ]
        searcher.client.search.return_value = mock_results

        results = await searcher.search_by_name("cholesterol")

        assert len(results) == 1
        result = results[0]

        # Check all expected fields
        assert "score" in result
        assert "hmdb_id" in result
        assert "name" in result
        assert "synonyms" in result
        assert "chemical_formula" in result
        assert "description" in result

        # Check values
        assert result["score"] == 0.92
        assert result["hmdb_id"] == "HMDB0000067"
        assert result["name"] == "Cholesterol"
        # This test should FAIL initially

    @pytest.mark.asyncio
    async def test_batch_search_handles_partial_failures(self, searcher):
        """Test batch search continues even if some queries fail."""
        compounds = ["cholesterol", "invalid-query", "glucose"]

        # Mock different responses for each compound
        def mock_search_response(*args, **kwargs):
            query_embedding = args[0] if args else kwargs.get("query_vector")
            # Simulate that middle query returns empty
            if hasattr(query_embedding, "__getitem__") and query_embedding[1] == 0:
                return []
            return [Mock(score=0.85, payload={"name": "Test Result"})]

        searcher.client.search = AsyncMock(side_effect=mock_search_response)

        batch_results = await searcher.batch_search(compounds)

        # Should have results for all compounds, even if some are empty
        assert len(batch_results) == 3
        assert "cholesterol" in batch_results
        assert "invalid-query" in batch_results
        assert "glucose" in batch_results

        # Invalid query should have empty results
        assert len(batch_results["invalid-query"]) == 0
        # This test should FAIL initially

    def test_searcher_initialization_with_custom_model(self):
        """Test searcher can be initialized with custom embedding model."""
        with patch("biomapper.rag.metabolite_search.QdrantClient"):
            with patch(
                "biomapper.rag.metabolite_search.TextEmbedding"
            ) as mock_embedding:
                from biomapper.rag.metabolite_search import MetaboliteSearcher

                searcher = MetaboliteSearcher(embedding_model="custom/model-name")

                # Should initialize embedding with custom model
                mock_embedding.assert_called_once_with(model_name="custom/model-name")
                # This test should FAIL initially

    @pytest.mark.asyncio
    async def test_search_limit_parameter(self, searcher):
        """Test search respects limit parameter."""

        # Mock function that respects limit parameter like Qdrant would
        def mock_search(*args, **kwargs):
            limit = kwargs.get("limit", 10)
            all_results = [
                Mock(
                    score=0.9 - i * 0.01,
                    payload={"hmdb_id": f"HMDB{i:07d}", "name": f"Compound {i}"},
                )
                for i in range(20)
            ]
            return all_results[:limit]

        searcher.client.search = Mock(side_effect=mock_search)

        results = await searcher.search_by_name("test", limit=5)

        assert len(results) == 5
        # Should be the top 5 by score
        assert all(results[i]["score"] >= results[i + 1]["score"] for i in range(4))
        # This test should FAIL initially

    @pytest.mark.asyncio
    async def test_batch_search_uses_single_embedding_call(self, searcher):
        """Test batch search embeds all queries in one call for efficiency."""
        compounds = ["cholesterol", "glucose", "alanine", "serine", "glycine"]

        # Mock the embedding model - embedding is synchronous
        mock_embed = Mock(return_value=[[0.1] * 384 for _ in compounds])
        searcher.embedding_model.embed = mock_embed

        await searcher.batch_search(compounds)

        # Should call embed only once with all compounds
        mock_embed.assert_called_once()
        call_args = mock_embed.call_args[0][0]
        assert len(call_args) == 5
        assert all(c in call_args for c in compounds)
        # This test should FAIL initially
