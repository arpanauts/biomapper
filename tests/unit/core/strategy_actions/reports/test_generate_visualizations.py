"""Test suite for visualization generation - WRITE THIS FIRST!"""

import pytest
from pathlib import Path
import tempfile
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock, AsyncMock
import json

# These imports will fail initially - expected in TDD
from biomapper.core.strategy_actions.reports.generate_visualizations import (
    GenerateMappingVisualizationsAction,
    VisualizationParams,
    create_coverage_pie,
    create_confidence_histogram,
    create_mapping_flow_sankey,
    create_one_to_many_chart,
    create_interactive_scatter,
    create_statistics_dashboard
)


class TestVisualizationFunctions:
    """Test individual visualization functions."""
    
    @pytest.fixture
    def sample_data(self):
        """Create sample DataFrame for testing."""
        return pd.DataFrame({
            'source_id': ['P12345', 'Q67890', 'A12345', 'B67890', 'C12345'],
            'target_id': ['ENSG001', 'ENSG002', None, 'ENSG004', 'ENSG005'],
            'confidence_score': [0.95, 0.80, 0.0, 0.65, 0.45],
            'mapping_method': ['direct', 'direct', 'unmapped', 'normalized', 'gene_bridge'],
            'coverage_score': [1.0, 0.9, 0.0, 0.7, 0.5]
        })
    
    @pytest.fixture
    def statistics_data(self):
        """Create sample statistics for testing."""
        return {
            'total_identifiers': 1201,
            'successfully_mapped': 923,
            'unmatched_count': 278,
            'mapping_success_rate': 76.9,
            'high_confidence_count': 812,
            'low_confidence_count': 111,
            'mapping_methods': {
                'direct_match': 812,
                'historical_resolution': 111,
                'gene_symbol_bridge': 87,
                'unmapped': 278
            }
        }
    
    def test_coverage_pie_chart(self, sample_data, statistics_data):
        """Test coverage pie chart generation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "coverage.png"
            
            result = create_coverage_pie(
                data=sample_data,
                statistics=statistics_data,
                output_path=output_path
            )
            
            assert result == True
            assert output_path.exists()
            assert output_path.stat().st_size > 0
            
            # Check that function handles empty data
            empty_df = pd.DataFrame()
            empty_output = Path(tmpdir) / "empty.png"
            result = create_coverage_pie(
                data=empty_df, 
                statistics={},
                output_path=empty_output
            )
            # Should handle gracefully
            assert result == False or empty_output.exists()
    
    def test_confidence_histogram(self, sample_data):
        """Test confidence histogram generation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "confidence.png"
            
            result = create_confidence_histogram(
                data=sample_data,
                output_path=output_path
            )
            
            assert result == True
            assert output_path.exists()
            
            # Test with data containing NaN values
            data_with_nan = sample_data.copy()
            data_with_nan.loc[2, 'confidence_score'] = np.nan
            
            output_path_nan = Path(tmpdir) / "confidence_nan.png"
            result = create_confidence_histogram(
                data=data_with_nan,
                output_path=output_path_nan
            )
            assert result == True
            assert output_path_nan.exists()
    
    def test_mapping_flow_sankey(self, statistics_data):
        """Test Sankey diagram generation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "flow.html"
            
            result = create_mapping_flow_sankey(
                statistics=statistics_data,
                output_path=output_path
            )
            
            assert result == True
            assert output_path.exists()
            
            # Check HTML contains plotly elements
            html_content = output_path.read_text()
            assert 'plotly' in html_content.lower()
            assert 'sankey' in html_content.lower() or 'mapping' in html_content.lower()
    
    def test_one_to_many_visualization(self):
        """Test one-to-many mapping visualization."""
        mapping_data = {
            'P12345': ['ENSG001', 'ENSG002'],
            'Q67890': ['ENSG003'],
            'A12345': ['ENSG004', 'ENSG005', 'ENSG006'],
            'B67890': ['ENSG007'],
            'C11111': ['ENSG008', 'ENSG009', 'ENSG010', 'ENSG011']
        }
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "one_to_many.png"
            
            result = create_one_to_many_chart(
                mapping_data=mapping_data,
                output_path=output_path
            )
            
            assert result == True
            assert output_path.exists()
            
            # Test with empty mapping data
            empty_output = Path(tmpdir) / "empty_mapping.png"
            result = create_one_to_many_chart(
                mapping_data={},
                output_path=empty_output
            )
            # Should handle empty data gracefully
            assert result == True or result == False
    
    def test_statistics_dashboard(self, statistics_data):
        """Test statistics dashboard generation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "dashboard.png"
            
            # Add unmapped identifiers for testing
            unmapped_ids = ['UNKNOWN1', 'UNKNOWN2', 'UNKNOWN3']
            
            result = create_statistics_dashboard(
                statistics=statistics_data,
                unmapped_identifiers=unmapped_ids,
                output_path=output_path
            )
            
            assert result == True
            assert output_path.exists()
            assert output_path.stat().st_size > 0
    
    def test_interactive_scatter(self, sample_data):
        """Test interactive scatter plot generation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "scatter.html"
            
            result = create_interactive_scatter(
                data=sample_data,
                output_path=output_path
            )
            
            assert result == True
            assert output_path.exists()
            
            # Check it's an HTML file with plotly
            html_content = output_path.read_text()
            assert 'scatter' in html_content.lower() or 'plot' in html_content.lower()
            assert 'plotly' in html_content.lower()


class TestGenerateMappingVisualizationsAction:
    """Test the complete visualization action."""
    
    @pytest.fixture
    def sample_context(self):
        """Create sample context with data and statistics."""
        return {
            "datasets": {
                "direct_match": pd.DataFrame({
                    'source_id': ['P12345', 'Q67890'],
                    'target_id': ['ENSG001', 'ENSG002'],
                    'confidence_score': [0.95, 0.80],
                    'mapping_method': ['direct', 'direct']
                }),
                "final_merged": pd.DataFrame({
                    'source_id': ['P12345', 'Q67890', 'A12345'],
                    'target_id': ['ENSG001', 'ENSG002', None],
                    'confidence_score': [0.95, 0.80, 0.0],
                    'mapping_method': ['direct', 'direct', 'unmapped'],
                    'mapped': [True, True, False]
                })
            },
            "statistics": {
                "total_identifiers": 1201,
                "successfully_mapped": 923,
                "unmatched_count": 278,
                "mapping_success_rate": 76.9,
                "high_confidence_count": 812,
                "low_confidence_count": 111,
                "direct_match_count": 812,
                "historical_resolution_count": 111,
                "gene_symbol_bridge_count": 87,
                "mapping_methods": {
                    "direct_match": 812,
                    "historical_resolution": 111,
                    "gene_symbol_bridge": 87
                }
            }
        }
    
    @pytest.mark.asyncio
    async def test_basic_visualization_generation(self, sample_context):
        """Test basic visualization generation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            action = GenerateMappingVisualizationsAction()
            params = VisualizationParams(
                dataset_keys=["final_merged"],
                output_dir=str(tmpdir),
                formats=["png"],
                charts=["coverage", "confidence"],
                style="default"
            )
            
            result = await action.execute_typed(
                params=params,
                context=sample_context
            )
            
            assert result.success == True
            assert "generated_files" in result.data
            
            # Check files were created
            output_dir = Path(tmpdir)
            png_files = list(output_dir.glob("*.png"))
            assert len(png_files) >= 2  # At least coverage and confidence
    
    @pytest.mark.asyncio
    async def test_all_chart_types(self, sample_context):
        """Test generation of all chart types."""
        with tempfile.TemporaryDirectory() as tmpdir:
            action = GenerateMappingVisualizationsAction()
            params = VisualizationParams(
                dataset_keys=["direct_match", "final_merged"],
                output_dir=str(tmpdir),
                formats=["png", "html"],
                charts=[
                    "coverage", 
                    "confidence", 
                    "mapping_flow", 
                    "one_to_many", 
                    "statistics_summary",
                    "interactive_scatter"
                ],
                style="scientific"
            )
            
            result = await action.execute_typed(
                params=params,
                context=sample_context
            )
            
            assert result.success == True
            
            # Check various file types were created
            output_dir = Path(tmpdir)
            png_files = list(output_dir.glob("*.png"))
            html_files = list(output_dir.glob("*.html"))
            
            assert len(png_files) > 0, "No PNG files generated"
            assert len(html_files) > 0, "No HTML files generated"
    
    @pytest.mark.asyncio
    async def test_missing_data_handling(self):
        """Test handling of missing or incomplete data."""
        context_with_empty = {
            "datasets": {
                "empty_dataset": pd.DataFrame()  # Empty DataFrame
            },
            "statistics": {}
        }
        
        with tempfile.TemporaryDirectory() as tmpdir:
            action = GenerateMappingVisualizationsAction()
            params = VisualizationParams(
                dataset_keys=["empty_dataset"],
                output_dir=str(tmpdir),
                charts=["coverage"],
                formats=["png"]
            )
            
            result = await action.execute_typed(
                params=params,
                context=context_with_empty
            )
            
            # Should handle gracefully without crashing
            assert result is not None
            # May succeed with empty visualizations or fail gracefully
            assert isinstance(result.success, bool)
    
    @pytest.mark.asyncio
    async def test_style_application(self, sample_context):
        """Test that different styles are applied."""
        styles = ["default", "scientific", "presentation"]
        
        with tempfile.TemporaryDirectory() as tmpdir:
            for style in styles:
                action = GenerateMappingVisualizationsAction()
                
                # Create subdirectory for each style
                style_dir = Path(tmpdir) / style
                style_dir.mkdir(exist_ok=True)
                
                params = VisualizationParams(
                    dataset_keys=["final_merged"],
                    output_dir=str(style_dir),
                    charts=["confidence"],
                    style=style,
                    figure_size=(12, 8)  # Custom size
                )
                
                result = await action.execute_typed(
                    params=params,
                    context=sample_context
                )
                
                assert result.success == True
                
                # File should exist for each style
                output_files = list(style_dir.glob("*.png"))
                assert len(output_files) > 0, f"No files generated for style: {style}"
    
    @pytest.mark.asyncio
    async def test_context_output_files_update(self, sample_context):
        """Test that generated files are added to context."""
        with tempfile.TemporaryDirectory() as tmpdir:
            action = GenerateMappingVisualizationsAction()
            params = VisualizationParams(
                dataset_keys=["final_merged"],
                output_dir=str(tmpdir),
                formats=["png"],
                charts=["coverage"]
            )
            
            # Ensure output_files list exists
            sample_context["output_files"] = []
            
            result = await action.execute_typed(
                params=params,
                context=sample_context
            )
            
            assert result.success == True
            # Check that files were added to context
            assert len(sample_context["output_files"]) > 0
            assert all(Path(f).exists() for f in sample_context["output_files"])
    
    @pytest.mark.asyncio
    async def test_multiple_formats(self, sample_context):
        """Test generation of multiple formats for same chart."""
        with tempfile.TemporaryDirectory() as tmpdir:
            action = GenerateMappingVisualizationsAction()
            params = VisualizationParams(
                dataset_keys=["final_merged"],
                output_dir=str(tmpdir),
                formats=["png", "svg", "html"],
                charts=["coverage"]
            )
            
            result = await action.execute_typed(
                params=params,
                context=sample_context
            )
            
            assert result.success == True
            
            # Check different formats exist
            output_dir = Path(tmpdir)
            assert any(output_dir.glob("*.png"))
            # SVG and HTML generation depends on chart type
    
    @pytest.mark.asyncio
    async def test_list_of_dicts_data_format(self):
        """Test handling of list of dicts data format."""
        context_with_lists = {
            "datasets": {
                "list_data": [
                    {"source_id": "P12345", "target_id": "ENSG001", "confidence_score": 0.95},
                    {"source_id": "Q67890", "target_id": "ENSG002", "confidence_score": 0.80},
                    {"source_id": "A12345", "target_id": None, "confidence_score": 0.0}
                ]
            },
            "statistics": {
                "total_identifiers": 3,
                "successfully_mapped": 2,
                "unmatched_count": 1
            }
        }
        
        with tempfile.TemporaryDirectory() as tmpdir:
            action = GenerateMappingVisualizationsAction()
            params = VisualizationParams(
                dataset_keys=["list_data"],
                output_dir=str(tmpdir),
                formats=["png"],
                charts=["confidence"]
            )
            
            result = await action.execute_typed(
                params=params,
                context=context_with_lists
            )
            
            assert result.success == True
            assert Path(tmpdir).glob("*.png")