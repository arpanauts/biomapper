"""Biomapper package for biological data harmonization and ontology mapping."""

# Core mapping functionality
from .standardization.metabolite import MetaboliteNameMapper

# API Clients
from .mapping.clients.chebi_client import ChEBIClient
from .mapping.clients.refmet_client import RefMetClient
from .mapping.clients.metaboanalyst_client import MetaboAnalystClient

# RAG Components
from .mapping.rag.store import ChromaCompoundStore
from .mapping.rag.prompts import PromptManager

# Optimization and Monitoring
from .utils.optimization import DSPyOptimizer
from .monitoring.langfuse_tracker import LangfuseTracker

# File I/O Utilities
from .utils.io_utils import load_tabular_file, get_max_file_size

# Legacy imports
from .standardization import RaMPClient
from .core import SetAnalyzer

__version__ = "0.5.1"
__all__ = [
    # Core mapping
    "MetaboliteNameMapper",
    # API Clients
    "ChEBIClient",
    "RefMetClient",
    "MetaboAnalystClient",
    # Utilities
    "load_tabular_file",
    "get_max_file_size",
    # RAG Components
    "ChromaCompoundStore",
    "PromptManager",
    # Optimization and Monitoring
    "DSPyOptimizer",
    "LangfuseTracker",
    # Legacy components
    "RaMPClient",
    "SetAnalyzer",
]
