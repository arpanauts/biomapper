"""Base classes for ArangoDB knowledge graph integration."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Set, Tuple

from pydantic import BaseModel


class ArangoNode(BaseModel):
    """Base model for an ArangoDB node."""
    id: str
    type: str
    name: str
    properties: Dict[str, Any]


class ArangoEdge(BaseModel):
    """Base model for an ArangoDB edge."""
    source_id: str
    target_id: str
    type: str
    properties: Dict[str, Any]


class ArangoQuery(BaseModel):
    """Model for ArangoDB graph queries."""
    start_node_type: str
    end_node_type: str
    relationship_types: Optional[List[str]] = None
    max_path_length: int = 3
    properties: Optional[Dict[str, Any]] = None


class ArangoResult(BaseModel):
    """Model for ArangoDB query results."""
    nodes: List[ArangoNode]
    edges: List[ArangoEdge]
    paths: List[List[str]]  # List of node IDs representing paths


class BaseArango(ABC):
    """Base class for ArangoDB knowledge graph operations."""

    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to ArangoDB database."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close connection to ArangoDB database."""
        pass

    @abstractmethod
    async def get_node(self, node_id: str) -> Optional[ArangoNode]:
        """Get a node by its ID.
        
        Args:
            node_id: ID of the node to retrieve

        Returns:
            Node if found, None otherwise
        """
        pass

    @abstractmethod
    async def get_node_by_property(
        self,
        node_type: str,
        property_name: str,
        property_value: Any
    ) -> Optional[ArangoNode]:
        """Get a node by a property value.
        
        Args:
            node_type: Type of node to search for
            property_name: Name of the property to match
            property_value: Value of the property to match

        Returns:
            Node if found, None otherwise
        """
        pass

    @abstractmethod
    async def get_neighbors(
        self,
        node_id: str,
        edge_types: Optional[List[str]] = None,
        node_types: Optional[List[str]] = None,
    ) -> List[Tuple[ArangoEdge, ArangoNode]]:
        """Get neighbors of a node.
        
        Args:
            node_id: ID of the node to get neighbors for
            edge_types: Optional list of edge types to filter by
            node_types: Optional list of node types to filter by

        Returns:
            List of (edge, node) tuples representing neighbors
        """
        pass

    @abstractmethod
    async def find_paths(
        self,
        query: ArangoQuery,
    ) -> ArangoResult:
        """Find paths between node types matching the query.
        
        Args:
            query: Query parameters including start/end node types and constraints

        Returns:
            Query results including nodes, edges, and paths found
        """
        pass

    @abstractmethod
    async def get_node_types(self) -> Set[str]:
        """Get all available node types in the graph.

        Returns:
            Set of node type strings
        """
        pass

    @abstractmethod
    async def get_edge_types(self) -> Set[str]:
        """Get all available edge types in the graph.

        Returns:
            Set of edge type strings
        """
        pass

    async def __aenter__(self) -> 'BaseArango':
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.close()
