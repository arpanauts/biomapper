"""
METABOLITE_EXTRACT_IDENTIFIERS action implementation.

Extracts multiple types of metabolite identifiers from compound datasets.
Handles HMDB, InChIKey, CHEBI, KEGG, and PubChem identifiers with normalization.
"""

import re
import logging
from typing import Dict, List, Any, Literal
import pandas as pd
import numpy as np
from pydantic import BaseModel, Field

from biomapper.core.strategy_actions.typed_base import TypedStrategyAction
from biomapper.core.strategy_actions.registry import register_action


class ActionResult(BaseModel):
    """Action result for metabolite identifier extraction."""

    success: bool
    message: str = ""
    error: str = ""
    statistics: Dict[str, Any] = Field(default_factory=dict)


logger = logging.getLogger(__name__)


class MetaboliteExtractIdentifiersParams(BaseModel):
    """Parameters for metabolite identifier extraction."""

    input_key: str = Field(description="Dataset key from context")
    id_types: List[str] = Field(description="List of identifier types to extract")
    source_columns: Dict[str, str] = Field(description="Column mapping per ID type")
    output_key: str = Field(description="Where to store results")
    normalize_ids: bool = Field(default=True, description="Apply format normalization")
    validate_formats: bool = Field(default=True, description="Validate extracted IDs")
    handle_multiple: Literal["expand_rows", "list", "first"] = Field(
        default="expand_rows", description="How to handle multiple IDs per row"
    )


@register_action("METABOLITE_EXTRACT_IDENTIFIERS")
class MetaboliteExtractIdentifiersAction(
    TypedStrategyAction[MetaboliteExtractIdentifiersParams, ActionResult]
):
    """
    Extracts metabolite identifiers from compound datasets.

    Supports multiple identifier types with format validation and normalization.
    """

    # Regex patterns for validation
    PATTERNS = {
        "inchikey": re.compile(r"^[A-Z]{14}-[A-Z]{10}-[A-Z]$"),
        "hmdb": re.compile(r"^HMDB\d{7}$"),  # After normalization
        "chebi": re.compile(r"^\d+$"),  # Just the number part
        "kegg": re.compile(r"^C\d{5}$"),  # KEGG compound format
        "pubchem": re.compile(r"^\d+$"),  # PubChem CID
    }

    # Common prefixes to strip
    PREFIXES = {
        "hmdb": ["HMDB:", "hmdb:", "HMDB"],
        "inchikey": ["InChIKey:", "InChIKey=", "inchikey:", "INCHIKEY:"],
        "chebi": ["CHEBI:", "ChEBI:", "chebi:"],
        "kegg": ["KEGG.COMPOUND:", "KEGG:", "kegg:", "KEGG.COMPOUND="],
        "pubchem": ["PUBCHEM.COMPOUND:", "PubChem:", "pubchem:", "PUBCHEM:"],
    }

    def get_params_model(self) -> type[MetaboliteExtractIdentifiersParams]:
        """Get the Pydantic model for parameters."""
        return MetaboliteExtractIdentifiersParams

    def get_result_model(self) -> type[ActionResult]:
        """Get the Pydantic model for results."""
        return ActionResult

    async def execute_typed(
        self,
        current_identifiers: List[str],
        current_ontology_type: str,
        params: MetaboliteExtractIdentifiersParams,
        source_endpoint: Any,
        target_endpoint: Any,
        context: Any,
    ) -> ActionResult:
        """Execute the metabolite identifier extraction."""
        try:
            # Get datasets from context
            context_dict = (
                context if isinstance(context, dict) else context.custom_action_data
            )
            if "datasets" not in context_dict:
                context_dict = {"datasets": context_dict}

            # Get input dataset
            if params.input_key not in context_dict.get("datasets", {}):
                return ActionResult(
                    success=False,
                    error=f"Input dataset '{params.input_key}' not found in context",
                )

            input_df = context_dict["datasets"][params.input_key].copy()
            logger.info(f"Processing {len(input_df)} rows for identifier extraction")

            # Initialize result dataframe with all original columns
            result_rows = []
            statistics = {
                "total_rows_processed": len(input_df),
                "identifiers_extracted": {},
            }

            # Process each row
            for idx, row in input_df.iterrows():
                # Extract identifiers for this row
                extracted_ids = {}
                for id_type in params.id_types:
                    ids = self._extract_identifiers_from_row(
                        row,
                        id_type,
                        params.source_columns.get(id_type, ""),
                        params.normalize_ids,
                        params.validate_formats,
                    )
                    extracted_ids[id_type] = ids

                # Handle multiple IDs based on strategy
                if params.handle_multiple == "expand_rows":
                    # Create multiple rows if needed
                    expanded_rows = self._expand_rows(row, extracted_ids)
                    result_rows.extend(expanded_rows)
                elif params.handle_multiple == "list":
                    # Keep as lists
                    new_row = row.to_dict()
                    for id_type, ids in extracted_ids.items():
                        new_row[id_type] = ids if ids else np.nan
                    result_rows.append(new_row)
                else:  # 'first'
                    # Take only first ID
                    new_row = row.to_dict()
                    for id_type, ids in extracted_ids.items():
                        new_row[id_type] = ids[0] if ids else np.nan
                    result_rows.append(new_row)

            # Create result dataframe
            if result_rows:
                result_df = pd.DataFrame(result_rows)
            else:
                # Create empty dataframe with expected columns
                result_df = input_df.copy()
                for id_type in params.id_types:
                    result_df[id_type] = np.nan

            # Calculate statistics
            for id_type in params.id_types:
                if id_type in result_df.columns:
                    non_null = result_df[id_type].notna()
                    if params.handle_multiple == "list":
                        # Count actual IDs in lists
                        count = sum(
                            len(x) if isinstance(x, list) else (1 if pd.notna(x) else 0)
                            for x in result_df[id_type]
                        )
                        unique_set = set()
                        for x in result_df[id_type]:
                            if isinstance(x, list):
                                unique_set.update(x)
                            elif pd.notna(x):
                                unique_set.add(x)
                        unique = len(unique_set)
                    else:
                        count = non_null.sum()
                        unique = result_df[id_type][non_null].nunique()

                    statistics["identifiers_extracted"][id_type] = {
                        "count": int(count),
                        "unique": int(unique),
                        "coverage": float(non_null.sum() / len(result_df))
                        if len(result_df) > 0
                        else 0.0,
                    }

            # Store result in context
            context_dict["datasets"][params.output_key] = result_df

            logger.info(f"Extracted identifiers: {statistics['identifiers_extracted']}")

            return ActionResult(
                success=True,
                message=f"Successfully extracted {len(params.id_types)} identifier types",
                statistics={"metabolite_extraction_stats": statistics},
            )

        except Exception as e:
            logger.error(f"Error extracting identifiers: {str(e)}")
            return ActionResult(
                success=False, error=f"Failed to extract identifiers: {str(e)}"
            )

    def _extract_identifiers_from_row(
        self,
        row: pd.Series,
        id_type: str,
        source_columns: str,
        normalize: bool,
        validate: bool,
    ) -> List[str]:
        """Extract identifiers of a specific type from a row."""
        identifiers = set()

        # Parse source columns
        columns = [col.strip() for col in source_columns.split(",") if col.strip()]

        for column in columns:
            if column not in row.index:
                continue

            value = row[column]
            if pd.isna(value) or value == "":
                continue

            # Extract IDs from the value
            extracted = self._extract_from_text(str(value), id_type)

            # Normalize if requested
            if normalize:
                extracted = [
                    self._normalize_identifier(id_val, id_type) for id_val in extracted
                ]

            # Validate if requested
            if validate:
                extracted = [
                    id_val
                    for id_val in extracted
                    if self._validate_identifier(id_val, id_type)
                ]

            identifiers.update(extracted)

        return sorted(list(identifiers))

    def _extract_from_text(self, text: str, id_type: str) -> List[str]:
        """Extract identifiers from text based on type."""
        results = []

        # Split by common delimiters
        parts = re.split(r"[,;|\s]+", text)

        for part in parts:
            part = part.strip()
            if not part:
                continue

            # Check for specific prefixes
            if id_type in self.PREFIXES:
                for prefix in self.PREFIXES[id_type]:
                    if part.startswith(prefix):
                        # Extract the ID part after prefix
                        id_val = part[len(prefix) :].lstrip(":=")
                        if id_val:
                            results.append(id_val)
                        break
                else:
                    # No prefix found, check if it matches expected pattern
                    if id_type == "hmdb" and re.match(r"^(HMDB)?\d+$", part):
                        # HMDB ID without full prefix
                        results.append(part)
                    elif id_type == "inchikey" and re.match(
                        r"^[A-Z]{14}-[A-Z]{10}-[A-Z]$", part
                    ):
                        # InChIKey without prefix
                        results.append(part)
                    elif id_type == "kegg" and re.match(r"^C\d{5}$", part):
                        # KEGG compound without prefix
                        results.append(part)
                    elif id_type == "chebi" and re.match(r"^\d+$", part):
                        # Could be CHEBI (context-dependent)
                        pass  # Skip ambiguous numeric IDs without prefix
                    elif id_type == "pubchem" and re.match(r"^\d+$", part):
                        # Could be PubChem (context-dependent)
                        pass  # Skip ambiguous numeric IDs without prefix

        return results

    def _normalize_identifier(self, id_val: str, id_type: str) -> str:
        """Normalize identifier to standard format."""
        if id_type == "hmdb":
            return self._normalize_hmdb(id_val)
        elif id_type == "chebi":
            # Just keep the numeric part
            return re.sub(r"^CHEBI:", "", id_val, flags=re.IGNORECASE)
        elif id_type == "kegg":
            # Ensure format is C#####
            if re.match(r"^\d+$", id_val):
                # Just numbers, add C prefix
                return f"C{id_val.zfill(5)}"
            return id_val.upper()
        elif id_type == "pubchem":
            # Just keep the numeric part
            return re.sub(
                r"^(PUBCHEM\.COMPOUND:|PubChem:|pubchem:)",
                "",
                id_val,
                flags=re.IGNORECASE,
            )
        elif id_type == "inchikey":
            return id_val.upper()
        return id_val

    def _normalize_hmdb(self, hmdb_id: str) -> str:
        """Normalize HMDB ID to HMDB####### format."""
        # Remove any prefix
        id_part = hmdb_id
        for prefix in ["HMDB:", "hmdb:", "HMDB"]:
            if id_part.startswith(prefix):
                id_part = id_part[len(prefix) :].lstrip(":")
                break

        # Extract numeric part
        numeric = re.sub(r"\D", "", id_part)
        if not numeric:
            return hmdb_id  # Can't normalize

        # Convert to 7-digit standard format
        num_val = int(numeric)
        return f"HMDB{num_val:07d}"

    def _validate_identifier(self, id_val: str, id_type: str) -> bool:
        """Validate identifier format."""
        if id_type not in self.PATTERNS:
            return True  # No validation pattern defined

        return bool(self.PATTERNS[id_type].match(id_val))

    def _expand_rows(
        self, row: pd.Series, extracted_ids: Dict[str, List[str]]
    ) -> List[Dict]:
        """Expand row into multiple rows based on extracted IDs."""
        # Find the maximum number of IDs for any type
        max_ids = max((len(ids) for ids in extracted_ids.values() if ids), default=1)

        if max_ids == 0:
            # No IDs found, return single row with NaN values
            new_row = row.to_dict()
            for id_type in extracted_ids:
                new_row[id_type] = np.nan
            return [new_row]

        # Create expanded rows
        expanded = []
        for i in range(max_ids):
            new_row = row.to_dict()
            for id_type, ids in extracted_ids.items():
                if ids and i < len(ids):
                    new_row[id_type] = ids[i]
                else:
                    new_row[id_type] = np.nan
            expanded.append(new_row)

        return expanded
