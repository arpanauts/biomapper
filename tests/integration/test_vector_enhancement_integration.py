import pytest
from unittest.mock import Mock, patch
import numpy as np

from biomapper.core.strategy_actions.vector_enhanced_match import VectorEnhancedMatchAction, VectorEnhancedMatchParams


@pytest.mark.integration
class TestVectorEnhancementIntegration:
    """Integration tests for vector enhancement stage."""
    
    @pytest.mark.asyncio
    @pytest.mark.requires_external_services
    async def test_progressive_enhancement_final_stage(self):
        """Test vector search as final enhancement stage."""
        # Simulate unmatched from CTS stage
        unmatched_from_cts = [
            {
                'BIOCHEMICAL_NAME': 'N-acetyl-L-methionine sulfoxide',
                'cts_enriched_names': [
                    'N-acetylmethionine sulfoxide',
                    'Acetylmethionine S-oxide'
                ],
                'SUB_PATHWAY': 'Methionine, Cysteine, SAM and Taurine Metabolism'
            },
            {
                'BIOCHEMICAL_NAME': '3-hydroxy-3-methylglutarate',
                'cts_enriched_names': ['HMG', 'meglutol'],
                'SUPER_PATHWAY': 'Lipid'
            }
        ]
        
        action = VectorEnhancedMatchAction()
        
        # Mock Qdrant with relevant HMDB entries
        with patch.object(action, 'qdrant_client') as mock_client:
            with patch.object(action, 'embedding_model') as mock_embed:
                # Mock embeddings
                mock_embed.embed = Mock(return_value=[np.random.rand(384) for _ in range(10)])
                
                # Mock search to return relevant matches
                def mock_search(collection_name, query_vector, limit, score_threshold=None):
                    # Return metabolite-specific results
                    if 'methionine' in str(query_vector):
                        return [Mock(
                            score=0.82,
                            payload={
                                'hmdb_id': 'HMDB0029432',
                                'name': 'N-Acetylmethionine sulfoxide',
                                'synonyms': ['AC-Met-sulfoxide']
                            }
                        )]
                    elif 'glutarate' in str(query_vector):
                        return [Mock(
                            score=0.79,
                            payload={
                                'hmdb_id': 'HMDB0000355',
                                'name': '3-Hydroxy-3-methylglutaric acid',
                                'synonyms': ['HMG', 'Meglutol']
                            }
                        )]
                    return []
                
                mock_client.search.side_effect = mock_search
                mock_client.get_collection.return_value = Mock(points_count=100000)
                
                params = VectorEnhancedMatchParams(
                    unmatched_dataset_key="unmatched",
                    similarity_threshold=0.75,
                    output_key="vector_matches"
                )
                
                context = {
                    'datasets': {
                        'unmatched': unmatched_from_cts
                    }
                }
                
                result = await action.execute_typed(
                    current_identifiers=[],
                    current_ontology_type="metabolite",
                    params=params,
                    source_endpoint=None,
                    target_endpoint=None,
                    context=context
                )
                
                matches = context['datasets']['vector_matches']
                
                # Should match both complex metabolites
                assert len(matches) >= 1
                
                # Verify semantic matching worked
                matched_names = {m['source']['BIOCHEMICAL_NAME'] for m in matches}
                assert any('methionine' in name.lower() for name in matched_names)
        # This test should FAIL initially