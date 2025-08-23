"""Parse composite identifiers into separate rows."""

import logging
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
import pandas as pd

from actions.typed_base import TypedStrategyAction
from actions.registry import register_action

logger = logging.getLogger(__name__)


class ParseCompositeIdentifiersParams(BaseModel):
    """Parameters for parsing composite identifiers."""

    # Standard parameter names for compatibility
    input_key: Optional[str] = Field(default=None, description="Input dataset key")
    input_context_key: Optional[str] = Field(default=None, description="Input dataset key (alias)")
    dataset_key: Optional[str] = Field(default=None, description="Input dataset key (backward compat)")
    
    id_field: str = Field(..., description="Field containing identifiers")
    
    # Pattern support
    separators: Optional[List[str]] = Field(
        default=None, description="List of separators to split on"
    )
    patterns: Optional[List['CompositePattern']] = Field(
        default=None, description="List of patterns for parsing"
    )
    
    # Output configuration
    output_key: Optional[str] = Field(default=None, description="Output dataset key")
    output_context_key: Optional[str] = Field(default=None, description="Output dataset key (alias)")
    output_format: str = Field(default="flat", description="Output format")
    
    # Processing options
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
    preserve_original: bool = Field(
        default=False, description="Preserve original composite values"
    )
    track_entity_identity: bool = Field(
        default=False, description="Track composite entities as single units for statistics"
    )
    
    # Validation options
    validate_format: bool = Field(default=False, description="Validate ID format")
    entity_type: Optional[str] = Field(default=None, description="Entity type for validation")
    
    class Config:
        extra = "allow"  # Allow extra fields for flexibility


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

    async def execute_typed(  # type: ignore[override]
        self, params: ParseCompositeIdentifiersParams, context: Any, **kwargs
    ) -> ParseCompositeIdentifiersResult:
        """Execute the composite identifier parsing."""
        try:
            # Use UniversalContext for consistent handling
            from core.standards.context_handler import UniversalContext
            ctx = UniversalContext.wrap(context)

            # Get input key (handle multiple parameter names)
            input_key = params.input_key or params.input_context_key or params.dataset_key
            if not input_key:
                return ParseCompositeIdentifiersResult(
                    success=False,
                    message="No input dataset key specified",
                )
            
            # Get output key
            output_key = params.output_key or params.output_context_key
            if not output_key:
                return ParseCompositeIdentifiersResult(
                    success=False,
                    message="No output dataset key specified",
                )
            
            # Get input data
            datasets = ctx.get_datasets()
            if input_key not in datasets:
                # Raise KeyError for backward compatibility with tests
                raise KeyError(f"Dataset '{input_key}' not found in context")

            input_data = datasets[input_key]

            if len(input_data) == 0:
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

            # Get separators from patterns or direct parameter
            separators = self._get_separators(params)
            
            # Add debug logging
            logger.info(f"Parsing composite identifiers in column '{params.id_field}'")
            logger.info(f"Input dataset has {len(df)} rows with columns: {list(df.columns)}")
            
            # Process the data
            expanded_df = self._expand_composite_ids(df, params, separators)

            # Calculate statistics
            rows_processed = len(df)
            rows_expanded = len(expanded_df)
            composite_count = self._count_composites(df, params, separators)
            expansion_factor = (
                rows_expanded / rows_processed if rows_processed > 0 else 1.0
            )
            
            # More debug logging
            logger.info(f"Found {composite_count} composite IDs, expanded to {rows_expanded} rows")
            if composite_count > 0:
                # Show sample of composite IDs
                composite_samples = []
                for _, row in df.iterrows():
                    id_val = row[params.id_field]
                    if pd.notna(id_val) and any(sep in str(id_val) for sep in separators):
                        composite_samples.append(str(id_val))
                        if len(composite_samples) >= 5:
                            break
                logger.info(f"Sample composite IDs: {composite_samples}")
            
            logger.info(f"Output dataset columns: {list(expanded_df.columns)}")

            # Track statistics (always track for test compatibility)
            self._track_statistics_universal(ctx, df, expanded_df, params, composite_count, separators)

            # Store result using UniversalContext
            datasets = ctx.get_datasets()
            datasets[output_key] = expanded_df.to_dict("records")
            ctx.set("datasets", datasets)

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

        except KeyError:
            # Re-raise KeyError for backward compatibility with tests
            raise
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
            # Use UniversalContext to handle pydantic and other context types
            from core.standards.context_handler import UniversalContext
            ctx = UniversalContext.wrap(context)
            # Build a dict view from the context
            result = {
                "datasets": ctx.get_datasets(),
                "statistics": ctx.get_statistics(),
            }
            # Add any other keys from the context
            if hasattr(context, 'custom_action_data'):
                for key, value in context.custom_action_data.items():
                    if key not in result:
                        result[key] = value
            return result

    def _get_separators(self, params: ParseCompositeIdentifiersParams) -> List[str]:
        """Get separators from patterns or direct parameter."""
        separators = []
        
        # Check patterns first
        if params.patterns:
            for pattern in params.patterns:
                if hasattr(pattern, 'separator'):
                    separators.append(pattern.separator)
        
        # Fall back to separators parameter
        if not separators and params.separators:
            separators = params.separators
        
        # Default to comma if nothing specified
        if not separators:
            separators = [',']
        
        return separators
    
    def _expand_composite_ids(
        self, df: pd.DataFrame, params: ParseCompositeIdentifiersParams, separators: List[str]
    ) -> pd.DataFrame:
        """Expand rows with composite identifiers."""
        expanded_rows = []

        for idx, row in df.iterrows():
            id_value = row[params.id_field]

            # Handle empty/null values
            if pd.isna(id_value) or id_value == "":
                if not params.skip_empty:
                    expanded_rows.append(row.to_dict())
                continue

            # Parse composite IDs
            id_str = str(id_value)
            components = self._split_by_separators(id_str, separators)

            if params.trim_whitespace:
                components = [c.strip() for c in components]
            
            # Validate format if requested
            if params.validate_format and params.entity_type == "uniprot":
                # Simple UniProt validation - 6-10 alphanumeric characters
                import re
                uniprot_pattern = re.compile(r'^[A-Z][0-9][A-Z0-9]{3,8}$')
                components = [c for c in components if uniprot_pattern.match(c)]
                if not components:
                    continue  # Skip if no valid components

            # Create a row for each component
            if len(components) > 1:
                # Composite ID - expand
                entity_weight = 1.0 / len(components) if params.track_entity_identity else 1.0
                for component in components:
                    row_dict = row.to_dict()
                    row_dict[params.id_field] = component
                    if params.preserve_original:
                        row_dict[f"_original_{params.id_field}"] = id_str
                    row_dict["_expansion_count"] = len(components)
                    if params.preserve_order:
                        row_dict["_original_index"] = idx
                    # Track composite entity identity
                    if params.track_entity_identity:
                        row_dict["_composite_entity_id"] = id_str
                        row_dict["_entity_weight"] = entity_weight
                        row_dict["_is_composite_component"] = True
                    expanded_rows.append(row_dict)
            else:
                # Single ID - keep as is
                row_dict = row.to_dict()
                if params.preserve_order:
                    row_dict["_original_index"] = idx
                if params.preserve_original and components:
                    row_dict[f"_original_{params.id_field}"] = id_str
                # Mark as non-composite for entity tracking
                if params.track_entity_identity:
                    row_dict["_composite_entity_id"] = None
                    row_dict["_entity_weight"] = 1.0
                    row_dict["_is_composite_component"] = False
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
        self, df: pd.DataFrame, params: ParseCompositeIdentifiersParams, separators: List[str]
    ) -> int:
        """Count rows with composite identifiers."""
        count = 0

        for _, row in df.iterrows():
            id_value = row[params.id_field]
            if pd.notna(id_value) and id_value != "":
                id_str = str(id_value)
                components = self._split_by_separators(id_str, separators)
                if len(components) > 1:
                    count += 1

        return count

    def _track_statistics_universal(
        self,
        ctx,  # UniversalContext
        original_df: pd.DataFrame,
        expanded_df: pd.DataFrame,
        params: ParseCompositeIdentifiersParams,
        composite_count: int,
        separators: List[str],
    ):
        """Track expansion statistics in context using UniversalContext."""
        # Calculate max components
        max_components = 1
        patterns_used = {}
        
        for _, row in original_df.iterrows():
            id_value = row[params.id_field]
            if pd.notna(id_value) and id_value != "":
                components = self._split_by_separators(str(id_value), separators)
                max_components = max(max_components, len(components))
                
                # Track which separators were actually used
                for sep in separators:
                    if sep in str(id_value):
                        patterns_used[sep] = patterns_used.get(sep, 0) + 1

        # Store statistics using UniversalContext
        statistics = ctx.get_statistics()

        # Store in format expected by tests
        statistics["composite_tracking"] = {
            "total_input": len(original_df),
            "composite_count": composite_count,
            "individual_count": len(expanded_df),
            "expansion_factor": len(expanded_df) / len(original_df)
            if len(original_df) > 0
            else 1.0,
            "patterns_used": patterns_used,
        }
        
        # Also store detailed expansion stats
        input_key = params.input_key or params.input_context_key or params.dataset_key
        statistics["composite_expansion"] = {
            "dataset_key": input_key,
            "field": params.id_field,
            "total_input_rows": len(original_df),
            "total_output_rows": len(expanded_df),
            "rows_with_composites": composite_count,
            "expansion_factor": len(expanded_df) / len(original_df)
            if len(original_df) > 0
            else 1.0,
            "max_components": max_components,
            "separators_used": separators,
        }
        
        # Write statistics back to context
        ctx.set("statistics", statistics)

    def _track_statistics(
        self,
        context: Dict[str, Any],
        original_df: pd.DataFrame,
        expanded_df: pd.DataFrame,
        params: ParseCompositeIdentifiersParams,
        composite_count: int,
        separators: List[str],
    ):
        """Track expansion statistics in context (backward compatibility)."""
        # Wrap dict context and delegate to universal version
        from core.standards.context_handler import UniversalContext
        ctx = UniversalContext.wrap(context)
        self._track_statistics_universal(ctx, original_df, expanded_df, params, composite_count, separators)

# Export compatibility functions for testing
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class CompositePattern(BaseModel):
    """Pattern for parsing composite identifiers."""
    separator: str = Field(default=",", description="Separator character")
    trim_whitespace: bool = Field(default=True, description="Trim whitespace")
    column: Optional[str] = Field(default=None, description="Column to parse")
    validation_pattern: Optional[str] = Field(default=None, description="Validation regex")

def parse_composite_string(value: Any, separators: List[str] = None) -> List[str]:
    """Parse a composite string into individual components.
    
    Args:
        value: The value to parse (string or None)
        separators: List of separators to use. Defaults to [',']
        
    Returns:
        List of parsed components
    """
    # Handle empty/None values
    if value is None or value == "":
        return []
    
    # Convert to string
    value_str = str(value).strip()
    if not value_str:
        return []
    
    # Default separator
    if separators is None:
        separators = [","]
    
    # Find the first separator that exists in the string
    # This matches the test expectation that only the first matching separator is used
    for separator in separators:
        if separator in value_str:
            # Split only by this separator
            parts = value_str.split(separator)
            # Clean up - remove empty strings and trim whitespace
            result = []
            for part in parts:
                cleaned = part.strip()
                if cleaned:  # Skip empty strings
                    result.append(cleaned)
            return result if result else [value_str.strip()]
    
    # No separator found - return original string
    return [value_str.strip()]

def expand_dataset_rows(data: List[Dict[str, Any]], field: str, separator: str = ",") -> List[Dict[str, Any]]:
    """Expand dataset rows with composite identifiers.
    
    Args:
        data: List of dictionaries representing rows
        field: Field name containing composite identifiers
        separator: Separator character (default ',')
        
    Returns:
        Expanded list of rows
    """
    if not data:
        return []
    
    expanded_rows = []
    
    for row in data:
        value = row.get(field, "")
        
        # Handle empty/null values
        if value is None or value == "":
            # Keep the row as-is for empty values
            new_row = row.copy()
            new_row["_original_" + field] = value
            new_row["_parsed_ids"] = []
            expanded_rows.append(new_row)
            continue
        
        # Parse the composite value
        parsed_ids = parse_composite_string(value, [separator])
        
        if len(parsed_ids) > 1:
            # Composite ID - expand into multiple rows
            for parsed_id in parsed_ids:
                new_row = row.copy()
                new_row[field] = parsed_id
                new_row["_original_" + field] = value
                new_row["_parsed_ids"] = parsed_ids
                expanded_rows.append(new_row)
        else:
            # Single ID - keep as is
            new_row = row.copy()
            new_row["_original_" + field] = value
            new_row["_parsed_ids"] = parsed_ids
            expanded_rows.append(new_row)
    
    return expanded_rows

