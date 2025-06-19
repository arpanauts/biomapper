"""Tests for ResolveAndMatchForwardAction."""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
import pandas as pd

from biomapper.core.strategy_actions.resolve_and_match_forward import ResolveAndMatchForwardAction
from biomapper.db.models import Endpoint, EndpointPropertyConfig, PropertyExtractionConfig


class TestResolveAndMatchForwardAction:
    """Test suite for ResolveAndMatchForwardAction."""
    
    @pytest.fixture
    def mock_session(self):
        """Create a mock database session."""
        session = AsyncMock()
        return session
    
    @pytest.fixture
    def action(self, mock_session):
        """Create a ResolveAndMatchForwardAction instance."""
        return ResolveAndMatchForwardAction(session=mock_session)
    
    @pytest.fixture
    def mock_endpoints(self):
        """Create mock source and target endpoints."""
        source = Mock(spec=Endpoint)
        source.id = 1
        source.name = "test_source"
        
        target = Mock(spec=Endpoint)
        target.id = 2
        target.name = "test_target"
        
        return source, target
    
    @pytest.fixture
    def mock_property_config(self):
        """Create mock property configuration."""
        extraction_config = Mock(spec=PropertyExtractionConfig)
        extraction_config.extraction_method = 'column'
        extraction_config.extraction_pattern = '{"column": "uniprot_id"}'
        
        property_config = Mock(spec=EndpointPropertyConfig)
        property_config.property_extraction_config = extraction_config
        
        return property_config
    
    async def test_basic_resolution_and_matching(self, action, mock_session, mock_endpoints, mock_property_config):
        """Test basic resolution and matching workflow."""
        source_endpoint, target_endpoint = mock_endpoints
        
        # Mock the database query for property config
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=mock_property_config)
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        # Mock UniProt resolver responses
        mock_resolver = AsyncMock()
        mock_resolver.map_identifiers.return_value = {
            'Q99895': (['P01308'], 'secondary:P01308'),  # Secondary to primary
            'P0CG05': (['P0DOY2', 'P0DOY3'], 'demerged'),  # Demerged ID
            'OBSOLETE1': (None, 'obsolete')  # Obsolete ID
        }
        
        # Mock CSV adapter for target data
        mock_target_data = pd.DataFrame({
            'uniprot_id': ['P01308', 'P0DOY2', 'P12345']
        })
        
        context = {
            'unmatched_source': ['Q99895', 'P0CG05', 'OBSOLETE1']
        }
        
        with patch('biomapper.core.strategy_actions.resolve_and_match_forward.UniProtHistoricalResolverClient') as mock_client_class, \
             patch('biomapper.mapping.adapters.csv_adapter.CSVAdapter') as mock_adapter_class:
            
            # Setup mocks
            mock_client_class.return_value = mock_resolver
            mock_adapter_instance = AsyncMock()
            mock_adapter_instance.load_data.return_value = mock_target_data
            mock_adapter_class.return_value = mock_adapter_instance
            
            # Execute action
            result = await action.execute(
                current_identifiers=[],
                current_ontology_type='PROTEIN_UNIPROTKB_AC_ONTOLOGY',
                action_params={
                    'target_ontology': 'PROTEIN_UNIPROTKB_AC_ONTOLOGY',
                    'input_from': 'unmatched_source',
                    'append_matched_to': 'all_matches',
                    'update_unmatched': 'unmatched_source'
                },
                source_endpoint=source_endpoint,
                target_endpoint=target_endpoint,
                context=context
            )
        
        # Verify results
        assert result['input_identifiers'] == ['Q99895', 'P0CG05', 'OBSOLETE1']
        assert set(result['output_identifiers']) == {'P01308', 'P0DOY2'}  # Matched IDs
        assert result['output_ontology_type'] == 'PROTEIN_UNIPROTKB_AC_ONTOLOGY'
        
        # Check context updates
        assert 'all_matches' in context
        matches = context['all_matches']
        assert len(matches) == 2  # Q99895 and P0CG05 matched
        
        # Check Q99895 match
        q99895_match = next(m for m in matches if m['source_id'] == 'Q99895')
        assert q99895_match['target_ids'] == ['P01308']
        
        # Check P0CG05 match (demerged, only P0DOY2 was in target)
        p0cg05_match = next(m for m in matches if m['source_id'] == 'P0CG05')
        assert 'P0DOY2' in p0cg05_match['target_ids']
        
        # Check unmatched update
        assert context['unmatched_source'] == ['OBSOLETE1']
        
        # Verify details
        assert result['details']['total_input'] == 3
        assert result['details']['total_resolved'] == 2
        assert result['details']['total_matched'] == 2
        assert result['details']['total_unmatched'] == 1
    
    async def test_composite_identifier_handling(self, action, mock_session, mock_endpoints, mock_property_config):
        """Test handling of composite identifiers."""
        source_endpoint, target_endpoint = mock_endpoints
        
        # Mock the database query
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=mock_property_config)
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        # Mock UniProt resolver responses for components
        mock_resolver = AsyncMock()
        mock_resolver.map_identifiers.return_value = {
            'Q99895': (['P01308'], 'secondary:P01308'),
            'P12345': (['P12345'], 'primary'),
            'Q99895_P12345': (None, 'obsolete')  # Composite itself not found
        }
        
        # Mock target data
        mock_target_data = pd.DataFrame({
            'uniprot_id': ['P01308', 'P12345', 'P67890']
        })
        
        context = {
            'unmatched_source': ['Q99895_P12345']  # Composite identifier
        }
        
        with patch('biomapper.core.strategy_actions.resolve_and_match_forward.UniProtHistoricalResolverClient') as mock_client_class, \
             patch('biomapper.mapping.adapters.csv_adapter.CSVAdapter') as mock_adapter_class:
            
            mock_client_class.return_value = mock_resolver
            mock_adapter_instance = AsyncMock()
            mock_adapter_instance.load_data.return_value = mock_target_data
            mock_adapter_class.return_value = mock_adapter_instance
            
            result = await action.execute(
                current_identifiers=[],
                current_ontology_type='PROTEIN_UNIPROTKB_AC_ONTOLOGY',
                action_params={
                    'target_ontology': 'PROTEIN_UNIPROTKB_AC_ONTOLOGY',
                    'input_from': 'unmatched_source',
                    'composite_handling': 'both'  # Test 'both' strategy
                },
                source_endpoint=source_endpoint,
                target_endpoint=target_endpoint,
                context=context
            )
        
        # Verify resolver was called with composite and components
        called_ids = mock_resolver.map_identifiers.call_args[0][0]
        assert set(called_ids) == {'Q99895_P12345', 'Q99895', 'P12345'}
        
        # Verify matches found via components
        assert 'all_matches' in context
        matches = context['all_matches']
        assert len(matches) == 1
        assert matches[0]['source_id'] == 'Q99895_P12345'
        assert set(matches[0]['target_ids']) == {'P01308', 'P12345'}
    
    async def test_error_handling(self, action, mock_session, mock_endpoints):
        """Test error handling scenarios."""
        source_endpoint, target_endpoint = mock_endpoints
        
        # Test missing required parameter
        with pytest.raises(ValueError, match="target_ontology is required"):
            await action.execute(
                current_identifiers=['P12345'],
                current_ontology_type='PROTEIN_UNIPROTKB_AC_ONTOLOGY',
                action_params={},  # Missing target_ontology
                source_endpoint=source_endpoint,
                target_endpoint=target_endpoint,
                context={}
            )
        
        # Test invalid match_against parameter
        with pytest.raises(ValueError, match="match_against must be 'TARGET'"):
            await action.execute(
                current_identifiers=['P12345'],
                current_ontology_type='PROTEIN_UNIPROTKB_AC_ONTOLOGY',
                action_params={
                    'target_ontology': 'PROTEIN_UNIPROTKB_AC_ONTOLOGY',
                    'match_against': 'SOURCE'
                },
                source_endpoint=source_endpoint,
                target_endpoint=target_endpoint,
                context={}
            )
    
    async def test_empty_input(self, action, mock_endpoints):
        """Test handling of empty input."""
        source_endpoint, target_endpoint = mock_endpoints
        
        result = await action.execute(
            current_identifiers=[],
            current_ontology_type='PROTEIN_UNIPROTKB_AC_ONTOLOGY',
            action_params={
                'target_ontology': 'PROTEIN_UNIPROTKB_AC_ONTOLOGY',
                'input_from': 'unmatched_source'
            },
            source_endpoint=source_endpoint,
            target_endpoint=target_endpoint,
            context={}  # No unmatched_source in context
        )
        
        assert result['input_identifiers'] == []
        assert result['output_identifiers'] == []
        assert result['details']['skipped'] == 'empty_input'
    
    async def test_batch_processing(self, action, mock_session, mock_endpoints, mock_property_config):
        """Test batch processing of large ID lists."""
        source_endpoint, target_endpoint = mock_endpoints
        
        # Mock the database query
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=mock_property_config)
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        # Create a large list of IDs
        large_id_list = [f'P{i:05d}' for i in range(250)]  # 250 IDs
        
        # Mock resolver to return primary for all
        mock_resolver = AsyncMock()
        mock_resolver.map_identifiers.return_value = {
            id: ([id], 'primary') for id in large_id_list[:100]  # First batch
        }
        
        # Second and third batch calls
        async def side_effect(ids):
            return {id: ([id], 'primary') for id in ids}
        
        mock_resolver.map_identifiers.side_effect = side_effect
        
        # Mock target data with some IDs
        mock_target_data = pd.DataFrame({
            'uniprot_id': large_id_list[:50]  # Only first 50 are in target
        })
        
        context = {
            'unmatched_source': large_id_list
        }
        
        with patch('biomapper.core.strategy_actions.resolve_and_match_forward.UniProtHistoricalResolverClient') as mock_client_class, \
             patch('biomapper.mapping.adapters.csv_adapter.CSVAdapter') as mock_adapter_class:
            
            mock_client_class.return_value = mock_resolver
            mock_adapter_instance = AsyncMock()
            mock_adapter_instance.load_data.return_value = mock_target_data
            mock_adapter_class.return_value = mock_adapter_instance
            
            result = await action.execute(
                current_identifiers=[],
                current_ontology_type='PROTEIN_UNIPROTKB_AC_ONTOLOGY',
                action_params={
                    'target_ontology': 'PROTEIN_UNIPROTKB_AC_ONTOLOGY',
                    'input_from': 'unmatched_source',
                    'batch_size': 100  # Process in batches of 100
                },
                source_endpoint=source_endpoint,
                target_endpoint=target_endpoint,
                context=context
            )
        
        # Verify batching occurred
        assert mock_resolver.map_identifiers.call_count == 3  # 250 IDs / 100 per batch = 3 calls
        
        # Verify results
        assert result['details']['total_input'] == 250
        assert result['details']['total_matched'] == 50
        assert result['details']['total_unmatched'] == 200
    
    async def test_many_to_many_vs_one_to_one_mode(self, action, mock_session, mock_endpoints, mock_property_config):
        """Test different matching modes."""
        source_endpoint, target_endpoint = mock_endpoints
        
        # Mock the database query
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=mock_property_config)
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        # Mock resolver - demerged ID maps to multiple
        mock_resolver = AsyncMock()
        mock_resolver.map_identifiers.return_value = {
            'P0CG05': (['P0DOY2', 'P0DOY3', 'P0DOY4'], 'demerged')
        }
        
        # Mock target data - all resolved IDs are present
        mock_target_data = pd.DataFrame({
            'uniprot_id': ['P0DOY2', 'P0DOY3', 'P0DOY4']
        })
        
        # Test many-to-many mode
        context_m2m = {'unmatched_source': ['P0CG05']}
        
        with patch('biomapper.core.strategy_actions.resolve_and_match_forward.UniProtHistoricalResolverClient') as mock_client_class, \
             patch('biomapper.mapping.adapters.csv_adapter.CSVAdapter') as mock_adapter_class:
            
            mock_client_class.return_value = mock_resolver
            mock_adapter_instance = AsyncMock()
            mock_adapter_instance.load_data.return_value = mock_target_data
            mock_adapter_class.return_value = mock_adapter_instance
            
            # Test many-to-many
            result_m2m = await action.execute(
                current_identifiers=[],
                current_ontology_type='PROTEIN_UNIPROTKB_AC_ONTOLOGY',
                action_params={
                    'target_ontology': 'PROTEIN_UNIPROTKB_AC_ONTOLOGY',
                    'input_from': 'unmatched_source',
                    'match_mode': 'many_to_many'
                },
                source_endpoint=source_endpoint,
                target_endpoint=target_endpoint,
                context=context_m2m
            )
            
            matches_m2m = context_m2m.get('all_matches', [])
            assert len(matches_m2m) == 1
            assert len(matches_m2m[0]['target_ids']) == 3  # All matches included
            
            # Test one-to-one
            context_o2o = {'unmatched_source': ['P0CG05']}
            result_o2o = await action.execute(
                current_identifiers=[],
                current_ontology_type='PROTEIN_UNIPROTKB_AC_ONTOLOGY',
                action_params={
                    'target_ontology': 'PROTEIN_UNIPROTKB_AC_ONTOLOGY',
                    'input_from': 'unmatched_source',
                    'match_mode': 'one_to_one'
                },
                source_endpoint=source_endpoint,
                target_endpoint=target_endpoint,
                context=context_o2o
            )
            
            matches_o2o = context_o2o.get('all_matches', [])
            assert len(matches_o2o) == 1
            assert len(matches_o2o[0]['target_ids']) == 1  # Only first match included
    
    async def test_provenance_tracking(self, action, mock_session, mock_endpoints, mock_property_config):
        """Test that provenance is properly tracked."""
        source_endpoint, target_endpoint = mock_endpoints
        
        # Mock the database query
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=mock_property_config)
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        # Mock resolver
        mock_resolver = AsyncMock()
        mock_resolver.map_identifiers.return_value = {
            'Q99895': (['P01308'], 'secondary:P01308'),
            'OBSOLETE1': (None, 'obsolete')
        }
        
        # Mock target data
        mock_target_data = pd.DataFrame({
            'uniprot_id': ['P01308']
        })
        
        context = {
            'unmatched_source': ['Q99895', 'OBSOLETE1']
        }
        
        with patch('biomapper.core.strategy_actions.resolve_and_match_forward.UniProtHistoricalResolverClient') as mock_client_class, \
             patch('biomapper.mapping.adapters.csv_adapter.CSVAdapter') as mock_adapter_class:
            
            mock_client_class.return_value = mock_resolver
            mock_adapter_instance = AsyncMock()
            mock_adapter_instance.load_data.return_value = mock_target_data
            mock_adapter_class.return_value = mock_adapter_instance
            
            result = await action.execute(
                current_identifiers=[],
                current_ontology_type='PROTEIN_UNIPROTKB_AC_ONTOLOGY',
                action_params={
                    'target_ontology': 'PROTEIN_UNIPROTKB_AC_ONTOLOGY',
                    'input_from': 'unmatched_source'
                },
                source_endpoint=source_endpoint,
                target_endpoint=target_endpoint,
                context=context
            )
        
        # Check provenance records
        provenance = result['provenance']
        assert len(provenance) >= 2
        
        # Find provenance for matched ID
        matched_prov = next(p for p in provenance if p['input'] == 'Q99895' and p.get('matched_in_target'))
        assert matched_prov['resolved_to'] == 'P01308'
        assert matched_prov['resolution_status'] == 'secondary:P01308'
        assert matched_prov['confidence'] == 0.8  # Secondary resolution confidence
        assert matched_prov['method'] == 'uniprot_historical_resolution'
        
        # Find provenance for unmatched ID
        unmatched_prov = next(p for p in provenance if p['input'] == 'OBSOLETE1')
        assert not unmatched_prov.get('matched_in_target', False)
        assert unmatched_prov['confidence'] == 0.0
    
    async def test_resolver_api_failure_handling(self, action, mock_session, mock_endpoints, mock_property_config):
        """Test handling of UniProt API failures."""
        source_endpoint, target_endpoint = mock_endpoints
        
        # Mock the database query
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=mock_property_config)
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        # Mock resolver to fail
        mock_resolver = AsyncMock()
        mock_resolver.map_identifiers.side_effect = Exception("API timeout")
        
        # Mock target data
        mock_target_data = pd.DataFrame({
            'uniprot_id': ['P01308']
        })
        
        context = {
            'unmatched_source': ['Q99895', 'P12345']
        }
        
        with patch('biomapper.core.strategy_actions.resolve_and_match_forward.UniProtHistoricalResolverClient') as mock_client_class, \
             patch('biomapper.mapping.adapters.csv_adapter.CSVAdapter') as mock_adapter_class:
            
            mock_client_class.return_value = mock_resolver
            mock_adapter_instance = AsyncMock()
            mock_adapter_instance.load_data.return_value = mock_target_data
            mock_adapter_class.return_value = mock_adapter_instance
            
            # Should complete even with API failure
            result = await action.execute(
                current_identifiers=[],
                current_ontology_type='PROTEIN_UNIPROTKB_AC_ONTOLOGY',
                action_params={
                    'target_ontology': 'PROTEIN_UNIPROTKB_AC_ONTOLOGY',
                    'input_from': 'unmatched_source'
                },
                source_endpoint=source_endpoint,
                target_endpoint=target_endpoint,
                context=context
            )
        
        # Should have no matches due to API failure
        assert result['details']['total_matched'] == 0
        assert result['details']['total_failed'] == 2
        assert context.get('unmatched_source') == ['Q99895', 'P12345']  # All remain unmatched