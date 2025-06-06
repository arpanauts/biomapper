"""API clients for various compound and metabolite databases."""

from .metaboanalyst_client import (
    MetaboAnalystClient,
    MetaboAnalystConfig,
    MetaboAnalystResult,
)

from .translator_name_resolver_client import TranslatorNameResolverClient
from .umls_client import UMLSClient
from .generic_file_client import GenericFileLookupClient

# Conditional import for optional dependencies
try:
    from .pubchem_rag_client import PubChemRAGMappingClient
except ImportError:
    # PubChemRAGMappingClient requires qdrant_client which may not be installed
    PubChemRAGMappingClient = None
