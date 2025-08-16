"""
Tests for PROTEIN_HISTORICAL_RESOLUTION action.

This action resolves deprecated/updated UniProt IDs to their current equivalents
using UniProt's historical mapping data.
"""

import pytest
import pandas as pd
from unittest.mock import Mock, patch, AsyncMock
from biomapper.core.strategy_actions.entities.proteins.matching.historical_resolution import (
    ProteinHistoricalResolution,
    ProteinHistoricalResolutionParams,
    ActionResult
)


class TestProteinHistoricalResolution:
    """Comprehensive tests for UniProt historical ID resolution."""
    
    @pytest.fixture
    def sample_deprecated_data(self):
        """Sample dataset with deprecated UniProt IDs."""
        return pd.DataFrame({
            'id': ['protein_1', 'protein_2', 'protein_3', 'protein_4'],
            'uniprot_id': ['P12345', 'Q99999', 'O00000', 'P54321'],  # Q99999 and O00000 are deprecated
            'gene_symbol': ['GENE1', 'GENE2', 'GENE3', 'GENE4']
        })
    
    @pytest.fixture
    def unmatched_results(self):
        """Previous matching results showing unmatched IDs."""
        return pd.DataFrame({
            'source_id': ['protein_2', 'protein_3'],
            'uniprot_id': ['Q99999', 'O00000'],
            'match_status': ['unmatched', 'unmatched']
        })
    
    @pytest.fixture
    def reference_dataset(self):
        """Reference dataset with current UniProt IDs."""
        return pd.DataFrame({
            'uniprot_id': ['P12345', 'Q88888', 'O11111', 'P54321'],  # Q88888 replaces Q99999, O11111 replaces O00000
            'gene_symbol': ['GENE1', 'GENE2', 'GENE3', 'GENE4'],
            'protein_name': ['Protein 1', 'Protein 2', 'Protein 3', 'Protein 4']
        })
    
    @pytest.fixture
    def mock_uniprot_api_responses(self):
        """Mock responses from UniProt API for historical mappings."""
        return {
            'Q99999': {
                'current_id': 'Q88888',
                'status': 'replaced',
                'confidence': 1.0,
                'reason': 'Entry merged'
            },
            'O00000': {
                'current_id': 'O11111',
                'status': 'superseded',
                'confidence': 0.95,
                'reason': 'Sequence update'
            }
        }
    
    @pytest.mark.asyncio
    async def test_resolve_deprecated_uniprot_ids(self, sample_deprecated_data, mock_uniprot_api_responses):
        """Should resolve deprecated UniProt IDs to current ones."""
        # This test will fail initially - that's the TDD point
        action = ProteinHistoricalResolution()
        params = ProteinHistoricalResolutionParams(
            dataset_key="deprecated_proteins",
            output_key="resolved_proteins"
        )
        
        context = {
            'datasets': {
                'deprecated_proteins': sample_deprecated_data
            }
        }
        
        # Mock the UniProt API calls
        with patch.object(action, '_query_uniprot_history', new_callable=AsyncMock) as mock_query:
            mock_query.side_effect = lambda uid: mock_uniprot_api_responses.get(uid, None)
            
            result = await action.execute_typed(params, context)
        
        # Assertions that will fail until implemented
        assert result.success is True
        assert 'resolved_proteins' in context['datasets']
        
        resolved_data = context['datasets']['resolved_proteins']
        resolved_df = pd.DataFrame(resolved_data)
        assert len(resolved_df) == 4
        
        # Check that deprecated IDs were resolved
        protein_2 = resolved_df[resolved_df['id'] == 'protein_2'].iloc[0]
        assert protein_2['resolved_uniprot_id'] == 'Q88888'
        assert protein_2['resolution_confidence'] == 1.0
        assert protein_2['resolution_status'] == 'replaced'
        
        protein_3 = resolved_df[resolved_df['id'] == 'protein_3'].iloc[0]
        assert protein_3['resolved_uniprot_id'] == 'O11111'
        assert protein_3['resolution_confidence'] == 0.95
        assert protein_3['resolution_status'] == 'superseded'
    
    @pytest.mark.asyncio
    async def test_resolve_with_unmatched_filter(self, sample_deprecated_data, unmatched_results, mock_uniprot_api_responses):
        """Should only resolve IDs that were previously unmatched."""
        action = ProteinHistoricalResolution()
        params = ProteinHistoricalResolutionParams(
            dataset_key="deprecated_proteins",
            unmatched_from="previous_matching",
            output_key="resolved_proteins"
        )
        
        context = {
            'datasets': {
                'deprecated_proteins': sample_deprecated_data,
                'previous_matching': unmatched_results
            }
        }
        
        with patch.object(action, '_query_uniprot_history', new_callable=AsyncMock) as mock_query:
            mock_query.side_effect = lambda uid: mock_uniprot_api_responses.get(uid, None)
            
            result = await action.execute_typed(params, context)
        
        assert result.success is True
        resolved_data = context['datasets']['resolved_proteins']
        resolved_df = pd.DataFrame(resolved_data)
        
        # Should only have processed the unmatched IDs
        assert len(resolved_df) == 2
        assert set(resolved_df['id'].values) == {'protein_2', 'protein_3'}
    
    @pytest.mark.asyncio
    async def test_resolve_with_reference_dataset_matching(self, sample_deprecated_data, reference_dataset, mock_uniprot_api_responses):
        """Should match resolved IDs against reference dataset."""
        action = ProteinHistoricalResolution()
        params = ProteinHistoricalResolutionParams(
            dataset_key="deprecated_proteins",
            reference_dataset="reference_proteins",
            output_key="resolved_proteins"
        )
        
        context = {
            'datasets': {
                'deprecated_proteins': sample_deprecated_data,
                'reference_proteins': reference_dataset
            }
        }
        
        with patch.object(action, '_query_uniprot_history', new_callable=AsyncMock) as mock_query:
            mock_query.side_effect = lambda uid: mock_uniprot_api_responses.get(uid, None)
            
            result = await action.execute_typed(params, context)
        
        assert result.success is True
        resolved_data = context['datasets']['resolved_proteins']
        resolved_df = pd.DataFrame(resolved_data)
        
        # Check that resolved IDs were matched against reference
        protein_2 = resolved_df[resolved_df['id'] == 'protein_2'].iloc[0]
        assert protein_2['reference_match'] == True
        assert protein_2['reference_protein_name'] == 'Protein 2'
        
        protein_3 = resolved_df[resolved_df['id'] == 'protein_3'].iloc[0]
        assert protein_3['reference_match'] == True
        assert protein_3['reference_protein_name'] == 'Protein 3'
    
    @pytest.mark.asyncio
    async def test_handle_unresolvable_ids(self, sample_deprecated_data):
        """Should handle IDs that cannot be resolved."""
        action = ProteinHistoricalResolution()
        params = ProteinHistoricalResolutionParams(
            dataset_key="deprecated_proteins",
            output_key="resolved_proteins"
        )
        
        context = {
            'datasets': {
                'deprecated_proteins': sample_deprecated_data
            }
        }
        
        # Mock API to return None for all queries (simulating unresolvable IDs)
        with patch.object(action, '_query_uniprot_history', new_callable=AsyncMock) as mock_query:
            mock_query.return_value = None
            
            result = await action.execute_typed(params, context)
        
        assert result.success is True
        resolved_data = context['datasets']['resolved_proteins']
        resolved_df = pd.DataFrame(resolved_data)
        
        # All IDs should be marked as unresolved
        assert (resolved_df['resolution_status'] == 'unresolved').all()
        assert resolved_df['resolved_uniprot_id'].isna().all()
        assert (resolved_df['resolution_confidence'] == 0.0).all()
    
    @pytest.mark.asyncio
    async def test_statistics_tracking(self, sample_deprecated_data, mock_uniprot_api_responses):
        """Should track resolution statistics in context."""
        action = ProteinHistoricalResolution()
        params = ProteinHistoricalResolutionParams(
            dataset_key="deprecated_proteins",
            output_key="resolved_proteins"
        )
        
        context = {
            'datasets': {
                'deprecated_proteins': sample_deprecated_data
            },
            'statistics': {}
        }
        
        with patch.object(action, '_query_uniprot_history', new_callable=AsyncMock) as mock_query:
            mock_query.side_effect = lambda uid: mock_uniprot_api_responses.get(uid, None)
            
            result = await action.execute_typed(params, context)
        
        assert result.success is True
        assert 'historical_resolution' in context['statistics']
        
        stats = context['statistics']['historical_resolution']
        assert stats['total_processed'] == 4
        assert stats['resolved_count'] == 2
        assert stats['unresolved_count'] == 2
        assert stats['resolution_rate'] == 0.5
        assert 'replaced' in stats['resolution_types']
        assert 'superseded' in stats['resolution_types']
    
    @pytest.mark.asyncio
    async def test_empty_dataset_handling(self):
        """Should handle empty input datasets gracefully."""
        action = ProteinHistoricalResolution()
        params = ProteinHistoricalResolutionParams(
            dataset_key="empty_proteins",
            output_key="resolved_proteins"
        )
        
        context = {
            'datasets': {
                'empty_proteins': pd.DataFrame()
            }
        }
        
        result = await action.execute_typed(params, context)
        
        assert result.success is False
        assert "empty" in result.message.lower()
    
    @pytest.mark.asyncio
    async def test_missing_dataset_handling(self):
        """Should handle missing input dataset with clear error."""
        action = ProteinHistoricalResolution()
        params = ProteinHistoricalResolutionParams(
            dataset_key="nonexistent",
            output_key="resolved_proteins"
        )
        
        context = {'datasets': {}}
        
        result = await action.execute_typed(params, context)
        
        assert result.success is False
        assert "not found" in result.message.lower()
    
    @pytest.mark.asyncio
    async def test_batch_processing_for_large_datasets(self):
        """Should process large datasets in batches to avoid API rate limits."""
        # Create large dataset
        large_data = pd.DataFrame({
            'id': [f'protein_{i}' for i in range(100)],
            'uniprot_id': [f'Q{i:05d}' for i in range(100)]
        })
        
        action = ProteinHistoricalResolution()
        params = ProteinHistoricalResolutionParams(
            dataset_key="large_proteins",
            output_key="resolved_proteins",
            batch_size=10  # Process in batches of 10
        )
        
        context = {
            'datasets': {
                'large_proteins': large_data
            }
        }
        
        call_count = 0
        async def mock_batch_query(uid):
            nonlocal call_count
            call_count += 1
            return None  # Simulate no resolution for simplicity
        
        with patch.object(action, '_query_uniprot_history', new_callable=AsyncMock) as mock_query:
            mock_query.side_effect = mock_batch_query
            
            result = await action.execute_typed(params, context)
        
        assert result.success is True
        assert call_count == 100  # Should have queried all 100 IDs
        
        # Check that results were collected properly
        resolved_data = context['datasets']['resolved_proteins']
        resolved_df = pd.DataFrame(resolved_data)
        assert len(resolved_df) == 100
    
    @pytest.mark.asyncio
    async def test_confidence_threshold_filtering(self, sample_deprecated_data, mock_uniprot_api_responses):
        """Should filter resolutions based on confidence threshold."""
        action = ProteinHistoricalResolution()
        params = ProteinHistoricalResolutionParams(
            dataset_key="deprecated_proteins",
            output_key="resolved_proteins",
            min_confidence=0.98  # High confidence threshold
        )
        
        context = {
            'datasets': {
                'deprecated_proteins': sample_deprecated_data
            }
        }
        
        with patch.object(action, '_query_uniprot_history', new_callable=AsyncMock) as mock_query:
            mock_query.side_effect = lambda uid: mock_uniprot_api_responses.get(uid, None)
            
            result = await action.execute_typed(params, context)
        
        assert result.success is True
        resolved_data = context['datasets']['resolved_proteins']
        resolved_df = pd.DataFrame(resolved_data)
        
        # Only Q99999 -> Q88888 has confidence 1.0 >= 0.98
        protein_2 = resolved_df[resolved_df['id'] == 'protein_2'].iloc[0]
        assert protein_2['resolved_uniprot_id'] == 'Q88888'
        assert protein_2['resolution_confidence'] == 1.0
        
        # O00000 -> O11111 has confidence 0.95 < 0.98, should not be resolved
        protein_3 = resolved_df[resolved_df['id'] == 'protein_3'].iloc[0]
        assert pd.isna(protein_3['resolved_uniprot_id']) or protein_3['resolution_status'] == 'below_threshold'