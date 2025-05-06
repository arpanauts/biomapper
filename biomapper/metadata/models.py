"""Resource metadata models.

This module defines the data models used by the resource metadata system,
including resource registrations, capabilities, and performance metrics.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Any, Optional, Union, Set


class ResourceType(str, Enum):
    """Types of resources that can be registered with the metadata system."""

    KNOWLEDGE_GRAPH = "knowledge_graph"
    DATABASE = "database"
    API = "api"
    CACHE = "cache"
    FILE = "file"
    MODEL = "model"
    SERVICE = "service"


class OperationType(str, Enum):
    """Types of operations for logging."""

    LOOKUP = "lookup"
    MAP = "map"


class OperationStatus(str, Enum):
    """Status of logged operations."""

    SUCCESS = "success"
    FAILURE = "failure"


class SupportLevel(str, Enum):
    """Level of ontology support provided by a resource."""

    NONE = "none"
    PARTIAL = "partial"
    FULL = "full"


@dataclass
class ResourceCapability:
    """Capability provided by a resource.

    A capability represents a specific operation that a resource can perform,
    such as mapping between specific entity types.
    """

    name: str
    description: str
    confidence: float = 1.0  # How confident we are in this capability (0.0 to 1.0)
    parameters: Dict[str, Any] = field(default_factory=dict)

    def __hash__(self) -> int:
        """Hash based on the capability name."""
        return hash(self.name)


@dataclass
class ResourcePerformanceMetrics:
    """Performance metrics for a resource.

    These metrics are used to evaluate and compare resources for similar
    capabilities, allowing the metadata system to route requests optimally.
    """

    # Success rate for operations (0.0 to 1.0)
    success_rate: float = 1.0

    # Average latency in milliseconds
    avg_latency_ms: float = 0.0

    # 95th percentile latency in milliseconds
    p95_latency_ms: float = 0.0

    # Average cost per operation (if applicable)
    avg_cost: float = 0.0

    # Total number of operations performed
    total_operations: int = 0

    # Failed operations count
    failed_operations: int = 0

    # Last updated timestamp (Unix timestamp)
    last_updated: float = 0.0

    # Metrics for specific capabilities
    capability_metrics: Dict[str, Dict[str, Any]] = field(default_factory=dict)


@dataclass
class ResourceRegistration:
    """Registration of a resource with the metadata system.

    A resource registration contains all the information needed to use a resource,
    including its configuration, capabilities, and performance metrics.
    """

    name: str
    type: Union[ResourceType, str]
    description: str

    # Resource configuration (connection details, etc.)
    config: Dict[str, Any] = field(default_factory=dict)

    # Capabilities provided by this resource
    capabilities: List[ResourceCapability] = field(default_factory=list)

    # Performance metrics
    metrics: ResourcePerformanceMetrics = field(
        default_factory=ResourcePerformanceMetrics
    )

    # Schema mapping for knowledge graphs
    schema_mapping: Dict[str, Any] = field(default_factory=dict)

    # Whether this resource is required for the system to function
    required: bool = False

    # Whether this resource is currently available
    available: bool = True

    # Fallback resources to use if this one is unavailable
    fallbacks: List[str] = field(default_factory=list)

    # Tags for categorizing and filtering resources
    tags: Set[str] = field(default_factory=set)

    def __hash__(self) -> int:
        """Hash based on the resource name."""
        return hash(self.name)

    def has_capability(self, capability_name: str) -> bool:
        """Check if this resource has a specific capability.

        Args:
            capability_name: Name of the capability to check

        Returns:
            Whether the resource has the capability
        """
        return any(c.name == capability_name for c in self.capabilities)

    def get_capability(self, capability_name: str) -> Optional[ResourceCapability]:
        """Get a specific capability from this resource.

        Args:
            capability_name: Name of the capability to get

        Returns:
            The capability if found, None otherwise
        """
        for capability in self.capabilities:
            if capability.name == capability_name:
                return capability
        return None


# --- Placeholder definitions for missing SQLAlchemy models ---
# These were likely defined in the removed biomapper.db.models_metadata
# Using Any as a placeholder to resolve NameErrors during import/collection.
# Runtime errors may still occur if code tries to use these as real models.

ResourceMetadata: Any = ...
OntologyCoverage: Any = ...
PerformanceMetrics: Any = ...
OperationLog: Any = ...
