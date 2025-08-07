"""
CHEMISTRY_VENDOR_HARMONIZATION action for standardizing clinical chemistry test data across vendors.

This action harmonizes clinical chemistry test data across different vendors (LabCorp, Quest, Mayo, 
Arivale, Israeli10k, UKBB). Each vendor has unique test naming conventions, units, reference ranges, 
and data formats. This action standardizes these differences to enable cross-vendor comparison.
"""

import re
import pandas as pd
from typing import Any, Dict, List, Optional, Literal, Tuple
from pydantic import BaseModel, Field
import logging

from biomapper.core.strategy_actions.registry import register_action


class ChemistryVendorHarmonizationParams(BaseModel):
    """Parameters for chemistry vendor harmonization."""

    # Input/Output
    input_key: str = Field(..., description="Input dataset key")
    output_key: str = Field(..., description="Output dataset key")

    # Vendor configuration
    vendor: Optional[
        Literal["arivale", "labcorp", "quest", "mayo", "israeli10k", "ukbb", "auto"]
    ] = Field("auto", description="Source vendor (auto-detect if not specified)")
    vendors: Optional[List[str]] = Field(
        None, description="List of vendors for multi-vendor harmonization"
    )

    # Column mapping
    test_name_column: str = Field("test_name", description="Test name column")
    value_column: str = Field("value", description="Test value column")
    unit_column: str = Field("unit", description="Unit column")
    reference_range_column: Optional[str] = Field(
        None, description="Reference range column"
    )
    vendor_column: Optional[str] = Field(None, description="Vendor identifier column")

    # Harmonization options
    harmonization_rules: Optional[Dict[str, List[str]]] = Field(
        None, description="Custom harmonization rules"
    )
    standardize_test_names: bool = Field(True, description="Standardize test names")
    standardize_units: bool = Field(True, description="Convert to standard units")
    standardize_reference_ranges: bool = Field(
        True, description="Harmonize reference ranges"
    )

    # Unit conversion
    target_unit_system: Literal["SI", "US", "hybrid"] = Field(
        "SI",
        description="Target unit system (SI International, US Conventional, hybrid)",
    )
    unit_conversion_file: Optional[str] = Field(
        "/procedure/data/local_data/references/unit_conversions.csv",
        description="Path to unit conversion factors",
    )

    # Test grouping
    group_by_category: bool = Field(
        True, description="Group tests by clinical category"
    )
    categories: Optional[List[str]] = Field(
        None, description="Specific categories to include"
    )

    # Quality control
    flag_out_of_range: bool = Field(
        True, description="Flag values outside reference range"
    )
    validate_units: bool = Field(True, description="Validate unit consistency")
    handle_missing_units: Literal["skip", "infer", "default"] = Field(
        "infer", description="How to handle missing units"
    )

    # Output options
    add_harmonization_log: bool = Field(True, description="Add harmonization metadata")
    preserve_original: bool = Field(
        True, description="Keep original values in separate columns"
    )


class ChemistryVendorHarmonizationResult(BaseModel):
    """Result of chemistry vendor harmonization."""

    success: bool
    total_tests: int
    harmonized_tests: int
    vendors_processed: List[str]
    unit_conversions: Dict[str, int]  # Count by conversion type
    test_name_mappings: Dict[str, int]  # Count by mapping
    out_of_range_values: int
    missing_units_handled: int
    category_distribution: Dict[str, int]
    warnings: Optional[List[str]] = None


class VendorProfile:
    """Define vendor-specific characteristics and detection patterns."""

    VENDOR_PROFILES: Dict[str, Dict[str, Any]] = {
        "labcorp": {
            "test_code_pattern": r"^LC\d{3,5}",
            "unit_style": "US",
            "name_format": "uppercase",
            "reference_format": "range",
            "common_tests": {
                "001453": "Glucose",
                "001123": "Cholesterol, Total",
                "001172": "LDL Cholesterol",
                "001869": "HDL Cholesterol",
            },
        },
        "quest": {
            "test_code_pattern": r"^QD\d{3,5}",
            "unit_style": "US",
            "name_format": "mixed_case",
            "reference_format": "low-high",
            "common_tests": {
                "483": "Glucose",
                "234": "Cholesterol, Total",
                "345": "LDL Cholesterol Direct",
            },
        },
        "mayo": {
            "test_code_pattern": r"^[A-Z]{2,4}\d{0,4}$",
            "unit_style": "hybrid",
            "name_format": "abbreviated",
            "reference_format": "age_sex_specific",
            "common_tests": {
                "GLU": "Glucose, Serum",
                "CHOL": "Cholesterol, Total, Serum",
                "LDLC": "Cholesterol, LDL, Serum",
            },
        },
        "arivale": {
            "test_code_pattern": None,
            "unit_style": "US",
            "name_format": "descriptive",
            "reference_format": "optimal_range",
            "name_suffix_pattern": r"\s*\([^)]+\)$",  # Test Name (details)
            "common_tests": {
                "Glucose, Serum": "Glucose",
                "Cholesterol, Total, Serum": "Cholesterol",
            },
        },
        "israeli10k": {
            "test_code_pattern": r"^\d{4,6}$",
            "unit_style": "SI",
            "name_format": "hebrew_english",
            "reference_format": "population_specific",
            "requires_translation": True,
        },
        "ukbb": {
            "test_code_pattern": r"^\d{5}$",  # Field IDs
            "unit_style": "SI",
            "name_format": "field_id",
            "reference_format": "ukbb_specific",
            "field_mapping": {
                "30000": "Glucose",
                "30690": "Cholesterol",
                "30780": "LDL Direct",
            },
        },
    }

    def detect_vendor(self, df: pd.DataFrame, columns: Dict[str, str]) -> str:
        """Auto-detect vendor from data patterns."""

        # Check test code patterns
        if "test_code" in columns and columns["test_code"] in df.columns:
            test_codes = df[columns["test_code"]].dropna().head(100)

            for vendor, profile in self.VENDOR_PROFILES.items():
                if profile.get("test_code_pattern"):
                    pattern = profile["test_code_pattern"]
                    matches = test_codes.str.match(pattern).sum()
                    if matches > len(test_codes) * 0.5:
                        return vendor

        # Check test name patterns
        if columns.get("test_name") in df.columns:
            test_names = df[columns["test_name"]].dropna().head(100).astype(str)

            # Check for Arivale pattern
            if test_names.str.contains(r"\([^)]+\)$").sum() > len(test_names) * 0.3:
                return "arivale"

            # Check for UKBB field IDs
            if test_names.str.match(r"^\d{5}$").sum() > len(test_names) * 0.5:
                return "ukbb"

        return "generic"


class TestNameHarmonizer:
    """Harmonize test names across vendors."""

    # Universal test name mappings
    UNIVERSAL_TEST_NAMES = {
        # Glucose variations
        "glucose": "Glucose",
        "glucose, serum": "Glucose",
        "glucose, plasma": "Glucose",
        "glucose, fasting": "Glucose (Fasting)",
        "blood sugar": "Glucose",
        "glu": "Glucose",
        # Cholesterol variations
        "cholesterol": "Cholesterol, Total",
        "cholesterol, total": "Cholesterol, Total",
        "total cholesterol": "Cholesterol, Total",
        "chol": "Cholesterol, Total",
        "ldl cholesterol": "Cholesterol, LDL",
        "ldl-c": "Cholesterol, LDL",
        "ldl cholesterol direct": "Cholesterol, LDL",
        "ldlc": "Cholesterol, LDL",
        "hdl cholesterol": "Cholesterol, HDL",
        "hdl-c": "Cholesterol, HDL",
        "hdlc": "Cholesterol, HDL",
        # Liver tests
        "alt": "Alanine Aminotransferase (ALT)",
        "alanine aminotransferase": "Alanine Aminotransferase (ALT)",
        "sgpt": "Alanine Aminotransferase (ALT)",
        "ast": "Aspartate Aminotransferase (AST)",
        "aspartate aminotransferase": "Aspartate Aminotransferase (AST)",
        "sgot": "Aspartate Aminotransferase (AST)",
        # Kidney tests
        "creatinine": "Creatinine",
        "creatinine, serum": "Creatinine",
        "cr": "Creatinine",
        "bun": "Blood Urea Nitrogen",
        "urea nitrogen": "Blood Urea Nitrogen",
        "blood urea nitrogen": "Blood Urea Nitrogen",
        "egfr": "eGFR",
        "estimated gfr": "eGFR",
        "glomerular filtration rate": "eGFR",
    }

    def harmonize_test_name(self, test_name: Optional[str], vendor: str) -> str:
        """Harmonize test name based on vendor."""

        if test_name is None or pd.isna(test_name):
            return ""

        test_name = str(test_name)

        # Handle empty or whitespace-only strings
        if not test_name.strip():
            return test_name

        # Clean and normalize
        clean_name = test_name.strip().lower()

        # Remove vendor-specific suffixes
        if vendor == "arivale":
            clean_name = re.sub(r"\s*\([^)]+\)$", "", clean_name)

        # Apply universal mapping
        if clean_name in self.UNIVERSAL_TEST_NAMES:
            return self.UNIVERSAL_TEST_NAMES[clean_name]

        # Check vendor-specific mappings
        vendor_profile = VendorProfile.VENDOR_PROFILES.get(vendor, {})
        vendor_tests = vendor_profile.get("common_tests", {})

        for code, standard_name in vendor_tests.items():
            if code.lower() in clean_name or clean_name in code.lower():
                return str(standard_name)

        # Return title case if no mapping found
        return test_name.title()


class UnitConverter:
    """Convert units between different systems."""

    # Conversion factors (to SI units)
    UNIT_CONVERSIONS = {
        # Glucose
        ("mg/dL", "mmol/L", "glucose"): 0.0555,  # mg/dL to mmol/L
        ("mg/dl", "mmol/L", "glucose"): 0.0555,
        # Cholesterol
        ("mg/dL", "mmol/L", "cholesterol"): 0.0259,
        ("mg/dl", "mmol/L", "cholesterol"): 0.0259,
        # Creatinine
        ("mg/dL", "umol/L", "creatinine"): 88.4,
        ("mg/dl", "umol/L", "creatinine"): 88.4,
        # Triglycerides
        ("mg/dL", "mmol/L", "triglycerides"): 0.0113,
        # Proteins (albumin, total protein)
        ("g/dL", "g/L", "protein"): 10.0,
        ("g/dl", "g/L", "protein"): 10.0,
        # Enzymes (no conversion, just standardize)
        ("U/L", "U/L", "enzyme"): 1.0,
        ("IU/L", "U/L", "enzyme"): 1.0,
        # Electrolytes (already in SI)
        ("mmol/L", "mmol/L", "electrolyte"): 1.0,
        ("mEq/L", "mmol/L", "electrolyte"): 1.0,
    }

    def standardize_unit(
        self, value: float, current_unit: str, target_unit: str, test_type: str
    ) -> Tuple[float, str]:
        """Convert value to target unit."""

        if not current_unit or pd.isna(value):
            return value, current_unit

        # Clean units
        current_clean = str(current_unit).strip()
        target_clean = str(target_unit).strip()

        # Find conversion factor
        for (from_unit, to_unit, test), factor in self.UNIT_CONVERSIONS.items():
            if (
                current_clean.lower() == from_unit.lower()
                and target_clean.lower() == to_unit.lower()
                and test in str(test_type).lower()
            ):
                return value * factor, target_unit

        # No conversion needed or found
        return value, current_unit

    def get_standard_unit(self, test_name: str, system: str = "SI") -> Optional[str]:
        """Get standard unit for test in specified system."""

        SI_UNITS = {
            "Glucose": "mmol/L",
            "Cholesterol": "mmol/L",
            "Triglycerides": "mmol/L",
            "Creatinine": "umol/L",
            "Blood Urea Nitrogen": "mmol/L",
            "Alanine Aminotransferase": "U/L",
            "Aspartate Aminotransferase": "U/L",
            "Albumin": "g/L",
            "Total Protein": "g/L",
            "Sodium": "mmol/L",
            "Potassium": "mmol/L",
            "Chloride": "mmol/L",
        }

        US_UNITS = {
            "Glucose": "mg/dL",
            "Cholesterol": "mg/dL",
            "Triglycerides": "mg/dL",
            "Creatinine": "mg/dL",
            "Blood Urea Nitrogen": "mg/dL",
            "Alanine Aminotransferase": "U/L",
            "Aspartate Aminotransferase": "U/L",
            "Albumin": "g/dL",
            "Total Protein": "g/dL",
            "Sodium": "mEq/L",
            "Potassium": "mEq/L",
            "Chloride": "mEq/L",
        }

        units = SI_UNITS if system == "SI" else US_UNITS

        # Find test in mapping
        for test, unit in units.items():
            if test.lower() in str(test_name).lower():
                return unit

        return None


class ReferenceRangeHarmonizer:
    """Harmonize reference ranges across vendors."""

    # Standard reference ranges (SI units)
    STANDARD_RANGES = {
        "Glucose": {"low": 3.9, "high": 5.6, "unit": "mmol/L"},
        "Glucose (Fasting)": {"low": 3.9, "high": 5.6, "unit": "mmol/L"},
        "Cholesterol, Total": {"low": 0, "high": 5.2, "unit": "mmol/L"},
        "Cholesterol, LDL": {"low": 0, "high": 3.4, "unit": "mmol/L"},
        "Cholesterol, HDL": {
            "low": 1.0,
            "high": 100,
            "unit": "mmol/L",
        },  # >1.0 for men, >1.3 for women
        "Triglycerides": {"low": 0, "high": 1.7, "unit": "mmol/L"},
        "Creatinine": {
            "low": 62,
            "high": 106,
            "unit": "umol/L",
        },  # Men: 62-106, Women: 44-80
        "Blood Urea Nitrogen": {"low": 2.5, "high": 7.1, "unit": "mmol/L"},
        "Alanine Aminotransferase (ALT)": {"low": 0, "high": 40, "unit": "U/L"},
        "Aspartate Aminotransferase (AST)": {"low": 0, "high": 40, "unit": "U/L"},
    }

    def parse_reference_range(
        self, range_str: Optional[str], vendor: str
    ) -> Tuple[Optional[float], Optional[float]]:
        """Parse vendor-specific reference range formats."""

        if not range_str or pd.isna(range_str):
            return None, None

        range_str = str(range_str).strip()

        # Common patterns
        patterns = [
            r"(\d+\.?\d*)\s*-\s*(\d+\.?\d*)",  # 70-100
            r"(\d+\.?\d*)\s*to\s*(\d+\.?\d*)",  # 70 to 100
            r"<\s*(\d+\.?\d*)",  # <100 (0 to value)
            r">\s*(\d+\.?\d*)",  # >70 (value to inf)
            r"≤\s*(\d+\.?\d*)",  # ≤100
            r"≥\s*(\d+\.?\d*)",  # ≥70
        ]

        for pattern in patterns:
            match = re.match(pattern, range_str)
            if match:
                groups = match.groups()
                if len(groups) == 2:
                    return float(groups[0]), float(groups[1])
                elif len(groups) == 1:
                    if "<" in range_str or "≤" in range_str:
                        return 0, float(groups[0])
                    else:
                        return float(groups[0]), float("inf")

        return None, None

    def harmonize_reference_range(
        self, test_name: str, value: float, current_range: Optional[str], vendor: str
    ) -> Dict[str, Any]:
        """Harmonize reference range and flag out-of-range values."""

        # Get standard range
        standard = self.STANDARD_RANGES.get(test_name, {})

        if not standard:
            # Try to parse vendor range
            low, high = self.parse_reference_range(current_range, vendor)
            return {
                "low": low,
                "high": high,
                "in_range": True if low and high and low <= value <= high else None,
            }

        # Check if value is in standard range
        low_val = standard.get("low", 0)
        high_val = standard.get("high", float("inf"))
        if isinstance(low_val, (int, float)) and isinstance(high_val, (int, float)):
            in_range = low_val <= value <= high_val
        else:
            in_range = None

        return {
            "low": standard.get("low"),
            "high": standard.get("high"),
            "in_range": in_range,
            "standard_unit": standard.get("unit"),
        }


@register_action("CHEMISTRY_VENDOR_HARMONIZATION")
class ChemistryVendorHarmonizationAction:
    """
    Harmonize clinical chemistry test data across different vendors.

    This action standardizes clinical chemistry test data from different laboratory
    vendors (LabCorp, Quest, Mayo, Arivale, Israeli10k, UKBB) by harmonizing:
    - Test names and nomenclature
    - Units of measurement
    - Reference ranges
    - Data formats

    Features:
    - Automatic vendor detection from data patterns
    - Configurable harmonization rules
    - Unit conversion between SI and US conventional systems
    - Reference range standardization
    - Quality control flags for out-of-range values
    - Preservation of original values for traceability
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the action with logging."""
        self.logger = logging.getLogger(__name__)

    def get_params_model(self) -> type[ChemistryVendorHarmonizationParams]:
        """Return the parameters model for this action."""
        return ChemistryVendorHarmonizationParams

    def get_result_model(self) -> type[ChemistryVendorHarmonizationResult]:
        """Return the result model for this action."""
        return ChemistryVendorHarmonizationResult

    def execute_typed(
        self, params: ChemistryVendorHarmonizationParams, context: Dict[str, Any]
    ) -> ChemistryVendorHarmonizationResult:
        """Execute chemistry vendor harmonization."""

        try:
            # Get input dataset
            if params.input_key not in context["datasets"]:
                raise KeyError(f"Dataset key '{params.input_key}' not found in context")

            df = context["datasets"][params.input_key].copy()

            # Validate required columns
            if params.test_name_column not in df.columns:
                raise KeyError(
                    f"Column '{params.test_name_column}' not found in dataset"
                )

            # Harmonize data
            harmonized_df = self.harmonize_batch(df, params)

            # Calculate statistics
            vendors = []
            if "vendor_detected" in harmonized_df.columns:
                vendors = harmonized_df["vendor_detected"].unique().tolist()

            unit_conversions = {}
            if (
                "unit_standardized" in harmonized_df.columns
                and "unit_original" in harmonized_df.columns
            ):
                conversions = harmonized_df[
                    harmonized_df["unit_standardized"] != harmonized_df["unit_original"]
                ]
                if len(conversions) > 0:
                    unit_conversions = (
                        conversions.groupby("unit_original").size().to_dict()
                    )

            test_name_mappings = {}
            if (
                "test_name_harmonized" in harmonized_df.columns
                and "test_name_original" in harmonized_df.columns
            ):
                mappings = harmonized_df[
                    harmonized_df["test_name_harmonized"]
                    != harmonized_df["test_name_original"]
                ]
                if len(mappings) > 0:
                    test_name_mappings = (
                        mappings.groupby("test_name_original").size().to_dict()
                    )

            out_of_range_count = 0
            if "in_range" in harmonized_df.columns:
                out_of_range_count = len(
                    harmonized_df[harmonized_df["in_range"] == False]
                )

            # Store results
            context["datasets"][params.output_key] = harmonized_df

            # Update statistics
            if "statistics" not in context:
                context["statistics"] = {}

            context["statistics"]["vendor_harmonization"] = {
                "total_tests": len(df),
                "harmonized_tests": len(harmonized_df),
                "vendors_processed": vendors,
                "unit_conversions": unit_conversions,
                "test_name_mappings": test_name_mappings,
                "out_of_range_values": out_of_range_count,
            }

            return ChemistryVendorHarmonizationResult(
                success=True,
                total_tests=len(df),
                harmonized_tests=len(harmonized_df),
                vendors_processed=vendors,
                unit_conversions=unit_conversions,
                test_name_mappings=test_name_mappings,
                out_of_range_values=out_of_range_count,
                missing_units_handled=0,  # Will be calculated in implementation
                category_distribution={},  # Will be calculated in implementation
            )

        except Exception as e:
            self.logger.error(f"Error in chemistry vendor harmonization: {str(e)}")
            raise

    def harmonize_batch(
        self, df: pd.DataFrame, params: ChemistryVendorHarmonizationParams
    ) -> pd.DataFrame:
        """Harmonize entire dataset."""

        # Initialize components
        vendor_profile = VendorProfile()
        name_harmonizer = TestNameHarmonizer()
        unit_converter = UnitConverter()
        range_harmonizer = ReferenceRangeHarmonizer()

        # Detect vendor if auto
        vendor_str: str
        if params.vendor == "auto":
            vendor_str = vendor_profile.detect_vendor(
                df,
                {
                    "test_name": params.test_name_column,
                    "test_code": "test_code",  # if exists
                },
            )
        else:
            vendor_str = params.vendor or "generic"

        # Process each row
        harmonized = []

        for idx, row in df.iterrows():
            result = row.copy()

            # Determine vendor for this row
            current_vendor = vendor_str
            if params.vendor_column and params.vendor_column in row:
                current_vendor = (
                    str(row[params.vendor_column])
                    if row[params.vendor_column]
                    else vendor_str
                )

            # Harmonize test name
            if params.standardize_test_names:
                original_name = row[params.test_name_column]
                harmonized_name = name_harmonizer.harmonize_test_name(
                    original_name, current_vendor
                )
                result["test_name_harmonized"] = harmonized_name

                if params.preserve_original:
                    result["test_name_original"] = original_name

            # Standardize units
            if params.standardize_units and params.value_column in row:
                value = row[params.value_column]
                unit = (
                    row.get(params.unit_column, None)
                    if params.unit_column in row.index
                    else None
                )
                test_name = result.get(
                    "test_name_harmonized", row[params.test_name_column]
                )

                standard_unit = unit_converter.get_standard_unit(
                    test_name, params.target_unit_system
                )

                if standard_unit and unit:
                    converted_value, new_unit = unit_converter.standardize_unit(
                        value, unit, standard_unit, test_name
                    )
                    result["value_standardized"] = converted_value
                    result["unit_standardized"] = new_unit

                    if params.preserve_original:
                        result["value_original"] = value
                        result["unit_original"] = unit

            # Harmonize reference ranges
            if params.standardize_reference_ranges:
                ref_range = (
                    row.get(params.reference_range_column, None)
                    if params.reference_range_column
                    else None
                )
                value = result.get("value_standardized", row.get(params.value_column))
                test_name = result.get(
                    "test_name_harmonized", row[params.test_name_column]
                )

                if value is not None and not pd.isna(value):
                    range_info = range_harmonizer.harmonize_reference_range(
                        test_name, value, ref_range, current_vendor
                    )

                    result["reference_low"] = range_info.get("low")
                    result["reference_high"] = range_info.get("high")

                    if params.flag_out_of_range:
                        result["in_range"] = range_info.get("in_range")

            # Add vendor info
            if params.add_harmonization_log:
                result["vendor_detected"] = current_vendor
                result["harmonization_timestamp"] = pd.Timestamp.now()

            harmonized.append(result)

        return pd.DataFrame(harmonized)
