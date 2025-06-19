"""Resource adapters for the metadata system."""

import asyncio
import logging
import time
from typing import Any, Optional, Protocol

from biomapper.cache.manager import CacheManager
from biomapper.metadata.manager import ResourceMetadataManager
from biomapper.metadata.models import OperationStatus, OperationType
from biomapper.spoke.client import SPOKEDBClient, SPOKEConfig


logger = logging.getLogger(__name__)


class ResourceAdapter(Protocol):
    """Protocol for resource adapters that work with the metadata system."""

    async def map_entity(
        self, source_id: str, source_type: str, target_type: str, **kwargs
    ) -> Any:
        """Map an entity from source to target type."""
        ...


class CacheResourceAdapter:
    """Adapter for integrating the SQLite cache with the resource metadata system."""

    def __init__(
        self,
        cache_manager: Optional[CacheManager] = None,
        metadata_manager: Optional[ResourceMetadataManager] = None,
        resource_name: str = "sqlite_cache",
    ):
        """Initialize the cache resource adapter.

        Args:
            cache_manager: Cache manager instance
            metadata_manager: Resource metadata manager instance
            resource_name: Name of the resource in the metadata system
        """
        self.cache_manager = cache_manager or CacheManager()
        self.metadata_manager = metadata_manager or ResourceMetadataManager()
        self.resource_name = resource_name

    async def map_entity(
        self,
        source_id: str,
        source_type: str,
        target_type: str,
        include_metadata: bool = False,
        check_transitivity: bool = True,
        **kwargs,
    ) -> Any:
        """Map an entity using the SQLite cache.

        Args:
            source_id: Source entity identifier
            source_type: Source ontology type
            target_type: Target ontology type
            include_metadata: Whether to include metadata in the result
            check_transitivity: Whether to check for transitive mappings
            **kwargs: Additional arguments passed to the cache manager

        Returns:
            Mapping result or None if not found
        """
        start_time = time.time()

        try:
            # Perform the mapping operation
            # Note: CacheManager.map_entity is synchronous, we're wrapping it
            result = await asyncio.to_thread(
                self.cache_manager.map_entity,
                source_id=source_id,
                source_type=source_type,
                target_type=target_type,
                include_metadata=include_metadata,
                check_transitivity=check_transitivity,
                **kwargs,
            )

            # Record operation metrics
            response_time_ms = int((time.time() - start_time) * 1000)
            status = OperationStatus.SUCCESS if result else OperationStatus.ERROR

            # Don't await this to avoid blocking
            asyncio.create_task(
                self._record_operation_metrics(
                    source_id=source_id,
                    source_type=source_type,
                    target_type=target_type,
                    response_time_ms=response_time_ms,
                    status=status,
                    error_message=None if result else "No mapping found",
                )
            )

            return result

        except Exception as e:
            # Record operation failure
            response_time_ms = int((time.time() - start_time) * 1000)

            # Don't await this to avoid blocking
            asyncio.create_task(
                self._record_operation_metrics(
                    source_id=source_id,
                    source_type=source_type,
                    target_type=target_type,
                    response_time_ms=response_time_ms,
                    status=OperationStatus.ERROR,
                    error_message=str(e),
                )
            )

            # Re-raise the exception
            raise

    async def _record_operation_metrics(
        self,
        source_id: str,
        source_type: str,
        target_type: str,
        response_time_ms: int,
        status: OperationStatus,
        error_message: Optional[str] = None,
    ) -> None:
        """Record operation metrics in the metadata system.

        Args:
            source_id: Source entity identifier
            source_type: Source ontology type
            target_type: Target ontology type
            response_time_ms: Response time in milliseconds
            status: Operation status
            error_message: Optional error message if status is ERROR
        """
        try:
            self.metadata_manager.log_operation(
                resource_name=self.resource_name,
                operation_type=OperationType.MAP,
                source_type=source_type,
                target_type=target_type,
                query=source_id,
                response_time_ms=response_time_ms,
                status=status,
                error_message=error_message,
            )
        except Exception as e:
            logger.error(f"Failed to record operation metrics: {e}")


class SpokeResourceAdapter:
    """Adapter for integrating SPOKE graph with the resource metadata system."""

    def __init__(
        self,
        spoke_client: Optional[SPOKEDBClient] = None,
        metadata_manager: Optional[ResourceMetadataManager] = None,
        resource_name: str = "spoke_graph",
    ):
        """Initialize the SPOKE resource adapter.

        Args:
            spoke_client: SPOKE client instance
            metadata_manager: Resource metadata manager instance
            resource_name: Name of the resource in the metadata system
        """
        if spoke_client is None:
            # Create default config and client
            config = SPOKEConfig(
                host="localhost",  # Default host
                database="spoke",  # Default database
            )
            spoke_client = SPOKEDBClient(config)

        self.spoke_client = spoke_client
        self.metadata_manager = metadata_manager or ResourceMetadataManager()
        self.resource_name = resource_name

    async def map_entity(
        self, source_id: str, source_type: str, target_type: str, **kwargs
    ) -> Any:
        """Map an entity using the SPOKE graph.

        Args:
            source_id: Source entity identifier
            source_type: Source ontology type
            target_type: Target ontology type
            **kwargs: Additional arguments passed to the SPOKE client

        Returns:
            Mapping result or None if not found
        """
        start_time = time.time()

        try:
            # We need to use the existing SPOKE client capabilities to implement mapping
            # First, we need to determine the node type for the source and target
            source_node_type = self._get_node_type_for_ontology(source_type)
            target_node_type = self._get_node_type_for_ontology(target_type)

            # Use SPOKE client to find the source node
            async with self.spoke_client as client:
                # Find the source node
                source_query = f"{source_type}:{source_id}"
                source_nodes = await client.query_nodes(
                    node_type=source_node_type, properties={source_type: source_id}
                )

                if not source_nodes:
                    logger.debug(f"No SPOKE node found for {source_query}")
                    return None

                # Get the first matching node
                source_node = source_nodes[0]

                # Try to find a direct property on the node
                if target_type in source_node:
                    result = {
                        "id": source_node[target_type],
                        "source": "spoke_direct",
                        "confidence": 1.0,
                    }
                else:
                    # Need to traverse relationships to find target
                    # This is a simplified implementation - in practice, you'd need a more
                    # sophisticated traversal algorithm based on SPOKE's structure
                    result = None

            # Record operation metrics
            response_time_ms = int((time.time() - start_time) * 1000)
            status = OperationStatus.SUCCESS if result else OperationStatus.ERROR

            # Don't await this to avoid blocking
            asyncio.create_task(
                self._record_operation_metrics(
                    source_id=source_id,
                    source_type=source_type,
                    target_type=target_type,
                    response_time_ms=response_time_ms,
                    status=status,
                    error_message=None if result else "No mapping found",
                )
            )

            return result

        except Exception as e:
            # Record operation failure
            response_time_ms = int((time.time() - start_time) * 1000)

            # Don't await this to avoid blocking
            asyncio.create_task(
                self._record_operation_metrics(
                    source_id=source_id,
                    source_type=source_type,
                    target_type=target_type,
                    response_time_ms=response_time_ms,
                    status=OperationStatus.ERROR,
                    error_message=str(e),
                )
            )

            # Re-raise the exception
            raise

    async def _record_operation_metrics(
        self,
        source_id: str,
        source_type: str,
        target_type: str,
        response_time_ms: int,
        status: OperationStatus,
        error_message: Optional[str] = None,
    ) -> None:
        """Record operation metrics in the metadata system.

        Args:
            source_id: Source entity identifier
            source_type: Source ontology type
            target_type: Target ontology type
            response_time_ms: Response time in milliseconds
            status: Operation status
            error_message: Optional error message if status is ERROR
        """
        try:
            self.metadata_manager.log_operation(
                resource_name=self.resource_name,
                operation_type=OperationType.MAP,
                source_type=source_type,
                target_type=target_type,
                query=source_id,
                response_time_ms=response_time_ms,
                status=status,
                error_message=error_message,
            )
        except Exception as e:
            logger.error(f"Failed to record operation metrics: {e}")

    def _get_node_type_for_ontology(self, ontology_type: str) -> str:
        """Map ontology type to SPOKE node type.

        Args:
            ontology_type: Ontology type (e.g., 'chebi', 'hmdb')

        Returns:
            SPOKE node type
        """
        # Map of ontology types to SPOKE node types
        ontology_to_node_type = {
            # Compounds/Metabolites
            "chebi": "Compound",
            "hmdb": "Compound",
            "pubchem": "Compound",
            "inchikey": "Compound",
            "compound_name": "Compound",
            "smiles": "Compound",
            # Genes/Proteins
            "uniprot": "Protein",
            "ensembl": "Gene",
            "gene_symbol": "Gene",
            # Diseases
            "mondo": "Disease",
            "doid": "Disease",
            "mesh": "Disease",
            # Pathways
            "reactome": "Pathway",
            "kegg": "Pathway",
            # Default fallback
            "default": "Compound",
        }

        return ontology_to_node_type.get(
            ontology_type.lower(), ontology_to_node_type["default"]
        )
