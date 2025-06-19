"""Unit tests for FilterByTargetPresenceAction."""

import pytest
import pandas as pd
from unittest.mock import Mock, AsyncMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from biomapper.core.strategy_actions.filter_by_target_presence import FilterByTargetPresenceAction
from biomapper.db.models import Endpoint, EndpointPropertyConfig, PropertyExtractionConfig


class TestFilterByTargetPresenceAction:
    """Test suite for FilterByTargetPresenceAction."""
    
    @pytest.fixture
    def mock_session(self):
        """Create a mock database session."""
        session = Mock(spec=AsyncSession)
        session.execute = AsyncMock()
        return session
    
    @pytest.fixture
    def mock_endpoints(self):
        """Create mock source and target endpoints."""
        source_endpoint = Mock(spec=Endpoint)
        source_endpoint.id = 1
        source_endpoint.name = "source_endpoint"
        
        target_endpoint = Mock(spec=Endpoint)
        target_endpoint.id = 2
        target_endpoint.name = "target_endpoint"
        
        return source_endpoint, target_endpoint
    
    @pytest.fixture
    def mock_property_config(self):
        """Create mock property configuration for target."""
        extraction = Mock(spec=PropertyExtractionConfig)
        extraction.column_name = "identifier_column"
        extraction.extraction_pattern = '{"column": "identifier_column"}'
        extraction.extraction_method = "column"
        
        config = Mock(spec=EndpointPropertyConfig)
        config.ontology_type = "PROTEIN_UNIPROT"
        config.property_extraction_config = extraction
        
        return config
    
    @pytest.mark.asyncio
    async def test_basic_filtering_without_conversion(self, mock_session, mock_endpoints, mock_property_config):
        """Test basic filtering without identifier conversion."""
        source_endpoint, target_endpoint = mock_endpoints
        
        # Setup mock session to return property config
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_property_config
        mock_session.execute.return_value = mock_result
        
        # Mock target CSV data
        mock_df = pd.DataFrame({
            'identifier_column': ['P12345', 'Q67890', 'S99999']
        })
        
        with patch('biomapper.mapping.adapters.csv_adapter.CSVAdapter') as MockCSVAdapter:
            mock_adapter = Mock()
            mock_adapter.load_data = AsyncMock(return_value=mock_df)
            MockCSVAdapter.return_value = mock_adapter
            
            action = FilterByTargetPresenceAction(mock_session)
            
            result = await action.execute(
                current_identifiers=['P12345', 'Q67890', 'R11111', 'T22222'],
                current_ontology_type='PROTEIN_UNIPROT',
                action_params={
                    'endpoint_context': 'TARGET',
                    'ontology_type_to_match': 'PROTEIN_UNIPROT'
                },
                source_endpoint=source_endpoint,
                target_endpoint=target_endpoint,
                context={}
            )
            
            # Verify results
            assert result['input_identifiers'] == ['P12345', 'Q67890', 'R11111', 'T22222']
            assert result['output_identifiers'] == ['P12345', 'Q67890']  # Only present in target
            assert result['output_ontology_type'] == 'PROTEIN_UNIPROT'  # Type unchanged
            assert len(result['provenance']) == 4  # One record per input
            
            # Check provenance
            passed_count = sum(1 for p in result['provenance'] if p['action'] == 'filter_passed')
            failed_count = sum(1 for p in result['provenance'] if p['action'] == 'filter_failed')
            assert passed_count == 2
            assert failed_count == 2
            
            # Check details
            details = result['details']
            assert details['action'] == 'FILTER_IDENTIFIERS_BY_TARGET_PRESENCE'
            assert details['total_input'] == 4
            assert details['total_passed'] == 2
            assert details['total_filtered'] == 2
    
    @pytest.mark.asyncio
    async def test_filtering_with_conversion_path(self, mock_session, mock_endpoints, mock_property_config):
        """Test filtering when conversion_path_to_match_ontology is provided."""
        source_endpoint, target_endpoint = mock_endpoints
        
        # Setup mock session to return property config
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_property_config
        mock_session.execute.return_value = mock_result
        
        # Mock target CSV data (contains ENSEMBL IDs)
        mock_property_config.property_extraction_config.column_name = "ensembl_column"
        mock_property_config.property_extraction_config.extraction_pattern = '{"column": "ensembl_column"}'
        mock_df = pd.DataFrame({
            'ensembl_column': ['ENSP001', 'ENSP002', 'ENSP999']
        })
        
        with patch('biomapper.mapping.adapters.csv_adapter.CSVAdapter') as MockCSVAdapter:
            mock_adapter = Mock()
            mock_adapter.load_data = AsyncMock(return_value=mock_df)
            MockCSVAdapter.return_value = mock_adapter
            
            # Mock the ExecuteMappingPathAction
            with patch('biomapper.core.strategy_actions.execute_mapping_path.ExecuteMappingPathAction') as MockExecuteAction:
                mock_execute_instance = Mock()
                MockExecuteAction.return_value = mock_execute_instance
                
                # Mock conversion result
                mock_conversion_result = {
                    'output_identifiers': ['ENSP001', 'ENSP002', 'ENSP003'],
                    'provenance': [
                        {'source_id': 'P12345', 'target_id': 'ENSP001'},
                        {'source_id': 'Q67890', 'target_id': 'ENSP002'},
                        {'source_id': 'R11111', 'target_id': 'ENSP003'},  # Not in target
                    ]
                }
                mock_execute_instance.execute = AsyncMock(return_value=mock_conversion_result)
                
                action = FilterByTargetPresenceAction(mock_session)
                
                result = await action.execute(
                    current_identifiers=['P12345', 'Q67890', 'R11111'],
                    current_ontology_type='PROTEIN_UNIPROT',
                    action_params={
                        'endpoint_context': 'TARGET',
                        'ontology_type_to_match': 'PROTEIN_ENSEMBL',
                        'conversion_path_to_match_ontology': 'uniprot_to_ensembl'
                    },
                    source_endpoint=source_endpoint,
                    target_endpoint=target_endpoint,
                    context={'mapping_executor': Mock()}
                )
                
                # Verify results
                assert result['output_identifiers'] == ['P12345', 'Q67890']  # R11111 filtered out
                assert result['output_ontology_type'] == 'PROTEIN_UNIPROT'  # Original type preserved
                
                # Check that conversion was called
                mock_execute_instance.execute.assert_called_once()
                call_args = mock_execute_instance.execute.call_args[1]
                assert call_args['action_params']['path_name'] == 'uniprot_to_ensembl'
                
                # Check provenance includes checked values
                for prov in result['provenance']:
                    if prov['source_id'] == 'P12345':
                        assert prov['checked_value'] == 'ENSP001'
                        assert prov['action'] == 'filter_passed'
                    elif prov['source_id'] == 'R11111':
                        assert prov['checked_value'] == 'ENSP003'
                        assert prov['action'] == 'filter_failed'
    
    @pytest.mark.asyncio
    async def test_empty_target_endpoint(self, mock_session, mock_endpoints, mock_property_config):
        """Test behavior when target endpoint has no data."""
        source_endpoint, target_endpoint = mock_endpoints
        
        # Setup mock session
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_property_config
        mock_session.execute.return_value = mock_result
        
        # Empty DataFrame
        mock_df = pd.DataFrame(columns=['identifier_column'])
        
        with patch('biomapper.mapping.adapters.csv_adapter.CSVAdapter') as MockCSVAdapter:
            mock_adapter = Mock()
            mock_adapter.load_data = AsyncMock(return_value=mock_df)
            MockCSVAdapter.return_value = mock_adapter
            
            action = FilterByTargetPresenceAction(mock_session)
            
            result = await action.execute(
                current_identifiers=['P12345', 'Q67890'],
                current_ontology_type='PROTEIN_UNIPROT',
                action_params={
                    'endpoint_context': 'TARGET',
                    'ontology_type_to_match': 'PROTEIN_UNIPROT'
                },
                source_endpoint=source_endpoint,
                target_endpoint=target_endpoint,
                context={}
            )
            
            # All should be filtered out
            assert result['output_identifiers'] == []
            assert result['details']['total_filtered'] == 2
            assert all(p['action'] == 'filter_failed' for p in result['provenance'])
    
    @pytest.mark.asyncio
    async def test_all_identifiers_filtered(self, mock_session, mock_endpoints, mock_property_config):
        """Test scenario where all input identifiers are filtered out."""
        source_endpoint, target_endpoint = mock_endpoints
        
        # Setup mock session
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_property_config
        mock_session.execute.return_value = mock_result
        
        # Target data with different identifiers
        mock_df = pd.DataFrame({
            'identifier_column': ['X11111', 'Y22222', 'Z33333']
        })
        
        with patch('biomapper.mapping.adapters.csv_adapter.CSVAdapter') as MockCSVAdapter:
            mock_adapter = Mock()
            mock_adapter.load_data = AsyncMock(return_value=mock_df)
            MockCSVAdapter.return_value = mock_adapter
            
            action = FilterByTargetPresenceAction(mock_session)
            
            result = await action.execute(
                current_identifiers=['P12345', 'Q67890', 'R11111'],
                current_ontology_type='PROTEIN_UNIPROT',
                action_params={
                    'endpoint_context': 'TARGET',
                    'ontology_type_to_match': 'PROTEIN_UNIPROT'
                },
                source_endpoint=source_endpoint,
                target_endpoint=target_endpoint,
                context={}
            )
            
            assert result['output_identifiers'] == []
            assert result['details']['total_passed'] == 0
            assert result['details']['total_filtered'] == 3
    
    @pytest.mark.asyncio
    async def test_no_identifiers_filtered(self, mock_session, mock_endpoints, mock_property_config):
        """Test scenario where no input identifiers are filtered out."""
        source_endpoint, target_endpoint = mock_endpoints
        
        # Setup mock session
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_property_config
        mock_session.execute.return_value = mock_result
        
        # Target data contains all input identifiers
        mock_df = pd.DataFrame({
            'identifier_column': ['P12345', 'Q67890', 'R11111', 'X99999']
        })
        
        with patch('biomapper.mapping.adapters.csv_adapter.CSVAdapter') as MockCSVAdapter:
            mock_adapter = Mock()
            mock_adapter.load_data = AsyncMock(return_value=mock_df)
            MockCSVAdapter.return_value = mock_adapter
            
            action = FilterByTargetPresenceAction(mock_session)
            
            result = await action.execute(
                current_identifiers=['P12345', 'Q67890', 'R11111'],
                current_ontology_type='PROTEIN_UNIPROT',
                action_params={
                    'endpoint_context': 'TARGET',
                    'ontology_type_to_match': 'PROTEIN_UNIPROT'
                },
                source_endpoint=source_endpoint,
                target_endpoint=target_endpoint,
                context={}
            )
            
            assert result['output_identifiers'] == ['P12345', 'Q67890', 'R11111']
            assert result['details']['total_passed'] == 3
            assert result['details']['total_filtered'] == 0
    
    @pytest.mark.asyncio
    async def test_invalid_endpoint_context(self, mock_session, mock_endpoints):
        """Test validation of endpoint_context parameter."""
        source_endpoint, target_endpoint = mock_endpoints
        
        action = FilterByTargetPresenceAction(mock_session)
        
        with pytest.raises(ValueError, match="endpoint_context must be 'TARGET'"):
            await action.execute(
                current_identifiers=['P12345'],
                current_ontology_type='PROTEIN_UNIPROT',
                action_params={
                    'endpoint_context': 'SOURCE',  # Invalid
                    'ontology_type_to_match': 'PROTEIN_UNIPROT'
                },
                source_endpoint=source_endpoint,
                target_endpoint=target_endpoint,
                context={}
            )
    
    @pytest.mark.asyncio
    async def test_missing_ontology_type_to_match(self, mock_session, mock_endpoints):
        """Test validation when ontology_type_to_match is missing."""
        source_endpoint, target_endpoint = mock_endpoints
        
        action = FilterByTargetPresenceAction(mock_session)
        
        with pytest.raises(ValueError, match="ontology_type_to_match is required"):
            await action.execute(
                current_identifiers=['P12345'],
                current_ontology_type='PROTEIN_UNIPROT',
                action_params={
                    'endpoint_context': 'TARGET'
                },
                source_endpoint=source_endpoint,
                target_endpoint=target_endpoint,
                context={}
            )
    
    @pytest.mark.asyncio
    async def test_missing_property_config(self, mock_session, mock_endpoints):
        """Test handling when target endpoint lacks configuration for ontology type."""
        source_endpoint, target_endpoint = mock_endpoints
        
        # Setup mock session to return None
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result
        
        action = FilterByTargetPresenceAction(mock_session)
        
        with pytest.raises(ValueError, match="does not have configuration for ontology type"):
            await action.execute(
                current_identifiers=['P12345'],
                current_ontology_type='PROTEIN_UNIPROT',
                action_params={
                    'endpoint_context': 'TARGET',
                    'ontology_type_to_match': 'PROTEIN_UNIPROT'
                },
                source_endpoint=source_endpoint,
                target_endpoint=target_endpoint,
                context={}
            )
    
    @pytest.mark.asyncio
    async def test_empty_input_identifiers(self, mock_session, mock_endpoints, mock_property_config):
        """Test behavior with empty list of input identifiers."""
        source_endpoint, target_endpoint = mock_endpoints
        
        # Setup mock session
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_property_config
        mock_session.execute.return_value = mock_result
        
        mock_df = pd.DataFrame({'identifier_column': ['P12345']})
        
        with patch('biomapper.mapping.adapters.csv_adapter.CSVAdapter') as MockCSVAdapter:
            mock_adapter = Mock()
            mock_adapter.load_data = AsyncMock(return_value=mock_df)
            MockCSVAdapter.return_value = mock_adapter
            
            action = FilterByTargetPresenceAction(mock_session)
            
            result = await action.execute(
                current_identifiers=[],
                current_ontology_type='PROTEIN_UNIPROT',
                action_params={
                    'endpoint_context': 'TARGET',
                    'ontology_type_to_match': 'PROTEIN_UNIPROT'
                },
                source_endpoint=source_endpoint,
                target_endpoint=target_endpoint,
                context={}
            )
            
            assert result['input_identifiers'] == []
            assert result['output_identifiers'] == []
            assert result['provenance'] == []
            assert result['details']['total_input'] == 0
    
    @pytest.mark.asyncio
    async def test_duplicate_identifiers_in_target(self, mock_session, mock_endpoints, mock_property_config):
        """Test behavior when target has duplicate identifiers."""
        source_endpoint, target_endpoint = mock_endpoints
        
        # Setup mock session
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_property_config
        mock_session.execute.return_value = mock_result
        
        # Target data with duplicates
        mock_df = pd.DataFrame({
            'identifier_column': ['P12345', 'P12345', 'Q67890', 'Q67890']
        })
        
        with patch('biomapper.mapping.adapters.csv_adapter.CSVAdapter') as MockCSVAdapter:
            mock_adapter = Mock()
            mock_adapter.load_data = AsyncMock(return_value=mock_df)
            MockCSVAdapter.return_value = mock_adapter
            
            action = FilterByTargetPresenceAction(mock_session)
            
            result = await action.execute(
                current_identifiers=['P12345', 'Q67890', 'R11111'],
                current_ontology_type='PROTEIN_UNIPROT',
                action_params={
                    'endpoint_context': 'TARGET',
                    'ontology_type_to_match': 'PROTEIN_UNIPROT'
                },
                source_endpoint=source_endpoint,
                target_endpoint=target_endpoint,
                context={}
            )
            
            # Should handle duplicates correctly (set operation)
            assert set(result['output_identifiers']) == {'P12345', 'Q67890'}
            assert len(result['output_identifiers']) == 2