"""
Chemistry identification actions for biomapper.

This module contains actions for clinical chemistry test code extraction
and identifier processing.

Available Actions (when implemented):
    CHEMISTRY_EXTRACT_LOINC: Extract LOINC codes from test descriptions

LOINC Processing Focus:
    - LOINC code extraction from clinical test descriptions
    - Format validation (numeric-check digit pattern)
    - Vendor-specific code mapping to standard LOINC

Development:
    Use TDD methodology with biomapper-action-developer agent.
    Handle the variability in clinical lab test naming conventions.
"""

# Import all identification actions to trigger registration

__all__ = []  # Actions register themselves
