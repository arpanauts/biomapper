"""
PARSE_COMPOSITE_IDENTIFIERS action for splitting composite identifier strings.

This action splits composite identifier strings (e.g., "P12345,Q67890") into 
individual identifiers, handling various separator patterns and providing 
flexible output formats.
"""

import re
from typing import Any, Dict, List, Optional, Literal
from pydantic import BaseModel, Field

from biomapper.core.strategy_actions.registry import register_action
from biomapper.core.strategy_actions.typed_base import TypedStrategyAction


class CompositePattern(BaseModel):
    """Pattern configuration for splitting composite identifiers."""

    separator: str = Field(..., description="Separator character(s) to split on")
    trim_whitespace: bool = Field(
        default=True, description="Trim whitespace from split values"
    )
    remove_empty: bool = Field(
        default=True, description="Remove empty values after splitting"
    )


class ParseCompositeIdentifiersParams(BaseModel):
    """Parameters for PARSE_COMPOSITE_IDENTIFIERS action."""

    input_key: str = Field(
        ..., description="Key of the dataset in context to process"
    )
    id_field: Optional[str] = Field(
        None,
        description="Field containing identifiers to parse. If None, assumes list of strings",
    )
    patterns: List[CompositePattern] = Field(
        default=[CompositePattern(separator=",")],
        description="Patterns to apply for splitting, in order",
    )
    output_format: Literal["flat", "mapped", "detailed"] = Field(
        default="flat",
        description="Output format: 'flat' (expanded rows), 'mapped' (original->split), 'detailed' (full info)",
    )
    output_key: str = Field(
        ..., description="Key to store parsed results in context"
    )
    preserve_original: bool = Field(
        default=True,
        description="Keep original composite ID in _original_{field} column",
    )
    validate_format: bool = Field(
        default=False, description="Whether to validate identifier format"
    )
    entity_type: Optional[Literal["uniprot", "ensembl", "gene"]] = Field(
        None, description="Entity type for validation (if validate_format=True)"
    )
    continue_on_error: bool = Field(
        default=True, description="Continue processing on errors"
    )


class ParseCompositeIdentifiersResult(BaseModel):
    """Result of parsing composite identifiers."""

    success: bool
    message: str
    data: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


def parse_composite_string(
    identifier: Any, separators: List[str] = [",", "|", ";"]
) -> List[str]:
    """
    Parse a composite identifier string into individual IDs.

    Args:
        identifier: String potentially containing multiple IDs
        separators: List of separator characters to try in order

    Returns:
        List of individual identifiers

    Examples:
        >>> parse_composite_string("P12345,Q67890")
        ["P12345", "Q67890"]
        >>> parse_composite_string("A12345")
        ["A12345"]
    """
    if identifier is None or identifier == "":
        return []

    identifier = str(identifier)

    # Try each separator
    for separator in separators:
        if separator in identifier:
            # Split and clean
            parts = identifier.split(separator)
            cleaned = []
            for part in parts:
                part = part.strip()
                if part:  # Skip empty values
                    cleaned.append(part)
            return cleaned

    # No separator found, return as single item
    return [identifier.strip()] if identifier.strip() else []


def expand_dataset_rows(
    data: List[Dict[str, Any]],
    id_field: str,
    parsed_ids_field: str = "_parsed_ids",
    separators: List[str] = [",", "|", ";"],
) -> List[Dict[str, Any]]:
    """
    Expand dataset rows for composite identifiers.

    Args:
        data: List of dictionaries containing the data
        id_field: Field containing the identifier(s)
        parsed_ids_field: Field to store parsed IDs
        separators: List of separators to try

    Returns:
        Expanded dataset with one row per identifier

    Example:
        Input: [{"uniprot": "P1,P2", "gene": "G1"}]
        Output: [
            {"uniprot": "P1", "gene": "G1", "_original_uniprot": "P1,P2"},
            {"uniprot": "P2", "gene": "G1", "_original_uniprot": "P1,P2"}
        ]
    """
    expanded_rows = []

    for row in data:
        original_value = row.get(id_field)

        # Parse the identifier
        parsed_ids = parse_composite_string(original_value, separators)

        if not parsed_ids:
            # Keep row with empty/null value
            new_row = row.copy()
            # Keep original (empty) value in main field
            new_row[id_field] = original_value
            # No parsed value
            new_row[f"parsed_{id_field}"] = None
            # Mark as not composite
            new_row[f"is_composite_{id_field}"] = False
            new_row[parsed_ids_field] = []
            expanded_rows.append(new_row)
        elif len(parsed_ids) == 1:
            # Single ID, no expansion needed
            new_row = row.copy()
            # Keep original value in main field
            new_row[id_field] = original_value
            # Add parsed value for matching
            new_row[f"parsed_{id_field}"] = parsed_ids[0]
            # Mark as not composite
            new_row[f"is_composite_{id_field}"] = False
            new_row[parsed_ids_field] = parsed_ids
            expanded_rows.append(new_row)
        else:
            # Multiple IDs, expand to multiple rows but preserve original composite
            for parsed_id in parsed_ids:
                new_row = row.copy()
                # Keep original composite value in main field
                new_row[id_field] = original_value
                # Add parsed value for matching
                new_row[f"parsed_{id_field}"] = parsed_id
                # Mark as composite
                new_row[f"is_composite_{id_field}"] = True
                new_row[parsed_ids_field] = parsed_ids
                expanded_rows.append(new_row)

    return expanded_rows


def validate_uniprot_format(identifier: str) -> bool:
    """
    Validate UniProt accession format.
    Pattern: [OPQ][0-9][A-Z0-9]{3}[0-9]|[A-NR-Z][0-9]([A-Z][A-Z0-9]{2}[0-9]){1,2}
    """
    pattern = (
        r"^([OPQ][0-9][A-Z0-9]{3}[0-9]|[A-NR-Z][0-9]([A-Z][A-Z0-9]{2}[0-9]){1,2})$"
    )
    return bool(re.match(pattern, identifier))


@register_action("PARSE_COMPOSITE_IDENTIFIERS")
class ParseCompositeIdentifiersAction(
    TypedStrategyAction[
        ParseCompositeIdentifiersParams, ParseCompositeIdentifiersResult
    ]
):
    """
    Parse composite identifiers into individual components.

    This action handles the complex task of splitting composite identifier strings
    (e.g., "P12345,Q67890") into individual identifiers, with support for various
    separator patterns and output formats.

    Features:
    - Multiple separator patterns (comma, pipe, semicolon, etc.)
    - Row expansion for one-to-many mappings
    - Optional identifier validation
    - Comprehensive statistics tracking
    - Preserves original composite values for traceability
    """

    def get_params_model(self) -> type[ParseCompositeIdentifiersParams]:
        """Return the parameters model for this action."""
        return ParseCompositeIdentifiersParams

    def get_result_model(self) -> type[ParseCompositeIdentifiersResult]:
        """Return the result model for this action."""
        return ParseCompositeIdentifiersResult

    async def execute_typed(
        self,
        current_identifiers: List[str],
        current_ontology_type: str,
        params: ParseCompositeIdentifiersParams,
        source_endpoint: Any,
        target_endpoint: Any,
        context: Any
    ) -> ParseCompositeIdentifiersResult:
        """
        Execute the composite identifier parsing.

        Args:
            params: Action parameters
            context: Execution context containing datasets

        Returns:
            ParseCompositeIdentifiersResult with parsed identifiers
        """
        # Handle context types - simplified approach
        if isinstance(context, dict):
            ctx = context
            if "datasets" not in ctx:
                ctx["datasets"] = {}
            if "statistics" not in ctx:
                ctx["statistics"] = {}
        elif hasattr(context, "_dict"):
            # MockContext
            ctx = context._dict
            if "datasets" not in ctx:
                ctx["datasets"] = {}
            if "statistics" not in ctx:
                ctx["statistics"] = {}
        else:
            # StrategyExecutionContext - access data directly
            ctx = {
                "datasets": context.get_action_data("datasets", {}),
                "statistics": context.get_action_data("statistics", {}),
                "output_files": context.get_action_data("output_files", {}),
                "current_identifiers": context.get_action_data("current_identifiers", [])
            }

        # Validate input
        if params.input_key not in ctx["datasets"]:
            available_keys = list(ctx["datasets"].keys())
            raise KeyError(
                f"Dataset key '{params.input_key}' not found in context. Available keys: {available_keys}"
            )

        # Get input data
        input_data = ctx["datasets"][params.input_key]

        # Convert to list of dicts if needed
        if not isinstance(input_data, list):
            # Might be a DataFrame
            try:
                import pandas as pd

                if isinstance(input_data, pd.DataFrame):
                    input_data = input_data.to_dict("records")
                else:
                    raise TypeError(f"Unsupported data type: {type(input_data)}")
            except ImportError:
                raise TypeError(f"Unsupported data type: {type(input_data)}")

        # Extract separators from patterns
        separators = [p.separator for p in params.patterns]

        # Process based on output format
        if params.output_format == "flat":
            # Expand rows for composite identifiers
            if params.id_field:
                expanded_data = expand_dataset_rows(
                    input_data, params.id_field, separators=separators
                )

                # Validate if requested
                if params.validate_format and params.entity_type == "uniprot":
                    validated_data = []
                    invalid_count = 0
                    for row in expanded_data:
                        if validate_uniprot_format(row[params.id_field]):
                            validated_data.append(row)
                        else:
                            invalid_count += 1
                            if not params.continue_on_error:
                                raise ValueError(
                                    f"Invalid UniProt ID: {row[params.id_field]}"
                                )
                    expanded_data = validated_data
            else:
                # Assume list of strings
                all_ids = []
                for item in input_data:
                    parsed = parse_composite_string(item, separators)
                    all_ids.extend(parsed)
                expanded_data = [{"id": id_val} for id_val in all_ids]

            output_data = expanded_data

        elif params.output_format == "mapped":
            # Create mapping of original -> parsed
            mapping = {}
            if params.id_field:
                for row in input_data:
                    original = row.get(params.id_field)
                    if original:
                        parsed = parse_composite_string(original, separators)
                        if len(parsed) > 1:  # Only include composite IDs
                            mapping[str(original)] = parsed
            else:
                for item in input_data:
                    parsed = parse_composite_string(item, separators)
                    if len(parsed) > 1:
                        mapping[str(item)] = parsed
            output_data = mapping

        else:  # detailed
            # Return full parsing details
            detailed_results = []
            if params.id_field:
                for row in input_data:
                    original = row.get(params.id_field)
                    parsed = (
                        parse_composite_string(original, separators) if original else []
                    )
                    detailed_results.append(
                        {
                            "original": original,
                            "parsed": parsed,
                            "is_composite": len(parsed) > 1,
                            "count": len(parsed),
                        }
                    )
            else:
                for item in input_data:
                    parsed = parse_composite_string(item, separators)
                    detailed_results.append(
                        {
                            "original": item,
                            "parsed": parsed,
                            "is_composite": len(parsed) > 1,
                            "count": len(parsed),
                        }
                    )
            output_data = detailed_results

        # Store output - handle both dict and Pydantic context
        if isinstance(context, dict) or hasattr(context, "_dict"):
            ctx["datasets"][params.output_key] = output_data
        else:
            # StrategyExecutionContext - store data directly
            updated_datasets = {**ctx["datasets"], params.output_key: output_data}
            context.set_action_data("datasets", updated_datasets)

        # Calculate statistics
        total_input = len(input_data)
        composite_count = 0
        individual_count = 0
        pattern_usage = {sep: 0 for sep in separators}

        if params.output_format == "flat" and params.id_field:
            individual_count = len(output_data)
            # Count composites from original data
            for row in input_data:
                original = row.get(params.id_field)
                if original:
                    parsed = parse_composite_string(original, separators)
                    if len(parsed) > 1:
                        composite_count += 1
                        # Track which separator was used
                        for sep in separators:
                            if sep in str(original):
                                pattern_usage[sep] += 1
                                break
        elif params.output_format == "mapped":
            # output_data is a dict for mapped format
            if isinstance(output_data, dict):
                composite_count = len(output_data)
                individual_count = sum(len(ids) for ids in output_data.values())
        else:  # detailed
            # output_data is a list of dicts for detailed format
            if isinstance(output_data, list):
                for result in output_data:
                    if result["is_composite"]:
                        composite_count += 1
                    individual_count += result["count"]

        # Update statistics
        stats = {
            "total_input": total_input,
            "composite_count": composite_count,
            "individual_count": individual_count,
            "expansion_factor": individual_count / total_input
            if total_input > 0
            else 1.0,
            "patterns_used": {k: v for k, v in pattern_usage.items() if v > 0},
        }

        # Store statistics - handle both dict and Pydantic context
        if isinstance(context, dict) or hasattr(context, "_dict"):
            if "statistics" not in ctx:
                ctx["statistics"] = {}
            ctx["statistics"]["composite_tracking"] = stats
        else:
            # StrategyExecutionContext - store statistics directly
            current_stats = context.get_action_data("statistics", {})
            current_stats["composite_tracking"] = stats
            context.set_action_data("statistics", current_stats)

        return ParseCompositeIdentifiersResult(
            success=True,
            message=f"Parsed {total_input} items: {composite_count} composites expanded to {individual_count} individuals",
            data={params.output_key: output_data},
            metadata={
                "action": "PARSE_COMPOSITE_IDENTIFIERS",
                "parameters": params.dict(),
                "statistics": stats,
            },
        )
