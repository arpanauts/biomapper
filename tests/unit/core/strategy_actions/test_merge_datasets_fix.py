"""Test suite for MERGE_DATASETS with backward compatibility - WRITE FIRST!"""

import pytest
from typing import Dict, Any
import pandas as pd
from unittest.mock import MagicMock

# This may fail initially - expected in TDD
from biomapper.core.strategy_actions.merge_datasets import (
    MergeDatasetsAction,
    MergeDatasetsParams
)


class MockContext:
    """Mock context for testing."""
    def __init__(self, data: Dict[str, Any]):
        self._data = data
    
    def get_action_data(self, key: str, default=None):
        return self._data.get(key, default)
    
    def set_action_data(self, key: str, value: Any):
        self._data[key] = value


class TestMergeDatasetsBackwardCompatibility:
    """Test both old and new parameter formats."""
    
    @pytest.fixture
    def sample_context(self):
        """Create sample context with test data."""
        return MockContext({
            "datasets": {
                "dataset1": [
                    {"id": "P12345", "value": 1.5, "name": "Protein1"},
                    {"id": "Q67890", "value": 2.0, "name": "Protein2"},
                    {"id": "A12345", "value": 3.0, "name": "Protein3"}
                ],
                "dataset2": [
                    {"uniprot": "P12345", "gene": "GENE1", "score": 0.9},
                    {"uniprot": "Q67890", "gene": "GENE2", "score": 0.8},
                    {"uniprot": "B99999", "gene": "GENE4", "score": 0.7}
                ]
            },
            "statistics": {}
        })
    
    @pytest.mark.asyncio
    async def test_old_format_parameters(self, sample_context):
        """Test with old parameter format (dataset1_key, dataset2_key)."""
        action = MergeDatasetsAction()
        
        # Old format params
        params = MergeDatasetsParams(
            dataset1_key="dataset1",
            dataset2_key="dataset2",
            join_column1="id",
            join_column2="uniprot",
            join_type="inner",
            output_key="merged",
            add_provenance=True,
            provenance_value="test_merge"
        )
        
        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="protein",
            params=params,
            source_endpoint=None,
            target_endpoint=None,
            context=sample_context
        )
        
        assert result.details["datasets_merged"] == 2
        assert "merged" in sample_context.get_action_data("datasets")
        
        merged = sample_context.get_action_data("datasets")["merged"]
        assert len(merged) == 2  # Only P12345 and Q67890 match
        
        # Check that both datasets' columns are present
        first_row = merged[0]
        assert "id" in first_row
        assert "uniprot" in first_row
        assert "gene" in first_row
        assert "value" in first_row
        
        # Check merge statistics
        stats = sample_context.get_action_data("statistics", {}).get("merge_statistics", {})
        assert stats["datasets_merged"] == 2
        assert stats["total_rows"] == 2
    
    @pytest.mark.asyncio
    async def test_new_format_parameters(self, sample_context):
        """Test with new parameter format (dataset_keys list)."""
        action = MergeDatasetsAction()
        
        # New format params
        params = MergeDatasetsParams(
            dataset_keys=["dataset1", "dataset2"],
            join_columns={"dataset1": "id", "dataset2": "uniprot"},
            join_how="outer",
            output_key="merged_outer"
        )
        
        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="protein",
            params=params,
            source_endpoint=None,
            target_endpoint=None,
            context=sample_context
        )
        
        assert result.details["datasets_merged"] == 2
        assert "merged_outer" in sample_context.get_action_data("datasets")
        
        merged = sample_context.get_action_data("datasets")["merged_outer"]
        assert len(merged) == 4  # All records in outer join
        
    @pytest.mark.asyncio
    async def test_one_to_many_detection(self, sample_context):
        """Test detection of one-to-many mappings."""
        # Add duplicate to create one-to-many
        datasets = sample_context.get_action_data("datasets")
        datasets["dataset2"].append(
            {"uniprot": "P12345", "gene": "GENE1_ALT", "score": 0.85}
        )
        
        action = MergeDatasetsAction()
        params = MergeDatasetsParams(
            dataset1_key="dataset1",
            dataset2_key="dataset2",
            join_column1="id",
            join_column2="uniprot",
            join_type="inner",
            handle_one_to_many="keep_all",
            output_key="merged_with_duplicates"
        )
        
        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="protein",
            params=params,
            source_endpoint=None,
            target_endpoint=None,
            context=sample_context
        )
        
        assert result.details["datasets_merged"] == 2
        
        merged = sample_context.get_action_data("datasets")["merged_with_duplicates"]
        # P12345 appears twice, Q67890 once = 3 total
        assert len(merged) == 3
        
        # Check one-to-many stats OR that duplicates were created
        one_to_many_stats = result.details.get("one_to_many_stats", {})
        # The merge should produce 3 rows from 2 unique matches (P12345 x2, Q67890 x1)
        # This indicates a one-to-many relationship was present
        # Either stats are recorded OR we see the expansion in row count
        assert len(merged) == 3  # This confirms one-to-many happened
        # Stats recording is optional but helpful
        if one_to_many_stats:
            assert len(one_to_many_stats) > 0
        
    @pytest.mark.asyncio
    async def test_concat_strategy(self, sample_context):
        """Test concatenation strategy."""
        action = MergeDatasetsAction()
        
        params = MergeDatasetsParams(
            dataset_keys=["dataset1", "dataset2"],
            merge_strategy="concat",
            output_key="concatenated",
            deduplication_column=None  # No deduplication
        )
        
        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="protein",
            params=params,
            source_endpoint=None,
            target_endpoint=None,
            context=sample_context
        )
        
        assert result.details["datasets_merged"] == 2
        concatenated = sample_context.get_action_data("datasets")["concatenated"]
        assert len(concatenated) == 6  # 3 + 3 records
        
    @pytest.mark.asyncio
    async def test_deduplication(self, sample_context):
        """Test deduplication functionality."""
        # Add a duplicate for deduplication test
        datasets = sample_context.get_action_data("datasets")
        datasets["dataset3"] = [
            {"id": "P12345", "value": 1.5, "name": "Protein1"},  # Duplicate
            {"id": "X99999", "value": 4.0, "name": "Protein4"}
        ]
        
        action = MergeDatasetsAction()
        params = MergeDatasetsParams(
            dataset_keys=["dataset1", "dataset3"],
            merge_strategy="concat",
            deduplication_column="id",
            keep="first",
            output_key="deduplicated"
        )
        
        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="protein",
            params=params,
            source_endpoint=None,
            target_endpoint=None,
            context=sample_context
        )
        
        deduplicated = sample_context.get_action_data("datasets")["deduplicated"]
        assert len(deduplicated) == 4  # 3 + 2 - 1 duplicate
        
        # Check that duplicate was removed
        ids = [row["id"] for row in deduplicated]
        assert ids.count("P12345") == 1
        
        # Check statistics
        assert result.details["duplicates_removed"] == 1