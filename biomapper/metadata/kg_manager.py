"""Knowledge Graph Resource Manager for Biomapper.

This module provides a specialized implementation of the resource metadata system
for managing knowledge graph resources, including their capabilities and schemas.
"""

import logging
import time
from typing import Dict, List, Optional, ClassVar

from biomapper.metadata.models import (
    ResourceRegistration,
)


logger = logging.getLogger(__name__)


class KnowledgeGraphManager:
    """Manager for knowledge graph resources in Biomapper.

    This class provides a registry for knowledge graph resources, tracking their
    capabilities, schema mappings, and performance metrics. It's designed to work
    alongside the existing ResourceMetadataManager while providing specialized
    functionality for knowledge graphs.
    """

    _instance: ClassVar[Optional["KnowledgeGraphManager"]] = None

    @classmethod
    def get_instance(cls) -> "KnowledgeGraphManager":
        """Get the singleton instance of the knowledge graph manager.

        Returns:
            The singleton instance
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        """Initialize the knowledge graph manager."""
        self._resources: Dict[str, ResourceRegistration] = {}
        self._capabilities_map: Dict[
            str, List[str]
        ] = {}  # Capability name to resource names

    def register_resource(self, resource: ResourceRegistration) -> None:
        """Register a knowledge graph resource.

        Args:
            resource: Resource registration to add
        """
        # Store the resource
        self._resources[resource.name] = resource

        # Update capabilities map
        for capability in resource.capabilities:
            if capability.name not in self._capabilities_map:
                self._capabilities_map[capability.name] = []

            if resource.name not in self._capabilities_map[capability.name]:
                self._capabilities_map[capability.name].append(resource.name)

        logger.info(
            f"Registered knowledge graph resource '{resource.name}' with {len(resource.capabilities)} capabilities"
        )

    def unregister_resource(self, resource_name: str) -> None:
        """Unregister a knowledge graph resource.

        Args:
            resource_name: Name of the resource to remove
        """
        if resource_name not in self._resources:
            logger.warning(f"Resource '{resource_name}' not found for unregistration")
            return

        # Remove from capabilities map
        resource = self._resources[resource_name]
        for capability in resource.capabilities:
            if capability.name in self._capabilities_map:
                if resource_name in self._capabilities_map[capability.name]:
                    self._capabilities_map[capability.name].remove(resource_name)

                # Clean up empty capability entries
                if not self._capabilities_map[capability.name]:
                    del self._capabilities_map[capability.name]

        # Remove the resource
        del self._resources[resource_name]
        logger.info(f"Unregistered knowledge graph resource '{resource_name}'")

    def get_resource(self, resource_name: str) -> Optional[ResourceRegistration]:
        """Get a knowledge graph resource by name.

        Args:
            resource_name: Name of the resource to get

        Returns:
            The resource if found, None otherwise
        """
        return self._resources.get(resource_name)

    def list_resources(self) -> List[ResourceRegistration]:
        """Get all registered knowledge graph resources.

        Returns:
            List of all registered resources
        """
        return list(self._resources.values())

    def get_resources_for_capability(
        self, capability_name: str
    ) -> List[ResourceRegistration]:
        """Get all resources that provide a specific capability.

        Args:
            capability_name: Name of the capability to find resources for

        Returns:
            List of resources that provide the capability
        """
        if capability_name not in self._capabilities_map:
            return []

        return [
            self._resources[name]
            for name in self._capabilities_map[capability_name]
            if name in self._resources and self._resources[name].available
        ]

    def best_resource_for_capability(
        self, capability_name: str
    ) -> Optional[ResourceRegistration]:
        """Get the best resource for a specific capability.

        The best resource is determined by performance metrics, confidence, and availability.

        Args:
            capability_name: Name of the capability to find the best resource for

        Returns:
            The best resource for the capability, or None if no resources are available
        """
        resources = self.get_resources_for_capability(capability_name)
        if not resources:
            return None

        # Sort by confidence and success rate
        sorted_resources = sorted(
            resources,
            key=lambda r: (
                r.get_capability(capability_name).confidence * r.metrics.success_rate
                if r.get_capability(capability_name)
                else 0.0
            ),
            reverse=True,
        )

        return sorted_resources[0] if sorted_resources else None

    def update_metrics(
        self,
        resource_name: str,
        capability_name: Optional[str] = None,
        success: bool = True,
        latency_ms: Optional[float] = None,
        cost: Optional[float] = None,
    ) -> None:
        """Update performance metrics for a resource.

        Args:
            resource_name: Name of the resource to update
            capability_name: Name of the capability being measured (optional)
            success: Whether the operation was successful
            latency_ms: Latency of the operation in milliseconds
            cost: Cost of the operation (if applicable)
        """
        if resource_name not in self._resources:
            logger.warning(f"Resource '{resource_name}' not found for metrics update")
            return

        resource = self._resources[resource_name]
        metrics = resource.metrics

        # Update global metrics
        metrics.total_operations += 1
        if not success:
            metrics.failed_operations += 1

        # Calculate success rate
        if metrics.total_operations > 0:
            metrics.success_rate = 1.0 - (
                metrics.failed_operations / metrics.total_operations
            )

        # Update latency if provided
        if latency_ms is not None:
            # Simple moving average for avg_latency_ms
            if metrics.total_operations > 1:
                metrics.avg_latency_ms = (
                    metrics.avg_latency_ms * (metrics.total_operations - 1) + latency_ms
                ) / metrics.total_operations
            else:
                metrics.avg_latency_ms = latency_ms

            # For now, we'll just approximate p95_latency_ms
            # A proper implementation would maintain a histogram
            if latency_ms > metrics.p95_latency_ms:
                metrics.p95_latency_ms = (
                    latency_ms * 0.05 + metrics.p95_latency_ms * 0.95
                )

        # Update cost if provided
        if cost is not None:
            # Simple moving average for avg_cost
            if metrics.total_operations > 1:
                metrics.avg_cost = (
                    metrics.avg_cost * (metrics.total_operations - 1) + cost
                ) / metrics.total_operations
            else:
                metrics.avg_cost = cost

        # Update capability-specific metrics if provided
        if capability_name:
            if capability_name not in metrics.capability_metrics:
                metrics.capability_metrics[capability_name] = {
                    "total_operations": 0,
                    "failed_operations": 0,
                    "success_rate": 1.0,
                    "avg_latency_ms": 0.0,
                    "p95_latency_ms": 0.0,
                    "avg_cost": 0.0,
                }

            cap_metrics = metrics.capability_metrics[capability_name]
            cap_metrics["total_operations"] += 1
            if not success:
                cap_metrics["failed_operations"] += 1

            # Calculate capability-specific success rate
            if cap_metrics["total_operations"] > 0:
                cap_metrics["success_rate"] = 1.0 - (
                    cap_metrics["failed_operations"] / cap_metrics["total_operations"]
                )

            # Update capability-specific latency if provided
            if latency_ms is not None:
                # Simple moving average
                if cap_metrics["total_operations"] > 1:
                    cap_metrics["avg_latency_ms"] = (
                        cap_metrics["avg_latency_ms"]
                        * (cap_metrics["total_operations"] - 1)
                        + latency_ms
                    ) / cap_metrics["total_operations"]
                else:
                    cap_metrics["avg_latency_ms"] = latency_ms

                # Approximate p95_latency_ms
                if latency_ms > cap_metrics["p95_latency_ms"]:
                    cap_metrics["p95_latency_ms"] = (
                        latency_ms * 0.05 + cap_metrics["p95_latency_ms"] * 0.95
                    )

            # Update capability-specific cost if provided
            if cost is not None:
                # Simple moving average
                if cap_metrics["total_operations"] > 1:
                    cap_metrics["avg_cost"] = (
                        cap_metrics["avg_cost"] * (cap_metrics["total_operations"] - 1)
                        + cost
                    ) / cap_metrics["total_operations"]
                else:
                    cap_metrics["avg_cost"] = cost

        # Update last updated timestamp
        metrics.last_updated = time.time()

        logger.debug(
            f"Updated metrics for '{resource_name}': "
            f"success_rate={metrics.success_rate:.2f}, "
            f"avg_latency={metrics.avg_latency_ms:.2f}ms"
        )


# Create singleton instance
kg_manager = KnowledgeGraphManager.get_instance()
