"""
Metadata System for Biomapper Resources.

This package implements a comprehensive metadata and orchestration system
for mapping operations across multiple resources in Biomapper.
"""

__version__ = "0.1.0"

from biomapper.mapping.metadata.interfaces import (
    StepExecutor,
    ResourceAdapter,
    EndpointAdapter,
)

from biomapper.mapping.metadata.pathfinder import RelationshipPathFinder
from biomapper.mapping.metadata.mapper import RelationshipMappingExecutor

__all__ = [
    "StepExecutor",
    "ResourceAdapter",
    "EndpointAdapter",
    "RelationshipPathFinder",
    "RelationshipMappingExecutor",
]