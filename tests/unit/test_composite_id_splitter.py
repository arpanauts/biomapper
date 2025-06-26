"""Unit tests for CompositeIdSplitter action."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from biomapper.core.strategy_actions.composite_id_splitter import CompositeIdSplitter
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


class TestCompositeIdSplitter:
    """Test CompositeIdSplitter functionality."""
    
    @pytest.fixture
    def action(self, mock_session):
        """Create CompositeIdSplitter instance."""
        return CompositeIdSplitter(session=mock_session)
    
    async def test_basic_splitting(self, action, mock_endpoints):
        """Test basic composite ID splitting."""
        source, target = mock_endpoints
        context = {
            'protein_ids': ['Q14213_Q8NEV9', 'P12345', 'A1B2C3_D4E5F6_G7H8I9']
        }
        
        action_params = {
            'input_context_key': 'protein_ids',
            'output_context_key': 'split_ids',
            'delimiter': '_'
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
        assert result['input_identifiers'] == ['Q14213_Q8NEV9', 'P12345', 'A1B2C3_D4E5F6_G7H8I9']
        assert set(result['output_identifiers']) == {'Q14213', 'Q8NEV9', 'P12345', 'A1B2C3', 'D4E5F6', 'G7H8I9'}
        assert result['output_ontology_type'] == 'UniProt'
        assert result['details']['input_count'] == 3
        assert result['details']['output_count'] == 6
        assert result['details']['composite_count'] == 2
        
        # Check context was updated
        assert set(context['split_ids']) == {'Q14213', 'Q8NEV9', 'P12345', 'A1B2C3', 'D4E5F6', 'G7H8I9'}
    
    async def test_custom_delimiter(self, action, mock_endpoints):
        """Test splitting with custom delimiter."""
        source, target = mock_endpoints
        context = {
            'protein_ids': ['Q14213|Q8NEV9', 'P12345', 'A1B2C3|D4E5F6']
        }
        
        action_params = {
            'input_context_key': 'protein_ids',
            'output_context_key': 'split_ids',
            'delimiter': '|'
        }
        
        result = await action.execute(
            current_identifiers=[],
            current_ontology_type='UniProt',
            action_params=action_params,
            source_endpoint=source,
            target_endpoint=target,
            context=context
        )
        
        assert set(result['output_identifiers']) == {'Q14213', 'Q8NEV9', 'P12345', 'A1B2C3', 'D4E5F6'}
        assert result['details']['delimiter'] == '|'
    
    async def test_no_splitting_needed(self, action, mock_endpoints):
        """Test when no identifiers need splitting."""
        source, target = mock_endpoints
        context = {
            'protein_ids': ['Q14213', 'P12345', 'A1B2C3']
        }
        
        action_params = {
            'input_context_key': 'protein_ids',
            'output_context_key': 'split_ids',
            'delimiter': '_'
        }
        
        result = await action.execute(
            current_identifiers=[],
            current_ontology_type='UniProt',
            action_params=action_params,
            source_endpoint=source,
            target_endpoint=target,
            context=context
        )
        
        assert set(result['output_identifiers']) == {'Q14213', 'P12345', 'A1B2C3'}
        assert result['details']['composite_count'] == 0
    
    async def test_metadata_lineage_tracking(self, action, mock_endpoints):
        """Test metadata lineage tracking."""
        source, target = mock_endpoints
        context = {
            'protein_ids': ['Q14213_Q8NEV9', 'P12345', 'A1B2C3_D4E5F6']
        }
        
        action_params = {
            'input_context_key': 'protein_ids',
            'output_context_key': 'split_ids',
            'delimiter': '_',
            'track_metadata_lineage': True
        }
        
        result = await action.execute(
            current_identifiers=[],
            current_ontology_type='UniProt',
            action_params=action_params,
            source_endpoint=source,
            target_endpoint=target,
            context=context
        )
        
        # Check lineage was tracked
        assert 'split_ids_lineage' in context
        lineage = context['split_ids_lineage']
        assert lineage['Q14213_Q8NEV9'] == ['Q14213', 'Q8NEV9']
        assert lineage['A1B2C3_D4E5F6'] == ['A1B2C3', 'D4E5F6']
        assert 'P12345' not in lineage  # Non-composite IDs not in lineage
    
    async def test_empty_input(self, action, mock_endpoints):
        """Test handling of empty input."""
        source, target = mock_endpoints
        context = {
            'protein_ids': []
        }
        
        action_params = {
            'input_context_key': 'protein_ids',
            'output_context_key': 'split_ids',
            'delimiter': '_'
        }
        
        result = await action.execute(
            current_identifiers=[],
            current_ontology_type='UniProt',
            action_params=action_params,
            source_endpoint=source,
            target_endpoint=target,
            context=context
        )
        
        assert result['input_identifiers'] == []
        assert result['output_identifiers'] == []
        assert result['details']['input_count'] == 0
        assert result['details']['output_count'] == 0
    
    async def test_missing_input_key(self, action, mock_endpoints):
        """Test handling of missing input key in context."""
        source, target = mock_endpoints
        context = {}  # No 'protein_ids' key
        
        action_params = {
            'input_context_key': 'protein_ids',
            'output_context_key': 'split_ids',
            'delimiter': '_'
        }
        
        result = await action.execute(
            current_identifiers=[],
            current_ontology_type='UniProt',
            action_params=action_params,
            source_endpoint=source,
            target_endpoint=target,
            context=context
        )
        
        assert result['input_identifiers'] == []
        assert result['output_identifiers'] == []
    
    async def test_missing_required_params(self, action, mock_endpoints):
        """Test validation of required parameters."""
        source, target = mock_endpoints
        context = {'protein_ids': ['Q14213_Q8NEV9']}
        
        # Test missing input_context_key
        action_params = {
            'output_context_key': 'split_ids',
            'delimiter': '_'
        }
        
        with pytest.raises(ValueError, match="input_context_key is required"):
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
            'input_context_key': 'protein_ids',
            'delimiter': '_'
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
    
    async def test_duplicate_handling(self, action, mock_endpoints):
        """Test handling of duplicate identifiers after splitting."""
        source, target = mock_endpoints
        context = {
            'protein_ids': ['Q14213_Q8NEV9', 'Q14213_P12345', 'Q8NEV9']
        }
        
        action_params = {
            'input_context_key': 'protein_ids',
            'output_context_key': 'split_ids',
            'delimiter': '_'
        }
        
        result = await action.execute(
            current_identifiers=[],
            current_ontology_type='UniProt',
            action_params=action_params,
            source_endpoint=source,
            target_endpoint=target,
            context=context
        )
        
        # Should have unique identifiers only
        assert set(result['output_identifiers']) == {'Q14213', 'Q8NEV9', 'P12345'}
        assert result['details']['input_count'] == 3
        assert result['details']['output_count'] == 3  # Duplicates removed
    
    async def test_provenance_tracking(self, action, mock_endpoints):
        """Test provenance tracking for split operations."""
        source, target = mock_endpoints
        context = {
            'protein_ids': ['Q14213_Q8NEV9', 'P12345']
        }
        
        action_params = {
            'input_context_key': 'protein_ids',
            'output_context_key': 'split_ids',
            'delimiter': '_'
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
        assert len(provenance) == 1  # Only one composite ID was split
        assert provenance[0]['action'] == 'composite_split'
        assert provenance[0]['input'] == 'Q14213_Q8NEV9'
        assert provenance[0]['output'] == ['Q14213', 'Q8NEV9']
        assert provenance[0]['delimiter'] == '_'
    
    async def test_empty_string_handling(self, action, mock_endpoints):
        """Test handling of empty strings in input."""
        source, target = mock_endpoints
        context = {
            'protein_ids': ['Q14213_Q8NEV9', '', 'P12345', '  ', None]
        }
        
        action_params = {
            'input_context_key': 'protein_ids',
            'output_context_key': 'split_ids',
            'delimiter': '_'
        }
        
        # Should handle None values without crashing
        result = await action.execute(
            current_identifiers=[],
            current_ontology_type='UniProt',
            action_params=action_params,
            source_endpoint=source,
            target_endpoint=target,
            context=context
        )
        
        # Check that empty strings and None are handled gracefully
        assert 'Q14213' in result['output_identifiers']
        assert 'Q8NEV9' in result['output_identifiers']
        assert 'P12345' in result['output_identifiers']
        assert '' in result['output_identifiers']  # Empty string is kept
        assert '  ' in result['output_identifiers']  # Whitespace string is kept
        # None values should be skipped
        assert None not in result['output_identifiers']
    
    async def test_multi_character_delimiter(self, action, mock_endpoints):
        """Test splitting with multi-character delimiter."""
        source, target = mock_endpoints
        context = {
            'protein_ids': ['Q14213::Q8NEV9', 'P12345', 'A1B2C3::D4E5F6::G7H8I9']
        }
        
        action_params = {
            'input_context_key': 'protein_ids',
            'output_context_key': 'split_ids',
            'delimiter': '::'
        }
        
        result = await action.execute(
            current_identifiers=[],
            current_ontology_type='UniProt',
            action_params=action_params,
            source_endpoint=source,
            target_endpoint=target,
            context=context
        )
        
        assert set(result['output_identifiers']) == {'Q14213', 'Q8NEV9', 'P12345', 'A1B2C3', 'D4E5F6', 'G7H8I9'}
        assert result['details']['delimiter'] == '::'
    
    async def test_special_character_delimiters(self, action, mock_endpoints):
        """Test splitting with various special character delimiters."""
        source, target = mock_endpoints
        
        # Test with different special characters
        test_cases = [
            ('|', ['Q14213|Q8NEV9', 'P12345']),
            ('-', ['Q14213-Q8NEV9', 'P12345']),
            ('.', ['Q14213.Q8NEV9', 'P12345']),
            ('/', ['Q14213/Q8NEV9', 'P12345']),
            ('+', ['Q14213+Q8NEV9', 'P12345'])
        ]
        
        for delimiter, protein_ids in test_cases:
            context = {'protein_ids': protein_ids}
            action_params = {
                'input_context_key': 'protein_ids',
                'output_context_key': 'split_ids',
                'delimiter': delimiter
            }
            
            result = await action.execute(
                current_identifiers=[],
                current_ontology_type='UniProt',
                action_params=action_params,
                source_endpoint=source,
                target_endpoint=target,
                context=context
            )
            
            assert 'Q14213' in result['output_identifiers']
            assert 'Q8NEV9' in result['output_identifiers']
            assert 'P12345' in result['output_identifiers']
    
    async def test_edge_case_delimiter_at_boundaries(self, action, mock_endpoints):
        """Test identifiers with delimiters at the beginning or end."""
        source, target = mock_endpoints
        context = {
            'protein_ids': ['_Q14213', 'Q8NEV9_', '_P12345_', 'A1B2C3__D4E5F6']
        }
        
        action_params = {
            'input_context_key': 'protein_ids',
            'output_context_key': 'split_ids',
            'delimiter': '_'
        }
        
        result = await action.execute(
            current_identifiers=[],
            current_ontology_type='UniProt',
            action_params=action_params,
            source_endpoint=source,
            target_endpoint=target,
            context=context
        )
        
        # Should include empty strings from leading/trailing delimiters
        assert '' in result['output_identifiers']
        assert 'Q14213' in result['output_identifiers']
        assert 'Q8NEV9' in result['output_identifiers']
        assert 'P12345' in result['output_identifiers']
        assert 'A1B2C3' in result['output_identifiers']
        assert 'D4E5F6' in result['output_identifiers']
    
    async def test_very_long_composite_ids(self, action, mock_endpoints):
        """Test handling of identifiers with many components."""
        source, target = mock_endpoints
        # Create a composite ID with 10 components
        long_composite = '_'.join([f'ID{i:04d}' for i in range(10)])
        context = {
            'protein_ids': [long_composite, 'P12345']
        }
        
        action_params = {
            'input_context_key': 'protein_ids',
            'output_context_key': 'split_ids',
            'delimiter': '_'
        }
        
        result = await action.execute(
            current_identifiers=[],
            current_ontology_type='UniProt',
            action_params=action_params,
            source_endpoint=source,
            target_endpoint=target,
            context=context
        )
        
        # Should have all 10 components plus P12345
        assert result['details']['output_count'] == 11
        for i in range(10):
            assert f'ID{i:04d}' in result['output_identifiers']
        assert 'P12345' in result['output_identifiers']
    
    async def test_context_details_structure(self, action, mock_endpoints):
        """Test that the details dictionary contains all expected keys."""
        source, target = mock_endpoints
        context = {
            'protein_ids': ['Q14213_Q8NEV9', 'P12345']
        }
        
        action_params = {
            'input_context_key': 'protein_ids',
            'output_context_key': 'split_ids',
            'delimiter': '_',
            'track_metadata_lineage': True
        }
        
        result = await action.execute(
            current_identifiers=[],
            current_ontology_type='UniProt',
            action_params=action_params,
            source_endpoint=source,
            target_endpoint=target,
            context=context
        )
        
        # Check all expected keys in details
        details = result['details']
        assert 'input_count' in details
        assert 'output_count' in details
        assert 'composite_count' in details
        assert 'delimiter' in details
        assert 'context_keys' in details
        
        # Check context_keys structure
        context_keys = details['context_keys']
        assert context_keys['input'] == 'protein_ids'
        assert context_keys['output'] == 'split_ids'
        assert context_keys['lineage'] == 'split_ids_lineage'