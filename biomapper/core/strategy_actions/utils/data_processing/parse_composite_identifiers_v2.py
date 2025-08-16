"""Parse composite identifiers into separate rows."""

import logging
from typing import Dict, Any, List
from pydantic import BaseModel, Field
import pandas as pd

from biomapper.core.strategy_actions.typed_base import TypedStrategyAction
from biomapper.core.strategy_actions.registry import register_action

logger = logging.getLogger(__name__)


class ParseCompositeIdentifiersParams(BaseModel):
    """Parameters for parsing composite identifiers."""

    input_key: str = Field(..., description="Input dataset key")
    id_field: str = Field(..., description="Field containing identifiers")
    separators: List[str] = Field(
        default=[","], description="List of separators to split on"
    )
    output_key: str = Field(..., description="Output dataset key")
    track_expansion: bool = Field(
        default=False, description="Track expansion statistics"
    )
    skip_empty: bool = Field(default=False, description="Skip empty/null values")
    trim_whitespace: bool = Field(
        default=True, description="Trim whitespace from parsed IDs"
    )
    preserve_order: bool = Field(
        default=True, description="Preserve original row order with indices"
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
class ParseCompositeIdentifiersAction(
    TypedStrategyAction[
        ParseCompositeIdentifiersParams, ParseCompositeIdentifiersResult
    ]
):
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
        self, params: ParseCompositeIdentifiersParams, context: Dict[str, Any]
    ) -> ParseCompositeIdentifiersResult:
        """Execute the composite identifier parsing."""
        try:
            # Handle different context types
            ctx = self._get_context_dict(context)

            # Get input data
            if params.dataset_key not in ctx.get("datasets", {}):
                return ParseCompositeIdentifiersResult(
                    success=False,
                    message=f"Dataset '{params.dataset_key}' not found in context",
                )

            input_data = ctx["datasets"][params.dataset_key]

            if not input_data:
                return ParseCompositeIdentifiersResult(
                    success=False, message="Input dataset is empty"
                )

            # Convert to DataFrame for easier processing
            df = pd.DataFrame(input_data)

            # Check if field exists
            if params.id_field not in df.columns:
                return ParseCompositeIdentifiersResult(
                    success=False,
                    message=f"Field '{params.id_field}' not found in dataset",
                )

            # Process the data
            expanded_df = self._expand_composite_ids(df, params)

            # Calculate statistics
            rows_processed = len(df)
            rows_expanded = len(expanded_df)
            composite_count = self._count_composites(df, params)
            expansion_factor = (
                rows_expanded / rows_processed if rows_processed > 0 else 1.0
            )

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
                message="Successfully parsed composite identifiers",
                rows_processed=rows_processed,
                rows_expanded=rows_expanded,
                composite_count=composite_count,
                expansion_factor=expansion_factor,
            )

        except Exception as e:
            logger.error(f"Error parsing composite identifiers: {str(e)}")
            return ParseCompositeIdentifiersResult(
                success=False, message=f"Error: {str(e)}"
            )

    def _get_context_dict(self, context: Any) -> Dict[str, Any]:
        """Get dictionary from context, handling different types."""
        if isinstance(context, dict):
            return context
        elif hasattr(context, "_dict"):  # MockContext
            return context._dict
        else:
            # Try to adapt other context types
            return {"datasets": {}, "statistics": {}}

    def _expand_composite_ids(
        self, df: pd.DataFrame, params: ParseCompositeIdentifiersParams
    ) -> pd.DataFrame:
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
                # Don't add composite tracking fields for single IDs
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

    def _count_composites(
        self, df: pd.DataFrame, params: ParseCompositeIdentifiersParams
    ) -> int:
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
        composite_count: int,
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
            "expansion_factor": len(expanded_df) / len(original_df)
            if len(original_df) > 0
            else 1.0,
            "max_components": max_components,
            "separators_used": params.separators,
        }
