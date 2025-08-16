"""
Protein matching actions for biomapper.

This module contains actions for cross-dataset protein identifier matching
and bridge resolution strategies.

Available Actions:
    PROTEIN_MULTI_BRIDGE: Multi-strategy protein matching with configurable attempts
    PROTEIN_HISTORICAL_RESOLUTION: Resolve deprecated/updated UniProt IDs to current ones
    PROTEIN_GENE_SYMBOL_BRIDGE: Bridge proteins via gene symbol matching (exact + fuzzy)
    PROTEIN_ENSEMBL_BRIDGE: Bridge proteins via Ensembl protein ID matching

Matching Strategies:
    - UniProt exact matching (90% success rate)
    - Gene symbol fuzzy matching (adds 8% more matches)
    - Ensembl ID exact matching (adds 2% more matches)
    - Historical UniProt ID resolution (handles deprecated/obsolete IDs)

Historical Resolution Features:
    - Uses UniProt REST API for historical mapping
    - Supports batch processing for performance
    - Tracks resolution confidence scores and types
    - Can filter by previous unmatched results
    - Integrates with reference dataset matching

Development:
    Use TDD methodology with biomapper-action-developer agent.
    Actions should leverage shared algorithms from algorithms/ directory.
"""

# Import all matching actions to trigger registration
from .multi_bridge import *  # Multi-strategy matching
from .historical_resolution import *  # Historical UniProt ID resolution
from .gene_symbol_bridge import *  # Gene symbol bridge matching
from .ensembl_bridge import *  # Ensembl bridge matching

__all__ = []  # Actions register themselves
