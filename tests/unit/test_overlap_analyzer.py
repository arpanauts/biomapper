"""Unit tests for DatasetOverlapAnalyzer action."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from biomapper.core.strategy_actions.overlap_analyzer import DatasetOverlapAnalyzer
from biomapper.db.models import Endpoint


@pytest.fixture
def mock_session():
    """Create a mock database session."""
    return AsyncMock()


@pytest.fixture
def mock_endpoints():
    """Create mock source and target endpoints."""
    source = MagicMock(spec=Endpoint)
    source.name = "test_source"
    target = MagicMock(spec=Endpoint)
    target.name = "test_target"
    return source, target


class TestDatasetOverlapAnalyzer:
    """Test DatasetOverlapAnalyzer functionality."""
    
    @pytest.fixture
    def action(self, mock_session):
        """Create DatasetOverlapAnalyzer instance."""
        return DatasetOverlapAnalyzer(session=mock_session)
    
    async def test_partial_overlap(self, action, mock_endpoints):
        """Test analysis with partial overlap between datasets."""
        source, target = mock_endpoints
        context = {
            'ukbb_proteins': ['Q14213', 'Q8NEV9', 'P12345', 'A1B2C3'],
            'hpa_proteins': ['Q14213', 'P12345', 'D4E5F6', 'G7H8I9']
        }
        
        action_params = {
            'dataset1_context_key': 'ukbb_proteins',
            'dataset2_context_key': 'hpa_proteins',
            'output_context_key': 'overlap_results'
        }
        
        result = await action.execute(
            current_identifiers=[],
            current_ontology_type='UniProt',
            action_params=action_params,
            source_endpoint=source,
            target_endpoint=target,
            context=context
        )
        
        # Check results
        assert set(result['output_identifiers']) == {'Q14213', 'P12345'}
        assert result['details']['dataset1_count'] == 4
        assert result['details']['dataset2_count'] == 4
        assert result['details']['overlap_count'] == 2
        
        # Check context was updated
        assert 'overlap_results' in context
        assert set(context['overlap_results']['overlapping_proteins']) == {'Q14213', 'P12345'}
        assert context['overlap_results']['overlap_count'] == 2
    
    async def test_full_overlap(self, action, mock_endpoints):
        """Test analysis with complete overlap."""
        source, target = mock_endpoints
        context = {
            'ukbb_proteins': ['Q14213', 'P12345'],
            'hpa_proteins': ['Q14213', 'P12345']
        }
        
        action_params = {
            'dataset1_context_key': 'ukbb_proteins',
            'dataset2_context_key': 'hpa_proteins',
            'output_context_key': 'overlap_results'
        }
        
        result = await action.execute(
            current_identifiers=[],
            current_ontology_type='UniProt',
            action_params=action_params,
            source_endpoint=source,
            target_endpoint=target,
            context=context
        )
        
        assert result['details']['overlap_count'] == 2
        assert result['details']['dataset1_count'] == 2
        assert result['details']['dataset2_count'] == 2
    
    async def test_no_overlap(self, action, mock_endpoints):
        """Test analysis with no overlap."""
        source, target = mock_endpoints
        context = {
            'ukbb_proteins': ['Q14213', 'Q8NEV9'],
            'hpa_proteins': ['P12345', 'A1B2C3']
        }
        
        action_params = {
            'dataset1_context_key': 'ukbb_proteins',
            'dataset2_context_key': 'hpa_proteins',
            'output_context_key': 'overlap_results'
        }
        
        result = await action.execute(
            current_identifiers=[],
            current_ontology_type='UniProt',
            action_params=action_params,
            source_endpoint=source,
            target_endpoint=target,
            context=context
        )
        
        assert result['output_identifiers'] == []
        assert result['details']['overlap_count'] == 0
        assert context['overlap_results']['overlapping_proteins'] == []
    
    async def test_with_statistics(self, action, mock_endpoints):
        """Test analysis with statistics generation."""
        source, target = mock_endpoints
        context = {
            'ukbb_proteins': ['Q14213', 'Q8NEV9', 'P12345', 'A1B2C3'],
            'hpa_proteins': ['Q14213', 'P12345', 'D4E5F6', 'G7H8I9', 'H1I2J3']
        }
        
        action_params = {
            'dataset1_context_key': 'ukbb_proteins',
            'dataset2_context_key': 'hpa_proteins',
            'output_context_key': 'overlap_results',
            'dataset1_name': 'UKBB',
            'dataset2_name': 'HPA',
            'generate_statistics': True
        }
        
        result = await action.execute(
            current_identifiers=[],
            current_ontology_type='UniProt',
            action_params=action_params,
            source_endpoint=source,
            target_endpoint=target,
            context=context
        )
        
        # Check statistics were generated
        assert 'statistics' in context['overlap_results']
        stats = context['overlap_results']['statistics']
        
        # Check counts
        assert stats['counts']['UKBB']['total'] == 4
        assert stats['counts']['UKBB']['unique'] == 4
        assert stats['counts']['UKBB']['unique_to_dataset'] == 2  # Q8NEV9, A1B2C3
        
        assert stats['counts']['HPA']['total'] == 5
        assert stats['counts']['HPA']['unique'] == 5
        assert stats['counts']['HPA']['unique_to_dataset'] == 3  # D4E5F6, G7H8I9, H1I2J3
        
        assert stats['counts']['overlap'] == 2  # Q14213, P12345
        
        # Check percentages
        assert stats['percentages']['overlap_in_UKBB'] == 50.0  # 2/4
        assert stats['percentages']['overlap_in_HPA'] == 40.0   # 2/5
    
    async def test_empty_datasets(self, action, mock_endpoints):
        """Test handling of empty datasets."""
        source, target = mock_endpoints
        
        # Both empty
        context = {
            'ukbb_proteins': [],
            'hpa_proteins': []
        }
        
        action_params = {
            'dataset1_context_key': 'ukbb_proteins',
            'dataset2_context_key': 'hpa_proteins',
            'output_context_key': 'overlap_results'
        }
        
        result = await action.execute(
            current_identifiers=[],
            current_ontology_type='UniProt',
            action_params=action_params,
            source_endpoint=source,
            target_endpoint=target,
            context=context
        )
        
        assert result['output_identifiers'] == []
        assert result['details']['overlap_count'] == 0
    
    async def test_one_empty_dataset(self, action, mock_endpoints):
        """Test handling when one dataset is empty."""
        source, target = mock_endpoints
        context = {
            'ukbb_proteins': ['Q14213', 'Q8NEV9'],
            'hpa_proteins': []
        }
        
        action_params = {
            'dataset1_context_key': 'ukbb_proteins',
            'dataset2_context_key': 'hpa_proteins',
            'output_context_key': 'overlap_results'
        }
        
        result = await action.execute(
            current_identifiers=[],
            current_ontology_type='UniProt',
            action_params=action_params,
            source_endpoint=source,
            target_endpoint=target,
            context=context
        )
        
        assert result['output_identifiers'] == []
        assert result['details']['overlap_count'] == 0
        assert result['details']['dataset1_count'] == 2
        assert result['details']['dataset2_count'] == 0
    
    async def test_missing_required_params(self, action, mock_endpoints):
        """Test validation of required parameters."""
        source, target = mock_endpoints
        context = {'ukbb_proteins': ['Q14213'], 'hpa_proteins': ['P12345']}
        
        # Test missing dataset1_context_key
        action_params = {
            'dataset2_context_key': 'hpa_proteins',
            'output_context_key': 'overlap_results'
        }
        
        with pytest.raises(ValueError, match="dataset1_context_key is required"):
            await action.execute(
                current_identifiers=[],
                current_ontology_type='UniProt',
                action_params=action_params,
                source_endpoint=source,
                target_endpoint=target,
                context=context
            )
        
        # Test missing dataset2_context_key
        action_params = {
            'dataset1_context_key': 'ukbb_proteins',
            'output_context_key': 'overlap_results'
        }
        
        with pytest.raises(ValueError, match="dataset2_context_key is required"):
            await action.execute(
                current_identifiers=[],
                current_ontology_type='UniProt',
                action_params=action_params,
                source_endpoint=source,
                target_endpoint=target,
                context=context
            )
        
        # Test missing output_context_key
        action_params = {
            'dataset1_context_key': 'ukbb_proteins',
            'dataset2_context_key': 'hpa_proteins'
        }
        
        with pytest.raises(ValueError, match="output_context_key is required"):
            await action.execute(
                current_identifiers=[],
                current_ontology_type='UniProt',
                action_params=action_params,
                source_endpoint=source,
                target_endpoint=target,
                context=context
            )
    
    async def test_missing_dataset_keys_in_context(self, action, mock_endpoints):
        """Test handling when dataset keys are missing in context."""
        source, target = mock_endpoints
        context = {}  # No dataset keys
        
        action_params = {
            'dataset1_context_key': 'ukbb_proteins',
            'dataset2_context_key': 'hpa_proteins',
            'output_context_key': 'overlap_results'
        }
        
        result = await action.execute(
            current_identifiers=[],
            current_ontology_type='UniProt',
            action_params=action_params,
            source_endpoint=source,
            target_endpoint=target,
            context=context
        )
        
        # Should handle gracefully
        assert result['output_identifiers'] == []
        assert result['details']['overlap_count'] == 0
    
    async def test_duplicate_handling(self, action, mock_endpoints):
        """Test handling of duplicate identifiers within datasets."""
        source, target = mock_endpoints
        context = {
            'ukbb_proteins': ['Q14213', 'Q8NEV9', 'Q14213', 'P12345'],  # Q14213 duplicated
            'hpa_proteins': ['Q14213', 'P12345', 'P12345', 'D4E5F6']   # P12345 duplicated
        }
        
        action_params = {
            'dataset1_context_key': 'ukbb_proteins',
            'dataset2_context_key': 'hpa_proteins',
            'output_context_key': 'overlap_results'
        }
        
        result = await action.execute(
            current_identifiers=[],
            current_ontology_type='UniProt',
            action_params=action_params,
            source_endpoint=source,
            target_endpoint=target,
            context=context
        )
        
        # Should count unique proteins only
        assert set(result['output_identifiers']) == {'Q14213', 'P12345'}
        assert result['details']['dataset1_count'] == 3  # Unique count
        assert result['details']['dataset2_count'] == 3  # Unique count
        assert result['details']['overlap_count'] == 2
    
    async def test_provenance_tracking(self, action, mock_endpoints):
        """Test provenance tracking for overlap analysis."""
        source, target = mock_endpoints
        context = {
            'ukbb_proteins': ['Q14213', 'Q8NEV9'],
            'hpa_proteins': ['Q14213', 'P12345']
        }
        
        action_params = {
            'dataset1_context_key': 'ukbb_proteins',
            'dataset2_context_key': 'hpa_proteins',
            'output_context_key': 'overlap_results',
            'dataset1_name': 'UKBB',
            'dataset2_name': 'HPA'
        }
        
        result = await action.execute(
            current_identifiers=[],
            current_ontology_type='UniProt',
            action_params=action_params,
            source_endpoint=source,
            target_endpoint=target,
            context=context
        )
        
        # Check provenance
        provenance = result['provenance']
        assert len(provenance) == 1
        assert provenance[0]['action'] == 'dataset_overlap_analysis'
        assert provenance[0]['datasets']['UKBB']['count'] == 2
        assert provenance[0]['datasets']['HPA']['count'] == 2
        assert provenance[0]['overlap_count'] == 1
        assert provenance[0]['output_key'] == 'overlap_results'