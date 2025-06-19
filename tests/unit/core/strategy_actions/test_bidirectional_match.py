"""
Tests for BidirectionalMatchAction.
"""

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from datetime import datetime
import pandas as pd

from biomapper.core.strategy_actions.bidirectional_match import BidirectionalMatchAction


class TestBidirectionalMatchAction:
    """Test suite for BidirectionalMatchAction."""
    
    @pytest.fixture
    def mock_session(self):
        """Create a mock database session."""
        from sqlalchemy.ext.asyncio import AsyncSession
        session = Mock(spec=AsyncSession)
        session.execute = AsyncMock()
        return session
    
    @pytest.fixture
    def action(self, mock_session):
        """Create a BidirectionalMatchAction instance."""
        return BidirectionalMatchAction(session=mock_session)
    
    @pytest.fixture
    def mock_source_endpoint(self):
        """Create a mock source endpoint."""
        endpoint = Mock()
        endpoint.name = "source_endpoint"
        return endpoint
    
    @pytest.fixture
    def mock_target_endpoint(self):
        """Create a mock target endpoint."""
        endpoint = Mock()
        endpoint.name = "target_endpoint"
        return endpoint
    
    @pytest.fixture
    def mock_mapping_executor(self):
        """Create a mock MappingExecutor."""
        return Mock()
    
    @pytest.mark.asyncio
    async def test_empty_input_returns_empty_result(self, action):
        """Test that empty input returns appropriate empty result."""
        result = await action.execute(
            current_identifiers=[],
            current_ontology_type="PROTEIN_UNIPROTKB_AC_ONTOLOGY",
            action_params={
                'source_ontology': 'PROTEIN_UNIPROTKB_AC_ONTOLOGY',
                'target_ontology': 'PROTEIN_UNIPROTKB_AC_ONTOLOGY'
            },
            source_endpoint=Mock(),
            target_endpoint=Mock(),
            context={}
        )
        
        assert result['input_identifiers'] == []
        assert result['output_identifiers'] == []
        assert result['output_ontology_type'] is None
        assert result['provenance'] == []
        assert result['details']['action'] == 'BIDIRECTIONAL_MATCH'
        assert result['details']['skipped'] == 'empty_input'
    
    @pytest.mark.asyncio
    async def test_missing_required_parameters_raises_error(self, action, mock_source_endpoint, mock_target_endpoint):
        """Test that missing required parameters raise appropriate errors."""
        # Missing source_ontology
        with pytest.raises(ValueError, match="source_ontology is required"):
            await action.execute(
                current_identifiers=['P12345'],
                current_ontology_type="PROTEIN_UNIPROTKB_AC_ONTOLOGY",
                action_params={'target_ontology': 'PROTEIN_UNIPROTKB_AC_ONTOLOGY'},
                source_endpoint=mock_source_endpoint,
                target_endpoint=mock_target_endpoint,
                context={}
            )
        
        # Missing target_ontology
        with pytest.raises(ValueError, match="target_ontology is required"):
            await action.execute(
                current_identifiers=['P12345'],
                current_ontology_type="PROTEIN_UNIPROTKB_AC_ONTOLOGY",
                action_params={'source_ontology': 'PROTEIN_UNIPROTKB_AC_ONTOLOGY'},
                source_endpoint=mock_source_endpoint,
                target_endpoint=mock_target_endpoint,
                context={}
            )
    
    @pytest.mark.asyncio
    async def test_basic_matching_many_to_many(self, action, mock_source_endpoint, mock_target_endpoint, monkeypatch):
        """Test basic many-to-many matching functionality."""
        # Set up endpoints with IDs
        mock_source_endpoint.id = 1
        mock_target_endpoint.id = 2
        
        # Mock the database query for property configuration
        mock_property_config = Mock()
        mock_property_config.property_extraction_config = Mock()
        mock_property_config.property_extraction_config.extraction_pattern = '{"column": "identifier"}'
        mock_property_config.property_extraction_config.extraction_method = 'column'
        
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=mock_property_config)
        
        # Configure the session.execute to return the mock result
        action.session.execute.return_value = mock_result
        
        # Mock the CSVAdapter
        source_df = pd.DataFrame({
            'identifier': ['P12345', 'Q67890', 'P11111']
        })
        target_df = pd.DataFrame({
            'identifier': ['P12345', 'Q67890', 'P22222']
        })
        
        mock_csv_adapter = Mock()
        mock_csv_adapter.load_data = AsyncMock()
        
        # Track which endpoint is being loaded
        call_count = {'count': 0}
        
        async def mock_load_data(columns_to_load=None):
            call_count['count'] += 1
            if call_count['count'] == 1:
                return source_df
            else:
                return target_df
        
        mock_csv_adapter.load_data.side_effect = mock_load_data
        
        # Mock CSVAdapter class
        with patch('biomapper.mapping.adapters.csv_adapter.CSVAdapter', return_value=mock_csv_adapter):
            # Execute action
            context = {}
            result = await action.execute(
                current_identifiers=['P12345', 'Q67890', 'P11111'],
                current_ontology_type="PROTEIN_UNIPROTKB_AC_ONTOLOGY",
                action_params={
                    'source_ontology': 'PROTEIN_UNIPROTKB_AC_ONTOLOGY',
                    'target_ontology': 'PROTEIN_UNIPROTKB_AC_ONTOLOGY',
                    'match_mode': 'many_to_many'
                },
                source_endpoint=mock_source_endpoint,
                target_endpoint=mock_target_endpoint,
                context=context
            )
            
            # Verify results
            assert len(result['output_identifiers']) == 2  # P12345, Q67890
            assert set(result['output_identifiers']) == {'P12345', 'Q67890'}
            assert result['output_ontology_type'] == 'PROTEIN_UNIPROTKB_AC_ONTOLOGY'
            assert len(result['provenance']) == 2
            assert result['details']['total_matches'] == 2
            assert result['details']['unmatched_source'] == 1  # P11111
            assert result['details']['unmatched_target'] == 1  # P22222
            
            # Check context updates
            assert 'matched_identifiers' in context
            assert len(context['matched_identifiers']) == 2
            assert ('P12345', 'P12345') in context['matched_identifiers']
            assert ('Q67890', 'Q67890') in context['matched_identifiers']
    
    @pytest.mark.asyncio
    async def test_composite_identifier_handling(self, action, mock_source_endpoint, mock_target_endpoint, monkeypatch):
        """Test handling of composite identifiers."""
        # Mock property config for database query
        mock_property_config = Mock()
        mock_property_config.property_extraction_config.extraction_pattern = '{"column": "identifier"}'
        mock_property_config.property_extraction_config.extraction_method = 'column'
        
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=mock_property_config)
        action.session.execute = AsyncMock(return_value=mock_result)
        
        # Mock the data loading
        source_data = pd.DataFrame({
            'identifier': ['P12345_Q67890', 'P11111', 'A12345'],
            'ontology_type': ['PROTEIN_UNIPROTKB_AC_ONTOLOGY'] * 3
        })
        target_data = pd.DataFrame({
            'identifier': ['P12345', 'Q67890', 'B12345'],
            'ontology_type': ['PROTEIN_UNIPROTKB_AC_ONTOLOGY'] * 3
        })
        
        # Mock CSVAdapter
        mock_csv_adapter = Mock()
        mock_csv_adapter.load_data = AsyncMock(side_effect=[source_data, target_data])
        
        with patch('biomapper.mapping.adapters.csv_adapter.CSVAdapter', return_value=mock_csv_adapter):
            # Execute action with split_and_match
            context = {}
            result = await action.execute(
                current_identifiers=['P12345_Q67890', 'P11111', 'A12345'],
                current_ontology_type="PROTEIN_UNIPROTKB_AC_ONTOLOGY",
                action_params={
                    'source_ontology': 'PROTEIN_UNIPROTKB_AC_ONTOLOGY',
                    'target_ontology': 'PROTEIN_UNIPROTKB_AC_ONTOLOGY',
                    'composite_handling': 'split_and_match'
                },
                source_endpoint=mock_source_endpoint,
                target_endpoint=mock_target_endpoint,
                context=context
            )
        
        # Verify results - composite P12345_Q67890 should match both P12345 and Q67890
        assert len(result['output_identifiers']) == 2
        assert set(result['output_identifiers']) == {'P12345', 'Q67890'}
        assert result['details']['total_matches'] == 2
        
        # Check matched pairs
        matched_pairs = context['matched_identifiers']
        assert len(matched_pairs) == 2
        assert ('P12345_Q67890', 'P12345') in matched_pairs
        assert ('P12345_Q67890', 'Q67890') in matched_pairs
    
    @pytest.mark.asyncio
    async def test_composite_handling_both_mode(self, action, mock_source_endpoint, mock_target_endpoint, monkeypatch):
        """Test composite handling with 'both' mode."""
        # Set up endpoints with IDs
        mock_source_endpoint.id = 1
        mock_target_endpoint.id = 2
        
        # Mock property config for database query
        mock_property_config = Mock()
        mock_property_config.property_extraction_config = Mock()
        mock_property_config.property_extraction_config.extraction_pattern = '{"column": "identifier"}'
        mock_property_config.property_extraction_config.extraction_method = 'column'
        
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=mock_property_config)
        action.session.execute = AsyncMock(return_value=mock_result)
        
        # Mock the data loading
        source_data = pd.DataFrame({
            'identifier': ['P12345_Q67890', 'A12345'],
            'ontology_type': ['PROTEIN_UNIPROTKB_AC_ONTOLOGY'] * 2
        })
        target_data = pd.DataFrame({
            'identifier': ['P12345_Q67890', 'P12345', 'Q67890'],
            'ontology_type': ['PROTEIN_UNIPROTKB_AC_ONTOLOGY'] * 3
        })
        
        # Mock CSVAdapter
        mock_csv_adapter = Mock()
        mock_csv_adapter.load_data = AsyncMock(side_effect=[source_data, target_data])
        
        with patch('biomapper.mapping.adapters.csv_adapter.CSVAdapter', return_value=mock_csv_adapter):
            # Execute action with 'both' mode
            context = {}
            result = await action.execute(
                current_identifiers=['P12345_Q67890', 'A12345'],
                current_ontology_type="PROTEIN_UNIPROTKB_AC_ONTOLOGY",
                action_params={
                    'source_ontology': 'PROTEIN_UNIPROTKB_AC_ONTOLOGY',
                    'target_ontology': 'PROTEIN_UNIPROTKB_AC_ONTOLOGY',
                    'composite_handling': 'both'
                },
                source_endpoint=mock_source_endpoint,
                target_endpoint=mock_target_endpoint,
                context=context
            )
            
            # Should match composite to composite AND components
            assert len(result['output_identifiers']) == 3
            assert set(result['output_identifiers']) == {'P12345_Q67890', 'P12345', 'Q67890'}
            
            matched_pairs = context['matched_identifiers']
            
            # With 'both' mode, P12345_Q67890 should expand to:
            # - P12345_Q67890 (original)
            # - P12345 (component)
            # - Q67890 (component)
            # These match with all three target identifiers
            assert result['details']['total_matches'] == len(matched_pairs)
            assert ('P12345_Q67890', 'P12345_Q67890') in matched_pairs
            assert ('P12345_Q67890', 'P12345') in matched_pairs
            assert ('P12345_Q67890', 'Q67890') in matched_pairs
    
    @pytest.mark.asyncio
    async def test_one_to_one_matching_mode(self, action, mock_source_endpoint, mock_target_endpoint, monkeypatch):
        """Test one-to-one matching mode."""
        # Set up endpoints with IDs
        mock_source_endpoint.id = 1
        mock_target_endpoint.id = 2
        
        # Mock property config for database query
        mock_property_config = Mock()
        mock_property_config.property_extraction_config = Mock()
        mock_property_config.property_extraction_config.extraction_pattern = '{"column": "identifier"}'
        mock_property_config.property_extraction_config.extraction_method = 'column'
        
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=mock_property_config)
        action.session.execute = AsyncMock(return_value=mock_result)
        
        # Mock the data loading - unique values only
        source_data = pd.DataFrame({
            'identifier': ['P12345', 'Q67890'],
            'ontology_type': ['PROTEIN_UNIPROTKB_AC_ONTOLOGY'] * 2
        })
        target_data = pd.DataFrame({
            'identifier': ['P12345', 'Q67890'],
            'ontology_type': ['PROTEIN_UNIPROTKB_AC_ONTOLOGY'] * 2
        })
        
        # Mock CSVAdapter
        mock_csv_adapter = Mock()
        mock_csv_adapter.load_data = AsyncMock(side_effect=[source_data, target_data])
        
        with patch('biomapper.mapping.adapters.csv_adapter.CSVAdapter', return_value=mock_csv_adapter):
            # Execute action with one-to-one mode
            context = {}
            result = await action.execute(
                current_identifiers=['P12345', 'Q67890'],
                current_ontology_type="PROTEIN_UNIPROTKB_AC_ONTOLOGY",
                action_params={
                    'source_ontology': 'PROTEIN_UNIPROTKB_AC_ONTOLOGY',
                    'target_ontology': 'PROTEIN_UNIPROTKB_AC_ONTOLOGY',
                    'match_mode': 'one_to_one'
                },
                source_endpoint=mock_source_endpoint,
                target_endpoint=mock_target_endpoint,
                context=context
            )
            
            # In one-to-one mode, each source matches to at most one target
            assert len(result['output_identifiers']) == 2
            assert len(context['matched_identifiers']) == 2
            
            # Check that no target is used twice
            used_targets = [pair[1] for pair in context['matched_identifiers']]
            assert len(used_targets) == len(set(used_targets))
    
    @pytest.mark.asyncio
    async def test_custom_context_keys(self, action, mock_source_endpoint, mock_target_endpoint, monkeypatch):
        """Test custom context key saving."""
        # Set up endpoints with IDs
        mock_source_endpoint.id = 1
        mock_target_endpoint.id = 2
        
        # Mock property config for database query
        mock_property_config = Mock()
        mock_property_config.property_extraction_config = Mock()
        mock_property_config.property_extraction_config.extraction_pattern = '{"column": "identifier"}'
        mock_property_config.property_extraction_config.extraction_method = 'column'
        
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=mock_property_config)
        action.session.execute = AsyncMock(return_value=mock_result)
        
        # Mock simple matching scenario
        source_data = pd.DataFrame({
            'identifier': ['P12345'],
            'ontology_type': ['PROTEIN_UNIPROTKB_AC_ONTOLOGY']
        })
        target_data = pd.DataFrame({
            'identifier': ['P12345', 'Q67890'],
            'ontology_type': ['PROTEIN_UNIPROTKB_AC_ONTOLOGY'] * 2
        })
        
        # Mock CSVAdapter
        mock_csv_adapter = Mock()
        mock_csv_adapter.load_data = AsyncMock(side_effect=[source_data, target_data])
        
        with patch('biomapper.mapping.adapters.csv_adapter.CSVAdapter', return_value=mock_csv_adapter):
            # Execute with custom context keys
            context = {}
            result = await action.execute(
                current_identifiers=['P12345'],
                current_ontology_type="PROTEIN_UNIPROTKB_AC_ONTOLOGY",
                action_params={
                    'source_ontology': 'PROTEIN_UNIPROTKB_AC_ONTOLOGY',
                    'target_ontology': 'PROTEIN_UNIPROTKB_AC_ONTOLOGY',
                    'save_matched_to': 'custom_matches',
                    'save_unmatched_source_to': 'custom_unmatched_src',
                    'save_unmatched_target_to': 'custom_unmatched_tgt'
                },
                source_endpoint=mock_source_endpoint,
                target_endpoint=mock_target_endpoint,
                context=context
            )
            
            # Check custom keys were used
            assert 'custom_matches' in context
            assert 'custom_unmatched_src' in context
            assert 'custom_unmatched_tgt' in context
            assert len(context['custom_matches']) == 1
            assert len(context['custom_unmatched_src']) == 0
            assert len(context['custom_unmatched_tgt']) == 1
            assert context['custom_unmatched_tgt'][0] == 'Q67890'
    
    @pytest.mark.asyncio
    async def test_error_handling(self, action, mock_source_endpoint, mock_target_endpoint, monkeypatch):
        """Test error handling during execution."""
        # Set up endpoints with IDs
        mock_source_endpoint.id = 1
        mock_target_endpoint.id = 2
        
        # Mock property config for database query
        mock_property_config = Mock()
        mock_property_config.property_extraction_config = Mock()
        mock_property_config.property_extraction_config.extraction_pattern = '{"column": "identifier"}'
        mock_property_config.property_extraction_config.extraction_method = 'column'
        
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=mock_property_config)
        action.session.execute = AsyncMock(return_value=mock_result)
        
        # Mock CSVAdapter that raises an error
        mock_csv_adapter = Mock()
        mock_csv_adapter.load_data = AsyncMock(side_effect=Exception("Database connection failed"))
        
        with patch('biomapper.mapping.adapters.csv_adapter.CSVAdapter', return_value=mock_csv_adapter):
            # Execute and expect RuntimeError
            with pytest.raises(RuntimeError, match="Action execution failed"):
                await action.execute(
                    current_identifiers=['P12345'],
                    current_ontology_type="PROTEIN_UNIPROTKB_AC_ONTOLOGY",
                    action_params={
                        'source_ontology': 'PROTEIN_UNIPROTKB_AC_ONTOLOGY',
                        'target_ontology': 'PROTEIN_UNIPROTKB_AC_ONTOLOGY'
                    },
                    source_endpoint=mock_source_endpoint,
                    target_endpoint=mock_target_endpoint,
                    context={}
                )
    
    @pytest.mark.asyncio
    async def test_provenance_tracking(self, action, mock_source_endpoint, mock_target_endpoint, monkeypatch):
        """Test that provenance is properly tracked."""
        # Set up endpoints with IDs
        mock_source_endpoint.id = 1
        mock_target_endpoint.id = 2
        
        # Mock property config for database query
        mock_property_config = Mock()
        mock_property_config.property_extraction_config = Mock()
        mock_property_config.property_extraction_config.extraction_pattern = '{"column": "identifier"}'
        mock_property_config.property_extraction_config.extraction_method = 'column'
        
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=mock_property_config)
        action.session.execute = AsyncMock(return_value=mock_result)
        
        # Mock simple matching scenario
        source_data = pd.DataFrame({
            'identifier': ['P12345', 'Q67890'],
            'ontology_type': ['PROTEIN_UNIPROTKB_AC_ONTOLOGY'] * 2
        })
        target_data = pd.DataFrame({
            'identifier': ['P12345', 'Q67890'],
            'ontology_type': ['PROTEIN_UNIPROTKB_AC_ONTOLOGY'] * 2
        })
        
        # Mock CSVAdapter
        mock_csv_adapter = Mock()
        mock_csv_adapter.load_data = AsyncMock(side_effect=[source_data, target_data])
        
        with patch('biomapper.mapping.adapters.csv_adapter.CSVAdapter', return_value=mock_csv_adapter):
            # Execute action
            result = await action.execute(
                current_identifiers=['P12345', 'Q67890'],
                current_ontology_type="PROTEIN_UNIPROTKB_AC_ONTOLOGY",
                action_params={
                    'source_ontology': 'PROTEIN_UNIPROTKB_AC_ONTOLOGY',
                    'target_ontology': 'PROTEIN_UNIPROTKB_AC_ONTOLOGY',
                    'match_mode': 'many_to_many',
                    'composite_handling': 'split_and_match'
                },
                source_endpoint=mock_source_endpoint,
                target_endpoint=mock_target_endpoint,
                context={}
            )
            
            # Check provenance records
            assert len(result['provenance']) == 2
            
            for prov in result['provenance']:
                assert prov['action'] == 'BIDIRECTIONAL_MATCH'
                assert 'timestamp' in prov
                assert prov['confidence'] == 1.0
                assert prov['method'] == 'many_to_many_match'
                assert prov['details']['source_ontology'] == 'PROTEIN_UNIPROTKB_AC_ONTOLOGY'
                assert prov['details']['target_ontology'] == 'PROTEIN_UNIPROTKB_AC_ONTOLOGY'
                assert prov['details']['composite_handling'] == 'split_and_match'
    
    @pytest.mark.asyncio
    async def test_empty_endpoint_data(self, action, mock_source_endpoint, mock_target_endpoint, monkeypatch):
        """Test handling when endpoint returns empty data."""
        # Set up endpoints with IDs
        mock_source_endpoint.id = 1
        mock_target_endpoint.id = 2
        
        # Mock property config for database query
        mock_property_config = Mock()
        mock_property_config.property_extraction_config = Mock()
        mock_property_config.property_extraction_config.extraction_pattern = '{"column": "identifier"}'
        mock_property_config.property_extraction_config.extraction_method = 'column'
        
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=mock_property_config)
        action.session.execute = AsyncMock(return_value=mock_result)
        
        # Mock empty data
        empty_df = pd.DataFrame(columns=['identifier', 'ontology_type'])
        
        # Mock CSVAdapter
        mock_csv_adapter = Mock()
        mock_csv_adapter.load_data = AsyncMock(return_value=empty_df)
        
        with patch('biomapper.mapping.adapters.csv_adapter.CSVAdapter', return_value=mock_csv_adapter):
            # Execute action
            context = {}
            result = await action.execute(
                current_identifiers=['P12345'],
                current_ontology_type="PROTEIN_UNIPROTKB_AC_ONTOLOGY",
                action_params={
                    'source_ontology': 'PROTEIN_UNIPROTKB_AC_ONTOLOGY',
                    'target_ontology': 'PROTEIN_UNIPROTKB_AC_ONTOLOGY'
                },
                source_endpoint=mock_source_endpoint,
                target_endpoint=mock_target_endpoint,
                context=context
            )
            
            # Should handle gracefully with no matches
            assert result['output_identifiers'] == []
            assert result['details']['total_matches'] == 0
            assert result['details']['unmatched_source'] == 1
            assert result['details']['unmatched_target'] == 0