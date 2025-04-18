"""
Endpoint-to-Endpoint Relationship Mapping Module.

This module implements the relationship mapping layer between endpoints,
leveraging ontology-level mapping paths for specific endpoint relationships.
"""

from biomapper.mapping.relationships.path_finder import RelationshipPathFinder
from biomapper.mapping.relationships.executor import RelationshipMappingExecutor

__all__ = ["RelationshipPathFinder", "RelationshipMappingExecutor"]
