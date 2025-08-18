"""
Biomapper External Service Integrations.

This module provides clients for external biological data services.
Currently only includes UniProt historical resolver client.
"""

# Import clients from clients subdirectory
from .clients.uniprot_historical_resolver_client import UniProtHistoricalResolverClient
from .clients.base_client import BaseMappingClient as BaseAPIClient

__all__ = [
    'UniProtHistoricalResolverClient',
    'BaseAPIClient',
]