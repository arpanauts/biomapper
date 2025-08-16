# Implementation Prompt 1: Parse Composite Identifiers Action

## 🎯 Mission
Implement the `PARSE_COMPOSITE_IDENTIFIERS` action that handles comma-separated biological identifiers (e.g., "Q8NEV9,Q14213") by expanding them into separate rows while tracking the expansion factor.

## 📍 Context
You are implementing a critical data preprocessing action for the biomapper project. This action must handle composite identifiers that appear in biological datasets where multiple IDs are stored in a single field.

## 📁 Files to Create/Modify

### 1. Test File (CREATE FIRST - TDD!)
**Path:** `/home/ubuntu/biomapper/tests/unit/core/strategy_actions/utils/data_processing/test_parse_composite_identifiers.py`

```python
"""Test suite for ParseCompositeIdentifiersAction - WRITE THIS FIRST!"""

import pytest
from typing import Dict, Any, List
import pandas as pd
from unittest.mock import MagicMock

# This import will fail initially - that's expected in TDD!
from biomapper.core.strategy_actions.utils.data_processing.parse_composite_identifiers import (
    ParseCompositeIdentifiersAction,
    ParseCompositeIdentifiersParams,
    ParseCompositeIdentifiersResult
)


class TestParseCompositeIdentifiersAction:
    """Comprehensive test suite for composite identifier parsing."""
    
    @pytest.fixture
    def sample_context(self) -> Dict[str, Any]:
        """Create sample context with composite identifiers."""
        return {
            "datasets": {
                "proteins": [
                    {"uniprot": "P12345", "name": "Protein1", "value": 1.5},
                    {"uniprot": "Q67890,Q11111", "name": "Protein2", "value": 2.0},
                    {"uniprot": "A12345;B67890;C99999", "name": "Protein3", "value": 3.0},
                    {"uniprot": "D55555|E66666", "name": "Protein4", "value": 4.0},
                    {"uniprot": "F77777", "name": "Protein5", "value": 5.0},
                    {"uniprot": "", "name": "Empty", "value": 0.0},
                    {"uniprot": None, "name": "Null", "value": -1.0}
                ]
            },
            "statistics": {},
            "output_files": {}
        }
    
    @pytest.fixture
    def action(self) -> ParseCompositeIdentifiersAction:
        """Create action instance."""
        return ParseCompositeIdentifiersAction()
    
    @pytest.mark.asyncio
    async def test_basic_comma_separation(self, action, sample_context):
        """Test parsing comma-separated identifiers."""
        params = ParseCompositeIdentifiersParams(
            dataset_key="proteins",
            id_field="uniprot",
            separators=[","],
            output_key="proteins_expanded",
            track_expansion=True
        )
        
        result = await action.execute_typed(params, sample_context)
        
        assert result.success is True
        assert "proteins_expanded" in sample_context["datasets"]
        
        expanded = sample_context["datasets"]["proteins_expanded"]
        
        # Check Q67890,Q11111 was expanded to 2 rows
        q_rows = [r for r in expanded if r["uniprot"] in ["Q67890", "Q11111"]]
        assert len(q_rows) == 2
        
        # Both rows should preserve other fields
        for row in q_rows:
            assert row["name"] == "Protein2"
            assert row["value"] == 2.0
            assert row.get("_original_composite") == "Q67890,Q11111"
            assert row.get("_expansion_count") == 2
    
    @pytest.mark.asyncio
    async def test_multiple_separators(self, action, sample_context):
        """Test handling multiple separator types."""
        params = ParseCompositeIdentifiersParams(
            dataset_key="proteins",
            id_field="uniprot",
            separators=[",", ";", "|"],
            output_key="proteins_multi_sep"
        )
        
        result = await action.execute_typed(params, sample_context)
        
        assert result.success is True
        expanded = sample_context["datasets"]["proteins_multi_sep"]
        
        # Count total rows (should expand all composite IDs)
        assert len(expanded) == 10  # 1 + 2 + 3 + 2 + 1 + 1 + 1
        
        # Check semicolon separation
        semicolon_rows = [r for r in expanded if r.get("_original_composite") == "A12345;B67890;C99999"]
        assert len(semicolon_rows) == 3
        assert set(r["uniprot"] for r in semicolon_rows) == {"A12345", "B67890", "C99999"}
        
        # Check pipe separation
        pipe_rows = [r for r in expanded if r.get("_original_composite") == "D55555|E66666"]
        assert len(pipe_rows) == 2
    
    @pytest.mark.asyncio
    async def test_empty_and_null_handling(self, action, sample_context):
        """Test proper handling of empty and null values."""
        params = ParseCompositeIdentifiersParams(
            dataset_key="proteins",
            id_field="uniprot",
            separators=[","],
            output_key="proteins_clean",
            skip_empty=True
        )
        
        result = await action.execute_typed(params, sample_context)
        
        expanded = sample_context["datasets"]["proteins_clean"]
        
        # Should skip empty and None values
        assert all(r["uniprot"] for r in expanded if r["name"] not in ["Empty", "Null"])
        
        # Empty/Null rows should be preserved but marked
        empty_rows = [r for r in expanded if r["name"] in ["Empty", "Null"]]
        assert len(empty_rows) == 2
        for row in empty_rows:
            assert row.get("_skipped", False) is True
    
    @pytest.mark.asyncio
    async def test_expansion_statistics(self, action, sample_context):
        """Test that expansion statistics are tracked correctly."""
        params = ParseCompositeIdentifiersParams(
            dataset_key="proteins",
            id_field="uniprot",
            separators=[",", ";", "|"],
            output_key="proteins_stats",
            track_expansion=True
        )
        
        result = await action.execute_typed(params, sample_context)
        
        # Check statistics were recorded
        assert "composite_expansion" in sample_context["statistics"]
        stats = sample_context["statistics"]["composite_expansion"]
        
        assert stats["total_input_rows"] == 7
        assert stats["total_output_rows"] == 10
        assert stats["expansion_factor"] == pytest.approx(10/7, rel=0.01)
        assert stats["rows_with_composites"] == 3
        assert stats["max_components"] == 3  # A12345;B67890;C99999
        
        # Check result object
        assert result.rows_processed == 7
        assert result.rows_expanded == 10
        assert result.composite_count == 3
    
    @pytest.mark.asyncio
    async def test_custom_separator_with_trim(self, action, sample_context):
        """Test custom separator with whitespace trimming."""
        # Add data with spaces
        sample_context["datasets"]["spaced"] = [
            {"ids": "A123 , B456 , C789", "type": "test"}
        ]
        
        params = ParseCompositeIdentifiersParams(
            dataset_key="spaced",
            id_field="ids",
            separators=[","],
            output_key="spaced_clean",
            trim_whitespace=True
        )
        
        result = await action.execute_typed(params, sample_context)
        
        expanded = sample_context["datasets"]["spaced_clean"]
        assert len(expanded) == 3
        assert expanded[0]["ids"] == "A123"  # Trimmed
        assert expanded[1]["ids"] == "B456"  # Trimmed
        assert expanded[2]["ids"] == "C789"  # Trimmed
    
    @pytest.mark.asyncio
    async def test_preserve_row_order(self, action, sample_context):
        """Test that row order and indices are preserved."""
        params = ParseCompositeIdentifiersParams(
            dataset_key="proteins",
            id_field="uniprot",
            separators=[","],
            output_key="proteins_ordered",
            preserve_order=True
        )
        
        result = await action.execute_typed(params, sample_context)
        
        expanded = sample_context["datasets"]["proteins_ordered"]
        
        # Check that original row indices are preserved
        for row in expanded:
            if "_original_index" in row:
                assert isinstance(row["_original_index"], int)
                assert 0 <= row["_original_index"] < 7
    
    @pytest.mark.asyncio
    async def test_error_handling(self, action):
        """Test error handling for invalid inputs."""
        # Test missing dataset
        context = {"datasets": {}}
        params = ParseCompositeIdentifiersParams(
            dataset_key="nonexistent",
            id_field="id",
            output_key="output"
        )
        
        result = await action.execute_typed(params, context)
        
        assert result.success is False
        assert "not found" in result.message.lower()
        
        # Test missing field
        context = {"datasets": {"data": [{"other": "value"}]}}
        params = ParseCompositeIdentifiersParams(
            dataset_key="data",
            id_field="missing_field",
            output_key="output"
        )
        
        result = await action.execute_typed(params, context)
        
        assert result.success is False
        assert "field" in result.message.lower()
    
    @pytest.mark.asyncio
    async def test_context_compatibility(self, action):
        """Test handling of different context types."""
        # Test with dict context
        dict_context = {
            "datasets": {"test": [{"id": "A,B"}]},
            "statistics": {}
        }
        
        params = ParseCompositeIdentifiersParams(
            dataset_key="test",
            id_field="id",
            output_key="expanded"
        )
        
        result = await action.execute_typed(params, dict_context)
        assert result.success is True
        
        # Test with MockContext
        from biomapper.core.strategy_actions.typed_base import MockContext
        mock_context = MockContext(dict_context)
        
        result = await action.execute_typed(params, mock_context)
        assert result.success is True
    
    @pytest.mark.asyncio
    async def test_large_dataset_performance(self, action):
        """Test performance with larger dataset."""
        # Create dataset with 1000 rows, 30% having composite IDs
        import random
        large_data = []
        for i in range(1000):
            if random.random() < 0.3:
                # Composite ID
                num_components = random.randint(2, 5)
                ids = ",".join(f"ID{i}_{j}" for j in range(num_components))
            else:
                # Single ID
                ids = f"ID{i}"
            large_data.append({"identifier": ids, "value": i})
        
        context = {"datasets": {"large": large_data}, "statistics": {}}
        
        params = ParseCompositeIdentifiersParams(
            dataset_key="large",
            id_field="identifier",
            separators=[","],
            output_key="large_expanded",
            track_expansion=True
        )
        
        import time
        start = time.time()
        result = await action.execute_typed(params, context)
        elapsed = time.time() - start
        
        assert result.success is True
        assert elapsed < 1.0  # Should process 1000 rows in under 1 second
        
        # Verify expansion worked
        expanded = context["datasets"]["large_expanded"]
        assert len(expanded) > 1000  # Should have expanded some rows
```

### 2. Implementation File (CREATE AFTER TESTS)
**Path:** `/home/ubuntu/biomapper/biomapper/core/strategy_actions/utils/data_processing/parse_composite_identifiers.py`

```python
"""Parse composite identifiers into separate rows."""

import logging
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
import pandas as pd

from biomapper.core.strategy_actions.typed_base import TypedStrategyAction
from biomapper.core.strategy_actions.registry import register_action

logger = logging.getLogger(__name__)


class ParseCompositeIdentifiersParams(BaseModel):
    """Parameters for parsing composite identifiers."""
    
    dataset_key: str = Field(..., description="Input dataset key")
    id_field: str = Field(..., description="Field containing identifiers")
    separators: List[str] = Field(
        default=[","],
        description="List of separators to split on"
    )
    output_key: str = Field(..., description="Output dataset key")
    track_expansion: bool = Field(
        default=False,
        description="Track expansion statistics"
    )
    skip_empty: bool = Field(
        default=False,
        description="Skip empty/null values"
    )
    trim_whitespace: bool = Field(
        default=True,
        description="Trim whitespace from parsed IDs"
    )
    preserve_order: bool = Field(
        default=True,
        description="Preserve original row order with indices"
    )


class ParseCompositeIdentifiersResult(BaseModel):
    """Result of parsing composite identifiers."""
    
    success: bool
    message: str
    rows_processed: int = 0
    rows_expanded: int = 0
    composite_count: int = 0
    expansion_factor: float = 1.0


@register_action("PARSE_COMPOSITE_IDENTIFIERS")
class ParseCompositeIdentifiersAction(TypedStrategyAction[ParseCompositeIdentifiersParams, ParseCompositeIdentifiersResult]):
    """
    Parse composite identifiers into separate rows.
    
    Handles comma-separated and other delimited identifiers by expanding
    them into multiple rows while preserving all other fields.
    """
    
    def get_params_model(self) -> type[ParseCompositeIdentifiersParams]:
        """Get the parameters model."""
        return ParseCompositeIdentifiersParams
    
    def get_result_model(self) -> type[ParseCompositeIdentifiersResult]:
        """Get the result model."""
        return ParseCompositeIdentifiersResult
    
    async def execute_typed(
        self,
        params: ParseCompositeIdentifiersParams,
        context: Dict[str, Any]
    ) -> ParseCompositeIdentifiersResult:
        """Execute the composite identifier parsing."""
        try:
            # Handle different context types
            ctx = self._get_context_dict(context)
            
            # Get input data
            if params.dataset_key not in ctx.get("datasets", {}):
                return ParseCompositeIdentifiersResult(
                    success=False,
                    message=f"Dataset '{params.dataset_key}' not found in context"
                )
            
            input_data = ctx["datasets"][params.dataset_key]
            
            if not input_data:
                return ParseCompositeIdentifiersResult(
                    success=False,
                    message="Input dataset is empty"
                )
            
            # Convert to DataFrame for easier processing
            df = pd.DataFrame(input_data)
            
            # Check if field exists
            if params.id_field not in df.columns:
                return ParseCompositeIdentifiersResult(
                    success=False,
                    message=f"Field '{params.id_field}' not found in dataset"
                )
            
            # Process the data
            expanded_df = self._expand_composite_ids(df, params)
            
            # Calculate statistics
            rows_processed = len(df)
            rows_expanded = len(expanded_df)
            composite_count = self._count_composites(df, params)
            expansion_factor = rows_expanded / rows_processed if rows_processed > 0 else 1.0
            
            # Track statistics if requested
            if params.track_expansion:
                self._track_statistics(ctx, df, expanded_df, params, composite_count)
            
            # Store result
            ctx["datasets"][params.output_key] = expanded_df.to_dict("records")
            
            logger.info(
                f"Expanded {rows_processed} rows to {rows_expanded} rows "
                f"(expansion factor: {expansion_factor:.2f})"
            )
            
            return ParseCompositeIdentifiersResult(
                success=True,
                message=f"Successfully parsed composite identifiers",
                rows_processed=rows_processed,
                rows_expanded=rows_expanded,
                composite_count=composite_count,
                expansion_factor=expansion_factor
            )
            
        except Exception as e:
            logger.error(f"Error parsing composite identifiers: {str(e)}")
            return ParseCompositeIdentifiersResult(
                success=False,
                message=f"Error: {str(e)}"
            )
    
    def _get_context_dict(self, context: Any) -> Dict[str, Any]:
        """Get dictionary from context, handling different types."""
        if isinstance(context, dict):
            return context
        elif hasattr(context, '_dict'):  # MockContext
            return context._dict
        else:
            # Try to adapt other context types
            return {"datasets": {}, "statistics": {}}
    
    def _expand_composite_ids(self, df: pd.DataFrame, params: ParseCompositeIdentifiersParams) -> pd.DataFrame:
        """Expand rows with composite identifiers."""
        expanded_rows = []
        
        for idx, row in df.iterrows():
            id_value = row[params.id_field]
            
            # Handle empty/null values
            if pd.isna(id_value) or id_value == "":
                if params.skip_empty:
                    row_dict = row.to_dict()
                    row_dict["_skipped"] = True
                    expanded_rows.append(row_dict)
                else:
                    expanded_rows.append(row.to_dict())
                continue
            
            # Parse composite IDs
            id_str = str(id_value)
            components = self._split_by_separators(id_str, params.separators)
            
            if params.trim_whitespace:
                components = [c.strip() for c in components]
            
            # Create a row for each component
            if len(components) > 1:
                # Composite ID - expand
                for component in components:
                    row_dict = row.to_dict()
                    row_dict[params.id_field] = component
                    row_dict["_original_composite"] = id_str
                    row_dict["_expansion_count"] = len(components)
                    if params.preserve_order:
                        row_dict["_original_index"] = idx
                    expanded_rows.append(row_dict)
            else:
                # Single ID - keep as is
                row_dict = row.to_dict()
                if params.preserve_order:
                    row_dict["_original_index"] = idx
                expanded_rows.append(row_dict)
        
        return pd.DataFrame(expanded_rows)
    
    def _split_by_separators(self, text: str, separators: List[str]) -> List[str]:
        """Split text by multiple separators."""
        # Start with the text as a single item
        parts = [text]
        
        # Split by each separator in sequence
        for separator in separators:
            new_parts = []
            for part in parts:
                new_parts.extend(part.split(separator))
            parts = new_parts
        
        # Remove empty strings
        return [p for p in parts if p]
    
    def _count_composites(self, df: pd.DataFrame, params: ParseCompositeIdentifiersParams) -> int:
        """Count rows with composite identifiers."""
        count = 0
        
        for _, row in df.iterrows():
            id_value = row[params.id_field]
            if pd.notna(id_value) and id_value != "":
                id_str = str(id_value)
                components = self._split_by_separators(id_str, params.separators)
                if len(components) > 1:
                    count += 1
        
        return count
    
    def _track_statistics(
        self,
        context: Dict[str, Any],
        original_df: pd.DataFrame,
        expanded_df: pd.DataFrame,
        params: ParseCompositeIdentifiersParams,
        composite_count: int
    ):
        """Track expansion statistics in context."""
        # Calculate max components
        max_components = 1
        for _, row in original_df.iterrows():
            id_value = row[params.id_field]
            if pd.notna(id_value) and id_value != "":
                components = self._split_by_separators(str(id_value), params.separators)
                max_components = max(max_components, len(components))
        
        # Store statistics
        if "statistics" not in context:
            context["statistics"] = {}
        
        context["statistics"]["composite_expansion"] = {
            "dataset_key": params.dataset_key,
            "field": params.id_field,
            "total_input_rows": len(original_df),
            "total_output_rows": len(expanded_df),
            "rows_with_composites": composite_count,
            "expansion_factor": len(expanded_df) / len(original_df) if len(original_df) > 0 else 1.0,
            "max_components": max_components,
            "separators_used": params.separators
        }
```

### 3. Run Tests and Iterate
```bash
# Step 1: Run tests (will fail initially)
poetry run pytest tests/unit/core/strategy_actions/utils/data_processing/test_parse_composite_identifiers.py -xvs

# Step 2: Fix any import errors
# Step 3: Implement minimal code to pass first test
# Step 4: Run tests again
# Step 5: Implement more functionality
# Step 6: Repeat until all tests pass

# Step 7: Check coverage
poetry run pytest tests/unit/core/strategy_actions/utils/data_processing/test_parse_composite_identifiers.py --cov=biomapper.core.strategy_actions.utils.data_processing.parse_composite_identifiers --cov-report=term-missing

# Step 8: Run integration test with actual strategy
poetry run pytest tests/integration/ -k composite
```

## 📋 Acceptance Criteria

1. ✅ All tests pass (100% pass rate)
2. ✅ Code coverage > 90%
3. ✅ Handles all separator types (comma, semicolon, pipe)
4. ✅ Preserves all other fields when expanding
5. ✅ Tracks expansion statistics
6. ✅ Handles empty/null values gracefully
7. ✅ Works with both dict and MockContext
8. ✅ Performance: processes 1000 rows in < 1 second
9. ✅ Proper logging of operations
10. ✅ Clear error messages for failures

## 🔧 Technical Requirements

- Use pandas for efficient data manipulation
- Follow TypedStrategyAction pattern
- Register with @register_action decorator
- Handle context compatibility (dict vs MockContext)
- Store data as list of dicts
- Track statistics in context["statistics"]
- Use proper type hints throughout
- Follow existing code style

## 📚 References

- Base class: `biomapper/core/strategy_actions/typed_base.py`
- Registry: `biomapper/core/strategy_actions/registry.py`
- Similar action: `biomapper/core/strategy_actions/utils/data_processing/filter_dataset.py`

## 🎯 Definition of Done

- [ ] All tests written and passing
- [ ] Implementation complete with >90% coverage
- [ ] Action registered and importable
- [ ] Tested with v2.2 strategy
- [ ] Documentation comments added
- [ ] Logging implemented
- [ ] Error handling comprehensive
- [ ] Performance validated
- [ ] Code reviewed and cleaned
- [ ] Integration test passing