"""Additional edge case tests for FilterByTargetPresenceAction."""

import pytest
import pandas as pd
from unittest.mock import Mock, AsyncMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from biomapper.core.strategy_actions.filter_by_target_presence import FilterByTargetPresenceAction
from biomapper.db.models import Endpoint, EndpointPropertyConfig, PropertyExtractionConfig


class TestFilterByTargetPresenceEdgeCases:
    """Additional edge case tests for FilterByTargetPresenceAction."""
    
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
    async def test_composite_identifiers(self, mock_session, mock_endpoints, mock_property_config):
        """Test handling of composite identifiers (underscore-separated)."""
        source_endpoint, target_endpoint = mock_endpoints
        
        # Setup mock session to return property config
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_property_config
        mock_session.execute.return_value = mock_result
        
        # Mock target CSV data with some composite identifiers
        mock_df = pd.DataFrame({
            'identifier_column': ['P12345', 'Q67890_R11111', 'S99999']
        })
        
        with patch('biomapper.mapping.adapters.csv_adapter.CSVAdapter') as MockCSVAdapter:
            mock_adapter = Mock()
            mock_adapter.load_data = AsyncMock(return_value=mock_df)
            MockCSVAdapter.return_value = mock_adapter
            
            action = FilterByTargetPresenceAction(mock_session)
            
            # Test with composite identifiers in input
            result = await action.execute(
                current_identifiers=['P12345', 'Q67890_R11111', 'T22222_U33333', 'V44444'],
                current_ontology_type='PROTEIN_UNIPROT',
                action_params={
                    'endpoint_context': 'TARGET',
                    'ontology_type_to_match': 'PROTEIN_UNIPROT'
                },
                source_endpoint=source_endpoint,
                target_endpoint=target_endpoint,
                context={}
            )
            
            # Should match exact composite identifiers
            assert 'P12345' in result['output_identifiers']
            assert 'Q67890_R11111' in result['output_identifiers']
            assert 'T22222_U33333' not in result['output_identifiers']
            assert 'V44444' not in result['output_identifiers']
    
    @pytest.mark.asyncio
    async def test_whitespace_handling(self, mock_session, mock_endpoints, mock_property_config):
        """Test handling of identifiers with whitespace."""
        source_endpoint, target_endpoint = mock_endpoints
        
        # Setup mock session
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_property_config
        mock_session.execute.return_value = mock_result
        
        # Target data with some whitespace issues
        mock_df = pd.DataFrame({
            'identifier_column': ['P12345', ' Q67890 ', 'R11111\n', '\tS99999']
        })
        
        with patch('biomapper.mapping.adapters.csv_adapter.CSVAdapter') as MockCSVAdapter:
            mock_adapter = Mock()
            mock_adapter.load_data = AsyncMock(return_value=mock_df)
            MockCSVAdapter.return_value = mock_adapter
            
            action = FilterByTargetPresenceAction(mock_session)
            
            # Test with clean input identifiers
            result = await action.execute(
                current_identifiers=['P12345', 'Q67890', 'R11111', 'S99999', 'T22222'],
                current_ontology_type='PROTEIN_UNIPROT',
                action_params={
                    'endpoint_context': 'TARGET',
                    'ontology_type_to_match': 'PROTEIN_UNIPROT'
                },
                source_endpoint=source_endpoint,
                target_endpoint=target_endpoint,
                context={}
            )
            
            # Should match after stripping whitespace
            assert 'P12345' in result['output_identifiers']
            assert 'Q67890' in result['output_identifiers']
            assert 'R11111' in result['output_identifiers']
            assert 'S99999' in result['output_identifiers']
            assert 'T22222' not in result['output_identifiers']
    
    @pytest.mark.asyncio
    async def test_null_and_empty_values(self, mock_session, mock_endpoints, mock_property_config):
        """Test handling of null, None, and empty string values in target."""
        source_endpoint, target_endpoint = mock_endpoints
        
        # Setup mock session
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_property_config
        mock_session.execute.return_value = mock_result
        
        # Target data with various problematic values
        mock_df = pd.DataFrame({
            'identifier_column': ['P12345', None, '', '  ', 'Q67890', float('nan')]
        })
        
        with patch('biomapper.mapping.adapters.csv_adapter.CSVAdapter') as MockCSVAdapter:
            mock_adapter = Mock()
            mock_adapter.load_data = AsyncMock(return_value=mock_df)
            MockCSVAdapter.return_value = mock_adapter
            
            action = FilterByTargetPresenceAction(mock_session)
            
            result = await action.execute(
                current_identifiers=['P12345', 'Q67890', '', 'R11111'],
                current_ontology_type='PROTEIN_UNIPROT',
                action_params={
                    'endpoint_context': 'TARGET',
                    'ontology_type_to_match': 'PROTEIN_UNIPROT'
                },
                source_endpoint=source_endpoint,
                target_endpoint=target_endpoint,
                context={}
            )
            
            # Should only match valid identifiers
            assert 'P12345' in result['output_identifiers']
            assert 'Q67890' in result['output_identifiers']
            assert '' not in result['output_identifiers']
            assert 'R11111' not in result['output_identifiers']
    
    @pytest.mark.asyncio
    async def test_case_sensitivity(self, mock_session, mock_endpoints, mock_property_config):
        """Test that filtering is case-sensitive."""
        source_endpoint, target_endpoint = mock_endpoints
        
        # Setup mock session
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_property_config
        mock_session.execute.return_value = mock_result
        
        # Target data with specific case
        mock_df = pd.DataFrame({
            'identifier_column': ['P12345', 'Q67890', 'r11111']  # lowercase r
        })
        
        with patch('biomapper.mapping.adapters.csv_adapter.CSVAdapter') as MockCSVAdapter:
            mock_adapter = Mock()
            mock_adapter.load_data = AsyncMock(return_value=mock_df)
            MockCSVAdapter.return_value = mock_adapter
            
            action = FilterByTargetPresenceAction(mock_session)
            
            result = await action.execute(
                current_identifiers=['P12345', 'q67890', 'R11111', 'r11111'],  # mixed case
                current_ontology_type='PROTEIN_UNIPROT',
                action_params={
                    'endpoint_context': 'TARGET',
                    'ontology_type_to_match': 'PROTEIN_UNIPROT'
                },
                source_endpoint=source_endpoint,
                target_endpoint=target_endpoint,
                context={}
            )
            
            # Should be case-sensitive
            assert 'P12345' in result['output_identifiers']
            assert 'q67890' not in result['output_identifiers']  # wrong case
            assert 'R11111' not in result['output_identifiers']  # wrong case
            assert 'r11111' in result['output_identifiers']  # correct case
    
    @pytest.mark.asyncio
    async def test_large_dataset_performance(self, mock_session, mock_endpoints, mock_property_config):
        """Test performance with large datasets."""
        source_endpoint, target_endpoint = mock_endpoints
        
        # Setup mock session
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_property_config
        mock_session.execute.return_value = mock_result
        
        # Create large dataset
        large_target_ids = [f'P{i:05d}' for i in range(10000)]
        mock_df = pd.DataFrame({
            'identifier_column': large_target_ids
        })
        
        # Input identifiers - mix of present and absent
        input_ids = [f'P{i:05d}' for i in range(0, 20000, 2)]  # Every other ID
        
        with patch('biomapper.mapping.adapters.csv_adapter.CSVAdapter') as MockCSVAdapter:
            mock_adapter = Mock()
            mock_adapter.load_data = AsyncMock(return_value=mock_df)
            MockCSVAdapter.return_value = mock_adapter
            
            action = FilterByTargetPresenceAction(mock_session)
            
            import time
            start_time = time.time()
            
            result = await action.execute(
                current_identifiers=input_ids,
                current_ontology_type='PROTEIN_UNIPROT',
                action_params={
                    'endpoint_context': 'TARGET',
                    'ontology_type_to_match': 'PROTEIN_UNIPROT'
                },
                source_endpoint=source_endpoint,
                target_endpoint=target_endpoint,
                context={}
            )
            
            execution_time = time.time() - start_time
            
            # Should complete quickly even with large datasets
            assert execution_time < 1.0  # Should complete in under 1 second
            
            # Verify correct filtering
            assert len(result['output_identifiers']) == 5000  # Half should match
            assert result['details']['total_input'] == 10000
            assert result['details']['total_passed'] == 5000
            assert result['details']['total_filtered'] == 5000
    
    @pytest.mark.asyncio
    async def test_special_characters_in_identifiers(self, mock_session, mock_endpoints, mock_property_config):
        """Test handling of special characters in identifiers."""
        source_endpoint, target_endpoint = mock_endpoints
        
        # Setup mock session
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_property_config
        mock_session.execute.return_value = mock_result
        
        # Target data with special characters
        mock_df = pd.DataFrame({
            'identifier_column': ['P12345', 'Q67890-1', 'R11111.2', 'S99999|HUMAN', 'T22222_MOUSE']
        })
        
        with patch('biomapper.mapping.adapters.csv_adapter.CSVAdapter') as MockCSVAdapter:
            mock_adapter = Mock()
            mock_adapter.load_data = AsyncMock(return_value=mock_df)
            MockCSVAdapter.return_value = mock_adapter
            
            action = FilterByTargetPresenceAction(mock_session)
            
            result = await action.execute(
                current_identifiers=['P12345', 'Q67890-1', 'R11111.2', 'S99999|HUMAN', 'T22222_MOUSE', 'U33333'],
                current_ontology_type='PROTEIN_UNIPROT',
                action_params={
                    'endpoint_context': 'TARGET',
                    'ontology_type_to_match': 'PROTEIN_UNIPROT'
                },
                source_endpoint=source_endpoint,
                target_endpoint=target_endpoint,
                context={}
            )
            
            # Should handle special characters correctly
            assert 'P12345' in result['output_identifiers']
            assert 'Q67890-1' in result['output_identifiers']
            assert 'R11111.2' in result['output_identifiers']
            assert 'S99999|HUMAN' in result['output_identifiers']
            assert 'T22222_MOUSE' in result['output_identifiers']
            assert 'U33333' not in result['output_identifiers']