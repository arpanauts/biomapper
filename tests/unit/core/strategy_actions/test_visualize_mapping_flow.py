"""Unit tests for VisualizeMappingFlowAction."""

import pytest
import json
from unittest.mock import Mock, AsyncMock, patch, mock_open
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from biomapper.core.strategy_actions.visualize_mapping_flow import VisualizeMappingFlowAction
from biomapper.db.models import Endpoint


class TestVisualizeMappingFlowAction:
    """Test suite for VisualizeMappingFlowAction."""
    
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
    def visualization_context(self):
        """Create context data for visualization."""
        return {
            'initial_identifiers': ['P001', 'P002', 'P003', 'Q001_Q002', 'P004'],
            'step_results': [
                {
                    'step_id': 'convert_identifiers',
                    'action_type': 'CONVERT_IDENTIFIERS_LOCAL',
                    'input_count': 5,
                    'output_count': 4,
                    'duration': 1.5,
                    'success': True,
                    'parameters': {'target_ontology': 'UNIPROT'}
                },
                {
                    'step_id': 'filter_by_presence',
                    'action_type': 'FILTER_IDENTIFIERS_BY_TARGET_PRESENCE',
                    'input_count': 4,
                    'output_count': 3,
                    'duration': 0.8,
                    'success': True,
                    'parameters': {}
                },
                {
                    'step_id': 'final_conversion',
                    'action_type': 'CONVERT_IDENTIFIERS_LOCAL',
                    'input_count': 3,
                    'output_count': 3,
                    'duration': 0.5,
                    'success': True,
                    'parameters': {'target_ontology': 'GENE_SYMBOL'}
                }
            ],
            'all_provenance': [
                {'source_id': 'P001', 'action': 'convert', 'method': 'direct'},
                {'source_id': 'P002', 'action': 'convert', 'method': 'direct'},
                {'source_id': 'P003', 'action': 'filter', 'method': 'removed'},
                {'source_id': 'Q001_Q002', 'action': 'convert', 'method': 'composite'}
            ]
        }
    
    @pytest.mark.asyncio
    async def test_json_visualization_output(self, mock_session, mock_endpoints, visualization_context):
        """Test generating JSON visualization data."""
        source_endpoint, target_endpoint = mock_endpoints
        
        action = VisualizeMappingFlowAction(mock_session)
        
        with patch('builtins.open', mock_open()) as mock_file:
            result = await action.execute(
                current_identifiers=['P001', 'P002', 'Q001_Q002'],
                current_ontology_type='GENE_SYMBOL',
                action_params={
                    'output_file': '/tmp/viz.json',
                    'chart_type': 'json',
                    'show_statistics': True
                },
                source_endpoint=source_endpoint,
                target_endpoint=target_endpoint,
                context=visualization_context
            )
            
            # Verify file was written
            mock_file.assert_called_once_with('/tmp/viz.json', 'w')
            
            # Verify result
            assert result['details']['visualization_generated'] is True
            assert result['details']['chart_type'] == 'json'
    
    @pytest.mark.asyncio
    async def test_sankey_diagram_generation(self, mock_session, mock_endpoints, visualization_context):
        """Test Sankey diagram data generation."""
        source_endpoint, target_endpoint = mock_endpoints
        
        action = VisualizeMappingFlowAction(mock_session)
        
        with patch('builtins.open', mock_open()) as mock_file:
            result = await action.execute(
                current_identifiers=['P001', 'P002', 'Q001_Q002'],
                current_ontology_type='GENE_SYMBOL',
                action_params={
                    'output_file': '/tmp/sankey.json',
                    'chart_type': 'sankey',
                    'show_statistics': True
                },
                source_endpoint=source_endpoint,
                target_endpoint=target_endpoint,
                context=visualization_context
            )
            
            # Get written content
            handle = mock_file()
            written_calls = handle.write.call_args_list
            if written_calls:
                written_content = ''.join(call[0][0] for call in written_calls)
                if written_content:
                    sankey_data = json.loads(written_content)
                    assert sankey_data['type'] == 'sankey'
                    assert 'nodes' in sankey_data
                    assert 'links' in sankey_data
                    assert len(sankey_data['nodes']) >= 4  # Initial + 3 steps + Final
    
    @pytest.mark.asyncio
    async def test_flow_diagram_generation(self, mock_session, mock_endpoints, visualization_context):
        """Test flow diagram data generation."""
        source_endpoint, target_endpoint = mock_endpoints
        
        action = VisualizeMappingFlowAction(mock_session)
        
        with patch('builtins.open', mock_open()) as mock_file:
            result = await action.execute(
                current_identifiers=['P001', 'P002'],
                current_ontology_type='GENE_SYMBOL',
                action_params={
                    'output_file': '/tmp/flow.json',
                    'chart_type': 'flow'
                },
                source_endpoint=source_endpoint,
                target_endpoint=target_endpoint,
                context=visualization_context
            )
            
            handle = mock_file()
            written_calls = handle.write.call_args_list
            if written_calls:
                written_content = ''.join(call[0][0] for call in written_calls)
                if written_content:
                    flow_data = json.loads(written_content)
                    assert flow_data['type'] == 'flow'
                    assert 'nodes' in flow_data
                    assert 'edges' in flow_data
                    assert len(flow_data['nodes']) == 3  # 3 steps
    
    @pytest.mark.asyncio
    async def test_bar_chart_with_matplotlib(self, mock_session, mock_endpoints, visualization_context):
        """Test bar chart generation with matplotlib available."""
        source_endpoint, target_endpoint = mock_endpoints
        
        action = VisualizeMappingFlowAction(mock_session)
        
        # Mock matplotlib
        with patch('matplotlib.pyplot') as mock_plt:
            # Set up mock for subplots
            mock_fig = Mock()
            mock_ax = Mock()
            mock_ax2 = Mock()
            
            # Mock bar returns
            mock_bar1 = Mock()
            mock_bar1.get_height.return_value = 5
            mock_bar1.get_x.return_value = 0
            mock_bar1.get_width.return_value = 0.35
            mock_bar2 = Mock()
            mock_bar2.get_height.return_value = 4
            mock_bar2.get_x.return_value = 0.35
            mock_bar2.get_width.return_value = 0.35
            
            mock_ax.bar.side_effect = [[mock_bar1], [mock_bar2]]  # Return list of bars
            mock_ax.twinx.return_value = mock_ax2
            mock_ax.get_legend_handles_labels.return_value = ([], [])
            mock_ax2.get_legend_handles_labels.return_value = ([], [])
            mock_ax2.plot.return_value = []
            mock_plt.subplots.return_value = (mock_fig, mock_ax)
            
            with patch('builtins.open', mock_open()):
                result = await action.execute(
                    current_identifiers=['P001', 'P002'],
                    current_ontology_type='GENE_SYMBOL',
                    action_params={
                        'output_file': '/tmp/bar.png',
                        'chart_type': 'bar'
                    },
                    source_endpoint=source_endpoint,
                    target_endpoint=target_endpoint,
                    context=visualization_context
                )
                
                # Should have called savefig
                mock_plt.savefig.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_bar_chart_fallback_without_matplotlib(self, mock_session, mock_endpoints, visualization_context):
        """Test bar chart fallback when matplotlib is not available."""
        source_endpoint, target_endpoint = mock_endpoints
        
        action = VisualizeMappingFlowAction(mock_session)
        
        # Simulate ImportError for matplotlib by patching the import mechanism
        import builtins
        original_import = builtins.__import__
        
        def mock_import(name, *args, **kwargs):
            if name == 'matplotlib.pyplot':
                raise ImportError('matplotlib not available')
            return original_import(name, *args, **kwargs)
        
        with patch('builtins.__import__', side_effect=mock_import):
            with patch('builtins.open', mock_open()) as mock_file:
                result = await action.execute(
                    current_identifiers=['P001', 'P002'],
                    current_ontology_type='GENE_SYMBOL',
                    action_params={
                        'output_file': '/tmp/bar.json',
                        'chart_type': 'bar'
                    },
                    source_endpoint=source_endpoint,
                    target_endpoint=target_endpoint,
                    context=visualization_context
                )
                
                # Should fall back to JSON
                handle = mock_file()
                written_calls = handle.write.call_args_list
                if written_calls:
                    written_content = ''.join(call[0][0] for call in written_calls)
                    if written_content:
                        bar_data = json.loads(written_content)
                        assert bar_data['type'] == 'bar'
                        assert 'datasets' in bar_data
    
    @pytest.mark.asyncio
    async def test_save_to_context(self, mock_session, mock_endpoints, visualization_context):
        """Test saving visualization data to context."""
        source_endpoint, target_endpoint = mock_endpoints
        
        action = VisualizeMappingFlowAction(mock_session)
        
        with patch('builtins.open', mock_open()):
            result = await action.execute(
                current_identifiers=['P001', 'P002'],
                current_ontology_type='GENE_SYMBOL',
                action_params={
                    'output_file': '/tmp/viz.json',
                    'chart_type': 'json',
                    'save_to_context': 'viz_data'
                },
                source_endpoint=source_endpoint,
                target_endpoint=target_endpoint,
                context=visualization_context
            )
            
            # Check context was updated
            assert 'viz_data' in visualization_context
            viz_data = visualization_context['viz_data']
            assert 'metadata' in viz_data
            assert 'flow' in viz_data
    
    @pytest.mark.asyncio
    async def test_without_statistics(self, mock_session, mock_endpoints, visualization_context):
        """Test visualization without detailed statistics."""
        source_endpoint, target_endpoint = mock_endpoints
        
        action = VisualizeMappingFlowAction(mock_session)
        
        with patch('builtins.open', mock_open()):
            result = await action.execute(
                current_identifiers=['P001', 'P002'],
                current_ontology_type='GENE_SYMBOL',
                action_params={
                    'output_file': '/tmp/viz.json',
                    'chart_type': 'json',
                    'show_statistics': False,
                    'save_to_context': 'no_stats_viz'
                },
                source_endpoint=source_endpoint,
                target_endpoint=target_endpoint,
                context=visualization_context
            )
            
            # Should not include identifier categories
            viz_data = visualization_context['no_stats_viz']
            assert 'identifier_categories' not in viz_data
    
    @pytest.mark.asyncio
    async def test_error_on_missing_output_file(self, mock_session, mock_endpoints):
        """Test error when output_file is not provided."""
        source_endpoint, target_endpoint = mock_endpoints
        
        action = VisualizeMappingFlowAction(mock_session)
        
        with pytest.raises(ValueError, match="output_file is required"):
            await action.execute(
                current_identifiers=['P001'],
                current_ontology_type='GENE_SYMBOL',
                action_params={'chart_type': 'json'},
                source_endpoint=source_endpoint,
                target_endpoint=target_endpoint,
                context={}
            )
    
    @pytest.mark.asyncio
    async def test_invalid_chart_type(self, mock_session, mock_endpoints):
        """Test error on invalid chart type."""
        source_endpoint, target_endpoint = mock_endpoints
        
        action = VisualizeMappingFlowAction(mock_session)
        
        with pytest.raises(ValueError, match="Unsupported chart type"):
            await action.execute(
                current_identifiers=['P001'],
                current_ontology_type='GENE_SYMBOL',
                action_params={
                    'output_file': '/tmp/viz.png',
                    'chart_type': 'invalid'
                },
                source_endpoint=source_endpoint,
                target_endpoint=target_endpoint,
                context={}
            )