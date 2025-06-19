"""Resource metadata management system for orchestrating mapping operations."""

import datetime
import json
import logging
from contextlib import contextmanager
from typing import Any, Dict, Iterator, List, Optional, Union

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

# Updated import: Point to metadata.models for Enums and placeholder models
from biomapper.metadata.models import (
    ResourceType,
    SupportLevel,
    OperationType,
    OperationStatus,
    ResourceMetadata,  # Placeholder
    OntologyCoverage,  # Placeholder
    PerformanceMetrics,  # Placeholder
    OperationLog,  # Placeholder
)

from biomapper.db.session import get_db_manager


logger = logging.getLogger(__name__)


class ResourceMetadataManager:
    """Manages metadata about available resources for mapping.

    This class provides a centralized registry of all mapping resources
    in the Biomapper system, including their capabilities, performance
    characteristics, and connection information. It enables intelligent
    routing of mapping operations to the most appropriate resource.
    """

    def __init__(self, data_dir: Optional[str] = None, db_name: Optional[str] = None):
        """Initialize the resource metadata manager.

        Args:
            data_dir: Directory for the SQLite database
            db_name: Name of the SQLite database file
        """
        self.db_manager = get_db_manager(data_dir=data_dir, db_name=db_name)
        self._ensure_tables_exist()

    def _ensure_tables_exist(self) -> None:
        """Ensure the metadata tables exist in the database."""
        try:
            with self.db_manager.session_scope() as session:
                # Check if ResourceMetadata table exists by attempting a simple query
                session.query(ResourceMetadata).first()
        except SQLAlchemyError:
            logger.info("Metadata tables not found, creating them...")
            self.db_manager.create_tables()

    @contextmanager
    def _session_scope(self) -> Iterator[Session]:
        """Provide a transactional scope around database operations."""
        with self.db_manager.session_scope() as session:
            yield session

    def register_resource(
        self,
        resource_name: str,
        resource_type: Union[str, ResourceType],
        connection_info: Optional[Dict[str, Any]] = None,
        priority: int = 0,
        is_active: bool = True,
    ) -> ResourceMetadata:
        """Register or update a resource in the metadata system.

        Args:
            resource_name: Name of the resource
            resource_type: Type of resource (cache, graph, api, etc.)
            connection_info: Connection details as a dictionary
            priority: Priority for routing (higher values have higher priority)
            is_active: Whether the resource is active

        Returns:
            ResourceMetadata: The registered resource metadata
        """
        # Convert resource_type to enum if it's a string
        if isinstance(resource_type, str):
            resource_type = ResourceType(resource_type.lower())

        # Convert connection_info to JSON string
        conn_info_str = None
        if connection_info:
            conn_info_str = json.dumps(connection_info)

        with self._session_scope() as session:
            # Check if resource already exists
            resource = (
                session.query(ResourceMetadata)
                .filter_by(resource_name=resource_name)
                .first()
            )

            if resource:
                # Update existing resource
                resource.resource_type = resource_type
                resource.connection_info = conn_info_str
                resource.priority = priority
                resource.is_active = is_active
                resource.updated_at = datetime.datetime.utcnow()
                logger.info(f"Updated resource metadata for '{resource_name}'")
            else:
                # Create new resource
                resource = ResourceMetadata(
                    resource_name=resource_name,
                    resource_type=resource_type,
                    connection_info=conn_info_str,
                    priority=priority,
                    is_active=is_active,
                    created_at=datetime.datetime.utcnow(),
                    updated_at=datetime.datetime.utcnow(),
                )
                session.add(resource)
                logger.info(f"Registered new resource '{resource_name}'")

            session.commit()
            return resource

    def register_ontology_coverage(
        self,
        resource_name: str,
        ontology_type: str,
        support_level: Union[str, SupportLevel],
        entity_count: Optional[int] = None,
    ) -> OntologyCoverage:
        """Register ontology coverage for a resource.

        Args:
            resource_name: Name of the resource
            ontology_type: Type of ontology (e.g., 'chebi', 'hmdb')
            support_level: Level of support (none, partial, full)
            entity_count: Approximate count of entities if available

        Returns:
            OntologyCoverage: The registered ontology coverage
        """
        # Convert support_level to enum if it's a string
        if isinstance(support_level, str):
            support_level = SupportLevel(support_level.lower())

        with self._session_scope() as session:
            # Get resource
            resource = (
                session.query(ResourceMetadata)
                .filter_by(resource_name=resource_name)
                .first()
            )

            if not resource:
                raise ValueError(f"Resource '{resource_name}' not found")

            # Check if coverage already exists
            coverage = (
                session.query(OntologyCoverage)
                .filter_by(resource_id=resource.id, ontology_type=ontology_type)
                .first()
            )

            if coverage:
                # Update existing coverage
                coverage.support_level = support_level
                coverage.entity_count = entity_count
                coverage.last_updated = datetime.datetime.utcnow()
                logger.info(
                    f"Updated ontology coverage for '{resource_name}' and '{ontology_type}'"
                )
            else:
                # Create new coverage
                coverage = OntologyCoverage(
                    resource_id=resource.id,
                    ontology_type=ontology_type,
                    support_level=support_level,
                    entity_count=entity_count,
                    last_updated=datetime.datetime.utcnow(),
                )
                session.add(coverage)
                logger.info(
                    f"Registered ontology coverage for '{resource_name}' and '{ontology_type}'"
                )

            session.commit()
            return coverage

    def update_resource_sync(self, resource_name: str) -> None:
        """Update the last sync timestamp for a resource.

        Args:
            resource_name: Name of the resource
        """
        with self._session_scope() as session:
            resource = (
                session.query(ResourceMetadata)
                .filter_by(resource_name=resource_name)
                .first()
            )

            if not resource:
                raise ValueError(f"Resource '{resource_name}' not found")

            resource.last_sync = datetime.datetime.utcnow()
            session.commit()
            logger.info(f"Updated last sync for '{resource_name}'")

    def log_operation(
        self,
        resource_name: str,
        operation_type: Union[str, OperationType],
        source_type: Optional[str] = None,
        target_type: Optional[str] = None,
        query: Optional[str] = None,
        response_time_ms: Optional[int] = None,
        status: Union[str, OperationStatus] = OperationStatus.SUCCESS,
        error_message: Optional[str] = None,
    ) -> OperationLog:
        """Log an operation for analysis.

        Args:
            resource_name: Name of the resource
            operation_type: Type of operation
            source_type: Source ontology type
            target_type: Target ontology type
            query: Simplified query representation
            response_time_ms: Response time in milliseconds
            status: Operation status
            error_message: Error message if applicable

        Returns:
            OperationLog: The logged operation
        """
        # Convert operation_type to enum if it's a string
        if isinstance(operation_type, str):
            operation_type = OperationType(operation_type.lower())

        # Convert status to enum if it's a string
        if isinstance(status, str):
            status = OperationStatus(status.lower())

        with self._session_scope() as session:
            # Get resource
            resource = (
                session.query(ResourceMetadata)
                .filter_by(resource_name=resource_name)
                .first()
            )

            if not resource:
                raise ValueError(f"Resource '{resource_name}' not found")

            # Create log entry
            log_entry = OperationLog(
                resource_id=resource.id,
                operation_type=operation_type,
                source_type=source_type,
                target_type=target_type,
                query=query,
                response_time_ms=response_time_ms,
                status=status,
                error_message=error_message,
                timestamp=datetime.datetime.utcnow(),
            )
            session.add(log_entry)

            # Update performance metrics
            if response_time_ms is not None:
                self._update_performance_metrics(
                    session=session,
                    resource_id=resource.id,
                    operation_type=operation_type,
                    source_type=source_type,
                    target_type=target_type,
                    response_time_ms=response_time_ms,
                    success=(status == OperationStatus.SUCCESS),
                )

            session.commit()
            return log_entry

    def _update_performance_metrics(
        self,
        session: Session,
        resource_id: int,
        operation_type: OperationType,
        source_type: Optional[str],
        target_type: Optional[str],
        response_time_ms: float,
        success: bool,
    ) -> None:
        """Update performance metrics for a resource.

        Args:
            session: SQLAlchemy session
            resource_id: Resource ID
            operation_type: Type of operation
            source_type: Source ontology type
            target_type: Target ontology type
            response_time_ms: Response time in milliseconds
            success: Whether the operation was successful
        """
        # Get metrics
        metrics = (
            session.query(PerformanceMetrics)
            .filter_by(
                resource_id=resource_id,
                operation_type=operation_type,
                source_type=source_type,
                target_type=target_type,
            )
            .first()
        )

        if metrics:
            # Update existing metrics
            metrics.update_metrics(response_time_ms, success)
        else:
            # Create new metrics
            metrics = PerformanceMetrics(
                resource_id=resource_id,
                operation_type=operation_type,
                source_type=source_type,
                target_type=target_type,
                avg_response_time_ms=response_time_ms,
                success_rate=1.0 if success else 0.0,
                sample_count=1,
                last_updated=datetime.datetime.utcnow(),
            )
            session.add(metrics)

    def get_resources(
        self,
        active_only: bool = True,
        resource_type: Optional[Union[str, ResourceType]] = None,
    ) -> List[Dict[str, Any]]:
        """Get list of registered resources.

        Args:
            active_only: Only include active resources
            resource_type: Filter by resource type

        Returns:
            List of resource metadata as dictionaries
        """
        if isinstance(resource_type, str) and resource_type:
            resource_type = ResourceType(resource_type.lower())

        with self._session_scope() as session:
            query = session.query(ResourceMetadata)

            if active_only:
                query = query.filter(ResourceMetadata.is_active == True)

            if resource_type:
                query = query.filter(ResourceMetadata.resource_type == resource_type)

            # Order by priority (highest first)
            query = query.order_by(ResourceMetadata.priority.desc())

            return [resource.to_dict() for resource in query.all()]

    def get_resource(self, resource_name: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a specific resource.

        Args:
            resource_name: Name of the resource

        Returns:
            Resource metadata as a dictionary, or None if not found
        """
        with self._session_scope() as session:
            resource = (
                session.query(ResourceMetadata)
                .filter_by(resource_name=resource_name)
                .first()
            )

            return resource.to_dict() if resource else None

    def has_ontology_support(
        self,
        resource_name: str,
        ontology_type: str,
        min_support: Union[str, SupportLevel] = SupportLevel.PARTIAL,
    ) -> bool:
        """Check if a resource supports a specific ontology type.

        Args:
            resource_name: Name of the resource
            ontology_type: Type of ontology
            min_support: Minimum support level required

        Returns:
            True if the resource supports the ontology type, False otherwise
        """
        if isinstance(min_support, str):
            min_support = SupportLevel(min_support.lower())

        with self._session_scope() as session:
            # Get resource
            resource = (
                session.query(ResourceMetadata)
                .filter_by(resource_name=resource_name)
                .first()
            )

            if not resource:
                return False

            # Check ontology coverage
            coverage = (
                session.query(OntologyCoverage)
                .filter_by(
                    resource_id=resource.id,
                    ontology_type=ontology_type,
                )
                .first()
            )

            if not coverage:
                return False

            # Check support level
            support_levels = {
                SupportLevel.NONE: 0,
                SupportLevel.PARTIAL: 1,
                SupportLevel.FULL: 2,
            }

            return support_levels[coverage.support_level] >= support_levels[min_support]

    def get_preferred_resource_order(
        self,
        source_type: str,
        target_type: str,
        operation_type: Union[str, OperationType] = OperationType.LOOKUP,
        min_success_rate: Optional[float] = None,
    ) -> List[str]:
        """Get ordered list of resources to try for this mapping type.

        Args:
            source_type: Source ontology type
            target_type: Target ontology type
            operation_type: Type of operation
            min_success_rate: Minimum success rate required

        Returns:
            Ordered list of resource names
        """
        if isinstance(operation_type, str):
            operation_type = OperationType(operation_type.lower())

        with self._session_scope() as session:
            # Get all active resources
            resources = session.query(ResourceMetadata).filter_by(is_active=True).all()

            # Filter resources that support both ontology types
            supported_resources = []

            for resource in resources:
                source_support = (
                    session.query(OntologyCoverage)
                    .filter_by(
                        resource_id=resource.id,
                        ontology_type=source_type,
                        support_level=SupportLevel.NONE,
                    )
                    .first()
                    is None
                )

                target_support = (
                    session.query(OntologyCoverage)
                    .filter_by(
                        resource_id=resource.id,
                        ontology_type=target_type,
                        support_level=SupportLevel.NONE,
                    )
                    .first()
                    is None
                )

                if source_support and target_support:
                    supported_resources.append(resource)

            # Calculate scores based on priority and performance
            scored_resources = []

            for resource in supported_resources:
                # Base score from priority
                score = resource.priority * 100  # Weight priority heavily

                # Add performance score if available
                metrics = (
                    session.query(PerformanceMetrics)
                    .filter_by(
                        resource_id=resource.id,
                        operation_type=operation_type,
                        source_type=source_type,
                        target_type=target_type,
                    )
                    .first()
                )

                if metrics:
                    # Skip resources with low success rate if specified
                    if (
                        min_success_rate is not None
                        and metrics.success_rate < min_success_rate
                    ):
                        continue

                    # Higher success rate is better
                    score += metrics.success_rate * 50

                    # Lower response time is better (inverse relationship)
                    if metrics.avg_response_time_ms > 0:
                        # Normalize response time (assume 0-1000ms range)
                        norm_time = min(1000, metrics.avg_response_time_ms) / 1000
                        # Invert so faster is better
                        score += (1 - norm_time) * 25

                scored_resources.append((resource, score))

            # Sort by score (highest first)
            scored_resources.sort(key=lambda x: x[1], reverse=True)

            return [r.resource_name for r, _ in scored_resources]

    def get_performance_metrics(
        self,
        resource_name: Optional[str] = None,
        operation_type: Optional[Union[str, OperationType]] = None,
        source_type: Optional[str] = None,
        target_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get performance metrics for resources.

        Args:
            resource_name: Filter by resource name
            operation_type: Filter by operation type
            source_type: Filter by source ontology type
            target_type: Filter by target ontology type

        Returns:
            List of performance metrics as dictionaries
        """
        if isinstance(operation_type, str) and operation_type:
            operation_type = OperationType(operation_type.lower())

        with self._session_scope() as session:
            query = session.query(PerformanceMetrics)

            if resource_name:
                resource = (
                    session.query(ResourceMetadata)
                    .filter_by(resource_name=resource_name)
                    .first()
                )

                if not resource:
                    return []

                query = query.filter(PerformanceMetrics.resource_id == resource.id)

            if operation_type:
                query = query.filter(
                    PerformanceMetrics.operation_type == operation_type
                )

            if source_type:
                query = query.filter(PerformanceMetrics.source_type == source_type)

            if target_type:
                query = query.filter(PerformanceMetrics.target_type == target_type)

            return [metrics.to_dict() for metrics in query.all()]

    def clear_operation_logs(
        self,
        older_than_days: Optional[int] = None,
        resource_name: Optional[str] = None,
    ) -> int:
        """Clear operation logs from the database.

        Args:
            older_than_days: Only clear logs older than this many days
            resource_name: Only clear logs for this resource

        Returns:
            Number of logs cleared
        """
        with self._session_scope() as session:
            query = session.query(OperationLog)

            if older_than_days:
                cutoff_date = datetime.datetime.utcnow() - datetime.timedelta(
                    days=older_than_days
                )
                query = query.filter(OperationLog.timestamp < cutoff_date)

            if resource_name:
                resource = (
                    session.query(ResourceMetadata)
                    .filter_by(resource_name=resource_name)
                    .first()
                )

                if not resource:
                    return 0

                query = query.filter(OperationLog.resource_id == resource.id)

            count = query.count()
            query.delete()
            session.commit()

            logger.info(f"Cleared {count} operation logs")
            return count
