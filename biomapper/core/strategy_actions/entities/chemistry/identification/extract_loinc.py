"""CHEMISTRY_EXTRACT_LOINC action for extracting and validating LOINC codes from chemistry data.

This action handles various LOINC formats, vendor-specific codes, and missing/malformed LOINC identifiers.
LOINC is the universal standard for identifying medical laboratory observations.
"""

import re
import json
import pandas as pd
from typing import Dict, Any, Optional, List, Literal
from pydantic import BaseModel, Field

from biomapper.core.strategy_actions.typed_base import TypedStrategyAction
from biomapper.core.strategy_actions.registry import register_action


# LOINC format validation patterns
LOINC_PATTERNS = {
    "standard": r"^\d{1,5}-\d{1}$",
    "with_prefix": r"^(?:LOINC:|loinc:|LN:)?(\d{1,5}-\d{1})$",
    "embedded": r"\b(\d{1,5}-\d{1})\b",
    "old_format": r"^(\d{6,7})$",  # 123456 or 1234567
}

# Common clinical chemistry tests to LOINC mapping
COMMON_TEST_LOINC_MAPPING = {
    # Glucose tests
    "glucose": "2345-7",
    "glucose, serum": "2345-7",
    "glucose, plasma": "2345-7",
    "glucose, fasting": "1558-6",
    "glucose, random": "2345-7",
    "blood sugar": "2345-7",
    # Cholesterol tests
    "cholesterol": "2093-3",
    "cholesterol, total": "2093-3",
    "ldl cholesterol": "13457-7",
    "hdl cholesterol": "2085-9",
    "ldl-c": "13457-7",
    "hdl-c": "2085-9",
    "ldl cholesterol, calculated": "13457-7",
    # Triglycerides
    "triglycerides": "2571-8",
    "triglyceride": "2571-8",
    "trig": "2571-8",
    # Liver function
    "alt": "1742-6",
    "ast": "1920-8",
    "alkaline phosphatase": "6768-6",
    "alk phos": "6768-6",
    "bilirubin, total": "1975-2",
    "bilirubin, direct": "1968-7",
    # Kidney function
    "creatinine": "2160-0",
    "creatinine, serum": "2160-0",
    "bun": "3094-0",
    "urea nitrogen": "3094-0",
    "egfr": "33914-3",
    # Electrolytes
    "sodium": "2951-2",
    "potassium": "2823-3",
    "chloride": "2075-0",
    "co2": "2028-9",
    "bicarbonate": "1963-8",
    # Complete Blood Count
    "hemoglobin": "718-7",
    "hematocrit": "4544-3",
    "wbc": "6690-2",
    "white blood cell count": "6690-2",
    "platelet count": "777-3",
    # Proteins
    "albumin": "1751-7",
    "total protein": "2885-2",
    "globulin": "10834-0",
    # Thyroid
    "tsh": "3016-3",
    "t4": "3026-2",
    "t3": "3051-0",
    "free t4": "3024-7",
    "free t3": "3052-8",
}

# LOINC classes for clinical chemistry
CLINICAL_CHEMISTRY_CLASSES = [
    "CHEM",  # Chemistry
    "HEM/BC",  # Hematology/Blood Count
    "COAG",  # Coagulation
    "UA",  # Urinalysis
    "DRUG/TOX",  # Drug/Toxicology (some)
    "SERO",  # Serology (some)
]


def validate_loinc_format(loinc_code: str) -> bool:
    """Validate LOINC code format.

    Args:
        loinc_code: The LOINC code to validate

    Returns:
        True if valid LOINC format, False otherwise
    """
    if not loinc_code:
        return False

    # Clean the code
    clean_code = clean_loinc_code(str(loinc_code))

    if not clean_code:
        return False

    # Check standard format
    return bool(re.match(r"^\d{1,5}-\d{1}$", clean_code))


def validate_loinc_checksum(loinc_code: str) -> bool:
    """Validate LOINC check digit using mod 10 algorithm.

    Args:
        loinc_code: The LOINC code to validate

    Returns:
        True if checksum is valid, False otherwise
    """
    if not loinc_code or "-" not in loinc_code:
        return False

    try:
        main_part, check_digit = loinc_code.split("-")

        # Calculate check digit using LOINC algorithm
        calculated_check = calculate_loinc_check_digit(main_part)

        return calculated_check == check_digit
    except (ValueError, TypeError):
        return False


def calculate_loinc_check_digit(main_part: str) -> str:
    """Calculate LOINC check digit using mod 10 algorithm.

    LOINC check digits are calculated using a specific mod-10 algorithm.

    Args:
        main_part: The main numeric part of the LOINC code

    Returns:
        The calculated check digit as string
    """
    if not main_part or not main_part.isdigit():
        return "0"

    # LOINC check digit algorithm
    # Based on the standard LOINC check digit calculation
    total = 0
    for i, char in enumerate(main_part):
        digit = int(char)
        # Weight alternates between 2 and 1, starting with 1 for rightmost
        weight = 2 if (len(main_part) - i - 1) % 2 == 1 else 1
        product = digit * weight

        # Add digits of product
        if product > 9:
            total += (product // 10) + (product % 10)
        else:
            total += product

    # Check digit is what makes total mod 10 equal 0
    check_digit = (10 - (total % 10)) % 10
    return str(check_digit)


def clean_loinc_code(loinc_code: str) -> str:
    """Clean LOINC code by removing prefixes and whitespace.

    Args:
        loinc_code: The raw LOINC code

    Returns:
        Cleaned LOINC code
    """
    if not loinc_code:
        return ""

    # Convert to string and strip whitespace
    clean_code = str(loinc_code).strip().upper()

    # Remove common prefixes
    for prefix in ["LOINC:", "LN:", "LOINC_"]:
        if clean_code.startswith(prefix):
            clean_code = clean_code[len(prefix) :]
            break

    # Strip again after prefix removal
    clean_code = clean_code.strip()

    return clean_code


def map_test_name_to_loinc(test_name: str) -> Optional[str]:
    """Map common test names to LOINC codes.

    Args:
        test_name: The test name to map

    Returns:
        LOINC code if found, None otherwise
    """
    if not test_name:
        return None

    # Normalize test name
    normalized = str(test_name).lower().strip()

    if not normalized:
        return None

    # Remove common suffixes
    normalized = re.sub(r",?\s*(serum|plasma|blood|urine)$", "", normalized)
    normalized = normalized.strip()

    # Direct lookup
    if normalized in COMMON_TEST_LOINC_MAPPING:
        return COMMON_TEST_LOINC_MAPPING[normalized]

    # Fuzzy matching for variations
    for test_pattern, loinc in COMMON_TEST_LOINC_MAPPING.items():
        if test_pattern in normalized or normalized in test_pattern:
            return loinc

    return None


def is_clinical_chemistry_loinc(
    loinc_code: str, loinc_metadata: Dict[str, Any]
) -> bool:
    """Check if LOINC code is for clinical chemistry.

    Args:
        loinc_code: The LOINC code
        loinc_metadata: Metadata about the LOINC code

    Returns:
        True if clinical chemistry, False otherwise
    """
    # Get LOINC class from metadata
    loinc_class = loinc_metadata.get("class", "")

    # Check if in clinical chemistry classes
    if loinc_class in CLINICAL_CHEMISTRY_CLASSES:
        return True

    # Check component for chemistry markers
    component = loinc_metadata.get("component", "").lower()
    chemistry_markers = [
        "glucose",
        "cholesterol",
        "triglyceride",
        "creatinine",
        "urea",
        "nitrogen",
        "sodium",
        "potassium",
        "chloride",
        "alt",
        "ast",
        "alkaline phosphatase",
        "hemoglobin",
        "hematocrit",
    ]

    return any(marker in component for marker in chemistry_markers)


def load_vendor_mapping(file_path: str) -> Dict[str, str]:
    """Load vendor-specific LOINC mapping from file.

    Args:
        file_path: Path to the mapping file

    Returns:
        Dictionary mapping vendor codes to LOINC codes
    """
    try:
        with open(file_path, "r") as f:
            result = json.load(f)
            return result if isinstance(result, dict) else {}
    except (FileNotFoundError, json.JSONDecodeError, PermissionError):
        return {}


class VendorLoincExtractor:
    """Handle vendor-specific LOINC extraction patterns."""

    VENDOR_PATTERNS = {
        "arivale": {
            "format": "test_name (LOINC)",
            "example": "Glucose, Serum (2345-7)",
            "pattern": r"\((\d{1,5}-\d{1})\)$",
        },
        "labcorp": {
            "format": "LOINC in separate column",
            "test_code_prefix": "LC",
            "loinc_column": "loinc_code",
        },
        "quest": {
            "format": "Test code maps to LOINC",
            "test_code_prefix": "QD",
            "mapping_required": True,
        },
        "mayo": {
            "format": "Mayo test ID to LOINC",
            "test_code_pattern": r"^[A-Z]{2,4}\d{1,4}$",
        },
        "israeli10k": {
            "format": "Hebrew names need translation",
            "requires_translation": True,
        },
        "ukbb": {"format": "Field ID to LOINC mapping", "field_pattern": r"^\d{5}$"},
    }

    def __init__(self) -> None:
        """Initialize the vendor extractor."""
        self._vendor_mappings: Dict[str, Dict[str, str]] = {}

    def _load_vendor_mapping(self, vendor: str) -> Dict[str, str]:
        """Load vendor mapping if not already cached."""
        if vendor not in self._vendor_mappings:
            self._vendor_mappings[vendor] = {}
        return self._vendor_mappings[vendor]

    def extract_by_vendor(
        self, row: pd.Series, vendor: str, columns: Dict[str, str]
    ) -> Optional[str]:
        """Extract LOINC based on vendor-specific patterns.

        Args:
            row: Data row
            vendor: Vendor identifier
            columns: Column mapping

        Returns:
            Extracted LOINC code or None
        """
        if vendor == "arivale":
            return self._extract_arivale(row, columns)
        elif vendor == "labcorp":
            return self._extract_labcorp(row, columns)
        elif vendor == "quest":
            return self._extract_quest(row, columns)
        elif vendor == "mayo":
            return self._extract_mayo(row, columns)
        elif vendor == "ukbb":
            return self._extract_ukbb(row, columns)
        elif vendor == "israeli10k":
            return self._extract_israeli10k(row, columns)

        return None

    def _extract_arivale(
        self, row: pd.Series, columns: Dict[str, str]
    ) -> Optional[str]:
        """Extract LOINC from Arivale format."""
        test_name_col = columns.get("test_name_column", "test_name")
        test_name = row.get(test_name_col)

        if not test_name:
            return None

        # Look for LOINC in parentheses
        match = re.search(r"\((\d{1,5}-\d{1})\)$", str(test_name))
        if match:
            return match.group(1)

        return None

    def _extract_labcorp(
        self, row: pd.Series, columns: Dict[str, str]
    ) -> Optional[str]:
        """Extract LOINC from LabCorp format."""
        loinc_col = columns.get("loinc_column", "loinc_code")
        loinc_code = row.get(loinc_col)

        if loinc_code and validate_loinc_format(str(loinc_code)):
            return clean_loinc_code(str(loinc_code))

        return None

    def _extract_quest(self, row: pd.Series, columns: Dict[str, str]) -> Optional[str]:
        """Extract LOINC from Quest format with mapping."""
        test_id_col = columns.get("test_id_column", "test_id")
        test_id = row.get(test_id_col)

        if not test_id:
            return None

        # Load Quest mapping
        mapping = self._load_vendor_mapping("quest")

        return mapping.get(str(test_id))

    def _extract_mayo(self, row: pd.Series, columns: Dict[str, str]) -> Optional[str]:
        """Extract LOINC from Mayo format."""
        test_id_col = columns.get("test_id_column", "test_id")
        test_id = row.get(test_id_col)

        if not test_id:
            return None

        # Load Mayo mapping
        mapping = self._load_vendor_mapping("mayo")

        return mapping.get(str(test_id))

    def _extract_ukbb(self, row: pd.Series, columns: Dict[str, str]) -> Optional[str]:
        """Extract LOINC from UKBB field IDs."""
        field_id_col = columns.get("test_id_column", "field_id")
        field_id = row.get(field_id_col)

        if not field_id:
            return None

        # Load UKBB mapping
        mapping = self._load_vendor_mapping("ukbb")

        return mapping.get(str(field_id))

    def _extract_israeli10k(
        self, row: pd.Series, columns: Dict[str, str]
    ) -> Optional[str]:
        """Extract LOINC from Israeli10k Hebrew names."""
        # This would require Hebrew translation - placeholder for now
        return None


class ChemistryExtractLoincParams(BaseModel):
    """Parameters for LOINC extraction from chemistry data."""

    # Input/Output
    input_key: str = Field(..., description="Dataset key from context")
    output_key: str = Field(..., description="Output dataset key")

    # Source columns
    loinc_column: Optional[str] = Field(
        None, description="Column containing LOINC codes"
    )
    test_name_column: Optional[str] = Field(None, description="Column with test names")
    test_id_column: Optional[str] = Field(
        None, description="Column with vendor test IDs"
    )

    # Vendor configuration
    vendor: Optional[
        Literal["arivale", "labcorp", "quest", "mayo", "israeli10k", "ukbb", "generic"]
    ] = Field("generic", description="Vendor-specific extraction rules")
    vendor_mapping_file: Optional[str] = Field(
        None, description="Path to vendor-specific LOINC mapping file"
    )

    # Extraction options
    validate_format: bool = Field(True, description="Validate LOINC format (12345-6)")
    validate_checksum: bool = Field(False, description="Validate LOINC check digit")
    extract_from_name: bool = Field(
        True, description="Try to extract LOINC from test names"
    )
    use_fallback_mapping: bool = Field(
        True, description="Use common test name to LOINC mapping"
    )

    # Filtering options
    filter_clinical_only: bool = Field(
        False, description="Filter to clinical chemistry LOINCs only"
    )
    filter_chemistry_related: bool = Field(
        False, description="Include chemistry-related tests"
    )
    chemistry_categories: Optional[List[str]] = Field(
        None, description="Specific chemistry categories to include"
    )

    # Output options
    add_loinc_metadata: bool = Field(
        True, description="Add LOINC description and units"
    )
    add_extraction_log: bool = Field(
        True, description="Add columns showing extraction source"
    )


class ActionResult(BaseModel):
    """Standard action result for LOINC extraction."""

    success: bool
    message: Optional[str] = None
    error: Optional[str] = None
    data: Dict[str, Any] = Field(default_factory=dict)


@register_action("CHEMISTRY_EXTRACT_LOINC")
class ChemistryExtractLoincAction(
    TypedStrategyAction[ChemistryExtractLoincParams, ActionResult]
):
    """Extract and validate LOINC codes from clinical chemistry data."""

    def get_params_model(self) -> type[ChemistryExtractLoincParams]:
        return ChemistryExtractLoincParams

    def get_result_model(self) -> type[ActionResult]:
        return ActionResult

    def extract_loinc_batch(
        self, df: pd.DataFrame, params: ChemistryExtractLoincParams
    ) -> pd.DataFrame:
        """Extract LOINC codes from entire dataset.

        Args:
            df: Input dataframe
            params: Extraction parameters

        Returns:
            Dataframe with extracted LOINC codes
        """
        if df.empty:
            return df.copy()

        # Initialize extractor
        vendor_extractor = VendorLoincExtractor()

        # Load vendor mapping if specified
        if params.vendor_mapping_file and params.vendor:
            vendor_mapping = load_vendor_mapping(params.vendor_mapping_file)
            vendor_extractor._vendor_mappings[params.vendor] = vendor_mapping

        # Process each row
        results = []
        extraction_stats = {
            "direct_column": 0,
            "vendor_specific": 0,
            "test_name_mapping": 0,
            "no_extraction": 0,
        }

        for idx, row in df.iterrows():
            loinc_code = None
            extraction_source = None

            # Try direct LOINC column first
            if params.loinc_column and params.loinc_column in df.columns:
                loinc_candidate = row[params.loinc_column]
                if pd.notna(loinc_candidate) and validate_loinc_format(
                    str(loinc_candidate)
                ):
                    loinc_code = clean_loinc_code(str(loinc_candidate))
                    extraction_source = "direct_column"
                    extraction_stats["direct_column"] += 1

            # Try vendor-specific extraction
            if not loinc_code and params.vendor != "generic":
                columns_dict: Dict[str, str] = {}
                if params.test_name_column:
                    columns_dict["test_name_column"] = params.test_name_column
                if params.test_id_column:
                    columns_dict["test_id_column"] = params.test_id_column
                if params.loinc_column:
                    columns_dict["loinc_column"] = params.loinc_column

                loinc_code = vendor_extractor.extract_by_vendor(
                    row, str(params.vendor), columns_dict
                )
                if loinc_code:
                    extraction_source = f"vendor_{params.vendor}"
                    extraction_stats["vendor_specific"] += 1

            # Try test name mapping
            if not loinc_code and params.extract_from_name and params.test_name_column:
                test_name = row[params.test_name_column]
                if pd.notna(test_name):
                    loinc_code = map_test_name_to_loinc(str(test_name))
                    if loinc_code:
                        extraction_source = "test_name_mapping"
                        extraction_stats["test_name_mapping"] += 1

            if not loinc_code:
                extraction_stats["no_extraction"] += 1

            # Add to results
            result_row = row.copy()
            result_row["extracted_loinc"] = loinc_code

            if params.add_extraction_log:
                result_row["loinc_extraction_source"] = extraction_source
                result_row["loinc_valid"] = (
                    validate_loinc_format(loinc_code) if loinc_code else False
                )
                if params.validate_checksum and loinc_code:
                    result_row["loinc_checksum_valid"] = validate_loinc_checksum(
                        loinc_code
                    )

            results.append(result_row)

        result_df = pd.DataFrame(results)

        # Store extraction statistics for later use
        self._last_extraction_stats = extraction_stats

        return result_df

    async def execute_typed(  # type: ignore[override]
        self, params: ChemistryExtractLoincParams, context: Dict[str, Any]
    ) -> ActionResult:
        """Execute LOINC extraction from chemistry data.

        Args:
            params: Extraction parameters
            context: Execution context

        Returns:
            Extraction result
        """

        # Get input dataset
        if params.input_key not in context.get("datasets", {}):
            return ActionResult(
                success=False,
                error=f"Dataset '{params.input_key}' not found"
            )

        df = context["datasets"][params.input_key].copy()

        if df.empty:
            # Handle empty dataset
            context["datasets"][params.output_key] = df
            return ActionResult(
                success=True,
                message="Empty dataset provided",
                data={
                    "total_rows": 0,
                    "rows_with_loinc": 0,
                    "valid_loinc_codes": 0,
                    "invalid_loinc_codes": 0,
                    "extracted_from_name": 0,
                    "vendor_mapped": 0,
                    "extraction_sources": {},
                }
            )

        # Extract LOINC codes
        extracted_df = self.extract_loinc_batch(df, params)

        # Apply clinical chemistry filter if requested
        if params.filter_clinical_only:
            # This would require LOINC metadata lookup
            # For now, keep all extracted codes
            pass

        # Calculate statistics
        total_rows = len(df)
        rows_with_loinc = extracted_df["extracted_loinc"].notna().sum()

        # Count valid/invalid LOINC codes
        valid_loinc = 0
        invalid_loinc = 0

        for loinc in extracted_df["extracted_loinc"].dropna():
            if validate_loinc_format(str(loinc)):
                valid_loinc += 1
            else:
                invalid_loinc += 1

        # Get extraction statistics
        extraction_stats = getattr(self, "_last_extraction_stats", {})
        extracted_from_name = extraction_stats.get("test_name_mapping", 0)
        vendor_mapped = extraction_stats.get("vendor_specific", 0)

        # Store results
        context["datasets"][params.output_key] = extracted_df

        # Update context statistics
        if "statistics" not in context:
            context["statistics"] = {}

        context["statistics"]["chemistry_extract_loinc"] = {
            "total_rows": total_rows,
            "rows_with_loinc": rows_with_loinc,
            "extraction_rate": rows_with_loinc / total_rows if total_rows > 0 else 0,
            "valid_loinc_codes": valid_loinc,
            "invalid_loinc_codes": invalid_loinc,
            "extraction_sources": extraction_stats,
        }

        return ActionResult(
            success=True,
            message=f"Extracted {rows_with_loinc} LOINC codes from {total_rows} rows",
            data={
                "total_rows": total_rows,
                "rows_with_loinc": rows_with_loinc,
                "valid_loinc_codes": valid_loinc,
                "invalid_loinc_codes": invalid_loinc,
                "extracted_from_name": extracted_from_name,
                "vendor_mapped": vendor_mapped,
                "extraction_sources": extraction_stats,
            }
        )
