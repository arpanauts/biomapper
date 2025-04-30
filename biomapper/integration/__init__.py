"""Integration module for Biomapper connections between different systems.

This module provides components for integrating the SQLite mapping cache with
other systems, including the SPOKE knowledge graph and external ontology sources.
"""

from biomapper.integration.spoke_cache_sync import (
    SpokeCacheSync,
    SyncConfig,
    SyncDirection,
    sync_entities_from_list,
)

__all__ = ["SpokeCacheSync", "SyncConfig", "SyncDirection", "sync_entities_from_list"]
