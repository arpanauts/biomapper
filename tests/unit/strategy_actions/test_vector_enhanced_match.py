import pytest
from unittest.mock import Mock, patch
import numpy as np

from biomapper.core.strategy_actions.vector_enhanced_match import (
    VectorEnhancedMatchAction,
    VectorEnhancedMatchParams,
    VectorMatchResult,
)


class TestVectorEnhancedMatch:
    """Test suite for vector-enhanced matching - WRITE FIRST!"""

    @pytest.fixture
    def action(self):
        """Create action instance."""
        return VectorEnhancedMatchAction()

    @pytest.fixture
    def mock_embedding_model(self):
        """Mock FastEmbed model."""
        model = Mock()
        # Return consistent embeddings
        model.embed = Mock(return_value=[np.random.rand(384) for _ in range(10)])
        return model

    @pytest.fixture
    def mock_qdrant_client(self):
        """Mock Qdrant client."""
        client = Mock()
        client.get_collection = Mock(return_value=Mock(points_count=100000))

        # Mock search results
        def mock_search(collection_name, query_vector, limit, score_threshold=None):
            results = []
            for i in range(min(3, limit)):
                point = Mock()
                point.score = 0.95 - (i * 0.05)  # Decreasing scores
                point.payload = {
                    "hmdb_id": f"HMDB{i:07d}",
                    "name": f"Test Metabolite {i}",
                    "synonyms": [f"Synonym {i}"],
                    "inchikey": f"TEST-INCHIKEY-{i}",
                }
                results.append(point)
            return results

        client.search = Mock(side_effect=mock_search)
        return client

    @pytest.fixture
    def unmatched_metabolites(self):
        """Unmatched metabolites from previous stages."""
        return [
            {
                "BIOCHEMICAL_NAME": "complex-metabolite-xyz",
                "HMDB": "",
                "cts_enriched_names": ["metabolite xyz variant"],
                "SUB_PATHWAY": "Amino Acid",
                "SUPER_PATHWAY": "Metabolism",
            },
            {
                "BIOCHEMICAL_NAME": "rare-compound-abc",
                "cts_enriched_names": [],
                "SUB_PATHWAY": "Lipid metabolism",
            },
        ]

    def test_client_initialization(self, action):
        """Test FastEmbed and Qdrant client initialization."""
        params = VectorEnhancedMatchParams(
            unmatched_dataset_key="unmatched",
            qdrant_url="localhost:6333",
            qdrant_collection="hmdb_metabolites",
            embedding_model="BAAI/bge-small-en-v1.5",
            output_key="matches",
        )

        with patch(
            "biomapper.core.strategy_actions.vector_enhanced_match.TextEmbedding"
        ) as mock_embed:
            with patch(
                "biomapper.core.strategy_actions.vector_enhanced_match.QdrantClient"
            ) as mock_qdrant:
                mock_qdrant_instance = Mock()
                mock_qdrant_instance.get_collection = Mock()
                mock_qdrant.return_value = mock_qdrant_instance

                action._initialize_clients(params)

                mock_embed.assert_called_once_with(model_name="BAAI/bge-small-en-v1.5")
                mock_qdrant.assert_called_once_with("localhost:6333")
                assert action.embedding_model is not None
                assert action.qdrant_client is not None
        # This test should FAIL initially

    def test_search_text_preparation(self, action):
        """Test preparation of multiple search texts."""
        metabolite = {
            "BIOCHEMICAL_NAME": "test-metabolite",
            "cts_enriched_names": ["metabolite-test", "test compound"],
            "SUB_PATHWAY": "Test Pathway",
            "SUPER_PATHWAY": "Test Super",
        }

        search_texts = action._prepare_search_texts(metabolite)

        # Should include original name
        assert ("test-metabolite", "original_name") in search_texts

        # Should include CTS names
        assert ("metabolite-test", "cts_enriched") in search_texts
        assert ("test compound", "cts_enriched") in search_texts

        # Should include contextual variants
        assert ("test-metabolite Test Pathway", "name_with_pathway") in search_texts
        assert ("test-metabolite Test Super", "name_with_super_pathway") in search_texts

        # No duplicates
        texts_only = [t[0] for t in search_texts]
        assert len(texts_only) == len(set(texts_only))
        # This test should FAIL initially

    def test_similarity_bucket_calculation(self, action):
        """Test similarity score bucketing."""
        assert action._calculate_similarity_bucket(0.95) == "very_high"
        assert action._calculate_similarity_bucket(0.87) == "high"
        assert action._calculate_similarity_bucket(0.82) == "medium"
        assert action._calculate_similarity_bucket(0.77) == "low"
        assert action._calculate_similarity_bucket(0.72) == "very_low"
        # This test should FAIL initially

    @pytest.mark.asyncio
    async def test_batch_vector_search(
        self, action, mock_embedding_model, mock_qdrant_client, unmatched_metabolites
    ):
        """Test batch vector search functionality."""
        action.embedding_model = mock_embedding_model
        action.qdrant_client = mock_qdrant_client

        params = VectorEnhancedMatchParams(
            unmatched_dataset_key="unmatched",
            qdrant_collection="hmdb_metabolites",
            similarity_threshold=0.75,
            top_k=3,
            output_key="matches",
            batch_size=10,
        )

        results, embed_time, search_time = await action._batch_vector_search(
            unmatched_metabolites, params
        )

        assert len(results) > 0
        assert embed_time > 0
        assert search_time > 0

        # Check result structure
        first_result = results[0]
        assert isinstance(first_result, VectorMatchResult)
        assert first_result.similarity_score >= 0.75
        assert "hmdb_id" in first_result.hmdb_match
        assert first_result.rank >= 1
        # This test should FAIL initially

    def test_match_deduplication(self, action):
        """Test deduplication keeps best matches."""
        matches = [
            VectorMatchResult(
                metabolite={"BIOCHEMICAL_NAME": "test"},
                hmdb_match={"hmdb_id": "HMDB001"},
                similarity_score=0.85,
                rank=1,
                matched_on="original_name",
            ),
            VectorMatchResult(
                metabolite={"BIOCHEMICAL_NAME": "test"},
                hmdb_match={"hmdb_id": "HMDB002"},
                similarity_score=0.90,  # Higher score
                rank=1,
                matched_on="cts_enriched",
            ),
            VectorMatchResult(
                metabolite={"BIOCHEMICAL_NAME": "other"},
                hmdb_match={"hmdb_id": "HMDB003"},
                similarity_score=0.88,
                rank=1,
                matched_on="original_name",
            ),
        ]

        deduplicated = action._deduplicate_matches(matches)

        assert len(deduplicated) == 2  # Two unique metabolites

        # Should keep the higher score for 'test'
        test_match = next(
            m for m in deduplicated if m.metabolite["BIOCHEMICAL_NAME"] == "test"
        )
        assert test_match.similarity_score == 0.90
        assert test_match.hmdb_match["hmdb_id"] == "HMDB002"
        # This test should FAIL initially

    @pytest.mark.asyncio
    async def test_full_vector_matching_workflow(
        self, action, mock_embedding_model, mock_qdrant_client, unmatched_metabolites
    ):
        """Test complete vector matching workflow."""
        action.embedding_model = mock_embedding_model
        action.qdrant_client = mock_qdrant_client

        params = VectorEnhancedMatchParams(
            unmatched_dataset_key="unmatched",
            qdrant_collection="hmdb_metabolites",
            similarity_threshold=0.75,
            output_key="vector_matches",
            track_metrics=True,
        )

        context = {"datasets": {"unmatched": unmatched_metabolites}}

        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="metabolite",
            params=params,
            source_endpoint=None,
            target_endpoint=None,
            context=context,
        )

        assert result is not None
        matches = context["datasets"]["vector_matches"]

        # Should find matches
        assert len(matches) > 0

        # Check match structure
        for match in matches:
            assert "source" in match
            assert "target" in match
            assert match["stage"] == "vector_enhanced"
            assert match["score"] >= 0.75
            assert "method" in match
            assert "vector_search" in match["method"]

        # Check metrics
        assert "metrics" in context
        metrics = context["metrics"]["vector_enhanced"]
        assert metrics["stage"] == "vector_enhanced"
        assert metrics["total_matched"] > 0
        assert metrics["embedding_time"] > 0
        assert metrics["search_time"] > 0
        # This test should FAIL initially

    @pytest.mark.asyncio
    async def test_no_collection_error(self, action):
        """Test error handling when collection doesn't exist."""
        params = VectorEnhancedMatchParams(
            unmatched_dataset_key="unmatched",
            qdrant_collection="non_existent",
            output_key="matches",
        )

        with patch(
            "biomapper.core.strategy_actions.vector_enhanced_match.QdrantClient"
        ) as mock_qdrant:
            mock_instance = Mock()
            mock_instance.get_collection.side_effect = Exception("Collection not found")
            mock_qdrant.return_value = mock_instance

            with pytest.raises(ValueError, match="collection 'non_existent' not found"):
                action._initialize_clients(params)
        # This test should FAIL initially

    @pytest.mark.asyncio
    async def test_empty_search_texts(
        self, action, mock_embedding_model, mock_qdrant_client
    ):
        """Test handling metabolites with no searchable text."""
        metabolites = [{"BIOCHEMICAL_NAME": "", "cts_enriched_names": []}]

        action.embedding_model = mock_embedding_model
        action.qdrant_client = mock_qdrant_client

        params = VectorEnhancedMatchParams(
            unmatched_dataset_key="unmatched",
            qdrant_collection="hmdb_metabolites",
            output_key="matches",
        )

        results, _, _ = await action._batch_vector_search(metabolites, params)

        assert len(results) == 0  # No search texts, no results
        # This test should FAIL initially
