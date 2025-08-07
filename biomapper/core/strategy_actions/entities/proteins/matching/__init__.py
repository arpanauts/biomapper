"""
Protein matching actions for biomapper.

This module contains actions for cross-dataset protein identifier matching
and bridge resolution strategies.

Available Actions (when implemented):
    PROTEIN_MULTI_BRIDGE: Multi-strategy protein matching with configurable attempts

Matching Strategies:
    - UniProt exact matching (90% success rate)
    - Gene symbol fuzzy matching (adds 8% more matches)
    - Ensembl ID exact matching (adds 2% more matches)

Development:
    Use TDD methodology with biomapper-action-developer agent.
    Actions should leverage shared algorithms from algorithms/ directory.
"""

# Import all matching actions to trigger registration
# from .multi_bridge import *  # To be implemented

__all__ = []  # Actions register themselves
