"""API clients for various compound and metabolite databases."""


# Conditional import for optional dependencies
try:
    from .pubchem_rag_client import PubChemRAGMappingClient
except ImportError:
    # PubChemRAGMappingClient requires qdrant_client which may not be installed
    PubChemRAGMappingClient = None
