"""Unit tests for MERGE_DATASETS action."""

import pytest
import pandas as pd
from unittest.mock import Mock, MagicMock

from biomapper.core.strategy_actions.merge_datasets import (
    MergeDatasetsAction, 
    MergeDatasetsParams
)


class MockContext:
    """Mock execution context for testing."""
    
    def __init__(self):
        self._data = {}
    
    def get_action_data(self, key: str, default=None):
        """Get data from context."""
        return self._data.get(key, default)
    
    def set_action_data(self, key: str, value):
        """Set data in context."""
        self._data[key] = value


class TestMergeDatasetsAction:
    """Test suite for MERGE_DATASETS action."""
    
    @pytest.fixture
    def action(self):
        """Create a MergeDatasetsAction instance."""
        return MergeDatasetsAction()
    
    @pytest.fixture
    def mock_context(self):
        """Create a mock context with test datasets."""
        context = MockContext()
        context.set_action_data("datasets", {
            "dataset1": [
                {"id": "1", "name": "Alpha", "value": 10},
                {"id": "2", "name": "Beta", "value": 20}
            ],
            "dataset2": [
                {"id": "2", "name": "Beta", "value": 25},
                {"id": "3", "name": "Gamma", "value": 30}
            ],
            "dataset3": [
                {"id": "4", "name": "Delta", "value": 40},
                {"id": "5", "name": "Epsilon", "value": 50}
            ]
        })
        return context
    
    @pytest.mark.asyncio
    async def test_merge_two_datasets_concat(self, action, mock_context):
        """Test merging two datasets with concatenation."""
        params = MergeDatasetsParams(
            dataset_keys=["dataset1", "dataset2"],
            output_key="merged",
            merge_strategy="concat"
        )
        
        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="test",
            params=params,
            source_endpoint=None,
            target_endpoint=None,
            context=mock_context
        )
        
        # Check result
        assert result.provenance[0]["status"] == "success"
        assert result.details["datasets_merged"] == 2
        assert result.details["total_rows"] == 4
        
        # Check merged data in context
        merged_data = mock_context.get_action_data("datasets")["merged"]
        assert len(merged_data) == 4
        assert any(row["id"] == "1" for row in merged_data)
        assert any(row["id"] == "3" for row in merged_data)
    
    @pytest.mark.asyncio
    async def test_merge_with_deduplication(self, action, mock_context):
        """Test merging with deduplication on id column."""
        params = MergeDatasetsParams(
            dataset_keys=["dataset1", "dataset2"],
            output_key="merged_dedup",
            merge_strategy="concat",
            deduplication_column="id",
            keep="first"
        )
        
        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="test",
            params=params,
            source_endpoint=None,
            target_endpoint=None,
            context=mock_context
        )
        
        # Check deduplication
        assert result.provenance[0]["duplicates_removed"] == 1
        assert result.details["total_rows"] == 3
        
        # Check that id=2 appears only once with first value
        merged_data = mock_context.get_action_data("datasets")["merged_dedup"]
        id2_rows = [row for row in merged_data if row["id"] == "2"]
        assert len(id2_rows) == 1
        assert id2_rows[0]["value"] == 20  # First occurrence value
    
    @pytest.mark.asyncio
    async def test_merge_three_datasets(self, action, mock_context):
        """Test merging three datasets."""
        params = MergeDatasetsParams(
            dataset_keys=["dataset1", "dataset2", "dataset3"],
            output_key="merged_all",
            merge_strategy="concat"
        )
        
        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="test",
            params=params,
            source_endpoint=None,
            target_endpoint=None,
            context=mock_context
        )
        
        assert result.provenance[0]["status"] == "success"
        assert result.details["datasets_merged"] == 3
        assert result.details["total_rows"] == 6
    
    @pytest.mark.asyncio
    async def test_merge_with_missing_dataset(self, action, mock_context):
        """Test merging when one dataset is missing."""
        params = MergeDatasetsParams(
            dataset_keys=["dataset1", "missing_dataset", "dataset3"],
            output_key="merged_partial",
            merge_strategy="concat"
        )
        
        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="test",
            params=params,
            source_endpoint=None,
            target_endpoint=None,
            context=mock_context
        )
        
        # Should still succeed with available datasets
        assert result.provenance[0]["status"] == "success"
        assert result.provenance[0]["datasets_missing"] == ["missing_dataset"]
        assert result.details["datasets_merged"] == 2
        assert result.details["datasets_requested"] == 3
    
    @pytest.mark.asyncio
    async def test_merge_no_datasets_found(self, action, mock_context):
        """Test merging when no datasets are found."""
        params = MergeDatasetsParams(
            dataset_keys=["nonexistent1", "nonexistent2"],
            output_key="merged_none",
            merge_strategy="concat"
        )
        
        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="test",
            params=params,
            source_endpoint=None,
            target_endpoint=None,
            context=mock_context
        )
        
        # Should fail gracefully
        assert result.provenance[0]["status"] == "failed"
        assert "No datasets found" in result.provenance[0]["error"]
        assert result.details["datasets_found"] == 0
    
    @pytest.mark.asyncio
    async def test_merge_with_join_strategy(self, action, mock_context):
        """Test merging with join strategy."""
        params = MergeDatasetsParams(
            dataset_keys=["dataset1", "dataset2"],
            output_key="merged_join",
            merge_strategy="join",
            join_on="id",
            join_how="inner"
        )
        
        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="test",
            params=params,
            source_endpoint=None,
            target_endpoint=None,
            context=mock_context
        )
        
        assert result.provenance[0]["status"] == "success"
        
        # Inner join should only keep id=2
        merged_data = mock_context.get_action_data("datasets")["merged_join"]
        assert len(merged_data) == 1
        assert merged_data[0]["id"] == "2"
    
    @pytest.mark.asyncio
    async def test_merge_join_without_join_column(self, action, mock_context):
        """Test join strategy without specifying join column."""
        params = MergeDatasetsParams(
            dataset_keys=["dataset1", "dataset2"],
            output_key="merged_fail",
            merge_strategy="join"
            # Missing join_on parameter
        )
        
        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="test",
            params=params,
            source_endpoint=None,
            target_endpoint=None,
            context=mock_context
        )
        
        # Should fail with appropriate error
        assert result.provenance[0]["status"] == "failed"
        assert "join_on parameter required" in result.provenance[0]["error"]
    
    @pytest.mark.asyncio
    async def test_keep_last_duplicate(self, action, mock_context):
        """Test deduplication keeping last occurrence."""
        params = MergeDatasetsParams(
            dataset_keys=["dataset1", "dataset2"],
            output_key="merged_last",
            merge_strategy="concat",
            deduplication_column="id",
            keep="last"
        )
        
        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="test",
            params=params,
            source_endpoint=None,
            target_endpoint=None,
            context=mock_context
        )
        
        # Check that id=2 has value from dataset2 (last occurrence)
        merged_data = mock_context.get_action_data("datasets")["merged_last"]
        id2_rows = [row for row in merged_data if row["id"] == "2"]
        assert len(id2_rows) == 1
        assert id2_rows[0]["value"] == 25  # Last occurrence value
    
    @pytest.mark.asyncio
    async def test_deduplication_nonexistent_column(self, action, mock_context):
        """Test deduplication with non-existent column."""
        params = MergeDatasetsParams(
            dataset_keys=["dataset1", "dataset2"],
            output_key="merged_no_dedup",
            merge_strategy="concat",
            deduplication_column="nonexistent_column"
        )
        
        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="test",
            params=params,
            source_endpoint=None,
            target_endpoint=None,
            context=mock_context
        )
        
        # Should succeed but log warning
        assert result.provenance[0]["status"] == "success"
        assert result.details["duplicates_removed"] == 0
        assert result.details["total_rows"] == 4  # No deduplication
    
    @pytest.mark.asyncio
    async def test_empty_dataset_handling(self, action):
        """Test handling of empty datasets."""
        context = MockContext()
        context.set_action_data("datasets", {
            "empty_dataset": [],
            "valid_dataset": [{"id": "1", "name": "Test"}]
        })
        
        params = MergeDatasetsParams(
            dataset_keys=["empty_dataset", "valid_dataset"],
            output_key="merged_with_empty",
            merge_strategy="concat"
        )
        
        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="test",
            params=params,
            source_endpoint=None,
            target_endpoint=None,
            context=context
        )
        
        # Should handle empty dataset gracefully
        assert result.provenance[0]["status"] == "success"
        assert result.details["total_rows"] == 1
    
    @pytest.mark.asyncio
    async def test_outer_join(self, action, mock_context):
        """Test outer join strategy."""
        params = MergeDatasetsParams(
            dataset_keys=["dataset1", "dataset2"],
            output_key="merged_outer",
            merge_strategy="join",
            join_on="id",
            join_how="outer"
        )
        
        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="test",
            params=params,
            source_endpoint=None,
            target_endpoint=None,
            context=mock_context
        )
        
        assert result.provenance[0]["status"] == "success"
        
        # Outer join should keep all unique ids
        merged_data = mock_context.get_action_data("datasets")["merged_outer"]
        ids = [row["id"] for row in merged_data]
        assert set(ids) == {"1", "2", "3"}
    
    def test_params_model(self, action):
        """Test that params model is correctly returned."""
        assert action.get_params_model() == MergeDatasetsParams
    
    def test_params_validation(self):
        """Test parameter validation."""
        # Valid params
        params = MergeDatasetsParams(
            dataset_keys=["ds1", "ds2"],
            output_key="output"
        )
        assert params.merge_strategy == "concat"  # Default
        assert params.keep == "first"  # Default
        
        # Invalid keep value should fail
        with pytest.raises(ValueError):
            MergeDatasetsParams(
                dataset_keys=["ds1"],
                output_key="output",
                keep="invalid"
            )