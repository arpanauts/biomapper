"""Biomapper package for biological data harmonization and ontology mapping."""

# Core mapping functionality
from .standardization.metabolite import MetaboliteNameMapper

# API Clients
from .mapping.clients.chebi_client import ChEBIClient
from .mapping.clients.refmet_client import RefMetClient

# RAG Components
from .mapping.rag.store import ChromaCompoundStore
from .mapping.rag.prompts import PromptManager

# Optimization and Monitoring
from .utils.optimization import DSPyOptimizer
from .monitoring.langfuse_tracker import LangfuseTracker

# Legacy imports
from .standardization import RaMPClient
from .core import SetAnalyzer

__version__ = "0.4.0"
__all__ = [
    # Core mapping
    "MetaboliteNameMapper",
    # API Clients
    "ChEBIClient",
    "RefMetClient",
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
