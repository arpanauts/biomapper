"""Dispatcher for routing mapping operations to appropriate resources."""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional, Protocol, Type, TypeVar

from biomapper.metadata.models import OperationType, OperationStatus
from biomapper.metadata.manager import ResourceMetadataManager


logger = logging.getLogger(__name__)


class MapperResource(Protocol):
    """Protocol for resources that can perform mapping operations."""

    async def map_entity(
        self, source_id: str, source_type: str, target_type: str, **kwargs
    ) -> Any:
        """Map an entity from source to target type."""
        ...


T = TypeVar("T")


class MappingDispatcher:
    """Orchestrates mapping operations across multiple resources.

    This class implements an intelligent routing system that directs
    mapping operations to the most appropriate resource based on metadata
    about resource capabilities and performance. It handles fallback logic
    and collects performance metrics.
    """

    def __init__(
        self,
        metadata_manager: Optional[ResourceMetadataManager] = None,
        resources: Optional[Dict[str, MapperResource]] = None,
        result_class: Optional[Type[T]] = None,
    ):
        """Initialize the mapping dispatcher.

        Args:
            metadata_manager: Manager for resource metadata
            resources: Dictionary of registered resources
            result_class: Optional class for mapping results
        """
        self.metadata = metadata_manager or ResourceMetadataManager()
        self.resources = resources or {}
        self.result_class = result_class

    def register_resource(self, name: str, resource: MapperResource) -> None:
        """Register a resource with the dispatcher.

        Args:
            name: Name of the resource
            resource: Resource instance
        """
        self.resources[name] = resource
        logger.info(f"Registered resource '{name}' with dispatcher")

    async def map_entity(
        self,
        source_id: str,
        source_type: str,
        target_type: str,
        resource_name: Optional[str] = None,
        fallback: bool = True,
        min_success_rate: Optional[float] = None,
        timeout: Optional[float] = None,
        **kwargs,
    ) -> Optional[Any]:
        """Map an entity using the optimal resource path.

        Args:
            source_id: Source entity identifier
            source_type: Source ontology type
            target_type: Target ontology type
            resource_name: Optional specific resource to use
            fallback: Whether to try fallback resources if the first fails
            min_success_rate: Minimum success rate for resources
            timeout: Timeout in seconds for the operation
            **kwargs: Additional arguments to pass to the resource

        Returns:
            Mapping result, or None if not found
        """
        # Use specific resource if specified
        if resource_name:
            if resource_name not in self.resources:
                raise ValueError(f"Resource '{resource_name}' not registered")

            resource_order = [resource_name]
        else:
            # Get resource order based on metadata
            resource_order = self.metadata.get_preferred_resource_order(
                source_type=source_type,
                target_type=target_type,
                operation_type=OperationType.MAP,
                min_success_rate=min_success_rate,
            )

            # Filter to resources that are actually registered
            resource_order = [name for name in resource_order if name in self.resources]

        # Try resources in order
        result = None
        errors = []

        for name in resource_order:
            resource = self.resources[name]

            try:
                # Start timing
                start_time = time.time()

                # Create a task with timeout if specified
                if timeout:
                    task = asyncio.create_task(
                        resource.map_entity(
                            source_id=source_id,
                            source_type=source_type,
                            target_type=target_type,
                            **kwargs,
                        )
                    )

                    try:
                        result = await asyncio.wait_for(task, timeout=timeout)
                    except asyncio.TimeoutError:
                        # Log timeout
                        self.metadata.log_operation(
                            resource_name=name,
                            operation_type=OperationType.MAP,
                            source_type=source_type,
                            target_type=target_type,
                            query=source_id,
                            response_time_ms=int(timeout * 1000),
                            status=OperationStatus.TIMEOUT,
                            error_message="Operation timed out",
                        )

                        # Continue to next resource
                        errors.append(f"Resource '{name}' timed out after {timeout}s")
                        continue
                else:
                    # No timeout specified
                    result = await resource.map_entity(
                        source_id=source_id,
                        source_type=source_type,
                        target_type=target_type,
                        **kwargs,
                    )

                # Calculate response time
                response_time_ms = int((time.time() - start_time) * 1000)

                # Log successful operation
                self.metadata.log_operation(
                    resource_name=name,
                    operation_type=OperationType.MAP,
                    source_type=source_type,
                    target_type=target_type,
                    query=source_id,
                    response_time_ms=response_time_ms,
                    status=OperationStatus.SUCCESS,
                )

                # If we got a result, return it
                if result:
                    # If result_class is specified and result is not already of that type
                    if self.result_class and not isinstance(result, self.result_class):
                        # Try to convert result to the expected type
                        if hasattr(self.result_class, "from_dict") and hasattr(
                            result, "to_dict"
                        ):
                            result = self.result_class.from_dict(result.to_dict())
                        elif hasattr(self.result_class, "from_mapping_result"):
                            result = self.result_class.from_mapping_result(result)

                    # Add metadata about which resource was used
                    if hasattr(result, "metadata"):
                        result.metadata = getattr(result, "metadata", {}) or {}
                        result.metadata["resource"] = name
                        result.metadata["response_time_ms"] = response_time_ms

                    return result

            except Exception as e:
                # Calculate response time
                response_time_ms = int((time.time() - start_time) * 1000)

                # Log error
                error_message = str(e)
                self.metadata.log_operation(
                    resource_name=name,
                    operation_type=OperationType.MAP,
                    source_type=source_type,
                    target_type=target_type,
                    query=source_id,
                    response_time_ms=response_time_ms,
                    status=OperationStatus.ERROR,
                    error_message=error_message,
                )

                # Add to errors
                errors.append(f"Resource '{name}' error: {error_message}")

                # If we're not using fallbacks, re-raise
                if not fallback:
                    raise

            # If we got here without a result and fallback is False, stop
            if not fallback:
                break

        # If we didn't find a result, log the details
        if errors:
            logger.warning(
                f"Failed to map {source_type}:{source_id} to {target_type} using "
                f"{len(resource_order)} resources: {'; '.join(errors)}"
            )
        else:
            logger.info(
                f"No mapping found for {source_type}:{source_id} to {target_type}"
            )

        return None

    async def batch_map_entities(
        self,
        entities: List[Dict[str, str]],
        target_type: str,
        **kwargs,
    ) -> List[Dict[str, Any]]:
        """Map multiple entities in batch.

        Args:
            entities: List of dictionaries with 'id' and 'type' keys
            target_type: Target ontology type
            **kwargs: Additional arguments to pass to map_entity

        Returns:
            List of mapping results (one per entity)
        """
        results = []

        for entity in entities:
            source_id = entity["id"]
            source_type = entity["type"]

            result = await self.map_entity(
                source_id=source_id,
                source_type=source_type,
                target_type=target_type,
                **kwargs,
            )

            results.append(
                {
                    "source_id": source_id,
                    "source_type": source_type,
                    "target_type": target_type,
                    "result": result,
                }
            )

        return results

    def get_resource_performance(
        self,
        source_type: Optional[str] = None,
        target_type: Optional[str] = None,
    ) -> Dict[str, Dict[str, Any]]:
        """Get performance metrics for resources.

        Args:
            source_type: Filter by source ontology type
            target_type: Filter by target ontology type

        Returns:
            Dictionary of resource performance metrics
        """
        metrics = self.metadata.get_performance_metrics(
            operation_type=OperationType.MAP,
            source_type=source_type,
            target_type=target_type,
        )

        # Group by resource
        result = {}
        for metric in metrics:
            resource_id = metric["resource_id"]

            # Get resource name
            resource_name = None
            for name, resource in self.resources.items():
                r_info = self.metadata.get_resource(name)
                if r_info and r_info["id"] == resource_id:
                    resource_name = name
                    break

            if not resource_name:
                continue

            if resource_name not in result:
                result[resource_name] = {}

            key = f"{metric['source_type']}_{metric['target_type']}"
            result[resource_name][key] = {
                "avg_response_time_ms": metric["avg_response_time_ms"],
                "success_rate": metric["success_rate"],
                "sample_count": metric["sample_count"],
            }

        return result
