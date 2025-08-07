"""METABOLITE_NORMALIZE_HMDB action for standardizing HMDB identifier formats.

This action normalizes HMDB (Human Metabolome Database) identifiers to a consistent format.
HMDB IDs come in various formats that need standardization for successful matching:
- HMDB1234 (4-digit old format)
- HMDB01234 (5-digit format)
- HMDB0001234 (7-digit current standard)
- Just the numeric part: 1234
- Various prefixes: HMDB:, HMDB_, HMDB-
"""

import re
import logging
from typing import Any, List, Optional, Literal
import pandas as pd
from pydantic import BaseModel, Field

from biomapper.core.strategy_actions.typed_base import (
    TypedStrategyAction,
    StandardActionResult as ActionResult,
)
from biomapper.core.strategy_actions.registry import register_action
from biomapper.core.exceptions import BiomapperError

logger = logging.getLogger(__name__)


def clean_hmdb_prefix(hmdb_id: str) -> str:
    """Clean various HMDB prefix formats.

    Args:
        hmdb_id: HMDB ID with potential prefix variations

    Returns:
        Cleaned HMDB ID with standard prefix
    """
    id_str = str(hmdb_id).strip().upper()

    # Remove common prefix variations
    prefixes = ["HMDB:", "HMDB_", "HMDB-"]
    for prefix in prefixes:
        if id_str.startswith(prefix):
            return "HMDB" + id_str[len(prefix) :]

    return id_str


def extract_hmdb_number(hmdb_id: str) -> Optional[int]:
    """Extract numeric part of HMDB ID for validation.

    Args:
        hmdb_id: HMDB ID string

    Returns:
        Numeric part as integer, or None if invalid
    """
    if not hmdb_id or not hmdb_id.startswith("HMDB"):
        return None

    try:
        numeric_part = hmdb_id[4:]
        return int(numeric_part)
    except (ValueError, IndexError):
        return None


def validate_hmdb_format(hmdb_id: Any) -> bool:
    """Validate HMDB ID format.

    Args:
        hmdb_id: HMDB ID to validate

    Returns:
        True if valid HMDB format, False otherwise
    """
    if pd.isna(hmdb_id) or hmdb_id is None:
        return False

    id_str = str(hmdb_id).strip().upper()

    # Valid patterns: HMDB followed by 4-7 digits
    pattern = r"^HMDB\d{4,7}$"
    return bool(re.match(pattern, id_str))


def normalize_hmdb_id(hmdb_id: Any, target_format: str = "7digit") -> Optional[str]:
    """Normalize HMDB ID to standard format.

    Args:
        hmdb_id: HMDB ID in any format
        target_format: Target padding format ('7digit', '5digit', 'minimal')

    Returns:
        Normalized HMDB ID or None if invalid
    """
    # Handle missing values
    if pd.isna(hmdb_id) or hmdb_id is None:
        return hmdb_id

    # Convert to string and clean
    id_str = str(hmdb_id).strip()

    # Handle empty string
    if not id_str:
        return None

    # Clean prefix variations
    id_str = clean_hmdb_prefix(id_str)
    id_str = id_str.upper()

    # Extract numeric part
    if id_str.startswith("HMDB"):
        numeric_part = id_str[4:]
    else:
        # Check if it could be a valid HMDB without prefix
        # If it doesn't look like just a number, return None
        if not id_str.isdigit():
            return None
        numeric_part = id_str

    # Remove any non-digits
    numeric_part = re.sub(r"[^\d]", "", numeric_part)

    # Handle empty numeric part
    if not numeric_part:
        return None

    # Check if it's a valid number
    try:
        int(numeric_part)
    except ValueError:
        return None

    # Apply target format padding
    if target_format == "7digit":
        # Truncate if longer than 7 digits (handle edge case)
        if len(numeric_part) > 7:
            numeric_part = numeric_part[:7]
        return f"HMDB{numeric_part.zfill(7)}"
    elif target_format == "5digit":
        # Truncate if longer than 5 digits
        if len(numeric_part) > 5:
            numeric_part = numeric_part[:5]
        return f"HMDB{numeric_part.zfill(5)}"
    else:  # minimal
        return f"HMDB{numeric_part}"


def handle_secondary_accessions(
    hmdb_id: Any, target_format: str = "7digit"
) -> List[str]:
    """Handle HMDB entries with multiple accessions.

    Args:
        hmdb_id: HMDB ID(s), potentially semicolon-separated
        target_format: Target padding format

    Returns:
        List of normalized HMDB IDs
    """
    if pd.isna(hmdb_id) or hmdb_id is None:
        return []

    id_str = str(hmdb_id).strip()

    # Split by semicolon for multiple IDs
    if ";" in id_str:
        ids = [id.strip() for id in id_str.split(";")]
    else:
        ids = [id_str]

    # Normalize each ID
    normalized = []
    for id_val in ids:
        norm_id = normalize_hmdb_id(id_val, target_format)
        if norm_id and not pd.isna(norm_id):
            normalized.append(norm_id)

    return normalized


class MetaboliteNormalizeHmdbParams(BaseModel):
    """Parameters for METABOLITE_NORMALIZE_HMDB action."""

    input_key: str = Field(..., description="Dataset key from context['datasets']")
    hmdb_columns: List[str] = Field(
        ..., description="Columns containing HMDB IDs to normalize"
    )
    target_format: Literal["7digit", "5digit", "minimal"] = Field(
        default="7digit",
        description="Target padding format (7digit=HMDB0001234, 5digit=HMDB01234, minimal=HMDB1234)",
    )
    handle_secondary: bool = Field(
        default=True,
        description="Handle secondary HMDB accessions (semicolon-separated)",
    )
    validate_format: bool = Field(
        default=True, description="Validate HMDB ID format and report invalid entries"
    )
    output_key: str = Field(..., description="Where to store normalized dataset")
    add_normalization_log: bool = Field(
        default=True, description="Add columns showing normalization changes"
    )


@register_action("METABOLITE_NORMALIZE_HMDB")
class MetaboliteNormalizeHmdb(
    TypedStrategyAction[MetaboliteNormalizeHmdbParams, ActionResult]
):
    """Normalize HMDB identifiers to standard format.

    This action standardizes HMDB (Human Metabolome Database) identifier formats
    for consistent matching across datasets.
    """

    def get_params_model(self) -> type[MetaboliteNormalizeHmdbParams]:
        """Get the Pydantic model for parameters."""
        return MetaboliteNormalizeHmdbParams

    def get_result_model(self) -> type[ActionResult]:
        """Get the Pydantic model for results."""
        return ActionResult

    async def execute_typed(
        self,
        current_identifiers: List[str],
        current_ontology_type: str,
        params: MetaboliteNormalizeHmdbParams,
        source_endpoint: Any,
        target_endpoint: Any,
        context: Any,
    ) -> ActionResult:
        """Execute HMDB normalization.

        Args:
            params: Validated parameters
            context: Execution context with datasets

        Returns:
            ActionResult with success status and metadata
        """
        try:
            # Get input dataset
            if params.input_key not in context.get("datasets", {}):
                raise BiomapperError(
                    f"Dataset '{params.input_key}' not found in context"
                )

            df = context["datasets"][params.input_key].copy()

            # Verify all columns exist
            for col in params.hmdb_columns:
                if col not in df.columns:
                    raise BiomapperError(f"Column '{col}' not found in dataset")

            # Initialize statistics
            stats = {
                "total_entries": 0,
                "normalized_count": 0,
                "invalid_count": 0,
                "valid_count": 0,
                "secondary_expanded": 0,
            }

            # Process each HMDB column
            for col in params.hmdb_columns:
                logger.info(f"Normalizing HMDB column: {col}")

                # Store original values if logging enabled
                if params.add_normalization_log:
                    df[f"{col}_original"] = df[col].copy()
                    df[f"{col}_normalized"] = False

                # Count total non-null entries
                non_null_mask = df[col].notna()
                stats["total_entries"] += non_null_mask.sum()

                # Validate format BEFORE normalization if requested
                if params.validate_format:
                    # Validate original values before normalization
                    for idx, value in df[col].items():
                        if pd.isna(value):
                            continue
                        if value == "" or (
                            isinstance(value, str) and not value.strip()
                        ):
                            # Empty strings count as invalid
                            stats["invalid_count"] += 1
                            continue

                        value_str = str(value).strip()
                        if ";" in value_str:
                            # Validate each part
                            parts = value_str.split(";")
                            all_valid = all(
                                normalize_hmdb_id(part.strip(), params.target_format)
                                is not None
                                for part in parts
                                if part.strip()
                            )
                            if all_valid:
                                stats["valid_count"] += 1
                            else:
                                stats["invalid_count"] += 1
                        else:
                            # Check if it can be normalized (not if it's already valid)
                            normalized = normalize_hmdb_id(
                                value_str, params.target_format
                            )
                            if normalized is not None and not pd.isna(normalized):
                                stats["valid_count"] += 1
                            else:
                                stats["invalid_count"] += 1

                # Handle secondary accessions
                if params.handle_secondary:
                    # Process entries with semicolons
                    has_semicolon = df[col].astype(str).str.contains(";", na=False)
                    stats["secondary_expanded"] += has_semicolon.sum()

                    # Normalize with secondary handling
                    normalized_values = []
                    for idx, value in df[col].items():
                        if pd.isna(value):
                            normalized_values.append(value)
                        else:
                            accessions = handle_secondary_accessions(
                                value, params.target_format
                            )
                            if accessions:
                                # Join multiple accessions back with semicolon
                                normalized_values.append(";".join(accessions))
                            else:
                                normalized_values.append(None)

                    df[col] = normalized_values
                else:
                    # Simple normalization without secondary handling
                    df[col] = df[col].apply(
                        lambda x: normalize_hmdb_id(x, params.target_format)
                    )

                # Track normalization changes
                if params.add_normalization_log:
                    # Mark entries that were changed
                    df[f"{col}_normalized"] = df[f"{col}_original"].notna() & (
                        df[f"{col}_original"] != df[col]
                    )
                    stats["normalized_count"] += df[f"{col}_normalized"].sum()

            # Store normalized dataset
            context["datasets"][params.output_key] = df

            # Log statistics
            logger.info(f"HMDB normalization complete: {stats}")

            # Extract all normalized HMDB IDs for result
            input_ids = []
            output_ids = []

            for col in params.hmdb_columns:
                # Get original IDs if logged
                if params.add_normalization_log and f"{col}_original" in df.columns:
                    orig_ids = df[f"{col}_original"].dropna().astype(str).tolist()
                    input_ids.extend(orig_ids)

                # Get normalized IDs
                norm_ids = df[col].dropna().astype(str).tolist()
                # Expand semicolon-separated IDs
                for id_val in norm_ids:
                    if ";" in id_val:
                        output_ids.extend(id_val.split(";"))
                    else:
                        output_ids.append(id_val)

            # Remove duplicates
            input_ids = list(set(input_ids))
            output_ids = list(set(output_ids))

            return ActionResult(
                input_identifiers=input_ids[:100],  # Limit for performance
                output_identifiers=output_ids[:100],  # Limit for performance
                output_ontology_type="HMDB",
                provenance=[
                    {
                        "action": "METABOLITE_NORMALIZE_HMDB",
                        "target_format": params.target_format,
                        "columns_processed": params.hmdb_columns,
                    }
                ],
                details={
                    "hmdb_normalization": stats,
                    "columns_processed": params.hmdb_columns,
                    "target_format": params.target_format,
                    "rows_processed": len(df),
                },
            )

        except BiomapperError:
            raise
        except Exception as e:
            logger.error(f"Error during HMDB normalization: {str(e)}")
            raise BiomapperError(f"HMDB normalization failed: {str(e)}")
