"""Unit tests for GenerateMappingSummaryAction."""

import pytest
import json
from unittest.mock import Mock, patch, mock_open
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from biomapper.core.strategy_actions.generate_mapping_summary import GenerateMappingSummaryAction
from biomapper.db.models import Endpoint


class TestGenerateMappingSummaryAction:
    """Test suite for GenerateMappingSummaryAction."""
    
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
        
        target_endpoint = Mock(spec=Endpoint)
        target_endpoint.name = "HPA_PROTEIN"
        
        return source_endpoint, target_endpoint
    
    @pytest.fixture
    def sample_context(self):
        """Create sample context data."""
        start_time = datetime.utcnow()
        return {
            'initial_identifiers': ['P001', 'P002', 'P003', 'Q001_Q002'],
            'execution_start_time': start_time,
            'step_results': [
                {
                    'step_id': 'convert_to_uniprot',
                    'action_type': 'CONVERT_IDENTIFIERS_LOCAL',
                    'input_count': 4,
                    'output_count': 3,
                    'duration': 1.5,
                    'success': True
                },
                {
                    'step_id': 'filter_by_target',
                    'action_type': 'FILTER_IDENTIFIERS_BY_TARGET_PRESENCE',
                    'input_count': 3,
                    'output_count': 2,
                    'duration': 0.8,
                    'success': True
                }
            ]
        }
    
    @pytest.mark.asyncio
    async def test_console_output_summary(self, mock_session, mock_endpoints, sample_context):
        """Test summary generation with console output."""
        source_endpoint, target_endpoint = mock_endpoints
        
        action = GenerateMappingSummaryAction(mock_session)
        
        result = await action.execute(
            current_identifiers=['P001', 'P002'],
            current_ontology_type='UNIPROT',
            action_params={
                'output_format': 'console',
                'include_statistics': True
            },
            source_endpoint=source_endpoint,
            target_endpoint=target_endpoint,
            context=sample_context
        )
        
        # Verify identifiers unchanged
        assert result['input_identifiers'] == ['P001', 'P002']
        assert result['output_identifiers'] == ['P001', 'P002']
        assert result['output_ontology_type'] == 'UNIPROT'
        
        # Check details
        details = result['details']
        assert details['action'] == 'GENERATE_MAPPING_SUMMARY'
        assert details['summary_generated'] is True
        assert details['output_format'] == 'console'
        
        # Check summary data structure
        summary_data = details['summary_data']
        assert 'execution_info' in summary_data
        assert 'input_analysis' in summary_data
        assert 'output_analysis' in summary_data
        assert 'mapping_coverage' in summary_data
        assert 'step_performance' in summary_data
        
        # Verify calculations
        assert summary_data['input_analysis']['total_input'] == 4
        assert summary_data['input_analysis']['composite_identifiers'] == 1
        assert summary_data['output_analysis']['total_output'] == 2
        assert summary_data['mapping_coverage']['coverage_percentage'] == 50.0
    
    @pytest.mark.asyncio
    async def test_json_output_to_file(self, mock_session, mock_endpoints, sample_context):
        """Test JSON output to file."""
        source_endpoint, target_endpoint = mock_endpoints
        
        action = GenerateMappingSummaryAction(mock_session)
        
        with patch('builtins.open', mock_open()) as mock_file:
            result = await action.execute(
                current_identifiers=['P001', 'P002'],
                current_ontology_type='UNIPROT',
                action_params={
                    'output_format': 'json',
                    'include_statistics': True,
                    'output_file': '/tmp/summary.json'
                },
                source_endpoint=source_endpoint,
                target_endpoint=target_endpoint,
                context=sample_context
            )
            
            # Verify file was written
            mock_file.assert_called_once_with('/tmp/summary.json', 'w')
            handle = mock_file()
            
            # Get written content
            written_calls = handle.write.call_args_list
            written_content = ''.join(call[0][0] for call in written_calls)
            
            # Parse and verify JSON
            if written_content:  # Only if write was called directly
                summary_data = json.loads(written_content)
                assert 'execution_info' in summary_data
    
    @pytest.mark.asyncio
    async def test_csv_output(self, mock_session, mock_endpoints, sample_context):
        """Test CSV output format."""
        source_endpoint, target_endpoint = mock_endpoints
        
        action = GenerateMappingSummaryAction(mock_session)
        
        with patch('builtins.open', mock_open()) as mock_file:
            result = await action.execute(
                current_identifiers=['P001', 'P002'],
                current_ontology_type='UNIPROT',
                action_params={
                    'output_format': 'csv',
                    'output_file': '/tmp/summary.csv'
                },
                source_endpoint=source_endpoint,
                target_endpoint=target_endpoint,
                context=sample_context
            )
            
            # Verify file was opened
            mock_file.assert_called_once_with('/tmp/summary.csv', 'w', newline='')
    
    @pytest.mark.asyncio
    async def test_save_to_context(self, mock_session, mock_endpoints, sample_context):
        """Test saving summary data to context."""
        source_endpoint, target_endpoint = mock_endpoints
        
        action = GenerateMappingSummaryAction(mock_session)
        
        result = await action.execute(
            current_identifiers=['P001', 'P002'],
            current_ontology_type='UNIPROT',
            action_params={
                'output_format': 'console',
                'save_to_context': 'mapping_summary'
            },
            source_endpoint=source_endpoint,
            target_endpoint=target_endpoint,
            context=sample_context
        )
        
        # Verify context was updated
        assert 'mapping_summary' in sample_context
        summary = sample_context['mapping_summary']
        assert 'execution_info' in summary
        assert 'input_analysis' in summary
    
    @pytest.mark.asyncio
    async def test_without_statistics(self, mock_session, mock_endpoints, sample_context):
        """Test summary without detailed statistics."""
        source_endpoint, target_endpoint = mock_endpoints
        
        action = GenerateMappingSummaryAction(mock_session)
        
        result = await action.execute(
            current_identifiers=['P001', 'P002'],
            current_ontology_type='UNIPROT',
            action_params={
                'output_format': 'console',
                'include_statistics': False
            },
            source_endpoint=source_endpoint,
            target_endpoint=target_endpoint,
            context=sample_context
        )
        
        # Check that step_performance is not included
        summary_data = result['details']['summary_data']
        assert 'step_performance' not in summary_data
    
    @pytest.mark.asyncio
    async def test_empty_input_handling(self, mock_session, mock_endpoints):
        """Test handling of empty input."""
        source_endpoint, target_endpoint = mock_endpoints
        
        action = GenerateMappingSummaryAction(mock_session)
        
        result = await action.execute(
            current_identifiers=[],
            current_ontology_type='UNIPROT',
            action_params={'output_format': 'console'},
            source_endpoint=source_endpoint,
            target_endpoint=target_endpoint,
            context={'initial_identifiers': []}
        )
        
        # Should still generate summary
        assert result['details']['summary_generated'] is True
        summary_data = result['details']['summary_data']
        assert summary_data['input_analysis']['total_input'] == 0
        assert summary_data['mapping_coverage']['coverage_percentage'] == 0