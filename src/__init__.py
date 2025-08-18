"""
Biomapper: Unified Toolkit for Biological Data Harmonization.

A professional Python package for mapping and harmonizing biological identifiers
across different databases and platforms, with focus on proteins and metabolites.

Core Components:
- CLI: Command-line interface for terminal users
- API: REST API server for HTTP access  
- Client: Python library for programmatic access
- Strategies: YAML workflow configurations
- Actions: Modular data processing operations

Examples:
    CLI Usage:
        $ biomapper health
        $ biomapper run strategy protein_mapping.yaml
    
    Python Usage:
        from client import BiomapperClient
        client = BiomapperClient()
        result = client.run_strategy("protein_mapping.yaml")
"""

__version__ = "0.5.2"
__author__ = "Trent Leslie"
__email__ = "trent.leslie@phenomehealth.org"

# Core public API
from .client import BiomapperClient
from .core import MinimalStrategyService
from .configs.strategies import get_strategy_path, list_available_strategies

__all__ = [
    'BiomapperClient',
    'MinimalStrategyService', 
    'get_strategy_path',
    'list_available_strategies',
    '__version__'
]