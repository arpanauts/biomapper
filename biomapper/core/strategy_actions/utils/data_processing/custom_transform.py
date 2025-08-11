"""Custom data transformation action for flexible data processing operations."""

from typing import Dict, Any, List, Literal, Optional
from pydantic import BaseModel, Field
import pandas as pd
import numpy as np

from biomapper.core.strategy_actions.typed_base import TypedStrategyAction
from biomapper.core.strategy_actions.registry import register_action
from biomapper.core.exceptions import (
    DatasetNotFoundError,
    TransformationError,
    SchemaValidationError,
)


class ActionResult(BaseModel):
    """Simple action result for transformation operations."""

    success: bool
    error: Optional[str] = None
    data: Dict[str, Any] = Field(default_factory=dict)


class TransformOperation(BaseModel):
    """Single transformation operation specification."""

    type: Literal[
        "column_rename",
        "column_add",
        "column_drop",
        "column_transform",
        "filter_rows",
        "merge_columns",
        "split_column",
        "aggregate",
        "pivot",
        "unpivot",
        "sort",
        "deduplicate",
        "fill_na",
    ]
    params: Dict[str, Any]
    condition: Optional[str] = None  # Optional condition for conditional transforms


class CustomTransformParams(BaseModel):
    """Parameters for CUSTOM_TRANSFORM action."""

    input_key: str = Field(..., description="Key of input dataset to transform")
    output_key: str = Field(..., description="Key for transformed dataset")

    transformations: List[TransformOperation] = Field(
        ..., description="List of transformation operations to apply in sequence"
    )

    validate_schema: bool = Field(
        default=True,
        description="Whether to validate output schema matches expectations",
    )

    expected_columns: Optional[List[str]] = Field(
        default=None, description="Expected columns in output (for validation)"
    )

    preserve_index: bool = Field(
        default=True, description="Whether to preserve original DataFrame index"
    )

    error_handling: Literal["strict", "warn", "ignore"] = Field(
        default="strict", description="How to handle transformation errors"
    )


class CustomTransformResult(ActionResult):
    """Result of CUSTOM_TRANSFORM action."""

    rows_processed: int = 0
    columns_before: int = 0
    columns_after: int = 0
    transformations_applied: int = 0
    transformations_failed: int = 0
    warnings: List[str] = Field(default_factory=list)
    schema_validation_passed: bool = True


@register_action("CUSTOM_TRANSFORM")
class CustomTransformAction(
    TypedStrategyAction[CustomTransformParams, CustomTransformResult]
):
    """
    Flexible data transformation action supporting multiple transformation types.

    Handles complex data transformations that don't fit standard action patterns.
    Supports chaining multiple transformations with error handling and validation.
    """

    def get_params_model(self) -> type[CustomTransformParams]:
        return CustomTransformParams

    def get_result_model(self) -> type[CustomTransformResult]:
        return CustomTransformResult

    async def execute_typed(  # type: ignore[override]
        self, params: CustomTransformParams, context: Dict[str, Any]
    ) -> CustomTransformResult:
        """Execute custom transformations on dataset."""

        # Validate input dataset exists
        if params.input_key not in context.get("datasets", {}):
            available_keys = list(context.get("datasets", {}).keys())
            raise DatasetNotFoundError(
                f"Dataset '{params.input_key}' not found. Available: {available_keys}"
            )

        df = context["datasets"][params.input_key].copy()
        original_cols = len(df.columns)

        transformations_applied = 0
        transformations_failed = 0
        warnings = []

        # Apply transformations in sequence
        for i, transform_op in enumerate(params.transformations):
            try:
                # Check conditional execution
                if transform_op.condition and not self._evaluate_condition(
                    df, transform_op.condition
                ):
                    continue

                df = await self._apply_transformation(df, transform_op)
                transformations_applied += 1

                self.logger.debug(f"Applied transformation {i+1}: {transform_op.type}")

            except Exception as e:
                transformations_failed += 1
                error_msg = (
                    f"Transformation {i+1} ({transform_op.type}) failed: {str(e)}"
                )

                if params.error_handling == "strict":
                    raise TransformationError(error_msg)
                elif params.error_handling == "warn":
                    warnings.append(error_msg)
                    self.logger.warning(error_msg)
                # "ignore" continues without logging

        # Schema validation
        schema_validation_passed = True
        if params.validate_schema and params.expected_columns:
            missing_cols = set(params.expected_columns) - set(df.columns)
            if missing_cols:
                schema_validation_passed = False
                error_msg = f"Missing expected columns: {missing_cols}"

                if params.error_handling == "strict":
                    raise SchemaValidationError(error_msg)
                else:
                    warnings.append(error_msg)

        # Store result
        context.setdefault("datasets", {})[params.output_key] = df

        # Update statistics
        context.setdefault("statistics", {}).update(
            {
                f"{params.output_key}_rows_processed": len(df),
                f"{params.output_key}_transformations_applied": transformations_applied,
            }
        )

        return CustomTransformResult(
            success=True,
            rows_processed=len(df),
            columns_before=original_cols,
            columns_after=len(df.columns),
            transformations_applied=transformations_applied,
            transformations_failed=transformations_failed,
            warnings=warnings,
            schema_validation_passed=schema_validation_passed,
            data={
                "output_key": params.output_key,
                "rows_processed": len(df),
                "columns_before": original_cols,
                "columns_after": len(df.columns),
            },
        )

    async def _apply_transformation(
        self, df: pd.DataFrame, transform_op: TransformOperation
    ) -> pd.DataFrame:
        """Apply single transformation operation."""

        transform_type = transform_op.type
        params = transform_op.params

        if transform_type == "column_rename":
            return df.rename(columns=params.get("mapping", {}))

        elif transform_type == "column_add":
            for col_name, col_value in params.get("columns", {}).items():
                if callable(col_value):
                    df[col_name] = col_value(df)
                else:
                    df[col_name] = col_value
            return df

        elif transform_type == "column_drop":
            cols_to_drop = params.get("columns", [])
            return df.drop(columns=cols_to_drop, errors="ignore")

        elif transform_type == "column_transform":
            col_name = params["column"]
            transform_func = params["function"]

            if isinstance(transform_func, str):
                # Handle string-based transformations
                if transform_func == "lower":
                    df[col_name] = df[col_name].str.lower()
                elif transform_func == "upper":
                    df[col_name] = df[col_name].str.upper()
                elif transform_func == "strip":
                    df[col_name] = df[col_name].str.strip()
                elif transform_func.startswith("replace:"):
                    # Format: "replace:old_value:new_value"
                    parts = transform_func.split(":", 2)
                    if len(parts) == 3:
                        _, old_val, new_val = parts
                        df[col_name] = df[col_name].str.replace(old_val, new_val)
            elif callable(transform_func):
                df[col_name] = df[col_name].apply(transform_func)

            return df

        elif transform_type == "filter_rows":
            query = params.get("query")
            if query:
                return df.query(query)
            else:
                # Handle column-based filtering
                for col, condition in params.get("conditions", {}).items():
                    if col in df.columns:
                        if isinstance(condition, dict):
                            op = condition.get("operator", "==")
                            value = condition.get("value")

                            if op == "==":
                                df = df[df[col] == value]
                            elif op == "!=":
                                df = df[df[col] != value]
                            elif op == ">":
                                df = df[df[col] > value]
                            elif op == "<":
                                df = df[df[col] < value]
                            elif op == ">=":
                                df = df[df[col] >= value]
                            elif op == "<=":
                                df = df[df[col] <= value]
                            elif op == "in":
                                df = df[df[col].isin(value)]
                            elif op == "not_in":
                                df = df[~df[col].isin(value)]
                return df

        elif transform_type == "merge_columns":
            new_col = params["new_column"]
            source_cols = params["source_columns"]
            separator = params.get("separator", "_")

            df[new_col] = df[source_cols].astype(str).agg(separator.join, axis=1)
            return df

        elif transform_type == "split_column":
            source_col = params["source_column"]
            separator = params.get("separator", "_")
            new_cols = params["new_columns"]

            split_data = df[source_col].str.split(separator, expand=True)
            for i, new_col in enumerate(new_cols):
                if i < split_data.shape[1]:
                    df[new_col] = split_data[i]
            return df

        elif transform_type == "deduplicate":
            subset = params.get("subset")
            keep = params.get("keep", "first")
            return df.drop_duplicates(subset=subset, keep=keep)

        elif transform_type == "fill_na":
            method = params.get("method", "value")
            if method == "value":
                fill_value = params.get("value", "")
                return df.fillna(fill_value)
            elif method == "forward":
                return df.fillna(method="ffill")  # type: ignore
            elif method == "backward":
                return df.fillna(method="bfill")  # type: ignore

        elif transform_type == "sort":
            by_columns = params.get("by", [])
            ascending = params.get("ascending", True)
            return df.sort_values(by=by_columns, ascending=ascending)

        else:
            raise TransformationError(
                f"Unsupported transformation type: {transform_type}"
            )

        # This should never be reached, but satisfies type checker
        return df

    def _evaluate_condition(self, df: pd.DataFrame, condition: str) -> bool:
        """Evaluate conditional expression for transformation."""
        try:
            # Simple condition evaluation - can be extended
            # For security, only allow specific safe operations
            safe_names = {"df": df, "len": len, "any": any, "all": all, "np": np}
            return bool(eval(condition, {"__builtins__": {}}, safe_names))
        except Exception:
            return True  # Default to applying transformation if condition fails
