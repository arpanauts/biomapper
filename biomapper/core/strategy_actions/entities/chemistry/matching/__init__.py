"""
Chemistry matching actions for biomapper.

This module contains actions for clinical test name fuzzy matching
and cross-platform test harmonization.

Available Actions:
    CHEMISTRY_FUZZY_TEST_MATCH: Fuzzy matching of clinical test names

Matching Strategies:
    - String similarity algorithms (Levenshtein, Jaro-Winkler)
    - Semantic matching for test name variations
    - Abbreviation expansion and normalization
    - Clinical domain-specific matching rules

Common Matching Challenges:
    - "HbA1c" vs "Hemoglobin A1c" vs "Glycated Hemoglobin"
    - "Total Cholesterol" vs "Cholesterol, Total" vs "CHOL"
    - Unit variations and method specifications

Development:
    Use TDD methodology with biomapper-action-developer agent.
    Leverage shared algorithms from algorithms/fuzzy_matching/.
"""

# Import all matching actions to trigger registration
from .fuzzy_test_match import *

__all__ = []  # Actions register themselves
