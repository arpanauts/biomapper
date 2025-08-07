"""Load biological dataset files with intelligent identifier handling."""

import re
import logging
from typing import Any, List, Optional, Literal
from pathlib import Path
import pandas as pd
from pydantic import BaseModel, Field

from biomapper.core.strategy_actions.typed_base import (
    TypedStrategyAction,
    StandardActionResult,
)
from biomapper.core.strategy_actions.registry import register_action
# StrategyExecutionContext not used in MVP mode

logger = logging.getLogger(__name__)


class LoadDatasetIdentifiersParams(BaseModel):
    """Parameters for LOAD_DATASET_IDENTIFIERS action."""

    # File access
    file_path: str = Field(..., description="Path to CSV/TSV file")
    file_type: Optional[Literal["csv", "tsv", "auto"]] = Field(
        "auto", description="File format"
    )

    # Column identification
    identifier_column: str = Field(
        ..., description="Column containing primary identifiers"
    )

    # Data cleaning (optional)
    strip_prefix: Optional[str] = Field(
        None, description="Prefix to remove (e.g., 'UniProtKB:')"
    )

    # Filtering (optional)
    filter_column: Optional[str] = Field(None, description="Column to filter on")
    filter_values: Optional[List[str]] = Field(
        None, description="Values to match (can be regex)"
    )
    filter_mode: Literal["include", "exclude"] = Field(
        "include", description="Include or exclude matches"
    )

    # Output
    output_key: str = Field(..., description="Key for storing in context['datasets']")

    # Options
    drop_empty_ids: bool = Field(
        True, description="Remove rows where identifier column is empty"
    )


@register_action("LOAD_DATASET_IDENTIFIERS")
class LoadDatasetIdentifiersAction(
    TypedStrategyAction[LoadDatasetIdentifiersParams, StandardActionResult]
):
    """
    Load biological dataset files with intelligent handling of identifier columns.

    This action:
    - Loads CSV/TSV files with automatic format detection
    - Strips prefixes while preserving original values
    - Filters rows based on regex patterns
    - Handles empty identifiers
    - Adds metadata columns for traceability
    """

    def get_params_model(self) -> type[LoadDatasetIdentifiersParams]:
        return LoadDatasetIdentifiersParams

    def get_result_model(self) -> type[StandardActionResult]:
        return StandardActionResult

    async def execute_typed(
        self,
        current_identifiers: List[str],
        current_ontology_type: str,
        params: LoadDatasetIdentifiersParams,
        source_endpoint: Any,
        target_endpoint: Any,
        context: Any,
    ) -> StandardActionResult:
        """Execute the action to load dataset identifiers."""

        # Initialize datasets and metadata in custom action data
        if "datasets" not in context.custom_action_data:
            context.set_action_data("datasets", {})
        if "metadata" not in context.custom_action_data:
            context.set_action_data("metadata", {})

        logger.info(f"Loading dataset from {params.file_path}")

        try:
            # Check if file exists
            file_path = Path(params.file_path)
            if not file_path.exists():
                raise FileNotFoundError(f"File not found: {params.file_path}")

            # Determine file type
            file_type = params.file_type
            if file_type == "auto":
                if file_path.suffix.lower() == ".tsv":
                    file_type = "tsv"
                else:
                    file_type = "csv"

            # Read file
            if file_type == "tsv":
                df = pd.read_csv(file_path, sep="\t", comment="#")
            else:
                df = pd.read_csv(file_path, comment="#")

            logger.debug(f"Loaded {len(df)} rows from {file_path}")

            # Track original row count for metadata
            original_row_count = len(df)

            # Add row number before any filtering
            df["_row_number"] = range(2, len(df) + 2)  # 1-based, accounting for header

            # Validate identifier column exists
            if params.identifier_column not in df.columns:
                available_cols = list(df.columns)
                raise ValueError(
                    f"Column '{params.identifier_column}' not found in file. "
                    f"Available columns: {available_cols}"
                )

            # Apply filtering if specified
            if params.filter_column and params.filter_values:
                logger.info(f"Applying filter on column '{params.filter_column}'")

                if params.filter_column not in df.columns:
                    raise ValueError(
                        f"Filter column '{params.filter_column}' not found"
                    )

                # Compile regex patterns
                patterns = [re.compile(pattern) for pattern in params.filter_values]

                # Apply filter
                def matches_any_pattern(value: Any) -> bool:
                    if pd.isna(value):
                        return False
                    str_value = str(value)
                    return any(pattern.search(str_value) for pattern in patterns)

                mask = df[params.filter_column].apply(matches_any_pattern)

                if params.filter_mode == "exclude":
                    mask = ~mask

                df = df[mask].copy()
                logger.info(f"Filtered from {original_row_count} to {len(df)} rows")

            # Strip prefix if specified
            if params.strip_prefix:
                logger.info(
                    f"Stripping prefix '{params.strip_prefix}' from column '{params.identifier_column}'"
                )

                # Preserve original values
                df[f"{params.identifier_column}_original"] = df[
                    params.identifier_column
                ].copy()

                # Strip prefix
                df[params.identifier_column] = (
                    df[params.identifier_column]
                    .astype(str)
                    .str.replace(params.strip_prefix, "", regex=False)
                )

            # Drop empty identifiers if requested
            if params.drop_empty_ids:
                # Count before dropping
                before_drop = len(df)

                # Drop rows where identifier is empty, NaN, or just whitespace
                df = df[df[params.identifier_column].notna()]
                df = df[df[params.identifier_column].astype(str).str.strip() != ""]

                if before_drop != len(df):
                    logger.info(
                        f"Dropped {before_drop - len(df)} rows with empty identifiers"
                    )

            # Add source file metadata
            df["_source_file"] = str(file_path.absolute())

            # Convert to list of dictionaries for storage
            dataset = df.to_dict("records")

            # Store in context
            datasets = context.get_action_data("datasets", {})
            datasets[params.output_key] = dataset
            context.set_action_data("datasets", datasets)

            # Create metadata
            metadata = {
                "source_file": str(file_path.absolute()),
                "row_count": len(dataset),
                "identifier_column": params.identifier_column,
                "columns": list(df.columns),
                "filtered": bool(params.filter_column and params.filter_values),
                "prefix_stripped": bool(params.strip_prefix),
            }

            # Add filter stats if filtering was applied
            if params.filter_column and params.filter_values:
                metadata["filter_stats"] = {
                    "original_count": original_row_count,
                    "filtered_count": len(dataset),
                    "filter_column": params.filter_column,
                    "filter_mode": params.filter_mode,
                }

            metadata_dict = context.get_action_data("metadata", {})
            metadata_dict[params.output_key] = metadata
            context.set_action_data("metadata", metadata_dict)

            logger.info(
                f"Successfully loaded {len(dataset)} rows into context key '{params.output_key}'"
            )

            return StandardActionResult(
                input_identifiers=[],  # No input identifiers for this action
                output_identifiers=[
                    str(row[params.identifier_column]) for row in dataset
                ],
                output_ontology_type="unknown",  # We don't know the type from just a CSV
                provenance=[
                    {
                        "action": "LOAD_DATASET_IDENTIFIERS",
                        "file": str(file_path.absolute()),
                        "rows_loaded": len(dataset),
                        "identifier_column": params.identifier_column,
                    }
                ],
                details={
                    "rows_loaded": len(dataset),
                    "output_key": params.output_key,
                    "identifier_column": params.identifier_column,
                    "file_path": str(file_path.absolute()),
                },
            )

        except Exception as e:
            logger.error(f"Failed to load dataset: {str(e)}")
            raise
