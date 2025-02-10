"""
SPOKE integration module for biomapper.

This module provides integration with the SPOKE (Scalable Precision Medicine Oriented Knowledge Engine)
database, enabling mapping of various biological entities (metabolites, proteins, diseases, etc.)
to SPOKE nodes and analysis of their relationships.
"""

from .client import SPOKEDBClient, SPOKEConfig, SPOKEError
from .mapper import SPOKEMapper, SPOKENodeType, SPOKEMappingResult

__all__ = [
    'SPOKEDBClient',
    'SPOKEConfig',
    'SPOKEError',
    'SPOKEMapper',
    'SPOKENodeType',
    'SPOKEMappingResult',
]
