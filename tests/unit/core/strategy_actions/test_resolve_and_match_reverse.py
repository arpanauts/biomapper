"""
Tests for RESOLVE_AND_MATCH_REVERSE action type.

Tests the reverse resolution and matching functionality, including:
- Basic reverse resolution and matching
- Composite identifier handling
- Many-to-many mapping support
- Context integration
- Error handling
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch

from biomapper.core.strategy_actions.resolve_and_match_reverse import ResolveAndMatchReverse
from biomapper.db.models import Endpoint


class TestResolveAndMatchReverse:
    """Test suite for ResolveAndMatchReverse action."""
    
    @pytest.fixture
    def mock_session(self):
        """Create a mock database session."""
        return Mock()
        
    @pytest.fixture
    def action(self, mock_session):
        """Create a ResolveAndMatchReverse instance."""
        return ResolveAndMatchReverse(session=mock_session)
        
    @pytest.fixture
    def mock_endpoints(self):
        """Create mock source and target endpoints."""
        source = Mock(spec=Endpoint)
        source.name = "UKBB"
        source.ontology_types = ["PROTEIN_UNIPROTKB_AC_ONTOLOGY"]
        
        target = Mock(spec=Endpoint)
        target.name = "HPA"
        target.ontology_types = ["PROTEIN_UNIPROTKB_AC_ONTOLOGY"]
        
        return source, target
        
    @pytest.fixture
    def mock_resolver_client(self):
        """Create a mock UniProt resolver client."""
        client = AsyncMock()
        return client
        
    @pytest.mark.asyncio
    async def test_basic_reverse_resolution_and_matching(self, action, mock_endpoints, mock_resolver_client):
        """Test basic reverse resolution where target IDs resolve to match source IDs."""
        source_endpoint, target_endpoint = mock_endpoints
        
        # Mock the resolver client
        with patch.object(action, '_resolver_client', mock_resolver_client):
            # Set up resolution results: old target IDs resolve to current IDs that match source
            mock_resolver_client.map_identifiers.return_value = {
                'P12345': (['Q67890'], 'secondary:Q67890'),  # Old ID resolves to current
                'P54321': (['Q09876'], 'secondary:Q09876'),  # Another resolution
                'P99999': (None, 'obsolete')  # This one is obsolete
            }
            
            # Set up context with unmatched IDs
            context = {
                'unmatched_target': ['P12345', 'P54321', 'P99999'],  # Old IDs in target
                'unmatched_source': ['Q67890', 'Q09876', 'Q11111']   # Current IDs in source
            }
            
            # Action parameters
            action_params = {
                'input_from': 'unmatched_target',
                'match_against_remaining': 'unmatched_source',
                'source_ontology': 'PROTEIN_UNIPROTKB_AC_ONTOLOGY',
                'append_matched_to': 'all_matches',
                'save_final_unmatched': 'final_unmatched'
            }
            
            # Execute the action
            result = await action.execute(
                current_identifiers=[],  # Not used in this action
                current_ontology_type='PROTEIN_UNIPROTKB_AC_ONTOLOGY',
                action_params=action_params,
                source_endpoint=source_endpoint,
                target_endpoint=target_endpoint,
                context=context
            )
            
            # Verify results
            assert result['input_identifiers'] == ['P12345', 'P54321', 'P99999']
            assert set(result['output_identifiers']) == {'Q67890', 'Q09876'}  # Matched source IDs
            assert result['output_ontology_type'] == 'PROTEIN_UNIPROTKB_AC_ONTOLOGY'
            
            # Check provenance
            assert len(result['provenance']) >= 4  # At least 2 resolutions + 2 matches
            resolution_provs = [p for p in result['provenance'] if p['method'].endswith('_resolution')]
            match_provs = [p for p in result['provenance'] if p['method'] == 'reverse_resolution_match']
            assert len(resolution_provs) >= 2
            assert len(match_provs) == 2
            
            # Check context updates
            assert context['all_matches'] == [('Q67890', 'P12345'), ('Q09876', 'P54321')]
            assert context['final_unmatched']['source'] == ['Q11111']  # Unmatched source
            assert set(context['final_unmatched']['target']) == {'P99999'}  # Obsolete target
            
            # Check details
            details = result['details']
            assert details['total_resolved'] == 2
            assert details['total_matches'] == 2
            assert details['remaining_unmatched_source'] == 1
            assert details['remaining_unmatched_target'] == 1
            
    @pytest.mark.asyncio
    async def test_composite_identifier_handling(self, action, mock_endpoints, mock_resolver_client):
        """Test handling of composite identifiers in reverse resolution."""
        source_endpoint, target_endpoint = mock_endpoints
        
        with patch.object(action, '_resolver_client', mock_resolver_client):
            # Set up resolution for components
            mock_resolver_client.map_identifiers.return_value = {
                'P12345': (['Q67890'], 'secondary:Q67890'),
                'P54321': (['Q09876'], 'secondary:Q09876'),
                'P12345_P54321': (None, 'invalid')  # Composite doesn't resolve as-is
            }
            
            context = {
                'unmatched_target': ['P12345_P54321'],  # Composite in target
                'unmatched_source': ['Q67890_Q09876', 'Q67890', 'Q11111']  # Mix in source
            }
            
            action_params = {
                'source_ontology': 'PROTEIN_UNIPROTKB_AC_ONTOLOGY',
                'composite_handling': 'split_and_match'
            }
            
            result = await action.execute(
                current_identifiers=[],
                current_ontology_type='PROTEIN_UNIPROTKB_AC_ONTOLOGY',
                action_params=action_params,
                source_endpoint=source_endpoint,
                target_endpoint=target_endpoint,
                context=context
            )
            
            # Should resolve components and match
            assert 'Q67890' in result['output_identifiers']
            
            # Check that composite was expanded
            details = result['details']
            assert details['total_resolved'] >= 1  # At least one component resolved
            
    @pytest.mark.asyncio
    async def test_many_to_many_mapping(self, action, mock_endpoints, mock_resolver_client):
        """Test many-to-many mapping support in reverse resolution."""
        source_endpoint, target_endpoint = mock_endpoints
        
        with patch.object(action, '_resolver_client', mock_resolver_client):
            # Demerged case: one old ID maps to multiple current IDs
            mock_resolver_client.map_identifiers.return_value = {
                'P12345': (['Q67890', 'Q11111'], 'demerged')  # Demerged to 2 IDs
            }
            
            context = {
                'unmatched_target': ['P12345'],
                'unmatched_source': ['Q67890', 'Q11111', 'Q99999']
            }
            
            action_params = {
                'source_ontology': 'PROTEIN_UNIPROTKB_AC_ONTOLOGY',
                'match_mode': 'many_to_many'
            }
            
            result = await action.execute(
                current_identifiers=[],
                current_ontology_type='PROTEIN_UNIPROTKB_AC_ONTOLOGY',
                action_params=action_params,
                source_endpoint=source_endpoint,
                target_endpoint=target_endpoint,
                context=context
            )
            
            # Should create matches for both resolved IDs
            assert len(result['output_identifiers']) == 2
            assert set(result['output_identifiers']) == {'Q67890', 'Q11111'}
            
            # Check provenance shows both matches
            match_provs = [p for p in result['provenance'] if p['method'] == 'reverse_resolution_match']
            assert len(match_provs) == 2
            
    @pytest.mark.asyncio
    async def test_one_to_one_mode(self, action, mock_endpoints, mock_resolver_client):
        """Test one-to-one matching mode."""
        source_endpoint, target_endpoint = mock_endpoints
        
        with patch.object(action, '_resolver_client', mock_resolver_client):
            # Demerged case but with one-to-one mode
            mock_resolver_client.map_identifiers.return_value = {
                'P12345': (['Q67890', 'Q11111'], 'demerged')
            }
            
            context = {
                'unmatched_target': ['P12345'],
                'unmatched_source': ['Q67890', 'Q11111']
            }
            
            action_params = {
                'source_ontology': 'PROTEIN_UNIPROTKB_AC_ONTOLOGY',
                'match_mode': 'one_to_one'
            }
            
            result = await action.execute(
                current_identifiers=[],
                current_ontology_type='PROTEIN_UNIPROTKB_AC_ONTOLOGY',
                action_params=action_params,
                source_endpoint=source_endpoint,
                target_endpoint=target_endpoint,
                context=context
            )
            
            # Should only create one match in one-to-one mode
            assert len(result['output_identifiers']) == 1
            assert result['output_identifiers'][0] in {'Q67890', 'Q11111'}
            
    @pytest.mark.asyncio
    async def test_empty_input_handling(self, action, mock_endpoints):
        """Test handling of empty input."""
        source_endpoint, target_endpoint = mock_endpoints
        
        # Test with empty target IDs
        context = {
            'unmatched_target': [],
            'unmatched_source': ['Q67890']
        }
        
        action_params = {
            'source_ontology': 'PROTEIN_UNIPROTKB_AC_ONTOLOGY'
        }
        
        result = await action.execute(
            current_identifiers=[],
            current_ontology_type='PROTEIN_UNIPROTKB_AC_ONTOLOGY',
            action_params=action_params,
            source_endpoint=source_endpoint,
            target_endpoint=target_endpoint,
            context=context
        )
        
        assert result['input_identifiers'] == []
        assert result['output_identifiers'] == []
        assert result['details']['skipped'] == 'empty_input'
        
    @pytest.mark.asyncio
    async def test_missing_required_parameters(self, action, mock_endpoints):
        """Test error handling for missing required parameters."""
        source_endpoint, target_endpoint = mock_endpoints
        
        context = {
            'unmatched_target': ['P12345'],
            'unmatched_source': ['Q67890']
        }
        
        # Missing source_ontology
        action_params = {}
        
        with pytest.raises(ValueError, match="source_ontology is required"):
            await action.execute(
                current_identifiers=[],
                current_ontology_type='PROTEIN_UNIPROTKB_AC_ONTOLOGY',
                action_params=action_params,
                source_endpoint=source_endpoint,
                target_endpoint=target_endpoint,
                context=context
            )
            
    @pytest.mark.asyncio
    async def test_batch_processing(self, action, mock_endpoints, mock_resolver_client):
        """Test batch processing of large identifier lists."""
        source_endpoint, target_endpoint = mock_endpoints
        
        with patch.object(action, '_resolver_client', mock_resolver_client):
            # Create many target IDs
            target_ids = [f'P{i:05d}' for i in range(250)]  # 250 IDs
            source_ids = [f'Q{i:05d}' for i in range(250)]
            
            # Mock resolution results
            resolution_results = {}
            for i in range(250):
                if i % 2 == 0:  # Half resolve successfully
                    resolution_results[f'P{i:05d}'] = ([f'Q{i:05d}'], 'secondary')
                else:
                    resolution_results[f'P{i:05d}'] = (None, 'obsolete')
                    
            mock_resolver_client.map_identifiers.side_effect = [
                {k: v for k, v in list(resolution_results.items())[i:i+100]}
                for i in range(0, 250, 100)
            ]
            
            context = {
                'unmatched_target': target_ids,
                'unmatched_source': source_ids
            }
            
            action_params = {
                'source_ontology': 'PROTEIN_UNIPROTKB_AC_ONTOLOGY',
                'batch_size': 100
            }
            
            result = await action.execute(
                current_identifiers=[],
                current_ontology_type='PROTEIN_UNIPROTKB_AC_ONTOLOGY',
                action_params=action_params,
                source_endpoint=source_endpoint,
                target_endpoint=target_endpoint,
                context=context
            )
            
            # Verify batching worked
            assert mock_resolver_client.map_identifiers.call_count == 3  # 250/100 = 3 batches
            
            # Verify correct number of matches
            assert len(result['output_identifiers']) == 125  # Half resolved and matched
            
    @pytest.mark.asyncio
    async def test_context_append_behavior(self, action, mock_endpoints, mock_resolver_client):
        """Test appending matches to existing context."""
        source_endpoint, target_endpoint = mock_endpoints
        
        with patch.object(action, '_resolver_client', mock_resolver_client):
            mock_resolver_client.map_identifiers.return_value = {
                'P12345': (['Q67890'], 'secondary:Q67890')
            }
            
            # Context with existing matches
            context = {
                'unmatched_target': ['P12345'],
                'unmatched_source': ['Q67890'],
                'all_matches': [('X1', 'Y1'), ('X2', 'Y2')]  # Existing matches
            }
            
            action_params = {
                'source_ontology': 'PROTEIN_UNIPROTKB_AC_ONTOLOGY',
                'append_matched_to': 'all_matches'
            }
            
            result = await action.execute(
                current_identifiers=[],
                current_ontology_type='PROTEIN_UNIPROTKB_AC_ONTOLOGY',
                action_params=action_params,
                source_endpoint=source_endpoint,
                target_endpoint=target_endpoint,
                context=context
            )
            
            # Should append, not replace
            assert len(context['all_matches']) == 3
            assert context['all_matches'][0] == ('X1', 'Y1')  # Original preserved
            assert context['all_matches'][2] == ('Q67890', 'P12345')  # New match added
            
    @pytest.mark.asyncio
    async def test_resolver_exception_handling(self, action, mock_endpoints, mock_resolver_client):
        """Test handling of resolver exceptions."""
        source_endpoint, target_endpoint = mock_endpoints
        
        with patch.object(action, '_resolver_client', mock_resolver_client):
            # Make resolver raise an exception
            mock_resolver_client.map_identifiers.side_effect = Exception("API error")
            
            context = {
                'unmatched_target': ['P12345'],
                'unmatched_source': ['Q67890']
            }
            
            action_params = {
                'source_ontology': 'PROTEIN_UNIPROTKB_AC_ONTOLOGY'
            }
            
            # Should continue processing despite batch failure
            result = await action.execute(
                current_identifiers=[],
                current_ontology_type='PROTEIN_UNIPROTKB_AC_ONTOLOGY',
                action_params=action_params,
                source_endpoint=source_endpoint,
                target_endpoint=target_endpoint,
                context=context
            )
            
            # No matches due to resolver failure
            assert result['output_identifiers'] == []
            assert result['details']['total_resolved'] == 0
            
    @pytest.mark.asyncio
    async def test_complex_composite_scenarios(self, action, mock_endpoints, mock_resolver_client):
        """Test complex scenarios with nested composites."""
        source_endpoint, target_endpoint = mock_endpoints
        
        with patch.object(action, '_resolver_client', mock_resolver_client):
            # Mock complex resolutions
            mock_resolver_client.map_identifiers.return_value = {
                'P12345': (['Q67890'], 'secondary:Q67890'),
                'P54321': (['Q09876'], 'secondary:Q09876'),
                'P11111': (['Q67890', 'Q22222'], 'demerged'),  # Demerged case
                'P12345_P54321': (None, 'invalid'),
                'P12345_P11111': (None, 'invalid')
            }
            
            context = {
                'unmatched_target': ['P12345_P54321', 'P11111'],  # Mix of composite and simple
                'unmatched_source': ['Q67890_Q09876', 'Q67890', 'Q22222', 'Q99999']
            }
            
            action_params = {
                'source_ontology': 'PROTEIN_UNIPROTKB_AC_ONTOLOGY',
                'composite_handling': 'both'  # Keep both composite and components
            }
            
            result = await action.execute(
                current_identifiers=[],
                current_ontology_type='PROTEIN_UNIPROTKB_AC_ONTOLOGY',
                action_params=action_params,
                source_endpoint=source_endpoint,
                target_endpoint=target_endpoint,
                context=context
            )
            
            # Should handle both simple and composite cases
            output_set = set(result['output_identifiers'])
            assert 'Q67890' in output_set  # From P11111 demerge
            assert 'Q22222' in output_set  # From P11111 demerge
            
            # Check detailed tracking
            details = result['details']
            assert details['total_resolved'] >= 2
            assert details['unique_matched_source'] >= 2