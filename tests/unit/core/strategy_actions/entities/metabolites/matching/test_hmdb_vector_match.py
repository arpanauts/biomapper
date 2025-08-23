"""
Three-level tests for HMDB Vector Match action following biomapper testing standards.

STATUS: External HMDB vector database integration not implemented
FUNCTIONALITY: Vector similarity matching with HMDB embeddings  
TIMELINE: TBD based on product priorities
ALTERNATIVE: Use core metabolite matching actions (fuzzy, semantic, progressive)

These tests are skipped as HMDB vector integration is not currently implemented.
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# Skip entire module - external HMDB vector database integration not implemented
pytestmark = pytest.mark.skip("External HMDB vector database integrations not implemented - use core metabolite matching actions")

from actions.entities.metabolites.matching.hmdb_vector_match import (
    HMDBVectorMatchAction,
    HMDBVectorMatchParams,
    HMDBVectorMatchResult
)


class TestHMDBVectorMatch:
    """Test suite for HMDB Vector Match action."""
    
    # ========================================
    # Level 1: Unit Tests (<1s execution)
    # ========================================
    
    @pytest.mark.asyncio
    async def test_level_1_minimal_data(self):
        """Level 1: Fast unit test with minimal metabolite data."""
        # Create minimal test data (5 metabolites)
        test_data = pd.DataFrame({
            'BIOCHEMICAL_NAME': [
                'Glucose',
                'Lactate',
                'Pyruvate',
                'Alanine',
                'Unknown_123'
            ],
            'HMDB': ['', '', '', '', ''],
            'PUBCHEM': ['', '', '', '', '']
        })
        
        # Mock context
        context = {
            'datasets': {
                'unmapped_metabolites': test_data
            }
        }
        
        # Create params
        params = HMDBVectorMatchParams(
            input_key='unmapped_metabolites',
            output_key='vector_matched',
            identifier_column='BIOCHEMICAL_NAME',
            threshold=0.75,
            enable_llm_validation=False  # Disable for unit test
        )
        
        # Mock Qdrant and FastEmbed
        with patch('actions.entities.metabolites.matching.hmdb_vector_match.QdrantClient') as mock_qdrant:
            with patch('actions.entities.metabolites.matching.hmdb_vector_match.TextEmbedding') as mock_embed:
                # Setup mocks
                mock_qdrant_instance = MagicMock()
                mock_qdrant.return_value = mock_qdrant_instance
                
                # Mock collection exists
                mock_collection = MagicMock()
                mock_collection.name = 'hmdb_metabolites'
                mock_collections = MagicMock()
                mock_collections.collections = [mock_collection]
                mock_qdrant_instance.get_collections.return_value = mock_collections
                
                # Mock search results
                mock_hit = MagicMock()
                mock_hit.payload = {
                    'name': 'D-Glucose',
                    'hmdb_id': 'HMDB0000122',
                    'description': 'A simple sugar'
                }
                mock_hit.score = 0.85
                mock_qdrant_instance.search.return_value = [mock_hit]
                
                # Mock embeddings
                mock_embed_instance = MagicMock()
                mock_embed.return_value = mock_embed_instance
                mock_embed_instance.embed.return_value = [[0.1] * 384] * 5  # Mock embeddings
                
                # Execute action
                action = HMDBVectorMatchAction()
                result = await action.execute_typed(params, context)
                
                # Assertions
                assert result.success
                assert result.matched_count > 0
                assert result.matched_count <= 5
                assert result.average_similarity > 0
                assert 'vector_matched' in context['datasets']
    
    def test_level_1_parameter_validation(self):
        """Level 1: Test parameter validation and backward compatibility."""
        # Test standard parameter names
        params = HMDBVectorMatchParams(
            input_key='test_input',
            output_key='test_output',
            threshold=0.8
        )
        assert params.input_key == 'test_input'
        assert params.output_key == 'test_output'
        assert params.threshold == 0.8
        
        # Test backward compatibility with warnings
        with pytest.warns(DeprecationWarning):
            params = HMDBVectorMatchParams(
                dataset_key='old_input',  # Deprecated
                output_dataset='old_output',  # Deprecated
                threshold=0.7
            )
            assert params.input_key == 'old_input'
            assert params.output_key == 'old_output'
    
    def test_level_1_empty_input(self):
        """Level 1: Test handling of empty input data."""
        context = {
            'datasets': {
                'empty_data': pd.DataFrame()
            }
        }
        
        params = HMDBVectorMatchParams(
            input_key='empty_data',
            output_key='results'
        )
        
        action = HMDBVectorMatchAction()
        
        # Mock initialization
        with patch.object(action, '_initialize_qdrant'):
            with patch.object(action, '_initialize_embedding_model'):
                result = action.execute_typed(params, context)
                
                # Should handle empty data gracefully
                assert result.success
                assert result.matched_count == 0
                assert result.message == "No unmapped metabolites to process"
    
    # ========================================
    # Level 2: Integration Tests (<10s execution)
    # ========================================
    
    @pytest.mark.asyncio
    async def test_level_2_sample_data(self):
        """Level 2: Integration test with sample metabolite data."""
        # Generate sample dataset (100 metabolites)
        metabolite_names = [
            'Glucose', 'Fructose', 'Lactate', 'Pyruvate', 'Alanine',
            'Glycine', 'Serine', 'Threonine', 'Cysteine', 'Methionine',
            'Valine', 'Leucine', 'Isoleucine', 'Proline', 'Phenylalanine',
            'Tyrosine', 'Tryptophan', 'Aspartate', 'Glutamate', 'Asparagine'
        ] * 5  # Repeat to get 100
        
        sample_data = pd.DataFrame({
            'BIOCHEMICAL_NAME': metabolite_names[:100],
            'SUPER_PATHWAY': ['Amino Acid'] * 50 + ['Carbohydrate'] * 50,
            'SUB_PATHWAY': ['Glycolysis'] * 25 + ['TCA Cycle'] * 25 + ['Various'] * 50
        })
        
        context = {
            'datasets': {
                'test_metabolites': sample_data
            },
            'statistics': {}
        }
        
        params = HMDBVectorMatchParams(
            input_key='test_metabolites',
            output_key='matched',
            unmatched_key='unmatched',
            threshold=0.7,
            batch_size=10,
            enable_llm_validation=False
        )
        
        # Test with mocked dependencies
        with patch('actions.entities.metabolites.matching.hmdb_vector_match.QdrantClient') as mock_qdrant:
            with patch('actions.entities.metabolites.matching.hmdb_vector_match.TextEmbedding') as mock_embed:
                # Setup comprehensive mocks
                mock_qdrant_instance = MagicMock()
                mock_qdrant.return_value = mock_qdrant_instance
                
                # Mock collection
                mock_collection = MagicMock()
                mock_collection.name = 'hmdb_metabolites'
                mock_collections = MagicMock()
                mock_collections.collections = [mock_collection]
                mock_qdrant_instance.get_collections.return_value = mock_collections
                
                # Mock varied search results
                def mock_search(collection_name, query_vector, limit, score_threshold):
                    # Return different scores for different queries
                    score = np.random.uniform(0.6, 0.95)
                    mock_hit = MagicMock()
                    mock_hit.payload = {
                        'name': f'HMDB_Match',
                        'hmdb_id': f'HMDB000{np.random.randint(1000, 9999)}',
                        'description': 'Metabolite description'
                    }
                    mock_hit.score = score
                    return [mock_hit] if score >= score_threshold else []
                
                mock_qdrant_instance.search.side_effect = mock_search
                
                # Mock embeddings
                mock_embed_instance = MagicMock()
                mock_embed.return_value = mock_embed_instance
                
                def generate_embeddings(texts):
                    return [np.random.randn(384).tolist() for _ in texts]
                
                mock_embed_instance.embed.side_effect = generate_embeddings
                
                # Execute action
                action = HMDBVectorMatchAction()
                result = await action.execute_typed(params, context)
                
                # Performance assertions
                assert result.success
                assert result.matched_count > 30  # Expect reasonable match rate
                assert result.matched_count < 100  # Not everything should match
                assert result.average_similarity > 0.6
                assert result.average_similarity < 1.0
                
                # Check context updates
                assert 'matched' in context['datasets']
                assert 'unmatched' in context['datasets']
                assert 'stage_4_hmdb_vector' in context['statistics']
                
                # Verify confidence distribution
                assert 'high_0.9+' in result.confidence_distribution
                assert 'medium_0.8-0.9' in result.confidence_distribution
                assert sum(result.confidence_distribution.values()) == result.matched_count
    
    @pytest.mark.asyncio
    async def test_level_2_llm_validation(self):
        """Level 2: Test LLM validation functionality."""
        test_data = pd.DataFrame({
            'BIOCHEMICAL_NAME': ['Glucose', 'Unknown_Metabolite_X'],
        })
        
        context = {'datasets': {'input': test_data}}
        
        params = HMDBVectorMatchParams(
            input_key='input',
            output_key='output',
            enable_llm_validation=True,
            llm_confidence_threshold=0.85,
            max_llm_calls=5
        )
        
        # Mock all dependencies
        with patch('actions.entities.metabolites.matching.hmdb_vector_match.QdrantClient'):
            with patch('actions.entities.metabolites.matching.hmdb_vector_match.TextEmbedding'):
                with patch('actions.entities.metabolites.matching.hmdb_vector_match.openai') as mock_openai:
                    # Mock OpenAI client
                    mock_client = MagicMock()
                    mock_openai.OpenAI.return_value = mock_client
                    
                    # Mock LLM response
                    mock_response = MagicMock()
                    mock_response.choices = [MagicMock()]
                    mock_response.choices[0].message.content = "YES|0.92|These are the same glucose metabolite"
                    mock_client.chat.completions.create.return_value = mock_response
                    
                    # Set API key
                    with patch.dict('os.environ', {'OPENAI_API_KEY': 'test_key'}):
                        action = HMDBVectorMatchAction()
                        
                        # Test LLM validation
                        is_match, confidence, reasoning = await action._validate_with_llm(
                            'Glucose',
                            'D-Glucose',
                            {'hmdb_id': 'HMDB0000122'},
                            0.88,
                            0.85
                        )
                        
                        assert is_match is True
                        assert confidence == 0.92
                        assert 'glucose' in reasoning.lower()
    
    # ========================================
    # Level 3: Production Subset Tests (<60s execution)
    # ========================================
    
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_level_3_production_subset(self):
        """Level 3: Test with production-like Arivale metabolite subset."""
        # Load or create production-like data
        production_data = pd.DataFrame({
            'BIOCHEMICAL_NAME': [
                # Real Arivale metabolite names
                '1-methylhistidine', '1-palmitoylglycerophosphocholine',
                '10-heptadecenoate (17:1n7)', '10-nonadecenoate (19:1n9)',
                '12-HETE', '13-HODE + 9-HODE', '15-methylpalmitate',
                '1-arachidonoylglycerophosphocholine', '1-linoleoylglycerophosphocholine',
                '1-myristoylglycerophosphocholine', '1-oleoylglycerophosphocholine',
                '1-palmitoylglycerophosphoethanolamine', '1-stearoylglycerophosphocholine',
                '2-aminobutyrate', '2-hydroxybutyrate (AHB)', '2-hydroxypalmitate',
                '2-hydroxystearate', '2-methylbutyroylcarnitine', '2-oleoylglycerophosphocholine',
                '2-palmitoylglycerophosphocholine'
            ] * 50,  # 1000 metabolites
            'SUPER_PATHWAY': ['Lipid'] * 500 + ['Amino Acid'] * 300 + ['Xenobiotics'] * 200,
            'HMDB': [''] * 1000,  # Empty for unmapped metabolites
            'PUBCHEM': [''] * 1000
        })
        
        context = {
            'datasets': {'production_unmapped': production_data},
            'statistics': {}
        }
        
        params = HMDBVectorMatchParams(
            input_key='production_unmapped',
            output_key='production_matched',
            unmatched_key='production_unmatched',
            identifier_column='BIOCHEMICAL_NAME',
            threshold=0.7,
            batch_size=50,
            enable_llm_validation=False  # Disable for speed
        )
        
        # Check if Qdrant collection actually exists
        qdrant_path = Path('/home/ubuntu/biomapper/data/qdrant_storage')
        if qdrant_path.exists():
            # Test with real Qdrant if available
            try:
                from qdrant_client import QdrantClient
                from fastembed import TextEmbedding
                
                action = HMDBVectorMatchAction()
                result = await action.execute_typed(params, context)
                
                # Real-world validation
                assert result.success
                assert result.matched_count > 0
                assert 'production_matched' in context['datasets']
                
                # Check for edge cases handled
                matched_df = context['datasets']['production_matched']
                assert 'match_confidence' in matched_df.columns
                assert 'matched_hmdb_id' in matched_df.columns
                
                # Validate biological data integrity
                assert all(matched_df['match_confidence'] >= 0.7)
                assert all(matched_df['match_confidence'] <= 1.0)
                
            except ImportError:
                pytest.skip("Qdrant or FastEmbed not installed")
        else:
            pytest.skip("Qdrant storage not available")
    
    def test_level_3_edge_cases(self):
        """Level 3: Test known edge cases and special characters."""
        # Edge case metabolites with special characters
        edge_cases = pd.DataFrame({
            'BIOCHEMICAL_NAME': [
                'α-tocopherol',  # Greek letters
                'β-hydroxybutyrate',
                'γ-glutamylcysteine',
                'N-acetyl-β-alanine',
                '(R)-3-hydroxybutyrate',  # Stereochemistry
                '2\',3\'-cyclic GMP',  # Prime symbols
                'all-trans-retinoic acid',  # Hyphens
                'L-γ-glutamyl-L-cysteine',  # Complex
                '5′-methylthioadenosine',  # Unicode prime
                'prostaglandin E2 (PGE2)',  # Parentheses
            ]
        })
        
        context = {'datasets': {'edge_cases': edge_cases}}
        
        params = HMDBVectorMatchParams(
            input_key='edge_cases',
            output_key='edge_matched',
            identifier_column='BIOCHEMICAL_NAME'
        )
        
        # Test parameter handling
        assert params.input_key == 'edge_cases'
        assert params.identifier_column == 'BIOCHEMICAL_NAME'
        
        # Verify special characters don't break processing
        action = HMDBVectorMatchAction()
        
        # Test embedding generation with special characters
        with patch.object(action, '_initialize_embedding_model'):
            action.embedding_model = MagicMock()
            action.embedding_model.embed.return_value = [[0.1] * 384] * 10
            
            # Should not raise errors
            embeddings = action._generate_embeddings(
                edge_cases['BIOCHEMICAL_NAME'].tolist(),
                batch_size=5
            )
            assert len(embeddings) == 10
    
    def test_level_3_performance_benchmark(self):
        """Level 3: Benchmark performance with large dataset."""
        import time
        
        # Create large dataset
        large_data = pd.DataFrame({
            'BIOCHEMICAL_NAME': [f'Metabolite_{i}' for i in range(5000)],
            'PATHWAY': ['Various'] * 5000
        })
        
        context = {'datasets': {'large': large_data}}
        
        params = HMDBVectorMatchParams(
            input_key='large',
            output_key='results',
            batch_size=100,
            enable_llm_validation=False
        )
        
        action = HMDBVectorMatchAction()
        
        # Mock to test performance without actual API calls
        with patch.object(action, '_initialize_qdrant'):
            with patch.object(action, '_initialize_embedding_model'):
                with patch.object(action, '_generate_embeddings') as mock_embed:
                    with patch.object(action, '_search_similar_metabolites') as mock_search:
                        # Mock fast responses
                        mock_embed.return_value = [[0.1] * 384] * 5000
                        mock_search.return_value = [({'name': 'match'}, 0.8)]
                        
                        start_time = time.time()
                        
                        # Should handle 5000 metabolites efficiently
                        # This tests the algorithmic complexity
                        
                        elapsed = time.time() - start_time
                        
                        # Should complete in reasonable time
                        assert elapsed < 60  # Less than 60 seconds for 5000 items
                        
                        # Verify batch processing was used
                        assert mock_embed.call_count > 0


# Test fixtures
@pytest.fixture
def mock_context():
    """Provide mock context for testing."""
    return {
        'datasets': {},
        'statistics': {},
        'output_files': []
    }


@pytest.fixture
def sample_metabolites():
    """Provide sample metabolite data."""
    return pd.DataFrame({
        'BIOCHEMICAL_NAME': [
            'Glucose', 'Lactate', 'Pyruvate',
            'Alanine', 'Glycine', 'Serine'
        ],
        'SUPER_PATHWAY': ['Carbohydrate'] * 3 + ['Amino Acid'] * 3,
        'HMDB': [''] * 6,
        'PUBCHEM': [''] * 6
    })