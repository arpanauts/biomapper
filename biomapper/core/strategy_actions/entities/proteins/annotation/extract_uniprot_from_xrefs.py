"""
PROTEIN_EXTRACT_UNIPROT_FROM_XREFS action for extracting UniProt accession IDs from xrefs fields.

This action extracts UniProt accession IDs from compound xrefs fields commonly found 
in KG2c and SPOKE protein datasets. It handles multiple IDs, isoforms, and various 
output formats according to user preferences.
"""

import re
import pandas as pd
from typing import Any, Dict, List, Literal
from pydantic import BaseModel, Field, validator

from biomapper.core.strategy_actions.registry import register_action
from biomapper.core.strategy_actions.typed_base import TypedStrategyAction


class ExtractUniProtFromXrefsResult(BaseModel):
    """Result of UniProt extraction from xrefs."""

    success: bool
    message: str
    data: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ExtractUniProtFromXrefsParams(BaseModel):
    """Parameters for PROTEIN_EXTRACT_UNIPROT_FROM_XREFS action."""

    dataset_key: str = Field(
        ..., description="Key of the dataset in context to process"
    )
    xrefs_column: str = Field(
        ..., description="Name of the column containing xrefs data"
    )
    output_column: str = Field(
        default="uniprot_id", description="Name of the output column for UniProt IDs"
    )
    output_key: str = Field(
        default=None, description="Optional output dataset key. If not provided, modifies dataset in-place"
    )
    handle_multiple: Literal["list", "first", "expand_rows"] = Field(
        default="list",
        description="How to handle multiple UniProt IDs: 'list' (as list), 'first' (take first), 'expand_rows' (create new rows)",
    )
    keep_isoforms: bool = Field(
        default=False, description="Whether to keep isoform suffixes (e.g., -1, -2)"
    )
    drop_na: bool = Field(
        default=True, description="Whether to drop rows with no UniProt IDs found"
    )

    @validator("handle_multiple")
    def validate_handle_multiple(cls, v):
        """Validate handle_multiple parameter."""
        valid_options = {"list", "first", "expand_rows"}
        if v not in valid_options:
            raise ValueError(
                f"handle_multiple must be one of {valid_options}, got: {v}"
            )
        return v


@register_action("PROTEIN_EXTRACT_UNIPROT_FROM_XREFS")
class ProteinExtractUniProtFromXrefsAction(
    TypedStrategyAction[ExtractUniProtFromXrefsParams, ExtractUniProtFromXrefsResult]
):
    """
    Extract UniProt accession IDs from xrefs fields in protein datasets.

    This action processes datasets containing compound xrefs fields (commonly found in
    KG2c and SPOKE) and extracts UniProt accession IDs using regex pattern matching.

    Features:
    - Extracts UniProt IDs using pattern: UniProtKB:([A-Z0-9]+)(?:-\d+)?
    - Handles multiple IDs per xrefs field with flexible output options
    - Optional isoform handling (keep or strip -1, -2 suffixes)
    - Validates UniProt ID format
    - Supports row expansion for multiple matches
    """

    # UniProt regex pattern - captures base ID and optional isoform suffix
    UNIPROT_PATTERN = re.compile(r"UniProtKB:([A-Z0-9]+(?:-\d+)?)")

    def get_params_model(self) -> type[ExtractUniProtFromXrefsParams]:
        """Return the parameters model for this action."""
        return ExtractUniProtFromXrefsParams
    
    def get_result_model(self) -> type[ExtractUniProtFromXrefsResult]:
        """Return the result model for this action."""
        return ExtractUniProtFromXrefsResult

    async def execute_typed(
        self, 
        params: ExtractUniProtFromXrefsParams, 
        context: Any,  # Changed to Any to accept both dict and context objects
        **kwargs  # Accept additional kwargs from TypedStrategyAction
    ) -> ExtractUniProtFromXrefsResult:
        """
        Execute the UniProt extraction from xrefs.

        Args:
            params: Action parameters
            context: Execution context containing datasets

        Returns:
            ActionResult with processed dataset containing extracted UniProt IDs

        Raises:
            KeyError: If dataset_key or xrefs_column not found
        """
        # Work directly with context - support dict, MockContext, and StrategyExecutionContext
        # Check if it's a dict or MockContext (has _dict attribute)
        if isinstance(context, dict):
            ctx = context
            if "datasets" not in ctx:
                ctx["datasets"] = {}
            if "statistics" not in ctx:
                ctx["statistics"] = {}
        elif hasattr(context, '_dict'):
            # MockContext - use the underlying dict
            ctx = context._dict
            if "datasets" not in ctx:
                ctx["datasets"] = {}
            if "statistics" not in ctx:
                ctx["statistics"] = {}
        else:
            # For StrategyExecutionContext, adapt it
            from biomapper.core.context_adapter import adapt_context
            ctx = adapt_context(context)
            if "datasets" not in ctx:
                ctx["datasets"] = {}
        
        # Validate input
        if params.dataset_key not in ctx["datasets"]:
            raise KeyError(f"Dataset key '{params.dataset_key}' not found in context")

        # Get dataset - handle both DataFrame and list of dicts
        dataset = ctx["datasets"][params.dataset_key]
        if isinstance(dataset, pd.DataFrame):
            df = dataset.copy()
        elif isinstance(dataset, list):
            # Convert list of dicts to DataFrame
            df = pd.DataFrame(dataset)
        else:
            raise TypeError(f"Dataset must be DataFrame or list of dicts, got {type(dataset)}")

        if params.xrefs_column not in df.columns:
            raise KeyError(f"Column '{params.xrefs_column}' not found in dataset")

        # Extract UniProt IDs from xrefs
        df[params.output_column] = df[params.xrefs_column].apply(
            lambda x: self._extract_uniprot_ids(x, params.keep_isoforms)
        )

        # Handle multiple IDs according to user preference
        if params.handle_multiple == "first":
            df[params.output_column] = df[params.output_column].apply(
                lambda ids: ids[0] if ids else None
            )
        elif params.handle_multiple == "expand_rows":
            df = self._expand_rows_for_multiple_ids(df, params.output_column)
        # For "list" mode, keep as-is (already lists)

        # Drop rows with no UniProt IDs if requested
        if params.drop_na:
            if params.handle_multiple == "list":
                df = df[df[params.output_column].apply(len) > 0]
            else:  # first or expand_rows modes
                df = df[df[params.output_column].notna()]

        # Update context - either use output_key or modify in-place
        output_key = params.output_key if params.output_key else params.dataset_key
        # Store as list of dicts for consistency with LoadDatasetIdentifiersAction
        ctx["datasets"][output_key] = df.to_dict("records")

        # Update statistics
        total_rows = len(df)
        rows_with_uniprot = len(
            df[
                df[params.output_column].apply(
                    lambda x: len(x) > 0 if isinstance(x, list) else pd.notna(x)
                )
            ]
        )

        stats = {
            "total_rows_processed": total_rows,
            "rows_with_uniprot_ids": rows_with_uniprot,
            "extraction_rate": rows_with_uniprot / total_rows
            if total_rows > 0
            else 0.0,
        }

        if "statistics" not in ctx:
            ctx["statistics"] = {}
        ctx["statistics"]["uniprot_extraction"] = stats

        return ExtractUniProtFromXrefsResult(
            success=True,
            message=f"Extracted UniProt IDs from {total_rows} rows, {rows_with_uniprot} with valid IDs",
            data={output_key: df},
            metadata={
                "action": "PROTEIN_EXTRACT_UNIPROT_FROM_XREFS",
                "parameters": params.dict(),
                "statistics": stats,
                "output_key": output_key,
            },
        )

    def _extract_uniprot_ids(self, xrefs_str: str, keep_isoforms: bool) -> List[str]:
        """
        Extract UniProt IDs from a single xrefs string.

        Args:
            xrefs_str: String containing pipe-separated xrefs
            keep_isoforms: Whether to keep isoform suffixes

        Returns:
            List of extracted UniProt IDs
        """
        if pd.isna(xrefs_str) or not isinstance(xrefs_str, str):
            return []

        # Find all UniProt matches
        matches = self.UNIPROT_PATTERN.findall(xrefs_str)

        if not keep_isoforms:
            # Strip isoform suffixes (e.g., P12345-1 becomes P12345)
            matches = [self._strip_isoform(match) for match in matches]

        # Validate UniProt ID format and filter out invalid ones
        valid_ids = [
            match
            for match in matches
            if self._is_valid_uniprot_id(match, keep_isoforms)
        ]

        return valid_ids

    def _strip_isoform(self, uniprot_id: str) -> str:
        """Strip isoform suffix from UniProt ID."""
        return re.sub(r"-\d+$", "", uniprot_id)

    def _is_valid_uniprot_id(self, uniprot_id: str, allow_isoforms: bool) -> bool:
        """
        Validate UniProt ID format.

        Args:
            uniprot_id: UniProt ID to validate
            allow_isoforms: Whether isoform suffixes are allowed

        Returns:
            True if valid UniProt ID format
        """
        if not uniprot_id:
            return False

        # Basic UniProt format: 6-10 characters, alphanumeric
        # Examples: P12345, Q14213, A0A123B4C5
        base_pattern = r"^[A-Z0-9]{6,10}$"
        isoform_pattern = r"^[A-Z0-9]{6,10}-\d+$"

        if allow_isoforms and "-" in uniprot_id:
            return bool(re.match(isoform_pattern, uniprot_id))
        else:
            return bool(re.match(base_pattern, uniprot_id))

    def _expand_rows_for_multiple_ids(
        self, df: pd.DataFrame, id_column: str
    ) -> pd.DataFrame:
        """
        Expand rows with multiple UniProt IDs into separate rows.

        Args:
            df: DataFrame to process
            id_column: Name of column containing UniProt ID lists

        Returns:
            DataFrame with expanded rows
        """
        expanded_rows = []

        for idx, row in df.iterrows():
            ids = row[id_column]
            if isinstance(ids, list) and len(ids) > 0:
                for uniprot_id in ids:
                    new_row = row.copy()
                    new_row[id_column] = uniprot_id
                    expanded_rows.append(new_row)
            else:
                # Keep rows with no IDs as-is (will be filtered if drop_na=True)
                new_row = row.copy()
                new_row[id_column] = None if not ids else ids
                expanded_rows.append(new_row)

        return pd.DataFrame(expanded_rows).reset_index(drop=True)
