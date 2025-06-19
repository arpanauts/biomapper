"""Unit tests for ExportResultsAction."""

import pytest
import json
import pandas as pd
from unittest.mock import Mock, patch, mock_open
from sqlalchemy.ext.asyncio import AsyncSession

from biomapper.core.strategy_actions.export_results import ExportResultsAction
from biomapper.db.models import Endpoint


class TestExportResultsAction:
    """Test suite for ExportResultsAction."""
    
    @pytest.fixture
    def mock_session(self):
        """Create a mock database session."""
        session = Mock(spec=AsyncSession)
        return session
    
    @pytest.fixture
    def mock_endpoints(self):
        """Create mock source and target endpoints."""
        source_endpoint = Mock(spec=Endpoint)
        source_endpoint.name = "UKBB_PROTEIN"
        source_endpoint.default_ontology_type = "UNIPROT"
        
        target_endpoint = Mock(spec=Endpoint)
        target_endpoint.name = "HPA_PROTEIN"
        target_endpoint.default_ontology_type = "GENE_SYMBOL"
        
        return source_endpoint, target_endpoint
    
    @pytest.fixture
    def sample_context(self):
        """Create sample context data with mapping results."""
        return {
            'initial_identifiers': ['P001', 'P002', 'P003', 'Q001_Q002'],
            'mapping_results': {
                'P001': {
                    'final_mapped_value': 'GENE1',
                    'all_mapped_values': ['GENE1', 'GENE1A'],
                    'mapping_method': 'direct_match',
                    'confidence_score': 1.0,
                    'hop_count': 1
                },
                'P002': {
                    'final_mapped_value': 'GENE2',
                    'all_mapped_values': ['GENE2'],
                    'mapping_method': 'resolved_match',
                    'confidence_score': 0.9,
                    'hop_count': 2
                }
            },
            'all_provenance': [
                {'source_id': 'P001', 'target_id': 'GENE1', 'action': 'direct_match'},
                {'source_id': 'P002', 'target_id': 'GENE2', 'action': 'resolved_match'}
            ]
        }
    
    @pytest.mark.asyncio
    async def test_export_to_csv(self, mock_session, mock_endpoints, sample_context):
        """Test exporting results to CSV file."""
        source_endpoint, target_endpoint = mock_endpoints
        
        action = ExportResultsAction(mock_session)
        
        # Mock pandas to_csv
        with patch.object(pd.DataFrame, 'to_csv') as mock_to_csv:
            result = await action.execute(
                current_identifiers=['P001', 'P002'],
                current_ontology_type='GENE_SYMBOL',
                action_params={
                    'output_format': 'csv',
                    'output_file': '/tmp/results.csv',
                    'include_metadata': True
                },
                source_endpoint=source_endpoint,
                target_endpoint=target_endpoint,
                context=sample_context
            )
            
            # Verify to_csv was called
            mock_to_csv.assert_called_once_with('/tmp/results.csv', index=False)
        
        # Verify result structure
        assert result['input_identifiers'] == ['P001', 'P002']
        assert result['output_identifiers'] == ['P001', 'P002']
        assert result['details']['export_successful'] is True
        assert result['details']['rows_exported'] == 4  # 2 mapped + 2 unmapped
    
    @pytest.mark.asyncio
    async def test_export_to_json(self, mock_session, mock_endpoints, sample_context):
        """Test exporting results to JSON file."""
        source_endpoint, target_endpoint = mock_endpoints
        
        action = ExportResultsAction(mock_session)
        
        with patch('builtins.open', mock_open()) as mock_file:
            result = await action.execute(
                current_identifiers=['P001', 'P002'],
                current_ontology_type='GENE_SYMBOL',
                action_params={
                    'output_format': 'json',
                    'output_file': '/tmp/results.json'
                },
                source_endpoint=source_endpoint,
                target_endpoint=target_endpoint,
                context=sample_context
            )
            
            # Verify file was opened
            mock_file.assert_called_once_with('/tmp/results.json', 'w')
            
            # Get written content
            handle = mock_file()
            written_calls = handle.write.call_args_list
            if written_calls:
                written_content = ''.join(call[0][0] for call in written_calls)
                # Verify it's valid JSON with expected structure
                if written_content:
                    data = json.loads(written_content)
                    assert 'metadata' in data
                    assert 'results' in data
    
    @pytest.mark.asyncio
    async def test_export_with_column_filtering(self, mock_session, mock_endpoints, sample_context):
        """Test exporting with specific columns only."""
        source_endpoint, target_endpoint = mock_endpoints
        
        action = ExportResultsAction(mock_session)
        
        with patch.object(pd.DataFrame, 'to_csv') as mock_to_csv:
            result = await action.execute(
                current_identifiers=['P001', 'P002'],
                current_ontology_type='GENE_SYMBOL',
                action_params={
                    'output_format': 'csv',
                    'output_file': '/tmp/results.csv',
                    'columns': ['input_identifier', 'output_identifier', 'mapping_status']
                },
                source_endpoint=source_endpoint,
                target_endpoint=target_endpoint,
                context=sample_context
            )
            
            # The export should succeed
            assert result['details']['export_successful'] is True
    
    @pytest.mark.asyncio
    async def test_export_to_context(self, mock_session, mock_endpoints, sample_context):
        """Test saving export data to context."""
        source_endpoint, target_endpoint = mock_endpoints
        
        action = ExportResultsAction(mock_session)
        
        result = await action.execute(
            current_identifiers=['P001', 'P002'],
            current_ontology_type='GENE_SYMBOL',
            action_params={
                'output_format': 'json',
                'save_to_context': 'exported_data'
            },
            source_endpoint=source_endpoint,
            target_endpoint=target_endpoint,
            context=sample_context
        )
        
        # Verify context was updated
        assert 'exported_data' in sample_context
        exported = sample_context['exported_data']
        assert 'metadata' in exported
        assert 'results' in exported
    
    @pytest.mark.asyncio
    async def test_export_with_provenance(self, mock_session, mock_endpoints, sample_context):
        """Test exporting with provenance information included."""
        source_endpoint, target_endpoint = mock_endpoints
        
        action = ExportResultsAction(mock_session)
        
        with patch.object(pd.DataFrame, 'to_csv') as mock_to_csv:
            result = await action.execute(
                current_identifiers=['P001', 'P002'],
                current_ontology_type='GENE_SYMBOL',
                action_params={
                    'output_format': 'csv',
                    'output_file': '/tmp/results.csv',
                    'include_provenance': True
                },
                source_endpoint=source_endpoint,
                target_endpoint=target_endpoint,
                context=sample_context
            )
            
            assert result['details']['export_successful'] is True
    
    @pytest.mark.asyncio
    async def test_error_on_missing_output_destination(self, mock_session, mock_endpoints):
        """Test error when neither output_file nor save_to_context is provided."""
        source_endpoint, target_endpoint = mock_endpoints
        
        action = ExportResultsAction(mock_session)
        
        with pytest.raises(ValueError, match="Either output_file or save_to_context must be specified"):
            await action.execute(
                current_identifiers=['P001'],
                current_ontology_type='GENE_SYMBOL',
                action_params={'output_format': 'csv'},
                source_endpoint=source_endpoint,
                target_endpoint=target_endpoint,
                context={}
            )
    
    @pytest.mark.asyncio
    async def test_invalid_output_format(self, mock_session, mock_endpoints):
        """Test error on invalid output format."""
        source_endpoint, target_endpoint = mock_endpoints
        
        action = ExportResultsAction(mock_session)
        
        with pytest.raises(ValueError, match="Unsupported output format"):
            await action.execute(
                current_identifiers=['P001'],
                current_ontology_type='GENE_SYMBOL',
                action_params={
                    'output_format': 'invalid',
                    'output_file': '/tmp/out.txt'
                },
                source_endpoint=source_endpoint,
                target_endpoint=target_endpoint,
                context={}
            )
    
    @pytest.mark.asyncio
    async def test_handles_unmapped_identifiers(self, mock_session, mock_endpoints, sample_context):
        """Test correct handling of unmapped identifiers."""
        source_endpoint, target_endpoint = mock_endpoints
        
        action = ExportResultsAction(mock_session)
        
        # Current identifiers don't include P003
        with patch.object(pd.DataFrame, 'to_csv') as mock_to_csv:
            result = await action.execute(
                current_identifiers=['P001', 'P002'],  # P003 is missing
                current_ontology_type='GENE_SYMBOL',
                action_params={
                    'output_format': 'csv',
                    'output_file': '/tmp/results.csv'
                },
                source_endpoint=source_endpoint,
                target_endpoint=target_endpoint,
                context=sample_context
            )
            
            # Should export 4 rows (P001, P002, P003, Q001_Q002)
            assert result['details']['rows_exported'] == 4