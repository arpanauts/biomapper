"""Biomapper package for biological data harmonization and ontology mapping."""

# Minimal imports for database setup
# Keep import statements commented to avoid dependency issues
# These will be imported dynamically when needed

# File I/O Utilities
try:
    from .utils.io_utils import load_tabular_file, get_max_file_size
except ImportError:
    pass

# Legacy imports
try:
    from .standardization import RaMPClient
    from .core import SetAnalyzer
except ImportError:
    pass

__version__ = "0.5.1"
__all__ = [
    # Utilities
    "load_tabular_file",
    "get_max_file_size",
    # Legacy components
    "RaMPClient",
    "SetAnalyzer",
]
