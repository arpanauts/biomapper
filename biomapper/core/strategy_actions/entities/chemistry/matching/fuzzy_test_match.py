"""
Chemistry fuzzy test matching action for biomapper.

This action provides fuzzy matching for clinical chemistry/laboratory test names.
Unlike proteins and metabolites where fuzzy matching is a fallback, for chemistry 
tests it's the PRIMARY matching method due to high variability in test naming 
conventions across vendors, laboratories, and healthcare systems.
"""

import re
from typing import Dict, Any, List, Optional, Literal, Tuple
from functools import lru_cache

import pandas as pd
from pydantic import BaseModel, Field

try:
    from fuzzywuzzy import fuzz  # type: ignore[import-untyped]
except ImportError:
    # Fallback to rapidfuzz if fuzzywuzzy not available
    from rapidfuzz import fuzz

from biomapper.core.strategy_actions.typed_base import TypedStrategyAction
from biomapper.core.strategy_actions.registry import register_action


class ChemistryFuzzyTestMatchParams(BaseModel):
    """Parameters for fuzzy chemistry test name matching."""

    # Input/Output
    source_key: str = Field(..., description="Source dataset key")
    target_key: str = Field(..., description="Target dataset key")
    output_key: str = Field(..., description="Output dataset key")

    # Column configuration
    source_test_column: str = Field("test_name", description="Source test name column")
    target_test_column: str = Field("test_name", description="Target test name column")
    source_loinc_column: Optional[str] = Field(
        None, description="Source LOINC column (for validation)"
    )
    target_loinc_column: Optional[str] = Field(
        None, description="Target LOINC column (for validation)"
    )

    # Matching configuration
    match_threshold: float = Field(
        0.75, description="Minimum similarity threshold (0-1)"
    )
    use_synonyms: bool = Field(True, description="Use synonym expansion")
    synonym_file: Optional[str] = Field(
        "/procedure/data/local_data/references/lab_test_synonyms.csv",
        description="Path to synonym mapping file",
    )
    use_abbreviations: bool = Field(True, description="Expand/match abbreviations")

    # Matching algorithms
    algorithms: List[
        Literal["exact", "token_sort", "partial", "abbreviation", "synonym", "phonetic"]
    ] = Field(
        default=["exact", "token_sort", "partial", "abbreviation", "synonym"],
        description="Matching algorithms to use (in order)",
    )

    # Unit handling
    normalize_units: bool = Field(True, description="Normalize measurement units")
    ignore_units: bool = Field(False, description="Ignore units in matching")
    unit_equivalence: bool = Field(
        True, description="Treat equivalent units as matches"
    )

    # Vendor handling
    handle_vendor_prefixes: bool = Field(
        True, description="Handle vendor-specific prefixes"
    )
    cross_vendor_matching: bool = Field(
        True, description="Enable cross-vendor matching"
    )

    # Advanced options
    use_loinc_primary: bool = Field(
        False, description="Use LOINC as primary match if available"
    )
    fallback_to_name: bool = Field(
        True, description="Fallback to name if LOINC doesn't match"
    )
    handle_panels: bool = Field(True, description="Expand test panels to components")
    metabolite_to_test_mapping: bool = Field(
        False, description="Map metabolite names to test names"
    )

    # Output options
    include_similarity_score: bool = Field(
        True, description="Include match confidence scores"
    )
    include_match_method: bool = Field(
        True, description="Include which algorithm matched"
    )
    max_matches_per_test: int = Field(
        1, description="Maximum matches to return per test"
    )


class ChemistryFuzzyTestMatchResult(BaseModel):
    """Result of fuzzy chemistry test matching."""

    success: bool
    total_source_tests: int
    total_target_tests: int
    matched_tests: int
    unmatched_tests: List[str]
    match_methods: Dict[str, int]  # Count by algorithm
    average_similarity: float
    match_quality_distribution: Dict[str, int]  # High/Medium/Low
    vendor_cross_matches: int
    warnings: Optional[List[str]] = None


class TestNameNormalizer:
    """Normalize chemistry test names for matching."""

    def __init__(self) -> None:
        """Initialize normalizer with caching."""
        self._cache: Dict[str, str] = {}

    @lru_cache(maxsize=1000)
    def normalize_test_name(self, test_name: str) -> str:
        """Apply comprehensive normalization with caching."""
        if not test_name or pd.isna(test_name):
            return ""

        if isinstance(test_name, (int, float)):  # type: ignore[unreachable]
            test_name = str(test_name)  # type: ignore[unreachable]

        normalized = test_name.lower().strip()

        if not normalized:
            return ""

        # Remove vendor prefixes
        normalized = self._remove_vendor_prefixes(normalized)

        # Standardize punctuation
        normalized = re.sub(r"[,;:]", " ", normalized)
        normalized = re.sub(r"[()]", "", normalized)
        normalized = re.sub(r"\s+", " ", normalized)

        # Remove specimen types
        normalized = self._remove_specimen_types(normalized)

        # Standardize units
        normalized = self._standardize_units(normalized)

        return normalized.strip()

    def _remove_vendor_prefixes(self, name: str) -> str:
        """Remove vendor-specific prefixes."""
        prefixes = [
            r"^lc\s*\d*\s*",  # LabCorp
            r"^qd\s*\d*\s*",  # Quest
            r"^mayo\s*",  # Mayo
            r"^\d{5}(-\d+\.\d+)?\s*",  # UKBB field codes like 30740-0.0
            r"^labcorp\s*",  # LabCorp full name
            r"^quest\s*",  # Quest full name
        ]
        for prefix in prefixes:
            name = re.sub(prefix, "", name, flags=re.IGNORECASE)
        return name

    def _remove_specimen_types(self, name: str) -> str:
        """Remove specimen type indicators."""
        specimens = [
            "24 hour urine",  # Put longer patterns first
            "cerebrospinal fluid",
            "whole blood",
            "serum",
            "plasma",
            "blood",
            "urine",
            "arterial",
            "venous",
            "capillary",
            "csf",
            "fluid",
            "stool",
            "saliva",
        ]

        # Remove comma-separated specimens and standalone specimens
        for specimen in specimens:
            patterns = [
                f", {specimen}",
                f"{specimen},",
                f" {specimen}$",  # End of string
                f"^{specimen} ",  # Beginning of string
            ]
            for pattern in patterns:
                name = re.sub(pattern, "", name, flags=re.IGNORECASE).strip()

        return name

    def _standardize_units(self, name: str) -> str:
        """Standardize measurement units."""
        unit_mappings = {
            r"\bmg/dl\b": "mg/dL",
            r"\bmmol/l\b": "mmol/L",
            r"\bg/dl\b": "g/dL",
            r"\bu/l\b": "U/L",
            r"\biu/ml\b": "IU/mL",
            r"\bng/ml\b": "ng/mL",
            r"\bpg/ml\b": "pg/mL",
            r"\bmg/l\b": "mg/L",
            r"\bμmol/l\b": "μmol/L",
            r"\bumol/l\b": "μmol/L",  # ASCII alternative
            r"\bmiu/ml\b": "mIU/mL",
        }
        for pattern, replacement in unit_mappings.items():
            name = re.sub(pattern, replacement, name, flags=re.IGNORECASE)
        return name


class AbbreviationExpander:
    """Handle test name abbreviations and synonyms."""

    # Common lab test abbreviations
    ABBREVIATIONS = {
        "alt": "alanine aminotransferase",
        "ast": "aspartate aminotransferase",
        "bun": "blood urea nitrogen",
        "cbc": "complete blood count",
        "chol": "cholesterol",
        "trig": "triglycerides",
        "gluc": "glucose",
        "hgb": "hemoglobin",
        "hct": "hematocrit",
        "wbc": "white blood cell",
        "rbc": "red blood cell",
        "plt": "platelet",
        "na": "sodium",
        "k": "potassium",
        "cl": "chloride",
        "co2": "carbon dioxide",
        "cr": "creatinine",
        "gfr": "glomerular filtration rate",
        "egfr": "estimated glomerular filtration rate",
        "ldl": "low density lipoprotein",
        "hdl": "high density lipoprotein",
        "vldl": "very low density lipoprotein",
        "tsh": "thyroid stimulating hormone",
        "t3": "triiodothyronine",
        "t4": "thyroxine",
        "ft3": "free triiodothyronine",
        "ft4": "free thyroxine",
        "psa": "prostate specific antigen",
        "hba1c": "hemoglobin a1c",
        "a1c": "hemoglobin a1c",
        "alk phos": "alkaline phosphatase",
        "alp": "alkaline phosphatase",
        "bili": "bilirubin",
        "tp": "total protein",
        "alb": "albumin",
        "glob": "globulin",
        "a/g": "albumin/globulin ratio",
        "inr": "international normalized ratio",
        "pt": "prothrombin time",
        "ptt": "partial thromboplastin time",
        "aptt": "activated partial thromboplastin time",
        "sgpt": "alanine aminotransferase",  # ALT synonym
        "sgot": "aspartate aminotransferase",  # AST synonym
        "ldl-c": "ldl cholesterol",
        "hdl-c": "hdl cholesterol",
    }

    # Synonym groups - tests that mean the same thing
    SYNONYM_GROUPS = [
        [
            "glucose",
            "blood sugar",
            "blood glucose",
            "fasting glucose",
            "random glucose",
        ],
        ["cholesterol", "total cholesterol", "cholesterol total"],
        [
            "ldl cholesterol",
            "ldl-c",
            "bad cholesterol",
            "low density lipoprotein cholesterol",
        ],
        [
            "hdl cholesterol",
            "hdl-c",
            "good cholesterol",
            "high density lipoprotein cholesterol",
        ],
        ["triglycerides", "trig", "trigs", "triglyceride"],
        ["hemoglobin a1c", "hba1c", "a1c", "glycated hemoglobin", "glycohemoglobin"],
        ["creatinine", "cr", "creat", "serum creatinine"],
        ["blood urea nitrogen", "bun", "urea nitrogen", "urea"],
        ["alanine aminotransferase", "alt", "sgpt", "alanine transaminase"],
        ["aspartate aminotransferase", "ast", "sgot", "aspartate transaminase"],
        ["alkaline phosphatase", "alk phos", "alp"],
        ["white blood cell count", "wbc", "white count", "leukocyte count"],
        ["red blood cell count", "rbc", "red count", "erythrocyte count"],
        ["platelet count", "plt", "platelets"],
        ["thyroid stimulating hormone", "tsh"],
        ["bilirubin total", "total bilirubin", "bili", "bilirubin"],
        ["albumin/globulin ratio", "a/g ratio", "a/g"],
    ]

    @lru_cache(maxsize=500)
    def expand_abbreviation(self, text: str) -> str:
        """Expand known abbreviations in text."""
        if not text:
            return text

        words = text.lower().split()
        expanded = []

        for word in words:
            # Clean up word (remove punctuation at end)
            clean_word = re.sub(r"[^\w]$", "", word)
            if clean_word in self.ABBREVIATIONS:
                expanded.append(self.ABBREVIATIONS[clean_word])
            else:
                expanded.append(word)

        return " ".join(expanded)

    @lru_cache(maxsize=500)
    def get_synonyms(self, test_name: str) -> List[str]:
        """Get all synonyms for a test name."""
        test_name_lower = test_name.lower().strip()
        synonyms = [test_name]

        for group in self.SYNONYM_GROUPS:
            group_lower = [s.lower() for s in group]
            if test_name_lower in group_lower:
                synonyms.extend(group)
                break

        # Remove duplicates and return
        return list(set(synonyms))


class TestPanelExpander:
    """Expand test panels to individual components."""

    # Common test panels and their components
    TEST_PANELS = {
        "basic metabolic panel": [
            "glucose",
            "sodium",
            "potassium",
            "chloride",
            "co2",
            "bun",
            "creatinine",
            "calcium",
        ],
        "bmp": [
            "glucose",
            "sodium",
            "potassium",
            "chloride",
            "co2",
            "bun",
            "creatinine",
            "calcium",
        ],
        "comprehensive metabolic panel": [
            "glucose",
            "sodium",
            "potassium",
            "chloride",
            "co2",
            "bun",
            "creatinine",
            "calcium",
            "albumin",
            "total protein",
            "alt",
            "ast",
            "alkaline phosphatase",
            "bilirubin total",
        ],
        "cmp": [
            "glucose",
            "sodium",
            "potassium",
            "chloride",
            "co2",
            "bun",
            "creatinine",
            "calcium",
            "albumin",
            "total protein",
            "alt",
            "ast",
            "alkaline phosphatase",
            "bilirubin total",
        ],
        "lipid panel": [
            "total cholesterol",
            "ldl cholesterol",
            "hdl cholesterol",
            "triglycerides",
        ],
        "lipid profile": [
            "total cholesterol",
            "ldl cholesterol",
            "hdl cholesterol",
            "triglycerides",
        ],
        "liver function panel": [
            "alt",
            "ast",
            "alkaline phosphatase",
            "bilirubin total",
            "bilirubin direct",
            "albumin",
            "total protein",
        ],
        "liver panel": [
            "alt",
            "ast",
            "alkaline phosphatase",
            "bilirubin total",
            "bilirubin direct",
            "albumin",
            "total protein",
        ],
        "hepatic function panel": [
            "alt",
            "ast",
            "alkaline phosphatase",
            "bilirubin total",
            "bilirubin direct",
            "albumin",
            "total protein",
        ],
        "complete blood count": [
            "white blood cell count",
            "red blood cell count",
            "hemoglobin",
            "hematocrit",
            "platelet count",
            "mcv",
            "mch",
            "mchc",
            "rdw",
        ],
        "cbc": [
            "white blood cell count",
            "red blood cell count",
            "hemoglobin",
            "hematocrit",
            "platelet count",
        ],
        "thyroid panel": ["tsh", "free t4", "free t3"],
        "thyroid function tests": ["tsh", "free t4", "free t3"],
    }

    @lru_cache(maxsize=100)
    def expand_if_panel(self, test_name: str) -> List[str]:
        """Expand test panel to components if applicable."""
        if not test_name:
            return [test_name]

        test_lower = test_name.lower().strip()

        # Check if it's a known panel
        for panel_name, components in self.TEST_PANELS.items():
            if panel_name == test_lower or panel_name in test_lower:
                return components.copy()  # Return copy to avoid mutation

        # Not a panel, return as is
        return [test_name]


class MultiAlgorithmMatcher:
    """Apply multiple matching algorithms with fallback."""

    def __init__(self) -> None:
        """Initialize matcher with helper classes."""
        self.normalizer = TestNameNormalizer()
        self.expander = AbbreviationExpander()

    def match_tests(
        self,
        source_test: str,
        target_test: str,
        algorithms: List[
            Literal[
                "exact", "token_sort", "partial", "abbreviation", "synonym", "phonetic"
            ]
        ],
        threshold: float,
    ) -> Tuple[bool, float, str]:
        """Try multiple algorithms until match found."""

        # Normalize both test names
        source_norm = self.normalizer.normalize_test_name(source_test)
        target_norm = self.normalizer.normalize_test_name(target_test)

        if not source_norm or not target_norm:
            return False, 0.0, "none"

        for algorithm in algorithms:
            try:
                is_match, score = self._apply_algorithm(
                    source_norm, target_norm, algorithm, source_test, target_test
                )

                if is_match and score >= threshold:
                    return True, score, algorithm
            except Exception:
                # Log warning but continue with other algorithms
                continue

        return False, 0.0, "none"

    def _apply_algorithm(
        self,
        source: str,
        target: str,
        algorithm: str,
        source_original: str = "",
        target_original: str = "",
    ) -> Tuple[bool, float]:
        """Apply specific matching algorithm."""

        if algorithm == "exact":
            return self._exact_match(source, target)
        elif algorithm == "token_sort":
            return self._token_sort_match(source, target)
        elif algorithm == "partial":
            return self._partial_match(source, target)
        elif algorithm == "abbreviation":
            return self._abbreviation_match(source, target)
        elif algorithm == "synonym":
            return self._synonym_match(
                source_original or source, target_original or target
            )
        elif algorithm == "phonetic":
            return self._phonetic_match(source, target)

        return False, 0.0

    def _exact_match(self, source: str, target: str) -> Tuple[bool, float]:
        """Exact string matching."""
        if source == target:
            return True, 1.0
        return False, 0.0

    def _token_sort_match(self, source: str, target: str) -> Tuple[bool, float]:
        """Token sort ratio matching (handles word order)."""
        score = fuzz.token_sort_ratio(source, target) / 100.0
        return score >= 0.75, score

    def _partial_match(self, source: str, target: str) -> Tuple[bool, float]:
        """Partial string matching."""
        score = fuzz.partial_ratio(source, target) / 100.0
        return score >= 0.80, score

    def _abbreviation_match(self, source: str, target: str) -> Tuple[bool, float]:
        """Match with abbreviation expansion."""
        source_expanded = self.expander.expand_abbreviation(source)
        target_expanded = self.expander.expand_abbreviation(target)

        # Try all combinations
        combinations = [
            (source, target),
            (source_expanded, target),
            (source, target_expanded),
            (source_expanded, target_expanded),
        ]

        best_score = 0.0
        for s, t in combinations:
            if s and t:  # Make sure neither is empty
                score = fuzz.ratio(s, t) / 100.0
                best_score = max(best_score, score)

        return best_score >= 0.75, best_score

    def _synonym_match(self, source: str, target: str) -> Tuple[bool, float]:
        """Match using synonym expansion."""
        source_synonyms = self.expander.get_synonyms(source)
        target_synonyms = self.expander.get_synonyms(target)

        # Check if any synonyms match
        for s_syn in source_synonyms:
            for t_syn in target_synonyms:
                if s_syn.lower() == t_syn.lower():
                    return True, 0.9  # High confidence for synonym match

        return False, 0.0

    def _phonetic_match(self, source: str, target: str) -> Tuple[bool, float]:
        """Phonetic matching for misspellings."""
        try:
            # Simple soundex-like matching for common misspellings
            if len(source) > 2 and len(target) > 2:
                # Check if first letters match and there's reasonable similarity
                if source[0] == target[0]:
                    score = fuzz.ratio(source, target) / 100.0
                    if score >= 0.6:  # Lower threshold for phonetic
                        return True, 0.7  # Lower confidence for phonetic
        except Exception:
            pass

        return False, 0.0


@register_action("CHEMISTRY_FUZZY_TEST_MATCH")
class ChemistryFuzzyTestMatchAction(
    TypedStrategyAction[ChemistryFuzzyTestMatchParams, ChemistryFuzzyTestMatchResult]
):
    """
    Chemistry fuzzy test matching action.

    Provides comprehensive fuzzy matching for clinical chemistry test names,
    handling abbreviations, synonyms, vendor variations, and test panels.
    """

    def get_params_model(self) -> type[ChemistryFuzzyTestMatchParams]:
        """Get the parameters model class."""
        return ChemistryFuzzyTestMatchParams

    def get_result_model(self) -> type[ChemistryFuzzyTestMatchResult]:
        """Get the result model class."""
        return ChemistryFuzzyTestMatchResult

    async def execute_typed(  # type: ignore[override]
        self, params: ChemistryFuzzyTestMatchParams, context: Dict[str, Any]
    ) -> ChemistryFuzzyTestMatchResult:
        """Execute fuzzy chemistry test matching."""

        try:
            # Get datasets from context
            source_df = context["datasets"][params.source_key].copy()
            target_df = context["datasets"][params.target_key].copy()

            # Validate required columns exist
            if params.source_test_column not in source_df.columns:
                raise ValueError(
                    f"Source column '{params.source_test_column}' not found"
                )
            if params.target_test_column not in target_df.columns:
                raise ValueError(
                    f"Target column '{params.target_test_column}' not found"
                )

            # Perform batch matching
            matches_df = await self._perform_batch_matching(
                source_df, target_df, params
            )

            # Calculate statistics
            total_source = len(source_df[params.source_test_column].dropna().unique())
            total_target = len(target_df[params.target_test_column].dropna().unique())
            matched_count = len(matches_df)

            # Get unmatched tests
            matched_source_tests = (
                set(matches_df["source_test"].tolist())
                if not matches_df.empty
                else set()
            )
            all_source_tests = set(
                source_df[params.source_test_column].dropna().unique()
            )
            unmatched_tests = list(all_source_tests - matched_source_tests)

            # Calculate match method distribution
            match_methods = (
                matches_df["match_method"].value_counts().to_dict()
                if not matches_df.empty
                else {}
            )

            # Calculate average similarity
            avg_similarity = (
                matches_df["similarity_score"].mean() if not matches_df.empty else 0.0
            )

            # Quality distribution
            if not matches_df.empty:
                quality_dist = {
                    "high": (matches_df["similarity_score"] >= 0.9).sum(),
                    "medium": (
                        (matches_df["similarity_score"] >= 0.75)
                        & (matches_df["similarity_score"] < 0.9)
                    ).sum(),
                    "low": (matches_df["similarity_score"] < 0.75).sum(),
                }
            else:
                quality_dist = {"high": 0, "medium": 0, "low": 0}

            # Store results in context
            context["datasets"][params.output_key] = matches_df

            # Update statistics
            context["statistics"]["chemistry_fuzzy_match"] = {
                "total_matches": matched_count,
                "average_similarity": float(avg_similarity)
                if not pd.isna(avg_similarity)
                else 0.0,
                "match_methods": match_methods,
                "quality_distribution": quality_dist,
                "unmatched_count": len(unmatched_tests),
            }

            return ChemistryFuzzyTestMatchResult(
                success=True,
                total_source_tests=total_source,
                total_target_tests=total_target,
                matched_tests=matched_count,
                unmatched_tests=unmatched_tests[:10],  # Limit to first 10
                match_methods=match_methods,
                average_similarity=float(avg_similarity)
                if not pd.isna(avg_similarity)
                else 0.0,
                match_quality_distribution=quality_dist,
                vendor_cross_matches=0,  # TODO: Calculate this properly
                warnings=None,
            )

        except Exception as e:
            return ChemistryFuzzyTestMatchResult(
                success=False,
                total_source_tests=0,
                total_target_tests=0,
                matched_tests=0,
                unmatched_tests=[],
                match_methods={},
                average_similarity=0.0,
                match_quality_distribution={"high": 0, "medium": 0, "low": 0},
                vendor_cross_matches=0,
                warnings=[f"Error during matching: {str(e)}"],
            )

    async def _perform_batch_matching(
        self,
        source_df: pd.DataFrame,
        target_df: pd.DataFrame,
        params: ChemistryFuzzyTestMatchParams,
    ) -> pd.DataFrame:
        """Perform fuzzy matching on entire datasets."""

        # Initialize components
        matcher = MultiAlgorithmMatcher()
        panel_expander = TestPanelExpander()

        # Get unique test names
        source_tests = (
            source_df[params.source_test_column].dropna().astype(str).unique()
        )
        target_tests = (
            target_df[params.target_test_column].dropna().astype(str).unique()
        )

        # Expand panels if requested
        if params.handle_panels:
            expanded_source = []
            for test in source_tests:
                expanded = panel_expander.expand_if_panel(test)
                expanded_source.extend(expanded)
            source_tests = list(set(expanded_source))  # type: ignore[assignment]

        # Build match results
        matches = []

        for source_test in source_tests:
            if not source_test or pd.isna(source_test):
                continue

            best_match = None
            best_score = 0.0
            best_method = "none"

            for target_test in target_tests:
                if not target_test or pd.isna(target_test):
                    continue

                is_match, score, method = matcher.match_tests(
                    str(source_test),
                    str(target_test),
                    params.algorithms,
                    params.match_threshold,
                )

                if is_match and score > best_score:
                    best_match = target_test
                    best_score = score
                    best_method = method

                    # If we want only one match per test and this is perfect, break
                    if params.max_matches_per_test == 1 and score >= 0.99:
                        break

            if best_match and best_score >= params.match_threshold:
                match_record = {
                    "source_test": source_test,
                    "target_test": best_match,
                    "similarity_score": best_score,
                    "match_method": best_method,
                }

                # Add optional columns based on params
                if params.include_similarity_score:
                    match_record["similarity_score"] = best_score
                if params.include_match_method:
                    match_record["match_method"] = best_method

                matches.append(match_record)

        return pd.DataFrame(matches)
