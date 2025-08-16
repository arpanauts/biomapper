"""Merge multiple datasets with deduplication support."""

from typing import List, Any, Optional, Dict
from pydantic import BaseModel, Field, model_validator
import pandas as pd
import logging

from biomapper.core.strategy_actions.typed_base import (
    TypedStrategyAction,
    StandardActionResult,
)
from biomapper.core.strategy_actions.registry import register_action
from biomapper.core.standards.context_handler import UniversalContext

logger = logging.getLogger(__name__)


class MergeDatasetsParams(BaseModel):
    """Parameters for MERGE_DATASETS action - supports both old and new formats."""

    # New format (preferred)
    dataset_keys: Optional[List[str]] = Field(
        None, description="List of dataset keys to merge from context"
    )
    join_columns: Optional[Dict[str, str]] = Field(
        None, description="Map of dataset_key to column name for joins"
    )

    # Old format (for backward compatibility)
    input_key: Optional[str] = Field(
        None, description="First dataset key (old format)"
    )
    dataset2_key: Optional[str] = Field(
        None, description="Second dataset key (old format)"
    )
    join_column1: Optional[str] = Field(
        None, description="Join column for first dataset (old format)"
    )
    join_column2: Optional[str] = Field(
        None, description="Join column for second dataset (old format)"
    )
    join_type: Optional[str] = Field(
        None, description="Join type (old format, maps to join_how)"
    )

    # Common parameters
    output_key: str = Field(..., description="Key for storing merged dataset")
    deduplication_column: Optional[str] = Field(
        None, description="Column to use for deduplication"
    )
    keep: str = Field(
        "first",
        description="Which duplicate to keep: 'first', 'last', or 'all'",
        pattern="^(first|last|all)$",
    )
    merge_strategy: Optional[str] = Field(
        None,
        description="How to merge: 'concat' or 'join'",
        pattern="^(concat|join)$",
    )
    join_on: Optional[str] = Field(
        None, description="Column to join on when using 'join' strategy"
    )
    join_how: Optional[str] = Field(
        None, description="Join type: 'inner', 'outer', 'left', 'right'"
    )

    # One-to-many handling
    handle_one_to_many: str = Field(
        "keep_all",
        description="How to handle one-to-many: 'keep_all', 'first', 'aggregate'",
        pattern="^(keep_all|first|aggregate)$",
    )
    aggregate_func: Optional[str] = Field(
        None, description="Aggregation function when handle_one_to_many='aggregate'"
    )

    # Additional features
    add_provenance: Optional[bool] = Field(
        False, description="Add provenance column tracking merge source"
    )
    provenance_value: Optional[str] = Field(
        None, description="Value for provenance column"
    )

    @model_validator(mode="after")
    def validate_and_convert_params(self):
        """Convert old format to new format and validate."""
        # If old format is provided, convert to new format
        if self.input_key and self.dataset2_key:
            if not self.dataset_keys:
                self.dataset_keys = [self.input_key, self.dataset2_key]

            # Set up join columns if using join
            if self.join_column1 and self.join_column2:
                if not self.join_columns:
                    self.join_columns = {
                        self.input_key: self.join_column1,
                        self.dataset2_key: self.join_column2,
                    }
                if not self.merge_strategy:
                    self.merge_strategy = "join"

            # Map old join_type to join_how
            if self.join_type and not self.join_how:
                self.join_how = self.join_type

        # Set default merge_strategy if not specified
        if not self.merge_strategy:
            if self.join_columns or self.join_on:
                self.merge_strategy = "join"
            else:
                self.merge_strategy = "concat"

        # Set default join_how if not specified for join strategy
        if self.merge_strategy == "join" and not self.join_how:
            self.join_how = "outer"

        # Validate that we have the necessary parameters
        if not self.dataset_keys:
            raise ValueError(
                "Either dataset_keys or dataset1_key/dataset2_key must be provided"
            )

        # Validate join parameters
        if self.merge_strategy == "join":
            if not self.join_columns and not self.join_on:
                raise ValueError(
                    "join_columns or join_on required when merge_strategy='join'"
                )

        return self


@register_action("MERGE_DATASETS")
class MergeDatasetsAction(
    TypedStrategyAction[MergeDatasetsParams, StandardActionResult]
):
    """Merge multiple datasets with optional deduplication.

    This action combines multiple datasets from the execution context into a single
    unified dataset. It supports both concatenation (stacking) and joining strategies,
    with optional deduplication based on a specified column.

    Example:
        ```yaml
        - name: merge_all_results
          action:
            type: MERGE_DATASETS
            params:
              dataset_keys: ["dataset1", "dataset2", "dataset3"]
              output_key: "merged_results"
              deduplication_column: "identifier"
              keep: "first"
              merge_strategy: "concat"
        ```
    """

    def get_params_model(self) -> type[MergeDatasetsParams]:
        """Get the Pydantic model for action parameters."""
        return MergeDatasetsParams

    def get_result_model(self) -> type[StandardActionResult]:
        """Get the Pydantic model for action results."""
        return StandardActionResult

    async def execute_typed(
        self,
        current_identifiers: List[str],
        current_ontology_type: str,
        params: MergeDatasetsParams,
        source_endpoint: Any,
        target_endpoint: Any,
        context: Any,
    ) -> StandardActionResult:
        """Execute dataset merging with type safety.

        Args:
            current_identifiers: Current list of identifiers (not used for dataset operations)
            current_ontology_type: Current ontology type
            params: Typed parameters for the action
            source_endpoint: Source endpoint (not used)
            target_endpoint: Target endpoint (not used)
            context: Execution context containing datasets

        Returns:
            StandardActionResult with merge details and provenance
        """
        logger.info(f"Starting MERGE_DATASETS with {len(params.dataset_keys)} datasets")

        # Wrap context for uniform access
        ctx = UniversalContext.wrap(context)
        
        # Get datasets from context
        datasets_store = ctx.get_datasets()

        # Collect datasets to merge with their keys
        datasets_to_merge = []
        dataset_keys_used = []
        missing_datasets = []

        for key in params.dataset_keys:
            if key in datasets_store:
                dataset = datasets_store[key]
                datasets_to_merge.append((key, dataset))
                dataset_keys_used.append(key)
                logger.info(f"Found dataset '{key}' with {len(dataset)} rows")
            else:
                missing_datasets.append(key)
                logger.warning(f"Dataset '{key}' not found in context")

        # Handle case where no datasets are found
        if not datasets_to_merge:
            error_msg = f"No datasets found to merge. Missing: {missing_datasets}"
            logger.error(error_msg)
            return StandardActionResult(
                input_identifiers=current_identifiers,
                output_identifiers=[],
                output_ontology_type=current_ontology_type,
                provenance=[
                    {
                        "action": "MERGE_DATASETS",
                        "status": "failed",
                        "error": error_msg,
                        "missing_datasets": missing_datasets,
                    }
                ],
                details={
                    "error": error_msg,
                    "datasets_requested": len(params.dataset_keys),
                    "datasets_found": 0,
                },
            )

        # Log if some datasets were missing
        if missing_datasets:
            logger.warning(
                f"Proceeding with {len(datasets_to_merge)} of {len(params.dataset_keys)} "
                f"requested datasets. Missing: {missing_datasets}"
            )

        try:
            # Convert to DataFrames for easier merging
            dfs_with_keys = []
            for key, dataset in datasets_to_merge:
                if isinstance(dataset, list) and len(dataset) > 0:
                    df = pd.DataFrame(dataset)
                    dfs_with_keys.append((key, df))
                elif isinstance(dataset, pd.DataFrame):
                    dfs_with_keys.append((key, dataset))
                else:
                    logger.warning(f"Dataset '{key}' is empty or invalid type")

            if not dfs_with_keys:
                raise ValueError("No valid dataframes to merge")

            # Track one-to-many statistics
            one_to_many_stats = {}

            # Merge based on strategy
            if params.merge_strategy == "concat":
                logger.info("Using concatenation strategy")
                dfs = [df for _, df in dfs_with_keys]

                # Add provenance if requested
                if params.add_provenance:
                    for key, df in dfs_with_keys:
                        df["_merge_source"] = key
                        if params.provenance_value:
                            df["_provenance"] = params.provenance_value

                merged_df = pd.concat(dfs, ignore_index=True)

            elif params.merge_strategy == "join":
                logger.info(f"Using join strategy with how='{params.join_how}'")

                # Handle different join column configurations
                if params.join_columns:
                    # New format with explicit column mapping
                    first_key, first_df = dfs_with_keys[0]
                    first_col = params.join_columns.get(first_key)
                    if not first_col:
                        raise ValueError(
                            f"No join column specified for dataset '{first_key}'"
                        )

                    merged_df = first_df.copy()
                    if params.add_provenance:
                        merged_df["_merge_source"] = first_key

                    for key, df in dfs_with_keys[1:]:
                        join_col = params.join_columns.get(key)
                        if not join_col:
                            raise ValueError(
                                f"No join column specified for dataset '{key}'"
                            )

                        # Check for one-to-many before merge
                        if join_col in df.columns and first_col in merged_df.columns:
                            pre_merge_len = len(merged_df)
                            temp_merge = pd.merge(
                                merged_df[[first_col]].drop_duplicates(),
                                df[[join_col]].drop_duplicates(),
                                left_on=first_col,
                                right_on=join_col,
                                how=params.join_how,
                            )
                            if len(temp_merge) > pre_merge_len:
                                one_to_many_stats[f"{first_key}-{key}"] = {
                                    "type": "one-to-many",
                                    "expansion_factor": len(temp_merge) / pre_merge_len,
                                    "duplicated_keys": len(temp_merge) - pre_merge_len,
                                }
                                logger.info(
                                    f"Detected one-to-many relationship between {first_key} and {key}"
                                )

                        # Add provenance before merge
                        if params.add_provenance:
                            df = df.copy()
                            df["_merge_source"] = key

                        # Perform the actual merge
                        merged_df = pd.merge(
                            merged_df,
                            df,
                            left_on=first_col,
                            right_on=join_col,
                            how=params.join_how,
                            suffixes=("", f"_{key}"),
                        )

                        # Handle one-to-many based on params
                        if (
                            params.handle_one_to_many != "keep_all"
                            and len(merged_df) > pre_merge_len
                        ):
                            if params.handle_one_to_many == "first":
                                merged_df = merged_df.drop_duplicates(
                                    subset=[first_col], keep="first"
                                )
                            elif params.handle_one_to_many == "aggregate":
                                # Group by the join column and aggregate
                                agg_func = params.aggregate_func or "first"
                                numeric_cols = merged_df.select_dtypes(
                                    include=["number"]
                                ).columns
                                agg_dict = {
                                    col: agg_func
                                    for col in numeric_cols
                                    if col != first_col
                                }
                                non_numeric_cols = [
                                    col
                                    for col in merged_df.columns
                                    if col not in numeric_cols and col != first_col
                                ]
                                for col in non_numeric_cols:
                                    agg_dict[col] = "first"

                                merged_df = (
                                    merged_df.groupby(first_col)
                                    .agg(agg_dict)
                                    .reset_index()
                                )

                elif params.join_on:
                    # Old format with single join column
                    logger.info(f"Using join on column '{params.join_on}'")
                    first_key, first_df = dfs_with_keys[0]
                    merged_df = first_df.copy()

                    if params.add_provenance:
                        merged_df["_merge_source"] = first_key

                    for i, (key, df) in enumerate(dfs_with_keys[1:], 1):
                        # Check for one-to-many
                        if (
                            params.join_on in df.columns
                            and params.join_on in merged_df.columns
                        ):
                            pre_merge_len = len(merged_df)
                            duplicates_in_right = df[params.join_on].duplicated().sum()
                            if duplicates_in_right > 0:
                                one_to_many_stats[f"{first_key}-{key}"] = {
                                    "duplicated_join_keys": duplicates_in_right,
                                    "type": "one-to-many",
                                }

                        if params.add_provenance:
                            df = df.copy()
                            df["_merge_source"] = key

                        merged_df = pd.merge(
                            merged_df,
                            df,
                            on=params.join_on,
                            how=params.join_how,
                            suffixes=("", f"_{i}"),
                        )
                else:
                    # Handle join with separate columns for old format
                    if params.join_column1 and params.join_column2:
                        logger.info(
                            f"Using join with column1='{params.join_column1}', column2='{params.join_column2}'"
                        )
                        first_key, first_df = dfs_with_keys[0]
                        second_key, second_df = (
                            dfs_with_keys[1]
                            if len(dfs_with_keys) > 1
                            else (None, pd.DataFrame())
                        )

                        if second_df.empty:
                            raise ValueError(
                                "Second dataset required for join with different columns"
                            )

                        # Check for one-to-many
                        if params.join_column2 in second_df.columns:
                            duplicates = (
                                second_df[params.join_column2].duplicated().sum()
                            )
                            if duplicates > 0:
                                one_to_many_stats[f"{first_key}-{second_key}"] = {
                                    "duplicated_join_keys": duplicates,
                                    "type": "one-to-many",
                                }

                        if params.add_provenance:
                            first_df = first_df.copy()
                            first_df["_merge_source"] = first_key
                            second_df = second_df.copy()
                            second_df["_merge_source"] = second_key

                        merged_df = pd.merge(
                            first_df,
                            second_df,
                            left_on=params.join_column1,
                            right_on=params.join_column2,
                            how=params.join_how,
                            suffixes=("", f"_{second_key}"),
                        )
                    else:
                        raise ValueError(
                            "join_columns, join_on, or join_column1/2 required for join strategy"
                        )
            else:
                raise ValueError(f"Unknown merge strategy: {params.merge_strategy}")

            # Record pre-deduplication count
            pre_dedup_count = len(merged_df)

            # Deduplication if requested
            duplicates_removed = 0
            if (
                params.deduplication_column
                and params.deduplication_column in merged_df.columns
            ):
                if params.keep != "all":
                    merged_df = merged_df.drop_duplicates(
                        subset=[params.deduplication_column], keep=params.keep
                    )
                    duplicates_removed = pre_dedup_count - len(merged_df)
                    logger.info(
                        f"Deduplication on '{params.deduplication_column}' "
                        f"removed {duplicates_removed} duplicates"
                    )
            elif params.deduplication_column:
                logger.warning(
                    f"Deduplication column '{params.deduplication_column}' "
                    f"not found in merged dataset"
                )

            # Convert back to list of dicts
            merged_data = merged_df.to_dict("records")

            # Store in context
            datasets_store[params.output_key] = merged_data
            ctx.set("datasets", datasets_store)

            logger.info(
                f"Successfully merged {len(datasets_to_merge)} datasets "
                f"into '{params.output_key}' with {len(merged_data)} total rows"
            )

            # Update context statistics with merge info
            stats = ctx.get_statistics()
            stats["merge_statistics"] = {
                "datasets_merged": len(datasets_to_merge),
                "total_rows": len(merged_data),
                "duplicates_removed": duplicates_removed,
                "one_to_many_relationships": one_to_many_stats,
                "pre_dedup_count": pre_dedup_count,
            }
            ctx.set("statistics", stats)

            # Create detailed provenance
            provenance = [
                {
                    "action": "MERGE_DATASETS",
                    "status": "success",
                    "datasets_merged": dataset_keys_used,
                    "datasets_missing": missing_datasets,
                    "total_rows": len(merged_data),
                    "pre_dedup_rows": pre_dedup_count,
                    "duplicates_removed": duplicates_removed,
                    "merge_strategy": params.merge_strategy,
                    "join_how": params.join_how
                    if params.merge_strategy == "join"
                    else None,
                    "deduplication": params.deduplication_column is not None,
                    "one_to_many_stats": one_to_many_stats,
                    "handle_one_to_many": params.handle_one_to_many,
                }
            ]

            return StandardActionResult(
                input_identifiers=current_identifiers,
                output_identifiers=[],  # Not used for dataset operations
                output_ontology_type=current_ontology_type,
                provenance=provenance,
                details={
                    "datasets_merged": len(datasets_to_merge),
                    "datasets_requested": len(params.dataset_keys),
                    "total_rows": len(merged_data),
                    "duplicates_removed": duplicates_removed,
                    "output_key": params.output_key,
                    "columns": list(merged_df.columns) if len(merged_df) > 0 else [],
                    "one_to_many_stats": one_to_many_stats,
                    "merge_strategy": params.merge_strategy,
                    "join_how": params.join_how
                    if params.merge_strategy == "join"
                    else None,
                },
            )

        except Exception as e:
            error_msg = f"Error during merge: {str(e)}"
            logger.error(error_msg, exc_info=True)

            return StandardActionResult(
                input_identifiers=current_identifiers,
                output_identifiers=[],
                output_ontology_type=current_ontology_type,
                provenance=[
                    {"action": "MERGE_DATASETS", "status": "failed", "error": error_msg}
                ],
                details={
                    "error": error_msg,
                    "datasets_found": len(datasets_to_merge),
                    "datasets_requested": len(params.dataset_keys),
                },
            )
