"""
Tests for BidirectionalMatchAction.
"""

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock
from datetime import datetime
import pandas as pd

from biomapper.core.strategy_actions.bidirectional_match import BidirectionalMatchAction


class TestBidirectionalMatchAction:
    """Test suite for BidirectionalMatchAction."""
    
    @pytest.fixture
    def mock_session(self):
        """Create a mock database session."""
        return Mock()
    
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
        # Mock the data loading
        source_data = pd.DataFrame({
            'identifier': ['P12345', 'Q67890', 'P11111'],
            'ontology_type': ['PROTEIN_UNIPROTKB_AC_ONTOLOGY'] * 3
        })
        target_data = pd.DataFrame({
            'identifier': ['P12345', 'Q67890', 'P22222'],
            'ontology_type': ['PROTEIN_UNIPROTKB_AC_ONTOLOGY'] * 3
        })
        
        # Create mock client
        mock_client = Mock()
        mock_client.fetch_data = AsyncMock(side_effect=[source_data, target_data])
        
        # Mock the MappingExecutor and client creation
        mock_executor_instance = Mock()
        mock_executor_instance._get_mapping_client.return_value = mock_client
        
        def mock_mapping_executor(session):
            return mock_executor_instance
        
        monkeypatch.setattr(
            'biomapper.core.mapping_executor.MappingExecutor',
            mock_mapping_executor
        )
        
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
        # Mock the data loading
        source_data = pd.DataFrame({
            'identifier': ['P12345_Q67890', 'P11111', 'A12345'],
            'ontology_type': ['PROTEIN_UNIPROTKB_AC_ONTOLOGY'] * 3
        })
        target_data = pd.DataFrame({
            'identifier': ['P12345', 'Q67890', 'B12345'],
            'ontology_type': ['PROTEIN_UNIPROTKB_AC_ONTOLOGY'] * 3
        })
        
        # Create mock client
        mock_client = Mock()
        mock_client.fetch_data = AsyncMock(side_effect=[source_data, target_data])
        
        # Mock the MappingExecutor and client creation
        mock_executor_instance = Mock()
        mock_executor_instance._get_mapping_client.return_value = mock_client
        
        def mock_mapping_executor(session):
            return mock_executor_instance
        
        monkeypatch.setattr(
            'biomapper.core.mapping_executor.MappingExecutor',
            mock_mapping_executor
        )
        
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
        # Mock the data loading
        source_data = pd.DataFrame({
            'identifier': ['P12345_Q67890', 'A12345'],
            'ontology_type': ['PROTEIN_UNIPROTKB_AC_ONTOLOGY'] * 2
        })
        target_data = pd.DataFrame({
            'identifier': ['P12345_Q67890', 'P12345', 'Q67890'],
            'ontology_type': ['PROTEIN_UNIPROTKB_AC_ONTOLOGY'] * 3
        })
        
        # Create mock client
        mock_client = Mock()
        mock_client.fetch_data = AsyncMock(side_effect=[source_data, target_data])
        
        # Mock the MappingExecutor and client creation
        mock_executor_instance = Mock()
        mock_executor_instance._get_mapping_client.return_value = mock_client
        
        def mock_mapping_executor(session):
            return mock_executor_instance
        
        monkeypatch.setattr(
            'biomapper.core.mapping_executor.MappingExecutor',
            mock_mapping_executor
        )
        
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
        # Mock the data loading
        source_data = pd.DataFrame({
            'identifier': ['P12345', 'P12345', 'Q67890'],  # Duplicate P12345
            'ontology_type': ['PROTEIN_UNIPROTKB_AC_ONTOLOGY'] * 3
        })
        target_data = pd.DataFrame({
            'identifier': ['P12345', 'Q67890', 'Q67890'],  # Duplicate Q67890
            'ontology_type': ['PROTEIN_UNIPROTKB_AC_ONTOLOGY'] * 3
        })
        
        # Create mock client that returns unique values
        mock_client = Mock()
        
        async def mock_fetch_data(*args, **kwargs):
            # Simulate that fetch_data returns unique values
            if mock_client.fetch_data.call_count == 1:
                return pd.DataFrame({
                    'identifier': ['P12345', 'Q67890'],
                    'ontology_type': ['PROTEIN_UNIPROTKB_AC_ONTOLOGY'] * 2
                })
            else:
                return pd.DataFrame({
                    'identifier': ['P12345', 'Q67890'],
                    'ontology_type': ['PROTEIN_UNIPROTKB_AC_ONTOLOGY'] * 2
                })
        
        mock_client.fetch_data = AsyncMock(side_effect=mock_fetch_data)
        
        # Mock the MappingExecutor and client creation
        mock_executor_instance = Mock()
        mock_executor_instance._get_mapping_client.return_value = mock_client
        
        def mock_mapping_executor(session):
            return mock_executor_instance
        
        monkeypatch.setattr(
            'biomapper.core.mapping_executor.MappingExecutor',
            mock_mapping_executor
        )
        
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
        # Mock simple matching scenario
        source_data = pd.DataFrame({
            'identifier': ['P12345'],
            'ontology_type': ['PROTEIN_UNIPROTKB_AC_ONTOLOGY']
        })
        target_data = pd.DataFrame({
            'identifier': ['P12345', 'Q67890'],
            'ontology_type': ['PROTEIN_UNIPROTKB_AC_ONTOLOGY'] * 2
        })
        
        # Create mock client
        mock_client = Mock()
        mock_client.fetch_data = AsyncMock(side_effect=[source_data, target_data])
        
        # Mock the MappingExecutor and client creation
        mock_executor_instance = Mock()
        mock_executor_instance._get_mapping_client.return_value = mock_client
        
        def mock_mapping_executor(session):
            return mock_executor_instance
        
        monkeypatch.setattr(
            'biomapper.core.mapping_executor.MappingExecutor',
            mock_mapping_executor
        )
        
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
        # Mock client that raises an error
        mock_client = Mock()
        mock_client.fetch_data = AsyncMock(side_effect=Exception("Database connection failed"))
        
        # Mock the MappingExecutor and client creation
        mock_executor_instance = Mock()
        mock_executor_instance._get_mapping_client.return_value = mock_client
        
        def mock_mapping_executor(session):
            return mock_executor_instance
        
        monkeypatch.setattr(
            'biomapper.core.mapping_executor.MappingExecutor',
            mock_mapping_executor
        )
        
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
        # Mock simple matching scenario
        source_data = pd.DataFrame({
            'identifier': ['P12345', 'Q67890'],
            'ontology_type': ['PROTEIN_UNIPROTKB_AC_ONTOLOGY'] * 2
        })
        target_data = pd.DataFrame({
            'identifier': ['P12345', 'Q67890'],
            'ontology_type': ['PROTEIN_UNIPROTKB_AC_ONTOLOGY'] * 2
        })
        
        # Create mock client
        mock_client = Mock()
        mock_client.fetch_data = AsyncMock(side_effect=[source_data, target_data])
        
        # Mock the MappingExecutor and client creation
        mock_executor_instance = Mock()
        mock_executor_instance._get_mapping_client.return_value = mock_client
        
        def mock_mapping_executor(session):
            return mock_executor_instance
        
        monkeypatch.setattr(
            'biomapper.core.mapping_executor.MappingExecutor',
            mock_mapping_executor
        )
        
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
        # Mock empty data
        empty_df = pd.DataFrame(columns=['identifier', 'ontology_type'])
        
        # Create mock client
        mock_client = Mock()
        mock_client.fetch_data = AsyncMock(return_value=empty_df)
        
        # Mock the MappingExecutor and client creation
        mock_executor_instance = Mock()
        mock_executor_instance._get_mapping_client.return_value = mock_client
        
        def mock_mapping_executor(session):
            return mock_executor_instance
        
        monkeypatch.setattr(
            'biomapper.core.mapping_executor.MappingExecutor',
            mock_mapping_executor
        )
        
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