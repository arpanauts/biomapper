# MVP Action Reference Implementation

## Example: FILTER_ROWS Action

This example demonstrates all the patterns and conventions for MVP actions.

```python
from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field, validator
from biomapper.core.strategy_actions.typed_base import TypedStrategyAction
from biomapper.core.models import ActionResult, TableData
import pandas as pd
import logging

logger = logging.getLogger(__name__)

# Parameter model with validation
class FilterRowsParams(BaseModel):
    """Parameters for FILTER_ROWS action."""
    
    input_key: str = Field(
        ..., 
        description="Context key for input dataset"
    )
    
    conditions: List['FilterCondition'] = Field(
        ...,
        min_items=1,
        description="List of filter conditions to apply"
    )
    
    combine_method: Literal['and', 'or'] = Field(
        'and',
        description="How to combine multiple conditions"
    )
    
    keep_filtered: bool = Field(
        False,
        description="If true, store filtered-out rows separately"
    )
    
    output_key: str = Field(
        ...,
        description="Context key for filtered dataset"
    )
    
    @validator('output_key')
    def output_key_different(cls, v, values):
        if v == values.get('input_key'):
            logger.warning(f"Output key '{v}' same as input - will overwrite")
        return v

class FilterCondition(BaseModel):
    """Single filter condition."""
    
    column: str = Field(..., description="Column to filter on")
    
    operator: Literal[
        'eq', 'ne', 'gt', 'lt', 'ge', 'le',
        'contains', 'not_contains', 'regex',
        'is_null', 'not_null', 'in', 'not_in'
    ] = Field(..., description="Comparison operator")
    
    value: Optional[Any] = Field(
        None,
        description="Value to compare against"
    )
    
    case_sensitive: bool = Field(
        True,
        description="For string operations"
    )
    
    @validator('value')
    def value_required_for_operators(cls, v, values):
        operator = values.get('operator')
        if operator in ['is_null', 'not_null'] and v is not None:
            raise ValueError(f"Operator '{operator}' should not have a value")
        if operator not in ['is_null', 'not_null'] and v is None:
            raise ValueError(f"Operator '{operator}' requires a value")
        return v


@register_action("FILTER_ROWS")
class FilterRowsAction(TypedStrategyAction[FilterRowsParams, ActionResult]):
    """Filter rows based on column conditions."""
    
    def get_params_model(self) -> type[FilterRowsParams]:
        return FilterRowsParams
    
    async def execute_typed(
        self,
        params: FilterRowsParams,
        context: Dict[str, Any],
        source_endpoint: Optional[Any],
        target_endpoint: Optional[Any]
    ) -> ActionResult:
        """Execute row filtering."""
        
        # 1. Validate input dataset exists
        if 'datasets' not in context:
            raise ValueError("No datasets found in context")
        
        if params.input_key not in context['datasets']:
            raise ValueError(f"Input dataset '{params.input_key}' not found")
        
        # 2. Get input data
        input_data = context['datasets'][params.input_key]
        input_df = input_data.to_dataframe()
        initial_count = len(input_df)
        
        logger.info(
            f"Starting FILTER_ROWS on '{params.input_key}' "
            f"with {initial_count} rows"
        )
        
        # 3. Validate all columns exist
        missing_columns = []
        for condition in params.conditions:
            if condition.column not in input_df.columns:
                missing_columns.append(condition.column)
        
        if missing_columns:
            raise ValueError(
                f"Columns not found in dataset: {missing_columns}. "
                f"Available columns: {list(input_df.columns)}"
            )
        
        # 4. Build filter masks
        masks = []
        for i, condition in enumerate(params.conditions):
            try:
                mask = self._apply_condition(input_df, condition)
                masks.append(mask)
                
                # Log condition results
                matching = mask.sum()
                logger.debug(
                    f"Condition {i+1}: {condition.column} {condition.operator} "
                    f"{condition.value} -> {matching} matches"
                )
                
            except Exception as e:
                logger.error(f"Error applying condition {i+1}: {e}")
                raise ValueError(
                    f"Failed to apply filter on column '{condition.column}' "
                    f"with operator '{condition.operator}': {str(e)}"
                )
        
        # 5. Combine masks
        if params.combine_method == 'and':
            final_mask = pd.concat(masks, axis=1).all(axis=1)
        else:  # 'or'
            final_mask = pd.concat(masks, axis=1).any(axis=1)
        
        # 6. Apply filter
        filtered_df = input_df[final_mask].copy()
        filtered_count = len(filtered_df)
        removed_count = initial_count - filtered_count
        
        logger.info(
            f"Filtered {removed_count} rows, keeping {filtered_count} rows"
        )
        
        # 7. Store filtered-out rows if requested
        if params.keep_filtered and removed_count > 0:
            filtered_out_df = input_df[~final_mask].copy()
            filtered_out_df['_filter_reason'] = self._get_filter_reasons(
                input_df[~final_mask], 
                params.conditions
            )
            
            filtered_out_data = TableData.from_dataframe(filtered_out_df)
            context['datasets'][f"{params.output_key}_filtered_out"] = filtered_out_data
            
            logger.info(
                f"Stored {removed_count} filtered rows in "
                f"'{params.output_key}_filtered_out'"
            )
        
        # 8. Create output TableData
        output_data = TableData.from_dataframe(filtered_df)
        
        # 9. Update context
        context['datasets'][params.output_key] = output_data
        
        # 10. Update metadata
        if 'metadata' not in context:
            context['metadata'] = {}
            
        context['metadata'][params.output_key] = {
            'row_count': filtered_count,
            'columns': list(filtered_df.columns),
            'filter_stats': {
                'input_rows': initial_count,
                'output_rows': filtered_count,
                'removed_rows': removed_count,
                'removal_rate': removed_count / initial_count if initial_count > 0 else 0,
                'conditions_applied': len(params.conditions),
                'combine_method': params.combine_method
            },
            'source_dataset': params.input_key
        }
        
        # 11. Create provenance
        provenance = {
            'action': 'FILTER_ROWS',
            'input_dataset': params.input_key,
            'input_rows': initial_count,
            'output_dataset': params.output_key,
            'output_rows': filtered_count,
            'conditions': [
                {
                    'column': c.column,
                    'operator': c.operator,
                    'value': c.value
                } for c in params.conditions
            ],
            'combine_method': params.combine_method
        }
        
        # 12. Return result
        return ActionResult(
            output_identifiers=output_data.get_column(
                context['metadata'][params.input_key].get('primary_column', 'id')
            ) if 'primary_column' in context['metadata'].get(params.input_key, {}) else [],
            output_ontology_type=context.get('current_ontology_type', 'unknown'),
            provenance=[provenance],
            details={
                'filter_stats': context['metadata'][params.output_key]['filter_stats']
            }
        )
    
    def _apply_condition(
        self, 
        df: pd.DataFrame, 
        condition: FilterCondition
    ) -> pd.Series:
        """Apply a single filter condition."""
        
        column = df[condition.column]
        value = condition.value
        
        # Handle case sensitivity for string operations
        if condition.operator in ['contains', 'not_contains', 'eq', 'ne'] and \
           column.dtype == 'object' and not condition.case_sensitive:
            column = column.str.lower()
            if isinstance(value, str):
                value = value.lower()
        
        # Apply operator
        if condition.operator == 'eq':
            return column == value
        elif condition.operator == 'ne':
            return column != value
        elif condition.operator == 'gt':
            return column > value
        elif condition.operator == 'lt':
            return column < value
        elif condition.operator == 'ge':
            return column >= value
        elif condition.operator == 'le':
            return column <= value
        elif condition.operator == 'contains':
            return column.astype(str).str.contains(value, na=False)
        elif condition.operator == 'not_contains':
            return ~column.astype(str).str.contains(value, na=False)
        elif condition.operator == 'regex':
            return column.astype(str).str.match(value, na=False)
        elif condition.operator == 'is_null':
            return column.isna()
        elif condition.operator == 'not_null':
            return column.notna()
        elif condition.operator == 'in':
            return column.isin(value if isinstance(value, list) else [value])
        elif condition.operator == 'not_in':
            return ~column.isin(value if isinstance(value, list) else [value])
        else:
            raise ValueError(f"Unknown operator: {condition.operator}")
    
    def _get_filter_reasons(
        self, 
        df: pd.DataFrame, 
        conditions: List[FilterCondition]
    ) -> List[str]:
        """Get reasons why each row was filtered out."""
        
        reasons = []
        for _, row in df.iterrows():
            failed = []
            for condition in conditions:
                try:
                    # Create single-row df for condition testing
                    test_df = pd.DataFrame([row])
                    if not self._apply_condition(test_df, condition).iloc[0]:
                        failed.append(
                            f"{condition.column} {condition.operator} "
                            f"{condition.value}"
                        )
                except:
                    pass
            
            reasons.append("; ".join(failed) if failed else "Unknown")
        
        return reasons


# Example usage in tests
def test_filter_rows_happy_path():
    # Arrange
    input_data = TableData(rows=[
        {'id': 'P12345', 'confidence': 0.95, 'status': 'active'},
        {'id': 'Q67890', 'confidence': 0.75, 'status': 'obsolete'},
        {'id': 'R11111', 'confidence': 0.99, 'status': 'active'},
    ])
    
    context = {
        'datasets': {'proteins': input_data},
        'metadata': {'proteins': {'primary_column': 'id'}}
    }
    
    params = FilterRowsParams(
        input_key='proteins',
        conditions=[
            FilterCondition(
                column='confidence',
                operator='ge',
                value=0.9
            ),
            FilterCondition(
                column='status',
                operator='eq',
                value='active'
            )
        ],
        combine_method='and',
        output_key='high_quality_proteins'
    )
    
    action = FilterRowsAction()
    
    # Act
    result = await action.execute_typed(params, context, None, None)
    
    # Assert
    output_data = context['datasets']['high_quality_proteins']
    assert len(output_data.rows) == 2
    assert all(row['confidence'] >= 0.9 for row in output_data.rows)
    assert all(row['status'] == 'active' for row in output_data.rows)
    
    # Check metadata
    assert context['metadata']['high_quality_proteins']['filter_stats']['removed_rows'] == 1
```

## Key Patterns Demonstrated

1. **Comprehensive parameter validation** with Pydantic
2. **Detailed logging** at multiple levels
3. **Error handling** with helpful messages
4. **Metadata tracking** in context
5. **Optional features** (keep_filtered)
6. **Provenance recording**
7. **Column validation** before processing
8. **Progress indication** for large datasets
9. **Test structure** showing usage
10. **Graceful handling** of edge cases