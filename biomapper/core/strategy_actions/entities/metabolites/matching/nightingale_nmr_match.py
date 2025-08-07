"""Enhanced Nightingale NMR platform-specific matching action for UKBB data."""

import logging
import re
from typing import Dict, Any, Optional, List, TypedDict

import pandas as pd
from pydantic import BaseModel, Field
from fuzzywuzzy import fuzz, process  # type: ignore[import-untyped]

from biomapper.core.strategy_actions.typed_base import TypedStrategyAction
from biomapper.core.strategy_actions.registry import register_action
from biomapper.core.models.execution_context import StrategyExecutionContext

logger = logging.getLogger(__name__)


class NightingalePattern(TypedDict):
    """Type definition for Nightingale pattern."""

    description: str
    hmdb: Optional[str]
    loinc: Optional[str]
    unit: str
    category: str


# Nightingale biomarker naming patterns with standard mappings
NIGHTINGALE_PATTERNS: Dict[str, NightingalePattern] = {
    # Lipids and Lipoproteins
    "Total_C": {
        "description": "Total cholesterol",
        "hmdb": "HMDB0000067",
        "loinc": "2093-3",
        "unit": "mmol/L",
        "category": "lipids",
    },
    "LDL_C": {
        "description": "LDL cholesterol",
        "hmdb": "HMDB0000067",
        "loinc": "13457-7",
        "unit": "mmol/L",
        "category": "lipids",
    },
    "HDL_C": {
        "description": "HDL cholesterol",
        "hmdb": "HMDB0000067",
        "loinc": "2085-9",
        "unit": "mmol/L",
        "category": "lipids",
    },
    "Triglycerides": {
        "description": "Triglycerides",
        "hmdb": "HMDB0000827",
        "loinc": "2571-8",
        "unit": "mmol/L",
        "category": "lipids",
    },
    # Apolipoproteins
    "ApoA1": {
        "description": "Apolipoprotein A1",
        "hmdb": None,
        "loinc": "1869-7",
        "unit": "g/L",
        "category": "apolipoproteins",
    },
    "ApoB": {
        "description": "Apolipoprotein B",
        "hmdb": None,
        "loinc": "1884-6",
        "unit": "g/L",
        "category": "apolipoproteins",
    },
    # Fatty Acids
    "Omega_3_pct": {
        "description": "Omega-3 fatty acids percentage",
        "hmdb": "HMDB0001388",
        "loinc": None,
        "unit": "%",
        "category": "fatty_acids",
    },
    "DHA_pct": {
        "description": "Docosahexaenoic acid percentage",
        "hmdb": "HMDB0002183",
        "loinc": None,
        "unit": "%",
        "category": "fatty_acids",
    },
    # Amino Acids
    "Ala": {
        "description": "Alanine",
        "hmdb": "HMDB0000161",
        "loinc": "1916-6",
        "unit": "mmol/L",
        "category": "amino_acids",
    },
    "Gln": {
        "description": "Glutamine",
        "hmdb": "HMDB0000641",
        "loinc": "14681-2",
        "unit": "mmol/L",
        "category": "amino_acids",
    },
    # Glycolysis
    "Glucose": {
        "description": "Glucose",
        "hmdb": "HMDB0000122",
        "loinc": "2345-7",
        "unit": "mmol/L",
        "category": "glycolysis",
    },
    "Lactate": {
        "description": "Lactate",
        "hmdb": "HMDB0000190",
        "loinc": "2524-7",
        "unit": "mmol/L",
        "category": "glycolysis",
    },
    # Ketone Bodies
    "bOHbutyrate": {
        "description": "Beta-hydroxybutyrate",
        "hmdb": "HMDB0000357",
        "loinc": "53060-9",
        "unit": "mmol/L",
        "category": "ketone_bodies",
    },
    # Inflammation
    "GlycA": {
        "description": "Glycoprotein acetyls",
        "hmdb": None,
        "loinc": None,
        "unit": "mmol/L",
        "category": "inflammation",
    },
}

# Lipoprotein particle patterns
LIPOPROTEIN_PATTERNS = {
    r"^(.+)_VLDL_(.+)$": "VLDL particles",
    r"^(.+)_LDL_(.+)$": "LDL particles",
    r"^(.+)_HDL_(.+)$": "HDL particles",
    r"^XXL_VLDL_(.+)$": "Extra extra large VLDL",
    r"^XL_HDL_(.+)$": "Extra large HDL",
    r"^S_LDL_(.+)$": "Small LDL",
}


class NightingaleNmrMatchParams(BaseModel):
    """Parameters for Nightingale NMR biomarker matching."""

    # Input/Output
    input_key: str = Field(..., description="Dataset key from context")
    output_key: str = Field(..., description="Output dataset key")

    # Source configuration
    biomarker_column: str = Field(
        "biomarker", description="Column with Nightingale biomarker names"
    )
    unit_column: Optional[str] = Field(
        None, description="Column with measurement units"
    )

    # Reference file
    reference_file: str = Field(
        "/procedure/data/local_data/references/nightingale_nmr_reference.csv",
        description="Path to Nightingale reference mapping file",
    )
    use_cached_reference: bool = Field(
        True, description="Cache reference file in memory"
    )

    # Target format
    target_format: str = Field(
        "hmdb", description="Target identifier format: 'hmdb', 'loinc', or 'both'"
    )

    # Matching configuration
    match_threshold: float = Field(
        0.85, description="Fuzzy match threshold for biomarker names"
    )
    use_abbreviations: bool = Field(
        True, description="Expand/match common abbreviations"
    )
    case_sensitive: bool = Field(False, description="Case-sensitive matching")

    # Output options
    add_metadata: bool = Field(True, description="Add Nightingale metadata columns")
    include_units: bool = Field(True, description="Include standardized units")
    include_categories: bool = Field(True, description="Include biomarker categories")


class NightingaleNmrMatchResult(BaseModel):
    """Result of Nightingale NMR biomarker matching."""

    success: bool
    total_biomarkers: int
    matched_biomarkers: int
    unmatched_biomarkers: List[str]
    match_statistics: Dict[str, Any]
    category_breakdown: Dict[str, int]
    reference_version: str
    warnings: Optional[List[str]] = None


class NightingaleReference:
    """Load and manage Nightingale reference mappings."""

    def __init__(self, reference_file: str, use_cache: bool = True):
        self.reference_file = reference_file
        self.use_cache = use_cache
        self._reference_data: Optional[pd.DataFrame] = None
        self._abbreviations: Optional[Dict[str, str]] = None

    def load_reference(self) -> pd.DataFrame:
        """Load Nightingale reference mapping file."""
        if self._reference_data is not None and self.use_cache:
            return self._reference_data

        try:
            # Try to load CSV reference file
            ref_df = pd.read_csv(self.reference_file)

            # Expected columns
            required_cols = ["nightingale_name", "hmdb_id", "description"]
            if not all(col in ref_df.columns for col in required_cols):
                raise ValueError(
                    f"Reference file missing required columns: {required_cols}"
                )

            if self.use_cache:
                self._reference_data = ref_df

            return ref_df
        except FileNotFoundError:
            logger.warning(f"Reference file not found: {self.reference_file}")
            # Return empty dataframe with required columns
            return pd.DataFrame(
                columns=[
                    "nightingale_name",
                    "hmdb_id",
                    "loinc_code",
                    "description",
                    "category",
                    "unit",
                ]
            )

    def load_abbreviations(self) -> Dict[str, str]:
        """Load common abbreviations and expansions."""
        if self._abbreviations is not None and self.use_cache:
            return self._abbreviations

        abbreviations = {
            # Cholesterol variants
            "C": "cholesterol",
            "CE": "cholesterol esters",
            "FC": "free cholesterol",
            # Triglycerides
            "TG": "triglycerides",
            # Phospholipids
            "PL": "phospholipids",
            "PC": "phosphatidylcholine",
            # Particle counts
            "P": "particles",
            # Sizes (Note: L is also used for "lipids" but size context takes precedence)
            "XXL": "extra extra large",
            "XL": "extra large",
            "L": "large",
            "M": "medium",
            "S": "small",
            "XS": "extra small",
        }

        if self.use_cache:
            self._abbreviations = abbreviations

        return abbreviations


class NightingaleMatcher:
    """Match Nightingale biomarkers to standard identifiers."""

    def __init__(self) -> None:
        self.abbreviations: Dict[str, str] = {}

    def load_abbreviations(self) -> Dict[str, str]:
        """Load and return abbreviations."""
        return NightingaleReference("", use_cache=False).load_abbreviations()

    def match_biomarker(
        self,
        biomarker_name: Optional[str],
        reference_df: pd.DataFrame,
        threshold: float = 0.85,
    ) -> Optional[Dict[str, Any]]:
        """Match single biomarker to reference."""

        # Handle invalid input
        if biomarker_name is None or pd.isna(biomarker_name):
            return None

        # Convert to string and strip
        biomarker_name = str(biomarker_name).strip()
        if not biomarker_name:
            return None

        # Try exact match first in reference dataframe
        if not reference_df.empty:
            exact_match = reference_df[
                reference_df["nightingale_name"].str.lower() == biomarker_name.lower()
            ]

            if not exact_match.empty:
                return self._format_match_result(exact_match.iloc[0], confidence=1.0)

        # Try exact match in built-in patterns
        if biomarker_name in NIGHTINGALE_PATTERNS:
            pattern_info = NIGHTINGALE_PATTERNS[biomarker_name]
            return {
                "nightingale_name": biomarker_name,
                "hmdb_id": pattern_info["hmdb"],
                "loinc_code": pattern_info["loinc"],
                "description": pattern_info["description"],
                "category": pattern_info["category"],
                "unit": pattern_info["unit"],
                "confidence": 1.0,
            }

        # Try pattern matching for lipoproteins
        for pattern, description in LIPOPROTEIN_PATTERNS.items():
            if re.match(pattern, biomarker_name):
                return self._handle_lipoprotein_pattern(
                    biomarker_name, pattern, description
                )

        # Clean the biomarker name for fuzzy matching
        clean_name = self._clean_biomarker_name(biomarker_name)

        # Try fuzzy matching against reference dataframe
        if not reference_df.empty:
            # First try matching with cleaned name
            choices = reference_df["nightingale_name"].tolist()
            best_match = process.extractOne(
                clean_name,
                [self._clean_biomarker_name(c) for c in choices],
                scorer=fuzz.token_sort_ratio,
            )

            if best_match and best_match[1] >= threshold * 100:
                # Find the original row
                matched_idx = [self._clean_biomarker_name(c) for c in choices].index(
                    best_match[0]
                )
                matched_row = reference_df.iloc[matched_idx]
                return self._format_match_result(
                    matched_row, confidence=best_match[1] / 100
                )

        # Try fuzzy matching against built-in patterns
        pattern_names = list(NIGHTINGALE_PATTERNS.keys())
        if pattern_names:
            best_match = process.extractOne(
                clean_name,
                [self._clean_biomarker_name(p) for p in pattern_names],
                scorer=fuzz.token_sort_ratio,
            )

            if best_match and best_match[1] >= threshold * 100:
                # Find the original pattern
                matched_idx = [
                    self._clean_biomarker_name(p) for p in pattern_names
                ].index(best_match[0])
                pattern_name = pattern_names[matched_idx]
                pattern_info = NIGHTINGALE_PATTERNS[pattern_name]
                return {
                    "nightingale_name": pattern_name,
                    "hmdb_id": pattern_info["hmdb"],
                    "loinc_code": pattern_info["loinc"],
                    "description": pattern_info["description"],
                    "category": pattern_info["category"],
                    "unit": pattern_info["unit"],
                    "confidence": best_match[1] / 100,
                }

        return None

    def _clean_biomarker_name(self, name: str) -> str:
        """Clean and standardize biomarker name."""
        # Remove underscores
        name = name.replace("_", " ")

        # Load abbreviations if not loaded
        if not self.abbreviations:
            self.abbreviations = self.load_abbreviations()

        # Expand abbreviations
        for abbr, full in self.abbreviations.items():
            # Use word boundaries for exact matching
            name = re.sub(
                r"\b" + re.escape(abbr) + r"\b", full, name, flags=re.IGNORECASE
            )

        return name.strip().lower()

    def _format_match_result(self, row: pd.Series, confidence: float) -> Dict[str, Any]:
        """Format match result from reference row."""
        return {
            "nightingale_name": row.get("nightingale_name", ""),
            "hmdb_id": row.get("hmdb_id"),
            "loinc_code": row.get("loinc_code"),
            "description": row.get("description", ""),
            "category": row.get("category", "unknown"),
            "unit": row.get("unit", ""),
            "confidence": confidence,
        }

    def _handle_lipoprotein_pattern(
        self, biomarker_name: str, pattern: str, description: str
    ) -> Optional[Dict[str, Any]]:
        """Handle lipoprotein particle patterns."""

        # Extract components
        match = re.match(pattern, biomarker_name)
        if not match:
            return None

        # Build result based on pattern
        result = {
            "nightingale_name": biomarker_name,
            "description": description,
            "category": "lipoproteins",
            "hmdb_id": None,  # Lipoproteins don't have HMDB IDs
            "loinc_code": self._get_lipoprotein_loinc(biomarker_name),
            "unit": self._get_lipoprotein_unit(biomarker_name),
            "confidence": 0.9,
        }

        return result

    def _get_lipoprotein_loinc(self, biomarker_name: str) -> Optional[str]:
        """Get LOINC code for lipoprotein particles if available."""
        # Map some common lipoprotein measurements to LOINC codes
        loinc_mappings = {
            "VLDL_C": "13458-5",
            "VLDL_TG": "13459-3",
            "LDL_P": "18262-6",
            "HDL_P": "30522-7",
        }

        for key, loinc in loinc_mappings.items():
            if key in biomarker_name:
                return loinc

        return None

    def _get_lipoprotein_unit(self, biomarker_name: str) -> str:
        """Get appropriate unit for lipoprotein measurement."""
        if "_P" in biomarker_name or "_P_" in biomarker_name:
            return "nmol/L"  # Particle concentration
        elif "_C" in biomarker_name or "_C_" in biomarker_name:
            return "mmol/L"  # Cholesterol concentration
        elif "_TG" in biomarker_name:
            return "mmol/L"  # Triglyceride concentration
        elif "_PL" in biomarker_name:
            return "mmol/L"  # Phospholipid concentration
        else:
            return "mmol/L"  # Default


@register_action("NIGHTINGALE_NMR_MATCH")
class NightingaleNmrMatchAction(
    TypedStrategyAction[NightingaleNmrMatchParams, NightingaleNmrMatchResult]
):
    """
    Match Nightingale NMR biomarkers to standard identifiers (HMDB/LOINC).

    This action provides specialized matching for UK Biobank NMR metabolomics data
    from the Nightingale Health platform. It handles:
    - Exact matching for known biomarkers
    - Fuzzy matching for variations
    - Lipoprotein particle pattern recognition
    - Abbreviation expansion
    - Category classification
    - Unit standardization
    """

    def get_params_model(self) -> type[NightingaleNmrMatchParams]:
        """Return the params model class."""
        return NightingaleNmrMatchParams

    def get_result_model(self) -> type[NightingaleNmrMatchResult]:
        """Return the result model class."""
        return NightingaleNmrMatchResult

    def load_reference_data(self, params: NightingaleNmrMatchParams) -> pd.DataFrame:
        """Load reference data from file or use built-in patterns."""
        # Try to load from file
        reference = NightingaleReference(
            params.reference_file, params.use_cached_reference
        )
        ref_df = reference.load_reference()

        # If file doesn't exist or is empty, use built-in patterns
        if ref_df.empty:
            logger.info("Using built-in Nightingale patterns as reference")
            ref_data = []
            for name, info in NIGHTINGALE_PATTERNS.items():
                ref_data.append(
                    {
                        "nightingale_name": name,
                        "hmdb_id": info["hmdb"],
                        "loinc_code": info["loinc"],
                        "description": info["description"],
                        "category": info["category"],
                        "unit": info["unit"],
                    }
                )
            ref_df = pd.DataFrame(ref_data)

        return ref_df

    def process_biomarkers(
        self,
        df: pd.DataFrame,
        params: NightingaleNmrMatchParams,
        reference_df: pd.DataFrame,
    ) -> pd.DataFrame:
        """Process all biomarkers in dataset."""

        # Initialize matcher
        matcher = NightingaleMatcher()
        if params.use_abbreviations:
            matcher.abbreviations = matcher.load_abbreviations()

        # Process each biomarker
        results = []
        for idx, row in df.iterrows():
            biomarker_name = row.get(params.biomarker_column)

            if pd.isna(biomarker_name) or biomarker_name == "":
                continue

            # Match biomarker
            match_result = matcher.match_biomarker(
                biomarker_name, reference_df, params.match_threshold
            )

            if match_result:
                # Build result row
                result_row = {
                    "original_biomarker": biomarker_name,
                    "matched_name": match_result.get("nightingale_name"),
                    "confidence": match_result.get("confidence"),
                }

                # Add identifiers based on target format
                if params.target_format in ["hmdb", "both"]:
                    result_row["hmdb_id"] = match_result.get("hmdb_id")
                if params.target_format in ["loinc", "both"]:
                    result_row["loinc_code"] = match_result.get("loinc_code")

                # Add metadata if requested
                if params.add_metadata:
                    result_row["description"] = match_result.get("description")
                if params.include_categories:
                    result_row["category"] = match_result.get("category")
                if params.include_units:
                    result_row["unit"] = match_result.get("unit")

                # Add original data columns
                for col in df.columns:
                    if col != params.biomarker_column and col not in result_row:
                        result_row[col] = row[col]

                results.append(result_row)

        return pd.DataFrame(results) if results else pd.DataFrame()

    async def execute_typed(
        self,
        current_identifiers: List[str],
        current_ontology_type: str,
        params: NightingaleNmrMatchParams,
        source_endpoint: Any,
        target_endpoint: Any,
        context: StrategyExecutionContext,
    ) -> NightingaleNmrMatchResult:
        """Execute Nightingale NMR biomarker matching."""

        # Get input dataset from context
        datasets = context.get_action_data("datasets", {})

        if params.input_key not in datasets:
            raise ValueError(f"Dataset '{params.input_key}' not found in context")

        input_data = datasets[params.input_key]

        # Convert to DataFrame if needed
        if isinstance(input_data, list):
            df = pd.DataFrame(input_data)
        elif isinstance(input_data, pd.DataFrame):
            df = input_data.copy()
        else:
            df = pd.DataFrame([input_data])

        # Load reference data
        reference_df = self.load_reference_data(params)

        # Process biomarkers
        matched_df = self.process_biomarkers(df, params, reference_df)

        # Calculate statistics
        total_biomarkers = len(df)
        matched_biomarkers = len(matched_df)

        # Get unmatched biomarkers
        if matched_df.empty:
            unmatched = df[params.biomarker_column].dropna().tolist()
        else:
            matched_names = matched_df["original_biomarker"].tolist()
            unmatched = (
                df[~df[params.biomarker_column].isin(matched_names)][
                    params.biomarker_column
                ]
                .dropna()
                .tolist()
            )

        # Category breakdown
        category_counts = {}
        if not matched_df.empty and "category" in matched_df.columns:
            category_counts = matched_df["category"].value_counts().to_dict()

        # Store results in context
        datasets[params.output_key] = matched_df
        context.set_action_data("datasets", datasets)

        # Update statistics
        statistics = context.get_action_data("statistics", {})

        match_rate = (
            matched_biomarkers / total_biomarkers if total_biomarkers > 0 else 0
        )
        statistics["nightingale_nmr_match"] = {
            "total_biomarkers": total_biomarkers,
            "matched_biomarkers": matched_biomarkers,
            "match_rate": match_rate,
            "category_breakdown": category_counts,
        }
        context.set_action_data("statistics", statistics)

        # Prepare warnings
        warnings = []
        if reference_df.empty:
            warnings.append("Reference file not found, using built-in patterns only")
        if match_rate < 0.5:
            warnings.append(f"Low match rate: {match_rate:.1%}")

        return NightingaleNmrMatchResult(
            success=True,
            total_biomarkers=total_biomarkers,
            matched_biomarkers=matched_biomarkers,
            unmatched_biomarkers=unmatched,
            match_statistics={"match_rate": match_rate},
            category_breakdown=category_counts,
            reference_version="1.0.0",
            warnings=warnings if warnings else None,
        )
