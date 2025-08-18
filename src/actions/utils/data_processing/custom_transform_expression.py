"""
Custom transformation action for flexible data manipulation using Python expressions.

This action allows strategies to apply arbitrary transformations to dataset columns
using Python expressions or callable functions, providing maximum flexibility for
data processing operations.
"""

from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np
from pydantic import BaseModel, Field
import logging

from actions.typed_base import TypedStrategyAction
from actions.registry import register_action
from core.standards.context_handler import UniversalContext

logger = logging.getLogger(__name__)


class ActionResult(BaseModel):
    """Simple action result for transformation operations."""

    success: bool
    message: Optional[str] = None
    error: Optional[str] = None
    data: Dict[str, Any] = Field(default_factory=dict)


class TransformationSpec(BaseModel):
    """Specification for a single column transformation using Python expressions."""

    column: str = Field(..., description="Column name to transform")
    expression: str = Field(
        ..., description="Python expression to apply (value available as 'value')"
    )
    new_column: Optional[str] = Field(
        None, description="Optional new column name for result"
    )
    on_error: str = Field(
        "keep_original", description="Action on error: keep_original, null, raise"
    )
    drop_original: bool = Field(
        False, description="Drop original column after creating new column"
    )


class CustomTransformExpressionParams(BaseModel):
    """Parameters for expression-based custom transformation action."""

    input_key: str = Field(..., description="Key for input dataset in context")
    output_key: str = Field(..., description="Key for output dataset in context")
    transformations: List[TransformationSpec] = Field(
        ..., description="List of transformations to apply"
    )
    parallel: bool = Field(
        True,
        description="Whether to apply transformations in parallel (currently unused)",
    )


@register_action("CUSTOM_TRANSFORM_EXPRESSION")
class CustomTransformExpressionAction(
    TypedStrategyAction[CustomTransformExpressionParams, ActionResult]
):
    """
    Apply custom transformations to dataset columns using Python expressions.

    This action provides maximum flexibility for data transformation by allowing
    arbitrary Python expressions to be applied to dataset columns. It supports:

    - Python expressions with 'value' as the current cell value
    - Complex transformations using conditionals and functions
    - Error handling with configurable behavior (keep_original, null, raise)
    - Creation of new columns while preserving originals
    - Safe evaluation with restricted namespace for security

    Examples:
        Simple uppercase transformation:
            expression: "value.upper()"

        Conditional transformation:
            expression: "value.split('|')[0] if '|' in value else value"

        Type conversion with null handling:
            expression: "float(value) if value else 0.0"

        Complex calculation:
            expression: "np.log10(float(value)) if value else np.nan"
    """

    def get_params_model(self) -> type[CustomTransformExpressionParams]:
        return CustomTransformExpressionParams

    def get_result_model(self) -> type[ActionResult]:
        return ActionResult

    async def execute_typed(  # type: ignore[override]
        self,
        current_identifiers: List[str],
        current_ontology_type: str,
        params: CustomTransformExpressionParams,
        source_endpoint: Any,
        target_endpoint: Any,
        context: Dict[str, Any]
    ) -> ActionResult:
        """Execute custom transformations on dataset using Python expressions."""
        try:
            # Wrap context for uniform access
            ctx = UniversalContext.wrap(context)
            
            # Get input dataset from context
            datasets = ctx.get_datasets()
            if params.input_key not in datasets:
                available_keys = list(datasets.keys())
                error_msg = f"Input key '{params.input_key}' not found in context. Available keys: {available_keys}"
                logger.error(error_msg)
                return ActionResult(
                    success=False,
                    error=error_msg,
                    data={
                        "input_key": params.input_key,
                        "available_keys": available_keys,
                    },
                )

            input_data = datasets[params.input_key]

            # Convert to DataFrame if needed
            if isinstance(input_data, dict) and "data" in input_data:
                df = pd.DataFrame(input_data["data"])
            elif isinstance(input_data, pd.DataFrame):
                df = input_data.copy()
            elif isinstance(input_data, list):
                df = pd.DataFrame(input_data)
            else:
                error_msg = f"Unsupported input type: {type(input_data)}"
                logger.error(error_msg)
                return ActionResult(
                    success=False,
                    error=error_msg,
                    data={"input_type": str(type(input_data))},
                )

            logger.info(
                f"Applying {len(params.transformations)} transformations to {len(df)} rows"
            )

            # Apply each transformation
            transformations_applied = 0
            for i, transform in enumerate(params.transformations):
                try:
                    df = await self._apply_transformation(df, transform)
                    transformations_applied += 1
                    logger.debug(f"Applied transformation {i+1}: {transform.column}")
                except Exception as e:
                    error_msg = f"Transformation {i+1} failed on column '{transform.column}': {str(e)}"
                    if transform.on_error == "raise":
                        logger.error(error_msg)
                        return ActionResult(
                            success=False,
                            error=error_msg,
                            data={
                                "column": transform.column,
                                "expression": transform.expression,
                            },
                        )
                    else:
                        logger.warning(error_msg)
                        # Continue with other transformations

            # Store result in context
            datasets = ctx.get_datasets()
            datasets[params.output_key] = df
            ctx.set("datasets", datasets)

            # Update statistics in context
            statistics = ctx.get_statistics()
            statistics.update(
                {
                    f"{params.output_key}_rows": len(df),
                    f"{params.output_key}_columns": len(df.columns),
                    f"{params.output_key}_transformations": transformations_applied,
                }
            )
            ctx.set("statistics", statistics)

            return ActionResult(
                success=True,
                message=f"Applied {transformations_applied} transformations successfully",
                data={
                    "rows_processed": len(df),
                    "transformations_applied": transformations_applied,
                    "output_columns": list(df.columns),
                },
            )

        except Exception as e:
            error_msg = f"Custom transformation failed: {str(e)}"
            logger.error(error_msg)
            return ActionResult(
                success=False, error=error_msg, data={"input_key": params.input_key}
            )

    async def _apply_transformation(
        self, df: pd.DataFrame, transform: TransformationSpec
    ) -> pd.DataFrame:
        """Apply a single transformation to a DataFrame column using Python expression."""

        # Check if column exists - if not, create it for new columns
        if transform.column not in df.columns:
            # If we have an expression, this is likely creating a new column
            if transform.expression:
                logger.info(
                    f"Creating new column '{transform.column}' via transformation."
                )
                # Initialize column with None so we can apply the expression
                df[transform.column] = None
            else:
                logger.warning(
                    f"Column '{transform.column}' not found and no expression provided. Skipping transformation."
                )
                return df

        # Determine target column name
        target_column = transform.new_column or transform.column

        # Create safe namespace for evaluation
        # Include commonly needed functions and modules
        safe_namespace = {
            # Built-in functions
            "str": str,
            "int": int,
            "float": float,
            "bool": bool,
            "len": len,
            "abs": abs,
            "round": round,
            "min": min,
            "max": max,
            "sum": sum,
            "any": any,
            "all": all,
            "sorted": sorted,
            "reversed": reversed,
            "enumerate": enumerate,
            "zip": zip,
            "range": range,
            "list": list,
            "dict": dict,
            "set": set,
            "tuple": tuple,
            # String methods (for convenience)
            "upper": str.upper,
            "lower": str.lower,
            "strip": str.strip,
            "split": str.split,
            "replace": str.replace,
            "startswith": str.startswith,
            "endswith": str.endswith,
            # Modules
            "np": np,
            "pd": pd,
            # Lambda support
            "lambda": lambda: None,  # Placeholder, actual lambdas work in eval
        }

        def transform_value(value: Any) -> Any:
            """Apply expression to a single value."""
            if pd.isna(value):
                # For null values, check if expression handles them
                if (
                    "if value" in transform.expression
                    or "if not value" in transform.expression
                ):
                    # Expression has null handling, let it proceed
                    pass
                else:
                    # No null handling in expression, return NaN
                    return np.nan

            try:
                # Add value to namespace
                local_namespace = {"value": value}
                local_namespace.update(safe_namespace)

                # Evaluate expression with restricted builtins for safety
                result = eval(
                    transform.expression, {"__builtins__": {}}, local_namespace
                )
                return result

            except Exception:
                if transform.on_error == "raise":
                    raise
                elif transform.on_error == "null":
                    return np.nan
                else:  # keep_original
                    return value

        # Apply transformation to column
        try:
            df[target_column] = df[transform.column].apply(transform_value)

            # Drop original column if requested and it's different from target
            if (
                transform.drop_original
                and transform.new_column
                and transform.column != target_column
            ):
                df = df.drop(columns=[transform.column])

            logger.debug(
                f"Transformed column '{transform.column}' -> '{target_column}' using expression: {transform.expression[:50]}..."
            )

        except Exception as e:
            error_msg = f"Failed to transform column '{transform.column}': {str(e)}"
            if transform.on_error == "raise":
                raise ValueError(error_msg)
            else:
                logger.warning(error_msg)
                # Return DataFrame unchanged if not raising

        return df


# Also register with the original name expected by strategies
@register_action("CUSTOM_TRANSFORM")
class CustomTransformAction(CustomTransformExpressionAction):
    """Alias for CustomTransformExpressionAction to maintain backward compatibility."""

    pass
