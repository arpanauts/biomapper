"""
Protein-specific actions for biomapper.

This module provides comprehensive protein identifier processing,
normalization, and matching capabilities for biological data harmonization.

Submodules:
    annotation: UniProt extraction, accession normalization
    matching: Multi-bridge resolution strategies
    structure: Protein structure analysis (future)

Common Data Patterns:
    UniProt: P12345, O00533 (standard 6-character accessions)
    Ensembl: ENSP00000123456 (protein IDs)
    Gene symbols: CD4, TP53 (HGNC official symbols)

Example Workflow:
    1. Load protein datasets with LOAD_DATASET_IDENTIFIERS
    2. Extract UniProt IDs with PROTEIN_EXTRACT_UNIPROT_FROM_XREFS
    3. Normalize formats with PROTEIN_NORMALIZE_ACCESSIONS
    4. Match across datasets with PROTEIN_MULTI_BRIDGE

Usage:
    Actions are auto-registered when this module is imported.
    Use the biomapper-action-developer agent for development guidance.
"""

# Import all protein action categories to trigger registration
# from . import structure  # Future expansion

__all__ = []  # Actions register themselves
