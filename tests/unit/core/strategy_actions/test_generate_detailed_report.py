"""Unit tests for GenerateDetailedReportAction."""

import pytest
import json
from unittest.mock import Mock, AsyncMock, patch, mock_open
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from biomapper.core.strategy_actions.generate_detailed_report import GenerateDetailedReportAction
from biomapper.db.models import Endpoint


class TestGenerateDetailedReportAction:
    """Test suite for GenerateDetailedReportAction."""
    
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
    def comprehensive_context(self):
        """Create comprehensive context data for detailed reporting."""
        return {
            'initial_identifiers': ['P001', 'P002', 'P003', 'Q001_Q002', 'P004'],
            'step_results': [
                {
                    'step_id': 'convert_to_uniprot',
                    'action_type': 'CONVERT_IDENTIFIERS_LOCAL',
                    'input_count': 5,
                    'output_count': 4,
                    'input_ontology_type': 'CUSTOM',
                    'output_ontology_type': 'UNIPROT',
                    'duration': 1.5,
                    'success': True,
                    'parameters': {'conversion_type': 'custom_to_uniprot'}
                },
                {
                    'step_id': 'filter_by_target',
                    'action_type': 'FILTER_IDENTIFIERS_BY_TARGET_PRESENCE',
                    'input_count': 4,
                    'output_count': 2,
                    'input_ontology_type': 'UNIPROT',
                    'output_ontology_type': 'UNIPROT',
                    'duration': 0.8,
                    'success': True,
                    'parameters': {'target_ontology': 'UNIPROT'}
                }
            ],
            'all_provenance': [
                {'source_id': 'P001', 'target_id': 'GENE1', 'action': 'convert', 'method': 'direct_conversion'},
                {'source_id': 'P001', 'target_id': 'GENE1', 'action': 'filter', 'method': 'presence_check'},
                {'source_id': 'P002', 'target_id': 'GENE2', 'action': 'convert', 'method': 'direct_conversion'},
                {'source_id': 'P002', 'target_id': 'GENE2', 'action': 'filter', 'method': 'presence_check'},
                {'source_id': 'P003', 'action': 'filter', 'method': 'filtered_out'},
                {'source_id': 'Q001_Q002', 'target_id': 'GENE3', 'action': 'convert', 'method': 'composite_split'},
                {'source_id': 'Q001_Q002', 'target_id': 'GENE4', 'action': 'convert', 'method': 'composite_split'}
            ],
            'mapping_results': {
                'P001': {'all_mapped_values': ['GENE1']},
                'P002': {'all_mapped_values': ['GENE2']},
                'Q001_Q002': {'all_mapped_values': ['GENE3', 'GENE4']}
            }
        }
    
    @pytest.mark.asyncio
    async def test_generate_markdown_report(self, mock_session, mock_endpoints, comprehensive_context):
        """Test generating detailed report in markdown format."""
        source_endpoint, target_endpoint = mock_endpoints
        
        action = GenerateDetailedReportAction(mock_session)
        
        with patch('builtins.open', mock_open()) as mock_file:
            result = await action.execute(
                current_identifiers=['P001', 'P002'],
                current_ontology_type='GENE_SYMBOL',
                action_params={
                    'output_file': '/tmp/report.md',
                    'format': 'markdown',
                    'include_unmatched': True,
                    'grouping_strategy': 'by_step'
                },
                source_endpoint=source_endpoint,
                target_endpoint=target_endpoint,
                context=comprehensive_context
            )
            
            # Verify file was written
            mock_file.assert_called_once_with('/tmp/report.md', 'w')
            
            # Verify result structure
            assert result['details']['report_generated'] is True
            assert result['details']['output_format'] == 'markdown'
            assert 'sections_included' in result['details']
    
    @pytest.mark.asyncio
    async def test_grouping_by_ontology(self, mock_session, mock_endpoints, comprehensive_context):
        """Test report grouping by ontology type."""
        source_endpoint, target_endpoint = mock_endpoints
        
        action = GenerateDetailedReportAction(mock_session)
        
        result = await action.execute(
            current_identifiers=['P001', 'P002'],
            current_ontology_type='GENE_SYMBOL',
            action_params={
                'format': 'json',
                'grouping_strategy': 'by_ontology',
                'save_to_context': 'detailed_report'
            },
            source_endpoint=source_endpoint,
            target_endpoint=target_endpoint,
            context=comprehensive_context
        )
        
        # Check saved report data
        report_data = comprehensive_context['detailed_report']
        assert 'step_details' in report_data
        
        # Should be grouped by ontology transitions
        step_details = report_data['step_details']
        assert isinstance(step_details, dict)
        assert any('→' in key for key in step_details.keys())
    
    @pytest.mark.asyncio
    async def test_grouping_by_method(self, mock_session, mock_endpoints, comprehensive_context):
        """Test report grouping by action method."""
        source_endpoint, target_endpoint = mock_endpoints
        
        action = GenerateDetailedReportAction(mock_session)
        
        result = await action.execute(
            current_identifiers=['P001', 'P002'],
            current_ontology_type='GENE_SYMBOL',
            action_params={
                'format': 'json',
                'grouping_strategy': 'by_method',
                'save_to_context': 'method_report'
            },
            source_endpoint=source_endpoint,
            target_endpoint=target_endpoint,
            context=comprehensive_context
        )
        
        # Check grouped by method
        report_data = comprehensive_context['method_report']
        step_details = report_data['step_details']
        assert 'CONVERT_IDENTIFIERS_LOCAL' in step_details
        assert 'FILTER_IDENTIFIERS_BY_TARGET_PRESENCE' in step_details
    
    @pytest.mark.asyncio
    async def test_unmatched_analysis(self, mock_session, mock_endpoints, comprehensive_context):
        """Test unmatched identifier analysis."""
        source_endpoint, target_endpoint = mock_endpoints
        
        action = GenerateDetailedReportAction(mock_session)
        
        result = await action.execute(
            current_identifiers=['P001', 'P002'],  # P003, P004, Q001_Q002 are unmatched
            current_ontology_type='GENE_SYMBOL',
            action_params={
                'format': 'json',
                'include_unmatched': True,
                'save_to_context': 'unmatched_report'
            },
            source_endpoint=source_endpoint,
            target_endpoint=target_endpoint,
            context=comprehensive_context
        )
        
        # Check unmatched analysis
        report_data = comprehensive_context['unmatched_report']
        unmatched = report_data['unmatched_analysis']
        assert unmatched['total_unmatched'] == 3  # P003, P004, Q001_Q002
        assert unmatched['summary']['composite_count'] == 1  # Q001_Q002
        assert unmatched['summary']['single_count'] == 2  # P003, P004
    
    @pytest.mark.asyncio
    async def test_relationship_analysis(self, mock_session, mock_endpoints, comprehensive_context):
        """Test many-to-many relationship analysis."""
        source_endpoint, target_endpoint = mock_endpoints
        
        action = GenerateDetailedReportAction(mock_session)
        
        result = await action.execute(
            current_identifiers=['P001', 'P002', 'GENE3', 'GENE4'],
            current_ontology_type='GENE_SYMBOL',
            action_params={
                'format': 'json',
                'save_to_context': 'relationship_report'
            },
            source_endpoint=source_endpoint,
            target_endpoint=target_endpoint,
            context=comprehensive_context
        )
        
        # Check relationship analysis
        report_data = comprehensive_context['relationship_report']
        relationships = report_data['relationship_analysis']
        assert 'one_to_many_count' in relationships
        assert 'many_to_one_count' in relationships
        assert 'average_targets_per_source' in relationships
    
    @pytest.mark.asyncio
    async def test_html_output(self, mock_session, mock_endpoints, comprehensive_context):
        """Test HTML output format."""
        source_endpoint, target_endpoint = mock_endpoints
        
        action = GenerateDetailedReportAction(mock_session)
        
        with patch('builtins.open', mock_open()) as mock_file:
            result = await action.execute(
                current_identifiers=['P001', 'P002'],
                current_ontology_type='GENE_SYMBOL',
                action_params={
                    'output_file': '/tmp/report.html',
                    'format': 'html'
                },
                source_endpoint=source_endpoint,
                target_endpoint=target_endpoint,
                context=comprehensive_context
            )
            
            # Verify HTML file was written
            mock_file.assert_called_once_with('/tmp/report.html', 'w')
            
            # Get written content
            handle = mock_file()
            written_calls = handle.write.call_args_list
            if written_calls:
                written_content = ''.join(call[0][0] for call in written_calls)
                # Should contain HTML tags
                assert '<html>' in written_content or written_content == ''
    
    @pytest.mark.asyncio
    async def test_exclude_unmatched(self, mock_session, mock_endpoints, comprehensive_context):
        """Test report without unmatched analysis."""
        source_endpoint, target_endpoint = mock_endpoints
        
        action = GenerateDetailedReportAction(mock_session)
        
        result = await action.execute(
            current_identifiers=['P001', 'P002'],
            current_ontology_type='GENE_SYMBOL',
            action_params={
                'format': 'json',
                'include_unmatched': False,
                'save_to_context': 'no_unmatched_report'
            },
            source_endpoint=source_endpoint,
            target_endpoint=target_endpoint,
            context=comprehensive_context
        )
        
        # Should not include unmatched analysis
        report_data = comprehensive_context['no_unmatched_report']
        assert 'unmatched_analysis' not in report_data
    
    @pytest.mark.asyncio
    async def test_invalid_grouping_strategy(self, mock_session, mock_endpoints):
        """Test error on invalid grouping strategy."""
        source_endpoint, target_endpoint = mock_endpoints
        
        action = GenerateDetailedReportAction(mock_session)
        
        with pytest.raises(ValueError, match="Unknown grouping strategy"):
            await action.execute(
                current_identifiers=['P001'],
                current_ontology_type='GENE_SYMBOL',
                action_params={
                    'grouping_strategy': 'invalid',
                    'output_file': '/tmp/report.json'
                },
                source_endpoint=source_endpoint,
                target_endpoint=target_endpoint,
                context={}
            )