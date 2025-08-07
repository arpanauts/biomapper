"""Merge multiple datasets with deduplication support."""

from typing import List, Any, Optional
from pydantic import BaseModel, Field
import pandas as pd
import logging

from biomapper.core.strategy_actions.typed_base import (
    TypedStrategyAction,
    StandardActionResult,
)
from biomapper.core.strategy_actions.registry import register_action

logger = logging.getLogger(__name__)


class MergeDatasetsParams(BaseModel):
    """Parameters for MERGE_DATASETS action."""

    dataset_keys: List[str] = Field(
        ..., description="List of dataset keys to merge from context"
    )
    output_key: str = Field(..., description="Key for storing merged dataset")
    deduplication_column: Optional[str] = Field(
        None, description="Column to use for deduplication"
    )
    keep: str = Field(
        "first",
        description="Which duplicate to keep: 'first', 'last', or 'all'",
        pattern="^(first|last|all)$",
    )
    merge_strategy: str = Field(
        "concat",
        description="How to merge: 'concat' or 'join'",
        pattern="^(concat|join)$",
    )
    join_on: Optional[str] = Field(
        None, description="Column to join on when using 'join' strategy"
    )
    join_how: str = Field(
        "outer", description="Join type: 'inner', 'outer', 'left', 'right'"
    )


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

        # Get datasets from context
        datasets_store = context.get_action_data("datasets", {})

        # Collect datasets to merge
        datasets_to_merge = []
        missing_datasets = []

        for key in params.dataset_keys:
            if key in datasets_store:
                dataset = datasets_store[key]
                datasets_to_merge.append(dataset)
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
            dfs = []
            for i, dataset in enumerate(datasets_to_merge):
                if isinstance(dataset, list) and len(dataset) > 0:
                    df = pd.DataFrame(dataset)
                    dfs.append(df)
                elif isinstance(dataset, pd.DataFrame):
                    dfs.append(dataset)
                else:
                    logger.warning(f"Dataset at index {i} is empty or invalid type")

            if not dfs:
                raise ValueError("No valid dataframes to merge")

            # Merge based on strategy
            if params.merge_strategy == "concat":
                logger.info("Using concatenation strategy")
                merged_df = pd.concat(dfs, ignore_index=True)
            elif params.merge_strategy == "join":
                logger.info(f"Using join strategy on column '{params.join_on}'")
                if not params.join_on:
                    raise ValueError("join_on parameter required for join strategy")

                # Start with first dataframe
                merged_df = dfs[0]
                for i, df in enumerate(dfs[1:], 1):
                    # Add suffix to avoid column conflicts
                    merged_df = pd.merge(
                        merged_df,
                        df,
                        on=params.join_on,
                        how=params.join_how,
                        suffixes=("", f"_{i}"),
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
            context.set_action_data("datasets", datasets_store)

            logger.info(
                f"Successfully merged {len(datasets_to_merge)} datasets "
                f"into '{params.output_key}' with {len(merged_data)} total rows"
            )

            # Create detailed provenance
            provenance = [
                {
                    "action": "MERGE_DATASETS",
                    "status": "success",
                    "datasets_merged": [
                        k for k in params.dataset_keys if k not in missing_datasets
                    ],
                    "datasets_missing": missing_datasets,
                    "total_rows": len(merged_data),
                    "pre_dedup_rows": pre_dedup_count,
                    "duplicates_removed": duplicates_removed,
                    "merge_strategy": params.merge_strategy,
                    "deduplication": params.deduplication_column is not None,
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
