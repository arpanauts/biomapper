"""Unit tests for semantic metabolite matching action."""

import os
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from actions.semantic_metabolite_match import (
    EmbeddingCache,
    SemanticMetaboliteMatchAction,
    SemanticMetaboliteMatchParams,
)


class TestEmbeddingCache:
    """Test the embedding cache functionality."""

    def test_memory_cache(self):
        """Test in-memory caching."""
        cache = EmbeddingCache()
        text = "test metabolite"
        embedding = [0.1, 0.2, 0.3]

        # Initially not cached
        assert cache.get(text) is None

        # Store and retrieve
        cache.set(text, embedding)
        assert cache.get(text) == embedding

    def test_disk_cache(self, tmp_path):
        """Test disk-based caching."""
        cache = EmbeddingCache(str(tmp_path))
        text = "test metabolite"
        embedding = [0.1, 0.2, 0.3]

        # Store in cache
        cache.set(text, embedding)

        # Create new cache instance
        new_cache = EmbeddingCache(str(tmp_path))
        assert new_cache.get(text) == embedding

    def test_invalid_disk_cache(self, tmp_path):
        """Test handling of corrupted cache files."""
        cache = EmbeddingCache(str(tmp_path))
        text = "test metabolite"

        # Create corrupted cache file
        import hashlib

        cache_key = hashlib.md5(text.encode()).hexdigest()
        cache_file = tmp_path / f"{cache_key}.json"
        cache_file.write_text("invalid json")

        # Should return None on error
        assert cache.get(text) is None


class TestSemanticMetaboliteMatchAction:
    """Test the semantic metabolite match action."""

    @pytest.fixture
    def action(self):
        """Create action instance."""
        return SemanticMetaboliteMatchAction()

    @pytest.fixture
    def mock_openai_client(self):
        """Mock OpenAI client."""
        client = MagicMock()

        # Mock embedding response
        embedding_response = MagicMock()
        embedding_response.data = [MagicMock(embedding=[0.1] * 1536)]
        client.embeddings.create.return_value = embedding_response

        # Mock chat completion response
        chat_response = MagicMock()
        chat_response.choices = [
            MagicMock(
                message=MagicMock(
                    content="YES|0.95|Both refer to total cholesterol measurements"
                )
            )
        ]
        client.chat.completions.create.return_value = chat_response

        return client

    @pytest.fixture
    def sample_params(self):
        """Create sample parameters."""
        return SemanticMetaboliteMatchParams(
            unmatched_dataset="arivale_unmatched",
            reference_map="nightingale_reference",
            context_fields={
                "arivale": ["BIOCHEMICAL_NAME", "SUPER_PATHWAY", "SUB_PATHWAY"],
                "nightingale": ["unified_name", "description", "category"],
            },
            output_key="semantic_matches",
            unmatched_key="final_unmatched",
            max_llm_calls=10,
            confidence_threshold=0.75,
            embedding_similarity_threshold=0.85,
        )

    @pytest.fixture
    def sample_context(self):
        """Create sample execution context."""
        return {
            "datasets": {
                "arivale_unmatched": [
                    {
                        "BIOCHEMICAL_NAME": "Total Cholesterol",
                        "SUPER_PATHWAY": "Lipid",
                        "SUB_PATHWAY": "Sterol",
                        "HMDB_ID": "HMDB0000067",
                    },
                    {
                        "BIOCHEMICAL_NAME": "Glucose",
                        "SUPER_PATHWAY": "Carbohydrate",
                        "SUB_PATHWAY": "Glycolysis",
                    },
                ],
                "nightingale_reference": [
                    {
                        "unified_name": "Total cholesterol",
                        "description": "Total cholesterol concentration",
                        "category": "Cholesterol",
                    },
                    {
                        "unified_name": "Glucose",
                        "description": "Glucose concentration",
                        "category": "Glycolysis related",
                    },
                ],
            }
        }

    def test_get_params_model(self, action):
        """Test parameter model retrieval."""
        assert action.get_params_model() == SemanticMetaboliteMatchParams

    def test_create_context_string(self, action):
        """Test context string creation."""
        metabolite = {
            "BIOCHEMICAL_NAME": "Test Metabolite",
            "SUPER_PATHWAY": "Test Pathway",
            "SUB_PATHWAY": "Test Subpathway",
            "description": "Test description",
        }
        fields = ["BIOCHEMICAL_NAME", "description"]

        context = action._create_context_string(metabolite, fields, "test_dataset")

        assert "Metabolite: Test Metabolite" in context
        assert "SUPER_PATHWAY: Test Pathway" in context
        assert "SUB_PATHWAY: Test Subpathway" in context
        assert "Description: Test description" in context

    def test_extract_additional_info(self, action):
        """Test additional info extraction."""
        metabolite = {
            "HMDB_ID": "HMDB0000067",
            "KEGG_ID": "C00001",
            "formula": "C27H46O",
            "unknown_field": "ignored",
        }

        info = action._extract_additional_info(metabolite)

        assert "HMDB_ID: HMDB0000067" in info
        assert "KEGG_ID: C00001" in info
        assert "formula: C27H46O" in info
        assert "unknown_field" not in info

    def test_find_candidates(self, action):
        """Test candidate finding with cosine similarity."""
        source_embedding = [1.0, 0.0, 0.0]
        reference_embeddings = {
            0: [0.9, 0.1, 0.0],  # High similarity
            1: [0.0, 1.0, 0.0],  # Low similarity
            2: [0.95, 0.05, 0.0],  # Very high similarity
        }

        candidates = action._find_candidates(
            source_embedding, reference_embeddings, threshold=0.8, top_k=2
        )

        # Should return top 2 with similarity >= 0.8
        assert len(candidates) == 2
        assert candidates[0][0] == 2  # Highest similarity
        assert candidates[1][0] == 0  # Second highest
        assert candidates[0][1] > candidates[1][1]

    @pytest.mark.asyncio
    async def test_generate_embeddings_with_cache(self, action, mock_openai_client):
        """Test embedding generation with caching."""
        action.openai_client = mock_openai_client
        action.embedding_cache = EmbeddingCache()

        texts = ["test1", "test2", "test1"]  # test1 repeated

        embeddings = await action._generate_embeddings(texts, "text-embedding-ada-002")

        # Should only call API twice (test1 cached on second occurrence)
        assert mock_openai_client.embeddings.create.call_count == 2
        assert len(embeddings) == 3
        assert embeddings[0] == embeddings[2]  # Cached result

    @pytest.mark.asyncio
    async def test_generate_embeddings_error_handling(self, action):
        """Test embedding generation error handling."""
        action.openai_client = MagicMock()
        action.openai_client.embeddings.create.side_effect = Exception("API Error")
        action.embedding_cache = EmbeddingCache()

        embeddings = await action._generate_embeddings(["test"], "model")

        # Should return zero vector on error
        assert len(embeddings) == 1
        assert all(v == 0.0 for v in embeddings[0])

    @pytest.mark.asyncio
    async def test_validate_match_with_llm(self, action, mock_openai_client):
        """Test LLM validation."""
        action.openai_client = mock_openai_client

        source = {
            "BIOCHEMICAL_NAME": "Total Cholesterol",
            "SUPER_PATHWAY": "Lipid",
            "SUB_PATHWAY": "Sterol",
        }
        candidate = {
            "unified_name": "Total cholesterol",
            "description": "Total cholesterol concentration",
            "category": "Cholesterol",
        }

        is_match, confidence, reasoning = await action._validate_match_with_llm(
            source, candidate, 0.92, "gpt-4"
        )

        assert is_match is True
        assert confidence == 0.95
        assert "cholesterol" in reasoning.lower()

    @pytest.mark.asyncio
    async def test_validate_match_llm_parse_error(self, action, mock_openai_client):
        """Test LLM validation with parse error."""
        action.openai_client = mock_openai_client
        mock_openai_client.chat.completions.create.return_value.choices[
            0
        ].message.content = "Invalid response format"

        is_match, confidence, reasoning = await action._validate_match_with_llm(
            {}, {}, 0.9, "gpt-4"
        )

        assert is_match is False
        assert confidence == 0.0
        assert "Failed to parse" in reasoning

    @pytest.mark.asyncio
    async def test_validate_match_llm_api_error(self, action):
        """Test LLM validation with API error."""
        action.openai_client = MagicMock()
        action.openai_client.chat.completions.create.side_effect = Exception(
            "API Error"
        )

        is_match, confidence, reasoning = await action._validate_match_with_llm(
            {}, {}, 0.9, "gpt-4"
        )

        assert is_match is False
        assert confidence == 0.0
        assert "LLM error" in reasoning

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    async def test_execute_typed_success(
        self, action, mock_openai_client, sample_params, sample_context
    ):
        """Test successful execution."""
        action.openai_client = mock_openai_client
        action.embedding_cache = EmbeddingCache()

        # Mock embeddings to ensure high similarity
        mock_embeddings = [[0.1] * 1536, [0.1] * 1536]
        action._generate_embeddings_batch = AsyncMock(
            side_effect=[
                {0: mock_embeddings[0], 1: mock_embeddings[1]},  # Source
                {0: mock_embeddings[0], 1: mock_embeddings[1]},  # Reference
            ]
        )

        result = await action.execute_typed(
            [],  # current_identifiers
            "metabolite",  # current_ontology_type
            sample_params,
            None,  # source_endpoint
            None,  # target_endpoint
            sample_context,
        )

        assert result.success
        assert "semantic_matches" in sample_context["datasets"]
        assert "final_unmatched" in sample_context["datasets"]

        matches = sample_context["datasets"]["semantic_matches"]
        assert len(matches) > 0
        assert matches[0]["match_method"] == "semantic_llm"
        assert matches[0]["match_confidence"] == 0.95

    @pytest.mark.asyncio
    async def test_execute_typed_no_unmatched(
        self, action, sample_params, mock_openai_client
    ):
        """Test execution with no unmatched metabolites."""
        context = {"datasets": {"arivale_unmatched": []}}

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            action.openai_client = mock_openai_client
            result = await action.execute_typed(
                [],  # current_identifiers
                "metabolite",  # current_ontology_type
                sample_params,
                None,  # source_endpoint
                None,  # target_endpoint
                context,
            )

        assert result.success
        assert result.data["matched_count"] == 0

    @pytest.mark.asyncio
    async def test_execute_typed_no_reference(
        self, action, sample_params, mock_openai_client
    ):
        """Test execution with no reference metabolites."""
        context = {"datasets": {"arivale_unmatched": [{"name": "test"}]}}

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            action.openai_client = mock_openai_client
            result = await action.execute_typed(
                [],  # current_identifiers
                "metabolite",  # current_ontology_type
                sample_params,
                None,  # source_endpoint
                None,  # target_endpoint
                context,
            )

        assert not result.success
        assert "Missing reference dataset" in result.error

    @pytest.mark.asyncio
    async def test_execute_typed_llm_limit(
        self, action, mock_openai_client, sample_context
    ):
        """Test LLM call limit enforcement."""
        params = SemanticMetaboliteMatchParams(
            unmatched_dataset="arivale_unmatched",
            reference_map="nightingale_reference",
            context_fields={
                "arivale": ["BIOCHEMICAL_NAME"],
                "nightingale": ["unified_name"],
            },
            output_key="semantic_matches",
            max_llm_calls=1,  # Very low limit
        )

        # Add more unmatched metabolites
        sample_context["datasets"]["arivale_unmatched"] = [
            {"BIOCHEMICAL_NAME": f"Metabolite {i}"} for i in range(5)
        ]

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            action.openai_client = mock_openai_client
            action.embedding_cache = EmbeddingCache()

            # Mock embeddings
            action._generate_embeddings_batch = AsyncMock(
                return_value={i: [0.1] * 1536 for i in range(5)}
            )

            result = await action.execute_typed(
                [],  # current_identifiers
                "metabolite",  # current_ontology_type
                params,
                None,  # source_endpoint
                None,  # target_endpoint
                sample_context,
            )

        assert result.success
        assert result.data["llm_calls"] == 1  # Respected limit

    @pytest.mark.asyncio
    async def test_execute_typed_no_api_key(
        self, action, sample_params, sample_context
    ):
        """Test execution without API key."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="OPENAI_API_KEY"):
                action._initialize_clients()

    def test_initialize_clients_import_error(self, action):
        """Test client initialization with missing openai library."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            with patch.dict("sys.modules", {"openai": None}):
                with pytest.raises(ImportError, match="OpenAI library not found"):
                    action._initialize_clients()

    @pytest.mark.asyncio
    async def test_generate_embeddings_batch(self, action, mock_openai_client):
        """Test batch embedding generation."""
        action.openai_client = mock_openai_client
        action.embedding_cache = EmbeddingCache()

        metabolites = [
            {"name": "Metabolite 1", "pathway": "Path 1"},
            {"name": "Metabolite 2", "pathway": "Path 2"},
        ]

        embeddings = await action._generate_embeddings_batch(
            metabolites, ["name", "pathway"], "test_dataset", "model", batch_size=1
        )

        assert len(embeddings) == 2
        assert 0 in embeddings
        assert 1 in embeddings

    @pytest.mark.asyncio
    async def test_cache_hit_tracking(
        self, action, mock_openai_client, sample_params, sample_context
    ):
        """Test cache hit tracking in results."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            action.openai_client = mock_openai_client
            action.embedding_cache = EmbeddingCache()

            # Pre-cache some embeddings
            action.embedding_cache.set("test", [0.1] * 1536)

            # Mock to use cached text
            action._create_context_string = Mock(return_value="test")
            action._generate_embeddings_batch = AsyncMock(
                return_value={0: [0.1] * 1536, 1: [0.1] * 1536}
            )

            result = await action.execute_typed(
                [],  # current_identifiers
                "metabolite",  # current_ontology_type
                sample_params,
                None,  # source_endpoint
                None,  # target_endpoint
                sample_context,
            )

            assert result.success
            assert "cache_hits" in result.data
            assert result.data["cache_hits"] >= 0
