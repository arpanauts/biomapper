"""Unit tests for ConvertIdentifiersLocalAction."""

import pytest
import pandas as pd
from unittest.mock import Mock, AsyncMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from biomapper.core.strategy_actions.convert_identifiers_local import ConvertIdentifiersLocalAction
from biomapper.db.models import Endpoint, EndpointPropertyConfig, PropertyExtractionConfig


class TestConvertIdentifiersLocalAction:
    """Test suite for ConvertIdentifiersLocalAction."""
    
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
    def mock_property_configs(self):
        """Create mock property configurations."""
        # Input config
        input_extraction = Mock(spec=PropertyExtractionConfig)
        input_extraction.column_name = "uniprot_id"
        
        input_config = Mock(spec=EndpointPropertyConfig)
        input_config.ontology_type = "PROTEIN_UNIPROT"
        input_config.property_extraction_config = input_extraction
        
        # Output config
        output_extraction = Mock(spec=PropertyExtractionConfig)
        output_extraction.column_name = "ensembl_id"
        
        output_config = Mock(spec=EndpointPropertyConfig)
        output_config.ontology_type = "PROTEIN_ENSEMBL"
        output_config.property_extraction_config = output_extraction
        
        return [input_config, output_config]
    
    @pytest.mark.asyncio
    async def test_successful_conversion(self, mock_session, mock_endpoints, mock_property_configs):
        """Test successful identifier conversion with valid configuration."""
        source_endpoint, target_endpoint = mock_endpoints
        
        # Setup mock session to return property configs
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = mock_property_configs
        mock_session.execute.return_value = mock_result
        
        # Mock CSV data
        mock_df = pd.DataFrame({
            'uniprot_id': ['P12345', 'Q67890', 'P12345'],  # Include duplicate for one-to-many
            'ensembl_id': ['ENSP001', 'ENSP002', 'ENSP003']
        })
        
        with patch('biomapper.mapping.adapters.csv_adapter.CSVAdapter') as MockCSVAdapter:
            mock_adapter = Mock()
            mock_adapter.load_data = AsyncMock(return_value=mock_df)
            MockCSVAdapter.return_value = mock_adapter
            
            action = ConvertIdentifiersLocalAction(mock_session)
            
            result = await action.execute(
                current_identifiers=['P12345', 'Q67890', 'R11111'],
                current_ontology_type='PROTEIN_UNIPROT',
                action_params={
                    'endpoint_context': 'SOURCE',
                    'output_ontology_type': 'PROTEIN_ENSEMBL'
                },
                source_endpoint=source_endpoint,
                target_endpoint=target_endpoint,
                context={}
            )
            
            # Verify results
            assert result['input_identifiers'] == ['P12345', 'Q67890', 'R11111']
            assert set(result['output_identifiers']) == {'ENSP001', 'ENSP003', 'ENSP002'}  # One-to-many for P12345
            assert result['output_ontology_type'] == 'PROTEIN_ENSEMBL'
            assert len(result['provenance']) == 3  # 2 for P12345, 1 for Q67890
            
            # Check statistics
            details = result['details']
            assert details['action'] == 'CONVERT_IDENTIFIERS_LOCAL'
            assert details['total_input'] == 3
            assert details['total_converted'] == 2
            assert details['total_unmapped'] == 1
            assert details['total_output'] == 3
    
    @pytest.mark.asyncio
    async def test_missing_property_configs(self, mock_session, mock_endpoints):
        """Test handling of missing EndpointPropertyConfig."""
        source_endpoint, target_endpoint = mock_endpoints
        
        # Setup mock session to return empty configs
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result
        
        action = ConvertIdentifiersLocalAction(mock_session)
        
        with pytest.raises(ValueError, match="does not have configurations for ontology types"):
            await action.execute(
                current_identifiers=['P12345'],
                current_ontology_type='PROTEIN_UNIPROT',
                action_params={
                    'endpoint_context': 'SOURCE',
                    'output_ontology_type': 'PROTEIN_ENSEMBL'
                },
                source_endpoint=source_endpoint,
                target_endpoint=target_endpoint,
                context={}
            )
    
    @pytest.mark.asyncio
    async def test_one_to_many_mapping(self, mock_session, mock_endpoints, mock_property_configs):
        """Test correct processing of one-to-many mappings."""
        source_endpoint, target_endpoint = mock_endpoints
        
        # Setup mock session
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = mock_property_configs
        mock_session.execute.return_value = mock_result
        
        # Mock CSV data with one-to-many mapping
        mock_df = pd.DataFrame({
            'uniprot_id': ['P12345', 'P12345', 'P12345'],
            'ensembl_id': ['ENSP001', 'ENSP002', 'ENSP003']
        })
        
        with patch('biomapper.mapping.adapters.csv_adapter.CSVAdapter') as MockCSVAdapter:
            mock_adapter = Mock()
            mock_adapter.load_data = AsyncMock(return_value=mock_df)
            MockCSVAdapter.return_value = mock_adapter
            
            action = ConvertIdentifiersLocalAction(mock_session)
            
            result = await action.execute(
                current_identifiers=['P12345'],
                current_ontology_type='PROTEIN_UNIPROT',
                action_params={
                    'endpoint_context': 'SOURCE',
                    'output_ontology_type': 'PROTEIN_ENSEMBL'
                },
                source_endpoint=source_endpoint,
                target_endpoint=target_endpoint,
                context={}
            )
            
            assert len(result['output_identifiers']) == 3
            assert set(result['output_identifiers']) == {'ENSP001', 'ENSP002', 'ENSP003'}
            assert len(result['provenance']) == 3
    
    @pytest.mark.asyncio
    async def test_empty_input_identifiers(self, mock_session, mock_endpoints, mock_property_configs):
        """Test behavior with empty list of input identifiers."""
        source_endpoint, target_endpoint = mock_endpoints
        
        # Setup mock session
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = mock_property_configs
        mock_session.execute.return_value = mock_result
        
        with patch('biomapper.mapping.adapters.csv_adapter.CSVAdapter') as MockCSVAdapter:
            mock_adapter = Mock()
            mock_adapter.load_data = AsyncMock(return_value=pd.DataFrame())
            MockCSVAdapter.return_value = mock_adapter
            
            action = ConvertIdentifiersLocalAction(mock_session)
            
            result = await action.execute(
                current_identifiers=[],
                current_ontology_type='PROTEIN_UNIPROT',
                action_params={
                    'endpoint_context': 'SOURCE',
                    'output_ontology_type': 'PROTEIN_ENSEMBL'
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
    async def test_empty_endpoint_data(self, mock_session, mock_endpoints, mock_property_configs):
        """Test behavior when endpoint data is empty."""
        source_endpoint, target_endpoint = mock_endpoints
        
        # Setup mock session
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = mock_property_configs
        mock_session.execute.return_value = mock_result
        
        # Empty DataFrame
        mock_df = pd.DataFrame(columns=['uniprot_id', 'ensembl_id'])
        
        with patch('biomapper.mapping.adapters.csv_adapter.CSVAdapter') as MockCSVAdapter:
            mock_adapter = Mock()
            mock_adapter.load_data = AsyncMock(return_value=mock_df)
            MockCSVAdapter.return_value = mock_adapter
            
            action = ConvertIdentifiersLocalAction(mock_session)
            
            result = await action.execute(
                current_identifiers=['P12345', 'Q67890'],
                current_ontology_type='PROTEIN_UNIPROT',
                action_params={
                    'endpoint_context': 'SOURCE',
                    'output_ontology_type': 'PROTEIN_ENSEMBL'
                },
                source_endpoint=source_endpoint,
                target_endpoint=target_endpoint,
                context={}
            )
            
            # All identifiers should be unmapped
            assert result['output_identifiers'] == []
            assert result['details']['total_unmapped'] == 2
            assert result['details']['total_converted'] == 0
    
    @pytest.mark.asyncio
    async def test_invalid_endpoint_context(self, mock_session, mock_endpoints):
        """Test validation of endpoint_context parameter."""
        source_endpoint, target_endpoint = mock_endpoints
        
        action = ConvertIdentifiersLocalAction(mock_session)
        
        with pytest.raises(ValueError, match="Invalid endpoint_context"):
            await action.execute(
                current_identifiers=['P12345'],
                current_ontology_type='PROTEIN_UNIPROT',
                action_params={
                    'endpoint_context': 'INVALID',
                    'output_ontology_type': 'PROTEIN_ENSEMBL'
                },
                source_endpoint=source_endpoint,
                target_endpoint=target_endpoint,
                context={}
            )
    
    @pytest.mark.asyncio
    async def test_missing_output_ontology_type(self, mock_session, mock_endpoints):
        """Test validation when output_ontology_type is missing."""
        source_endpoint, target_endpoint = mock_endpoints
        
        action = ConvertIdentifiersLocalAction(mock_session)
        
        with pytest.raises(ValueError, match="output_ontology_type is required"):
            await action.execute(
                current_identifiers=['P12345'],
                current_ontology_type='PROTEIN_UNIPROT',
                action_params={
                    'endpoint_context': 'SOURCE'
                },
                source_endpoint=source_endpoint,
                target_endpoint=target_endpoint,
                context={}
            )
    
    @pytest.mark.asyncio
    async def test_target_endpoint_conversion(self, mock_session, mock_endpoints, mock_property_configs):
        """Test conversion using target endpoint."""
        source_endpoint, target_endpoint = mock_endpoints
        
        # Setup mock session
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = mock_property_configs
        mock_session.execute.return_value = mock_result
        
        # Mock CSV data
        mock_df = pd.DataFrame({
            'uniprot_id': ['P12345'],
            'ensembl_id': ['ENSP001']
        })
        
        with patch('biomapper.mapping.adapters.csv_adapter.CSVAdapter') as MockCSVAdapter:
            mock_adapter = Mock()
            mock_adapter.load_data = AsyncMock(return_value=mock_df)
            MockCSVAdapter.return_value = mock_adapter
            
            action = ConvertIdentifiersLocalAction(mock_session)
            
            result = await action.execute(
                current_identifiers=['P12345'],
                current_ontology_type='PROTEIN_UNIPROT',
                action_params={
                    'endpoint_context': 'TARGET',
                    'output_ontology_type': 'PROTEIN_ENSEMBL'
                },
                source_endpoint=source_endpoint,
                target_endpoint=target_endpoint,
                context={}
            )
            
            # Should use target endpoint
            MockCSVAdapter.assert_called_with(target_endpoint)
            assert result['details']['endpoint_used'] == 'target_endpoint'
    
    @pytest.mark.asyncio
    async def test_input_ontology_type_override(self, mock_session, mock_endpoints, mock_property_configs):
        """Test using input_ontology_type parameter to override current_ontology_type."""
        source_endpoint, target_endpoint = mock_endpoints
        
        # Modify mock configs for different input type
        mock_property_configs[0].ontology_type = 'GENE_SYMBOL'
        
        # Setup mock session
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = mock_property_configs
        mock_session.execute.return_value = mock_result
        
        # Mock CSV data
        mock_df = pd.DataFrame({
            'gene_symbol': ['TP53'],
            'ensembl_id': ['ENSP001']
        })
        mock_property_configs[0].property_extraction_config.column_name = 'gene_symbol'
        
        with patch('biomapper.mapping.adapters.csv_adapter.CSVAdapter') as MockCSVAdapter:
            mock_adapter = Mock()
            mock_adapter.load_data = AsyncMock(return_value=mock_df)
            MockCSVAdapter.return_value = mock_adapter
            
            action = ConvertIdentifiersLocalAction(mock_session)
            
            result = await action.execute(
                current_identifiers=['TP53'],
                current_ontology_type='PROTEIN_UNIPROT',  # This will be overridden
                action_params={
                    'endpoint_context': 'SOURCE',
                    'output_ontology_type': 'PROTEIN_ENSEMBL',
                    'input_ontology_type': 'GENE_SYMBOL'  # Override
                },
                source_endpoint=source_endpoint,
                target_endpoint=target_endpoint,
                context={}
            )
            
            assert result['details']['conversion'] == 'GENE_SYMBOL -> PROTEIN_ENSEMBL'
            assert result['provenance'][0]['source_ontology'] == 'GENE_SYMBOL'
    
    @pytest.mark.asyncio
    async def test_selective_column_loading(self, mock_session, mock_endpoints, mock_property_configs):
        """Test that CSVAdapter is called with selective column loading."""
        source_endpoint, target_endpoint = mock_endpoints
        
        # Setup mock session
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = mock_property_configs
        mock_session.execute.return_value = mock_result
        
        # Mock CSV data
        mock_df = pd.DataFrame({
            'uniprot_id': ['P12345'],
            'ensembl_id': ['ENSP001']
        })
        
        with patch('biomapper.mapping.adapters.csv_adapter.CSVAdapter') as MockCSVAdapter:
            mock_adapter = Mock()
            mock_adapter.load_data = AsyncMock(return_value=mock_df)
            MockCSVAdapter.return_value = mock_adapter
            
            action = ConvertIdentifiersLocalAction(mock_session)
            
            await action.execute(
                current_identifiers=['P12345'],
                current_ontology_type='PROTEIN_UNIPROT',
                action_params={
                    'endpoint_context': 'SOURCE',
                    'output_ontology_type': 'PROTEIN_ENSEMBL'
                },
                source_endpoint=source_endpoint,
                target_endpoint=target_endpoint,
                context={}
            )
            
            # Verify CSVAdapter was initialized with the endpoint
            MockCSVAdapter.assert_called_with(endpoint=source_endpoint)
            
            # Verify load_data was called with only the required columns
            mock_adapter.load_data.assert_called_once_with(
                columns_to_load=['uniprot_id', 'ensembl_id']
            )