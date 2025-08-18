"""
Metabolite enrichment actions for biomapper.

This module contains actions for enriching metabolite data with external
database information and annotations.

Available Actions (when implemented):
    [Existing actions to be moved here]:
    - METABOLITE_API_ENRICHMENT: External metabolite database integration

Enrichment Sources:
    - PubChem API for chemical properties
    - ChEBI API for ontology annotations
    - HMDB API for biological context
    - KEGG API for pathway information

Development:
    Use TDD methodology with biomapper-action-developer agent.
    Implement robust error handling for external API failures.
"""

# Import all enrichment actions to trigger registration
# Existing actions will be moved here during migration:
# from .api_enrichment import *  # To be moved from root level

__all__ = []  # Actions register themselves
