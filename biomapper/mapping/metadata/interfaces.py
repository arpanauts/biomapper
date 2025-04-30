"""
Interface definitions for the Resource Metadata System.

This module defines the abstract base classes and protocols
that resources must implement to integrate with the system.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Protocol, runtime_checkable


@runtime_checkable
class ResourceAdapter(Protocol):
    """
    Protocol for resource adapters.

    Resource adapters provide a consistent interface for interacting with
    different types of resources (databases, APIs, knowledge graphs, etc.).
    """

    async def connect(self) -> bool:
        """
        Establish a connection to the resource.

        Returns:
            bool: True if connection was successful, False otherwise
        """
        ...

    async def map_entity(
        self, source_id: str, source_type: str, target_type: str, **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Map an entity from source_type to target_type.

        Args:
            source_id: Source identifier
            source_type: Source ontology type
            target_type: Target ontology type
            **kwargs: Additional arguments specific to the resource

        Returns:
            List of mappings, each containing at least 'target_id' and 'confidence'
        """
        ...

    def get_capabilities(self) -> Dict[str, Any]:
        """
        Get the capabilities of this resource.

        Returns:
            Dictionary describing the resource's capabilities
        """
        ...

    async def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get performance metrics for this resource.

        Returns:
            Dictionary of performance metrics
        """
        ...


class BaseResourceAdapter(ABC):
    """
    Abstract base class for resource adapters.

    This class provides a base implementation of the ResourceAdapter
    protocol with common functionality.
    """

    def __init__(self, config: Dict[str, Any], name: str):
        """
        Initialize the resource adapter.

        Args:
            config: Configuration for the resource
            name: Name of the resource
        """
        self.config = config
        self.name = name
        self.is_connected = False

    @abstractmethod
    async def connect(self) -> bool:
        """
        Establish a connection to the resource.

        Returns:
            bool: True if connection was successful, False otherwise
        """
        pass

    @abstractmethod
    async def map_entity(
        self, source_id: str, source_type: str, target_type: str, **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Map an entity from source_type to target_type.

        Args:
            source_id: Source identifier
            source_type: Source ontology type
            target_type: Target ontology type
            **kwargs: Additional arguments specific to the resource

        Returns:
            List of mappings, each containing at least 'target_id' and 'confidence'
        """
        pass

    def get_capabilities(self) -> Dict[str, Any]:
        """
        Get the capabilities of this resource.

        Returns:
            Dictionary describing the resource's capabilities
        """
        return {
            "name": self.name,
            "supports_batch": False,
            "supports_async": True,
            "max_batch_size": 1,
        }

    async def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get performance metrics for this resource.

        Returns:
            Dictionary of performance metrics
        """
        return {"avg_response_time_ms": None, "success_rate": None, "sample_count": 0}


@runtime_checkable
class KnowledgeGraphClient(Protocol):
    """
    Protocol for knowledge graph clients.

    Knowledge graph clients provide access to graph databases like SPOKE,
    Neo4j, ArangoDB, etc.
    """

    async def connect(self) -> bool:
        """
        Establish a connection to the knowledge graph.

        Returns:
            bool: True if connection was successful, False otherwise
        """
        ...

    async def get_entity(
        self, identifier: str, entity_type: str
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve an entity by identifier and type.

        Args:
            identifier: Entity identifier
            entity_type: Entity type

        Returns:
            Entity data, or None if not found
        """
        ...

    async def map_identifier(
        self, source_id: str, source_type: str, target_type: str
    ) -> List[Dict[str, Any]]:
        """
        Map an identifier from source_type to target_type.

        Args:
            source_id: Source identifier
            source_type: Source ontology type
            target_type: Target ontology type

        Returns:
            List of target identifiers with confidence scores
        """
        ...

    def get_supported_entity_types(self) -> List[str]:
        """
        Get the entity types supported by this knowledge graph.

        Returns:
            List of supported entity types
        """
        ...


@runtime_checkable
class StepExecutor(Protocol):
    """Interface for executing mapping steps."""

    async def execute_step(
        self,
        source_id: str,
        source_type: str,
        target_type: str,
        step_config: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Execute a mapping step.

        Args:
            source_id: The source ID to map.
            source_type: The source ontology type.
            target_type: The target ontology type.
            step_config: Step configuration dictionary.

        Returns:
            List of mapping results.
        """
        ...


class EndpointAdapter(ABC):
    """Base class for endpoint adapters that extract IDs from endpoints."""

    @abstractmethod
    async def extract_ids(
        self, value: str, endpoint_id: int, ontology_type: str, **kwargs
    ) -> List[Dict[str, Any]]:
        """Extract IDs of a specific ontology type from a value.

        Args:
            value: The value to extract IDs from.
            endpoint_id: The endpoint ID.
            ontology_type: The ontology type to extract.
            **kwargs: Additional keyword arguments.

        Returns:
            List of extraction results.
        """
        pass

    @abstractmethod
    def get_supported_extractions(self, endpoint_id: int) -> List[str]:
        """Get supported extraction ontology types for an endpoint.

        Args:
            endpoint_id: The endpoint ID.

        Returns:
            List of supported ontology type strings.
        """
        pass
