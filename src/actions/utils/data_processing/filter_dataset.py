"""FILTER_DATASET action for filtering datasets by column conditions."""

import logging
from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field
import pandas as pd

from actions.registry import register_action
from actions.base import BaseStrategyAction

logger = logging.getLogger(__name__)


class FilterCondition(BaseModel):
    """A single filter condition for dataset filtering."""

    column: str = Field(..., description="Column to filter on")
    operator: Literal[
        "equals",
        "not_equals",
        "contains",
        "not_contains",
        "greater_than",
        "less_than",
        "greater_equal",
        "less_equal",
        "in_list",
        "not_in_list",
        "regex",
        "is_null",
        "not_null",
    ] = Field(..., description="Filter operator")
    value: Optional[Any] = Field(
        None, description="Value to compare against (not needed for null checks)"
    )
    case_sensitive: bool = Field(
        default=True, description="Case sensitivity for string operations"
    )


class FilterDatasetParams(BaseModel):
    """Parameters for FILTER_DATASET action."""

    input_key: str = Field(..., description="Dataset key from context['datasets']")
    filter_conditions: List[FilterCondition] = Field(
        ..., description="List of filter conditions to apply"
    )
    logic_operator: Literal["AND", "OR"] = Field(
        default="AND", description="How to combine multiple conditions"
    )
    output_key: str = Field(..., description="Where to store filtered dataset")
    keep_or_remove: Literal["keep", "remove"] = Field(
        default="keep", description="Keep matching or remove matching rows"
    )
    add_filter_log: bool = Field(
        default=True, description="Add metadata about filtering"
    )


class ActionResult(BaseModel):
    """Enhanced action result with detailed information."""

    success: bool
    message: str
    details: Dict[str, Any] = Field(default_factory=dict)


@register_action("FILTER_DATASET")
class FilterDatasetAction(BaseStrategyAction):
    """Filter datasets by column values and conditions.

    This is a generic utility action for filtering datasets across all entity types.
    Supports multiple operators, conditions, and logical combinations.
    """

    def __init__(self, db_session: Any = None, *args: Any, **kwargs: Any) -> None:
        """Initialize the action with logging."""
        self.db_session = db_session
        self.logger = logging.getLogger(
            self.__class__.__module__ + "." + self.__class__.__name__
        )

    def apply_filter_condition(
        self, df: pd.DataFrame, condition: FilterCondition
    ) -> pd.Series:
        """Apply a single filter condition and return boolean mask."""
        if condition.column not in df.columns:
            raise ValueError(f"Column '{condition.column}' not found in dataset")

        column_data = df[condition.column]

        try:
            if condition.operator == "equals":
                return column_data == condition.value

            elif condition.operator == "not_equals":
                return column_data != condition.value

            elif condition.operator == "greater_than":
                return column_data > condition.value

            elif condition.operator == "less_than":
                return column_data < condition.value

            elif condition.operator == "greater_equal":
                return column_data >= condition.value

            elif condition.operator == "less_equal":
                return column_data <= condition.value

            elif condition.operator == "contains":
                if condition.case_sensitive:
                    return column_data.astype(str).str.contains(
                        str(condition.value), na=False, regex=False
                    )
                else:
                    return (
                        column_data.astype(str)
                        .str.lower()
                        .str.contains(
                            str(condition.value).lower(), na=False, regex=False
                        )
                    )

            elif condition.operator == "not_contains":
                if condition.case_sensitive:
                    return ~column_data.astype(str).str.contains(
                        str(condition.value), na=False, regex=False
                    )
                else:
                    return ~column_data.astype(str).str.lower().str.contains(
                        str(condition.value).lower(), na=False, regex=False
                    )

            elif condition.operator == "in_list":
                if condition.value is None:
                    raise ValueError("Value cannot be None for in_list operator")
                return column_data.isin(condition.value)

            elif condition.operator == "not_in_list":
                if condition.value is None:
                    raise ValueError("Value cannot be None for not_in_list operator")
                return ~column_data.isin(condition.value)

            elif condition.operator == "regex":
                if condition.value is None:
                    raise ValueError("Value cannot be None for regex operator")
                return column_data.astype(str).str.contains(
                    str(condition.value), regex=True, na=False
                )

            elif condition.operator == "is_null":
                return column_data.isna()

            elif condition.operator == "not_null":
                return column_data.notna()

            else:
                raise ValueError(f"Unknown operator: {condition.operator}")

        except Exception as e:
            if (
                "regex" in str(e).lower()
                or "unterminated" in str(e).lower()
                or "bad character" in str(e).lower()
            ):
                raise ValueError(f"Invalid regex pattern '{condition.value}': {str(e)}")
            raise

    def apply_multiple_conditions(
        self, df: pd.DataFrame, conditions: List[FilterCondition], logic_operator: str
    ) -> pd.Series:
        """Combine multiple filter conditions with AND/OR logic."""
        if not conditions:
            return pd.Series([True] * len(df), index=df.index)

        masks = [self.apply_filter_condition(df, condition) for condition in conditions]

        if logic_operator == "AND":
            # Combine with logical AND
            result_mask = masks[0]
            for mask in masks[1:]:
                result_mask = result_mask & mask
            return result_mask
        else:  # OR
            # Combine with logical OR
            result_mask = masks[0]
            for mask in masks[1:]:
                result_mask = result_mask | mask
            return result_mask

    async def execute_typed(
        self,
        current_identifiers: List[str],
        current_ontology_type: str,
        params: FilterDatasetParams,
        source_endpoint: Any,
        target_endpoint: Any,
        context: Any,
    ) -> ActionResult:
        """Execute dataset filtering with type safety."""
        try:
            # Get datasets from context (support both dict and Pydantic context)
            if hasattr(context, "get_action_data"):
                # Pydantic-style context
                datasets_store = context.get_action_data("datasets", {})
            else:
                # Dict-style context
                datasets_store = context.get("datasets", {})

            # Check if input dataset exists
            if params.input_key not in datasets_store:
                error_msg = f"Input dataset '{params.input_key}' not found in context"
                self.logger.error(error_msg)
                return ActionResult(success=False, message=error_msg)

            # Get input dataset
            input_dataset = datasets_store[params.input_key]

            # Convert to DataFrame if needed
            if isinstance(input_dataset, list):
                if not input_dataset:  # Empty list
                    filtered_data = []
                    input_rows = 0
                    self.logger.info("Processing empty dataset")
                else:
                    df = pd.DataFrame(input_dataset)
                    input_rows = len(df)
                    self.logger.info(f"Processing {input_rows} rows for filtering")

                    # Apply filtering conditions
                    filter_mask = self.apply_multiple_conditions(
                        df, params.filter_conditions, params.logic_operator
                    )

                    # Apply keep vs remove logic
                    if params.keep_or_remove == "remove":
                        filter_mask = ~filter_mask

                    # Filter the dataset
                    filtered_df = df[filter_mask]
                    filtered_data = filtered_df.to_dict("records")

                    self.logger.info(f"Filtered to {len(filtered_data)} rows")
            elif isinstance(input_dataset, pd.DataFrame):
                df = input_dataset
                input_rows = len(df)

                if input_rows == 0:  # Empty DataFrame
                    filtered_data = []
                    self.logger.info("Processing empty DataFrame")
                else:
                    self.logger.info(f"Processing {input_rows} rows for filtering")

                    # Apply filtering conditions
                    filter_mask = self.apply_multiple_conditions(
                        df, params.filter_conditions, params.logic_operator
                    )

                    # Apply keep vs remove logic
                    if params.keep_or_remove == "remove":
                        filter_mask = ~filter_mask

                    # Filter the dataset
                    filtered_df = df[filter_mask]
                    filtered_data = filtered_df.to_dict("records")

                    self.logger.info(f"Filtered to {len(filtered_data)} rows")
            else:
                # Empty or invalid dataset
                filtered_data = []
                input_rows = 0
                self.logger.info("Empty or invalid input dataset")

            # Store results
            datasets_store[params.output_key] = filtered_data

            # Update context appropriately
            if hasattr(context, "set_action_data"):
                # Pydantic-style context
                context.set_action_data("datasets", datasets_store)
            else:
                # Dict-style context
                context["datasets"] = datasets_store

            # Calculate statistics
            output_rows = len(filtered_data) if filtered_data else 0

            # Create detailed message and statistics
            if params.add_filter_log:
                success_msg = (
                    f"Successfully filtered dataset '{params.input_key}' to '{params.output_key}': "
                    f"{input_rows} → {output_rows} rows"
                )
                detailed_stats = {
                    "total_input_rows": input_rows,
                    "total_output_rows": output_rows,
                    "filter_conditions_count": len(params.filter_conditions),
                    "logic_operator": params.logic_operator,
                    "keep_or_remove": params.keep_or_remove,
                    "input_key": params.input_key,
                    "output_key": params.output_key,
                }
            else:
                success_msg = f"Successfully filtered dataset '{params.input_key}' to '{params.output_key}' with {output_rows} rows"
                detailed_stats = {"output_rows": output_rows}

            self.logger.info(success_msg)

            return ActionResult(
                success=True, message=success_msg, details=detailed_stats
            )

        except ValueError as e:
            error_msg = f"Filter validation error: {str(e)}"
            self.logger.error(error_msg)
            return ActionResult(
                success=False,
                message=error_msg,
                details={"error_type": "validation_error"},
            )

        except Exception as e:
            error_msg = f"Unexpected filtering error: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return ActionResult(
                success=False,
                message=error_msg,
                details={"error_type": "unexpected_error"},
            )

    async def execute(
        self,
        current_identifiers: List[str],
        current_ontology_type: str,
        action_params: Dict[str, Any],
        source_endpoint: Any,
        target_endpoint: Any,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute method for BaseStrategyAction compatibility."""
        # Convert params dict to FilterDatasetParams
        params = FilterDatasetParams(**action_params)
        
        # Execute with typed params
        result = await self.execute_typed(
            current_identifiers, current_ontology_type, params,
            source_endpoint, target_endpoint, context
        )
        
        # Convert ActionResult to dict format expected by BaseStrategyAction
        return {
            "input_identifiers": current_identifiers,
            "output_identifiers": current_identifiers,  # Filtering doesn't change identifiers
            "output_ontology_type": current_ontology_type,
            "provenance": [{"action": "FILTER_DATASET", "success": result.success}],
            "details": result.details if result.success else {"error": result.message}
        }
