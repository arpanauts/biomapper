"""
Chemistry-specific actions for biomapper.

This module provides clinical chemistry test identifier processing,
matching, and vendor harmonization capabilities.

Submodules:
    identification: LOINC code extraction and processing
    matching: Fuzzy test name matching strategies
    harmonization: Cross-vendor test standardization

Common Data Patterns:
    LOINC: 12345-6 (numeric-check digit format)
    Test names: Highly variable (e.g., "HbA1c", "Hemoglobin A1c", "Glycated Hemoglobin")
    Vendor codes: LabCorp, Quest, local lab-specific codes

Example Workflow:
    1. Load chemistry datasets with LOAD_DATASET_IDENTIFIERS
    2. Extract LOINC codes with CHEMISTRY_EXTRACT_LOINC
    3. Match test names with CHEMISTRY_FUZZY_TEST_MATCH
    4. Harmonize vendors with CHEMISTRY_VENDOR_HARMONIZATION

Usage:
    Actions are auto-registered when this module is imported.
    Use the biomapper-action-developer agent for development guidance.
"""

# Import only matching actions - identification and harmonization removed

__all__ = []  # Actions register themselves
