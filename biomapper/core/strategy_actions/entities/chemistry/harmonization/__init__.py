"""
Chemistry harmonization actions for biomapper.

This module contains actions for harmonizing clinical test data
across different laboratory vendors and platforms.

Available Actions (when implemented):
    CHEMISTRY_VENDOR_HARMONIZATION: Cross-vendor test standardization

Vendor Harmonization Focus:
    - LabCorp vs Quest Diagnostics code mapping
    - Local lab-specific code standardization
    - Reference range harmonization
    - Unit conversion and standardization

Common Vendor Differences:
    - Different test codes for same analyte
    - Varying reference ranges
    - Different units of measurement
    - Method-specific variations

Development:
    Use TDD methodology with biomapper-action-developer agent.
    Implement configurable vendor mapping tables.
"""

# Import all harmonization actions to trigger registration
from .vendor_harmonization import *

__all__: list[str] = []  # Actions register themselves
