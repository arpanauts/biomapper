"""
Unit tests for ResultsSaver strategy action.
"""

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

import pandas as pd
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from biomapper.core.exceptions import MappingExecutionError
from biomapper.core.strategy_actions.results_saver import ResultsSaver
from biomapper.db.models import Endpoint


class TestResultsSaver:
    """Test cases for ResultsSaver action."""
    
    @pytest.fixture
    def mock_session(self):
        """Create a mock database session."""
        return Mock(spec=AsyncSession)
    
    @pytest.fixture
    def mock_endpoints(self):
        """Create mock source and target endpoints."""
        source = Mock(spec=Endpoint)
        source.name = "TestSource"
        target = Mock(spec=Endpoint)
        target.name = "TestTarget"
        return source, target
    
    @pytest.fixture
    def action(self, mock_session):
        """Create a ResultsSaver instance."""
        return ResultsSaver(session=mock_session)
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test outputs."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir
    
    async def test_save_list_of_dicts_as_csv(self, action, mock_endpoints, temp_dir):
        """Test saving a list of dictionaries as CSV."""
        # Prepare test data
        test_data = [
            {"id": "P12345", "name": "Protein1", "score": 0.95},
            {"id": "P67890", "name": "Protein2", "score": 0.87},
            {"id": "Q11111", "name": "Protein3", "score": 0.92}
        ]
        
        context = {"mapping_results": test_data}
        action_params = {
            "input_context_key": "mapping_results",
            "output_directory": temp_dir,
            "filename": "test_results",
            "format": "csv"
        }
        
        # Execute the action
        source, target = mock_endpoints
        result = await action.execute(
            current_identifiers=["P12345", "P67890"],
            current_ontology_type="uniprot",
            action_params=action_params,
            source_endpoint=source,
            target_endpoint=target,
            context=context
        )
        
        # Verify the result
        assert result['details']['status'] == 'success'
        assert result['details']['format'] == 'csv'
        assert result['details']['rows_saved'] == 3
        
        # Check the saved file
        csv_path = result['details']['file_path']
        assert os.path.exists(csv_path)
        
        # Read and verify CSV content
        df = pd.read_csv(csv_path)
        assert len(df) == 3
        assert list(df.columns) == ["id", "name", "score"]
        assert df.iloc[0]["id"] == "P12345"
        
        # Check context was updated
        assert context["mapping_results_saved_path"] == csv_path
    
    async def test_save_dataframe_as_csv(self, action, mock_endpoints, temp_dir):
        """Test saving a pandas DataFrame as CSV."""
        # Prepare test data
        test_df = pd.DataFrame({
            "source_id": ["A", "B", "C"],
            "target_id": ["X", "Y", "Z"],
            "confidence": [0.9, 0.8, 0.95]
        })
        
        context = {"df_data": test_df}
        action_params = {
            "input_context_key": "df_data",
            "output_directory": temp_dir,
            "filename": "dataframe_test",
            "format": "csv"
        }
        
        # Execute the action
        source, target = mock_endpoints
        result = await action.execute(
            current_identifiers=[],
            current_ontology_type="test",
            action_params=action_params,
            source_endpoint=source,
            target_endpoint=target,
            context=context
        )
        
        # Verify the result
        assert result['details']['status'] == 'success'
        assert result['details']['rows_saved'] == 3
        
        # Verify saved content
        saved_df = pd.read_csv(result['details']['file_path'])
        pd.testing.assert_frame_equal(saved_df, test_df)
    
    async def test_save_as_json(self, action, mock_endpoints, temp_dir):
        """Test saving data as JSON."""
        # Prepare test data
        test_data = {
            "mappings": [
                {"from": "A", "to": "X"},
                {"from": "B", "to": "Y"}
            ],
            "metadata": {
                "version": "1.0",
                "date": "2024-01-01"
            }
        }
        
        context = {"json_data": test_data}
        action_params = {
            "input_context_key": "json_data",
            "output_directory": temp_dir,
            "filename": "test_output",
            "format": "json"
        }
        
        # Execute the action
        source, target = mock_endpoints
        result = await action.execute(
            current_identifiers=[],
            current_ontology_type="test",
            action_params=action_params,
            source_endpoint=source,
            target_endpoint=target,
            context=context
        )
        
        # Verify the result
        assert result['details']['status'] == 'success'
        assert result['details']['format'] == 'json'
        
        # Check the saved file
        json_path = result['details']['file_path']
        assert os.path.exists(json_path)
        
        # Read and verify JSON content
        with open(json_path) as f:
            saved_data = json.load(f)
        assert saved_data == test_data
    
    async def test_csv_with_summary(self, action, mock_endpoints, temp_dir):
        """Test creating a summary file when saving CSV."""
        # Prepare test data with numeric columns
        test_data = [
            {"id": "A", "value": 10, "score": 0.8},
            {"id": "B", "value": 20, "score": 0.9},
            {"id": "C", "value": 15, "score": 0.85}
        ]
        
        context = {"data": test_data}
        action_params = {
            "input_context_key": "data",
            "output_directory": temp_dir,
            "filename": "with_summary",
            "format": "csv",
            "create_summary": True
        }
        
        # Execute the action
        source, target = mock_endpoints
        result = await action.execute(
            current_identifiers=[],
            current_ontology_type="test",
            action_params=action_params,
            source_endpoint=source,
            target_endpoint=target,
            context=context
        )
        
        # Verify summary was created
        assert result['details']['summary_path'] is not None
        summary_path = result['details']['summary_path']
        assert os.path.exists(summary_path)
        
        # Check summary content
        with open(summary_path) as f:
            summary = json.load(f)
        
        assert summary['format'] == 'csv'
        assert summary['statistics']['total_rows'] == 3
        assert summary['statistics']['columns_count'] == 3
        assert 'numeric_statistics' in summary
        assert 'value' in summary['numeric_statistics']
        assert summary['numeric_statistics']['value']['mean'] == 15.0
    
    async def test_timestamp_in_filename(self, action, mock_endpoints, temp_dir):
        """Test including timestamp in filename."""
        context = {"data": [{"id": 1}]}
        action_params = {
            "input_context_key": "data",
            "output_directory": temp_dir,
            "filename": "timestamped",
            "format": "csv",
            "include_timestamp": True
        }
        
        # Execute the action
        source, target = mock_endpoints
        result = await action.execute(
            current_identifiers=[],
            current_ontology_type="test",
            action_params=action_params,
            source_endpoint=source,
            target_endpoint=target,
            context=context
        )
        
        # Check that filename contains timestamp
        filename = os.path.basename(result['details']['file_path'])
        assert "timestamped_" in filename
        assert filename.endswith(".csv")
        # Check timestamp format (YYYYMMDD_HHMMSS)
        parts = filename.split("_")
        assert len(parts) >= 3  # timestamped_YYYYMMDD_HHMMSS.csv
    
    async def test_ensure_unique_filename(self, action, mock_endpoints, temp_dir):
        """Test ensuring unique filename to prevent overwriting."""
        context = {"data": [{"id": 1}]}
        action_params = {
            "input_context_key": "data",
            "output_directory": temp_dir,
            "filename": "duplicate",
            "format": "csv",
            "ensure_unique": True
        }
        
        # Create a file that would conflict
        existing_file = os.path.join(temp_dir, "duplicate.csv")
        Path(existing_file).touch()
        
        # Execute the action
        source, target = mock_endpoints
        result = await action.execute(
            current_identifiers=[],
            current_ontology_type="test",
            action_params=action_params,
            source_endpoint=source,
            target_endpoint=target,
            context=context
        )
        
        # Check that a different filename was used
        saved_path = result['details']['file_path']
        assert saved_path != existing_file
        assert "duplicate_1.csv" in saved_path
    
    async def test_environment_variable_expansion(self, action, mock_endpoints, temp_dir):
        """Test expanding environment variables in output directory."""
        # Set a test environment variable
        os.environ['TEST_OUTPUT_DIR'] = temp_dir
        
        context = {"data": [{"id": 1}]}
        action_params = {
            "input_context_key": "data",
            "output_directory": "${TEST_OUTPUT_DIR}/results",
            "filename": "env_test",
            "format": "csv"
        }
        
        try:
            # Execute the action
            source, target = mock_endpoints
            result = await action.execute(
                current_identifiers=[],
                current_ontology_type="test",
                action_params=action_params,
                source_endpoint=source,
                target_endpoint=target,
                context=context
            )
            
            # Verify the file was saved in the correct location
            expected_dir = os.path.join(temp_dir, "results")
            assert os.path.dirname(result['details']['file_path']) == expected_dir
            assert os.path.exists(result['details']['file_path'])
            
        finally:
            # Clean up environment variable
            del os.environ['TEST_OUTPUT_DIR']
    
    async def test_missing_data_warning(self, action, mock_endpoints, temp_dir):
        """Test handling when no data is found at the specified key."""
        context = {"other_key": "data"}
        action_params = {
            "input_context_key": "missing_key",
            "output_directory": temp_dir,
            "filename": "test",
            "format": "csv"
        }
        
        # Execute the action
        source, target = mock_endpoints
        result = await action.execute(
            current_identifiers=["A", "B"],
            current_ontology_type="test",
            action_params=action_params,
            source_endpoint=source,
            target_endpoint=target,
            context=context
        )
        
        # Verify warning response
        assert result['details']['status'] == 'no_data'
        assert 'No data found' in result['details']['message']
        # Identifiers should be passed through unchanged
        assert result['output_identifiers'] == ["A", "B"]
        assert result['output_ontology_type'] == "test"
    
    async def test_permission_error_handling(self, action, mock_endpoints):
        """Test handling permission errors when writing files."""
        context = {"data": [{"id": 1}]}
        action_params = {
            "input_context_key": "data",
            "output_directory": "/root/forbidden",  # Likely to cause permission error
            "filename": "test",
            "format": "csv"
        }
        
        # Execute the action and expect an error
        source, target = mock_endpoints
        with pytest.raises(MappingExecutionError) as exc_info:
            await action.execute(
                current_identifiers=[],
                current_ontology_type="test",
                action_params=action_params,
                source_endpoint=source,
                target_endpoint=target,
                context=context
            )
        
        assert "Permission denied" in str(exc_info.value) or "Failed to save results" in str(exc_info.value)
    
    async def test_invalid_format_error(self, action, mock_endpoints, temp_dir):
        """Test error handling for invalid format specification."""
        context = {"data": [{"id": 1}]}
        action_params = {
            "input_context_key": "data",
            "output_directory": temp_dir,
            "filename": "test",
            "format": "xml"  # Unsupported format
        }
        
        # Execute the action and expect an error
        source, target = mock_endpoints
        with pytest.raises(ValueError) as exc_info:
            await action.execute(
                current_identifiers=[],
                current_ontology_type="test",
                action_params=action_params,
                source_endpoint=source,
                target_endpoint=target,
                context=context
            )
        
        assert "Unsupported format: xml" in str(exc_info.value)
    
    async def test_missing_required_parameters(self, action, mock_endpoints):
        """Test validation of required parameters."""
        context = {"data": [{"id": 1}]}
        source, target = mock_endpoints
        
        # Test missing input_context_key
        with pytest.raises(ValueError) as exc_info:
            await action.execute(
                current_identifiers=[],
                current_ontology_type="test",
                action_params={"output_directory": "/tmp", "filename": "test"},
                source_endpoint=source,
                target_endpoint=target,
                context=context
            )
        assert "input_context_key is required" in str(exc_info.value)
        
        # Test missing output_directory
        with pytest.raises(ValueError) as exc_info:
            await action.execute(
                current_identifiers=[],
                current_ontology_type="test",
                action_params={"input_context_key": "data", "filename": "test"},
                source_endpoint=source,
                target_endpoint=target,
                context=context
            )
        assert "output_directory is required" in str(exc_info.value)
        
        # Test missing filename
        with pytest.raises(ValueError) as exc_info:
            await action.execute(
                current_identifiers=[],
                current_ontology_type="test",
                action_params={"input_context_key": "data", "output_directory": "/tmp"},
                source_endpoint=source,
                target_endpoint=target,
                context=context
            )
        assert "filename is required" in str(exc_info.value)
    
    async def test_complex_nested_json(self, action, mock_endpoints, temp_dir):
        """Test saving complex nested data structures as JSON."""
        complex_data = {
            "results": {
                "forward": [{"id": "A", "matches": ["X", "Y"]}],
                "reverse": [{"id": "X", "matches": ["A", "B"]}]
            },
            "statistics": {
                "total": 100,
                "matched": 85,
                "confidence_scores": [0.9, 0.85, 0.92]
            }
        }
        
        context = {"complex": complex_data}
        action_params = {
            "input_context_key": "complex",
            "output_directory": temp_dir,
            "filename": "complex_data",
            "format": "json"
        }
        
        # Execute the action
        source, target = mock_endpoints
        result = await action.execute(
            current_identifiers=[],
            current_ontology_type="test",
            action_params=action_params,
            source_endpoint=source,
            target_endpoint=target,
            context=context
        )
        
        # Verify the saved data
        with open(result['details']['file_path']) as f:
            saved_data = json.load(f)
        assert saved_data == complex_data