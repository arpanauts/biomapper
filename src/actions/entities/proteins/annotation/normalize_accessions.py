"""PROTEIN_NORMALIZE_ACCESSIONS action for normalizing UniProt accession formats.

This action normalizes UniProt accession identifiers by:
1. Normalizing case (lowercase to uppercase)
2. Stripping prefixes (sp|, tr|, UniProt:, etc.)
3. Removing version suffixes (.1, .2, etc.)
4. Handling isoform suffixes (-1, -2, etc.)
5. Validating UniProt format
"""
import re
import logging
from typing import Dict, List, Any, Optional
import pandas as pd
from pydantic import BaseModel, Field

from actions.typed_base import TypedStrategyAction
from actions.registry import register_action

logger = logging.getLogger(__name__)


class ProteinNormalizeAccessionsParams(BaseModel):
    """Parameters for PROTEIN_NORMALIZE_ACCESSIONS action."""

    input_key: str = Field(..., description="Dataset key from context['datasets']")
    id_columns: List[str] = Field(
        ..., description="Columns containing UniProt IDs to normalize"
    )
    strip_isoforms: bool = Field(
        default=True, description="Remove -1, -2 isoform suffixes"
    )
    strip_versions: bool = Field(
        default=True, description="Remove .1, .2 version numbers"
    )
    validate_format: bool = Field(
        default=True, description="Validate UniProt ID format"
    )
    output_key: str = Field(..., description="Where to store normalized dataset")
    add_normalization_log: bool = Field(
        default=True, description="Add columns showing what was normalized"
    )


class ActionResult(BaseModel):
    """Standard action result for protein accession normalization."""

    success: bool
    message: Optional[str] = None
    error: Optional[str] = None
    data: Dict[str, Any] = Field(default_factory=dict)


@register_action("PROTEIN_NORMALIZE_ACCESSIONS")
class ProteinNormalizeAccessionsAction(
    TypedStrategyAction[ProteinNormalizeAccessionsParams, ActionResult]
):
    """Action to normalize UniProt accession formats for consistent matching."""

    def get_params_model(self) -> type[ProteinNormalizeAccessionsParams]:
        return ProteinNormalizeAccessionsParams

    def get_result_model(self) -> type[ActionResult]:
        return ActionResult

    # UniProt format regex:
    # Standard format: [A-Z][0-9]{5} (P12345, Q67890) - 6 chars
    # Standard variant: [A-Z][0-9A-Z]{5} (Q123A5) - 6 chars
    # Extended format: [A-Z][0-9A-Z]{6,9} (Q123456) - 7-10 chars
    # Special format: [A-Z][0-9][A-Z][A-Z0-9]{3,6} (A0A123456) - 6-10 chars
    # Must start with letter then digit (excludes PP12345, AA12345, etc.)
    UNIPROT_PATTERN = re.compile(r"^[A-Z][0-9][A-Z0-9]{4,8}$")

    # Common prefixes to strip
    PREFIX_PATTERNS = [
        re.compile(
            r"^sp\|([A-Z0-9]+)(\|.*)?$", re.IGNORECASE
        ),  # SwissProt: sp|P12345|GENE_NAME or sp|P12345
        re.compile(
            r"^tr\|([A-Z0-9]+)(\|.*)?$", re.IGNORECASE
        ),  # TrEMBL: tr|Q67890|GENE_NAME or tr|Q67890
        re.compile(r"^uniprot:([A-Z0-9]+)$", re.IGNORECASE),  # UniProt: UniProt:P12345
        re.compile(r"^\|([A-Z0-9]+)\|.*$"),  # Edge case: |P12345|...
    ]

    async def execute_typed(  # type: ignore[override]
        self, params: ProteinNormalizeAccessionsParams, context: Any, **kwargs
    ) -> ActionResult:
        """Execute the normalization action.

        This method applies the complete UniProt normalization pipeline:
        1. Case normalization (lowercase → uppercase)
        2. Prefix stripping (sp|, tr|, UniProt:)
        3. Version removal (.1, .2, etc.)
        4. Isoform handling (-1, -2, etc.)
        5. Format validation
        """
        logger.info(f"Starting PROTEIN_NORMALIZE_ACCESSIONS with params: {params}")

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
            from core.context_adapter import adapt_context
            ctx = adapt_context(context)
            if "datasets" not in ctx:
                ctx["datasets"] = {}
            if "statistics" not in ctx:
                ctx["statistics"] = {}

        # Validate input dataset exists
        if params.input_key not in ctx["datasets"]:
            raise KeyError(f"Input dataset '{params.input_key}' not found in context")

        # Get dataset - handle both DataFrame and list of dicts
        dataset = ctx["datasets"][params.input_key]
        if isinstance(dataset, pd.DataFrame):
            input_df = dataset.copy()
        elif isinstance(dataset, list):
            # Convert list of dicts to DataFrame
            input_df = pd.DataFrame(dataset)
        else:
            return ActionResult(
                success=False,
                error=f"Dataset must be DataFrame or list of dicts, got {type(dataset)}"
            )

        # Validate columns exist
        missing_columns = [
            col for col in params.id_columns if col not in input_df.columns
        ]
        if missing_columns:
            raise KeyError(f"Columns not found in dataset: {missing_columns}")

        # Track normalization statistics
        stats = {
            "total_processed": 0,
            "case_normalized": 0,
            "prefixes_stripped": 0,
            "versions_removed": 0,
            "isoforms_handled": 0,
            "validation_failures": 0,
        }

        # Process each specified column
        for col in params.id_columns:
            logger.info(f"Processing column: {col}")

            # Store original values if logging enabled
            if params.add_normalization_log:
                input_df[f"{col}_original"] = input_df[col].copy()

            # Apply normalization pipeline
            normalized_series, col_stats = self._normalize_column(
                input_df[col],
                params.strip_isoforms,
                params.strip_versions,
                params.validate_format,
            )

            input_df[col] = normalized_series

            # Add normalization log columns
            if params.add_normalization_log:
                input_df[f"{col}_normalized"] = normalized_series

            # Update statistics
            for key, value in col_stats.items():
                stats[key] += value

        # Store results in context as list of dicts for consistency
        ctx["datasets"][params.output_key] = input_df.to_dict("records")

        # Update context statistics
        if "normalization_stats" not in ctx["statistics"]:
            ctx["statistics"]["normalization_stats"] = {}
        ctx["statistics"]["normalization_stats"].update(stats)

        logger.info(f"Normalization complete. Statistics: {stats}")

        return ActionResult(
            success=True,
            message=f"Normalized {stats['total_processed']} values across {len(params.id_columns)} columns",
            data={
                "output_key": params.output_key,
                "statistics": stats,
                "processed_columns": params.id_columns,
                "provenance": {
                    "action": "PROTEIN_NORMALIZE_ACCESSIONS",
                    "timestamp": pd.Timestamp.now().isoformat(),
                    "details": stats,
                }
            }
        )

    def _normalize_column(
        self,
        series: pd.Series,
        strip_isoforms: bool,
        strip_versions: bool,
        validate_format: bool,
    ) -> tuple[pd.Series, Dict[str, int]]:
        """Normalize a single column of UniProt identifiers."""
        stats = {
            "total_processed": 0,
            "case_normalized": 0,
            "prefixes_stripped": 0,
            "versions_removed": 0,
            "isoforms_handled": 0,
            "validation_failures": 0,
        }

        normalized_values = []

        for value in series:
            stats["total_processed"] += 1
            normalized, item_stats = self._normalize_single_value_with_stats(
                value, strip_isoforms, strip_versions, validate_format
            )
            normalized_values.append(normalized)

            # Update statistics
            for key, count in item_stats.items():
                stats[key] += count

        return pd.Series(normalized_values, index=series.index), stats

    def _normalize_single_value_with_stats(
        self,
        value: Any,
        strip_isoforms: bool,
        strip_versions: bool,
        validate_format: bool,
    ) -> tuple[Any, Dict[str, int]]:
        """Normalize a single value and return statistics."""
        stats = {
            "case_normalized": 0,
            "prefixes_stripped": 0,
            "versions_removed": 0,
            "isoforms_handled": 0,
            "validation_failures": 0,
        }

        # Handle empty/null values
        if pd.isna(value) or value == "" or value is None:
            return value, stats

        # Convert to string
        if not isinstance(value, str):
            value = str(value)

        original_value = value

        # Step 1: Normalize case
        if value != value.upper():
            stats["case_normalized"] = 1
        value = self._normalize_case(value)

        # Step 2: Strip prefixes
        stripped_value = self._strip_prefixes(value)
        if stripped_value != value:
            stats["prefixes_stripped"] = 1
        value = stripped_value

        # Step 3: Remove versions if enabled
        if strip_versions:
            version_removed = self._strip_versions(value)
            if version_removed != value:
                stats["versions_removed"] = 1
            value = version_removed

        # Step 4: Handle isoforms
        isoform_handled = self._strip_isoforms(value, strip_isoforms)
        if isoform_handled != value:
            stats["isoforms_handled"] = 1
        value = isoform_handled

        # Step 5: Validate format if enabled
        if validate_format and not self._validate_uniprot_format(value):
            stats["validation_failures"] = 1
            logger.warning(
                f"Invalid UniProt format after normalization: {original_value} -> {value}"
            )

        return value, stats

    def _normalize_single_value(self, value: Any) -> Any:
        """Normalize a single value (simplified version for testing)."""
        result, _ = self._normalize_single_value_with_stats(
            value, strip_isoforms=True, strip_versions=True, validate_format=False
        )
        return result

    def _normalize_case(self, value: str) -> str:
        """Normalize case to uppercase."""
        return value.upper()

    def _strip_prefixes(self, value: str) -> str:
        """Strip common UniProt prefixes."""
        for pattern in self.PREFIX_PATTERNS:
            match = pattern.match(value)
            if match:
                return match.group(1).upper()
        return value

    def _strip_versions(self, value: str) -> str:
        """Remove version suffixes like .1, .2, etc."""
        # Remove version suffixes (last occurrence of .number)
        if "." in value:
            parts = value.split(".")
            if len(parts) >= 2 and parts[-1].isdigit():
                return ".".join(parts[:-1])
            # Handle trailing dot
            elif parts[-1] == "":
                return ".".join(parts[:-1])
        return value

    def _strip_isoforms(self, value: str, strip: bool) -> str:
        """Handle isoform suffixes like -1, -2, etc."""
        if not strip:
            return value

        # Remove isoform suffixes (last occurrence of -number)
        if "-" in value:
            parts = value.split("-")
            if len(parts) >= 2 and parts[-1].isdigit():
                return "-".join(parts[:-1])
            # Handle trailing dash
            elif parts[-1] == "":
                return "-".join(parts[:-1])
        return value

    def _validate_uniprot_format(self, value: str) -> bool:
        """Validate UniProt accession format."""
        if not isinstance(value, str) or not value:
            return False
        return bool(self.UNIPROT_PATTERN.match(value))
