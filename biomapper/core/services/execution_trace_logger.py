"""
ExecutionTraceLogger service for logging execution trace records.

This service centralizes the creation and management of execution trace records
including MappingSession, MappingPathExecutionLog, EntityMapping, and 
ExecutionMetric records to the cache database.
"""

from datetime import datetime, timezone
from typing import List, Dict, Any
from sqlalchemy.exc import SQLAlchemyError

from biomapper.core.engine_components.session_manager import SessionManager
from biomapper.db.cache_models import (
    EntityMapping,
    PathExecutionLog,
    MappingSession,
    ExecutionMetric,
    EntityMappingProvenance
)


class ExecutionTraceLogger:
    """
    Service for logging execution trace records to the cache database.
    
    Handles the creation and persistence of mapping sessions, path executions,
    entity mappings, and execution metrics with proper error handling and
    transaction management.
    """

    def __init__(self, session_manager: SessionManager):
        """
        Initialize ExecutionTraceLogger with a SessionManager.
        
        Args:
            session_manager: SessionManager instance for database access
        """
        self.session_manager = session_manager

    async def log_mapping_session_start(self, session_data: Dict[str, Any]) -> MappingSession:
        """
        Log the start of a mapping session.
        
        Args:
            session_data: Dictionary containing session start data with keys:
                - source_endpoint: Source API endpoint
                - target_endpoint: Target API endpoint  
                - parameters: Session parameters
                - start_time: Session start timestamp
                
        Returns:
            MappingSession: The created session record
            
        Raises:
            SQLAlchemyError: If database operation fails
        """
        session = self.session_manager.get_async_cache_session()
        try:
            mapping_session = MappingSession(
                source_endpoint=session_data["source_endpoint"],
                target_endpoint=session_data["target_endpoint"],
                parameters=session_data["parameters"],
                start_time=session_data["start_time"]
            )
            
            session.add(mapping_session)
            await session.commit()
            await session.refresh(mapping_session)
            
            return mapping_session
            
        except SQLAlchemyError:
            await session.rollback()
            raise
        finally:
            await session.close()

    async def log_mapping_session_end(self, session_id: int, status: str, 
                                    metrics: Dict[str, Any]) -> None:
        """
        Log the end of a mapping session with completion status and metrics.
        
        Args:
            session_id: ID of the mapping session to update
            status: Final status of the session
            metrics: Dictionary of session metrics
            
        Raises:
            SQLAlchemyError: If database operation fails
        """
        session = self.session_manager.get_async_cache_session()
        try:
            mapping_session = await session.get(MappingSession, session_id)
            if mapping_session:
                mapping_session.status = status
                mapping_session.end_time = datetime.now(timezone.utc)
                
                # Update metrics if provided
                if metrics:
                    for key, value in metrics.items():
                        if hasattr(mapping_session, key):
                            setattr(mapping_session, key, value)
            
            await session.commit()
            
        except SQLAlchemyError:
            await session.rollback()
            raise
        finally:
            await session.close()

    async def log_path_execution(self, path_data: Dict[str, Any]) -> PathExecutionLog:
        """
        Log the execution of a mapping path.
        
        Args:
            path_data: Dictionary containing path execution data with keys:
                - relationship_mapping_path_id: ID of the path
                - source_entity_id: Source entity identifier
                - source_entity_type: Type of source entity
                - start_time: Execution start time
                - end_time: Execution end time
                - duration_ms: Execution duration in milliseconds
                - status: Execution status (PathExecutionStatus enum)
                - log_messages: List of log messages
                - error_message: Error message if any (optional)
                
        Returns:
            PathExecutionLog: The created path execution record
            
        Raises:
            SQLAlchemyError: If database operation fails
        """
        session = self.session_manager.get_async_cache_session()
        try:
            path_log = PathExecutionLog(
                relationship_mapping_path_id=path_data["relationship_mapping_path_id"],
                source_entity_id=path_data["source_entity_id"],
                source_entity_type=path_data["source_entity_type"],
                start_time=path_data["start_time"],
                end_time=path_data["end_time"],
                duration_ms=path_data["duration_ms"],
                status=path_data["status"],
                log_messages=path_data.get("log_messages", []),
                error_message=path_data.get("error_message")
            )
            
            session.add(path_log)
            await session.commit()
            await session.refresh(path_log)
            
            return path_log
            
        except SQLAlchemyError:
            await session.rollback()
            raise
        finally:
            await session.close()

    async def log_entity_mappings(self, mappings: List[Dict[str, Any]], 
                                provenance_data: Dict[str, Any]) -> None:
        """
        Log entity mappings with their provenance information.
        
        Args:
            mappings: List of entity mapping dictionaries, each containing:
                - source_id: Source entity ID
                - source_type: Source entity type
                - target_id: Target entity ID
                - target_type: Target entity type
                - confidence: Mapping confidence score
                - mapping_source: Source of the mapping
                - is_derived: Whether mapping is derived
                - derivation_path: Path of derivation (optional)
            provenance_data: Dictionary containing provenance information:
                - relationship_mapping_path_id: Path ID
                - execution_timestamp: Execution timestamp
                - executor_version: Version of executor
                
        Raises:
            SQLAlchemyError: If database operation fails
        """
        session = self.session_manager.get_async_cache_session()
        try:
            entities_to_add = []
            provenance_to_add = []
            
            for mapping_data in mappings:
                # Create entity mapping
                entity_mapping = EntityMapping(
                    source_id=mapping_data["source_id"],
                    source_type=mapping_data["source_type"],
                    target_id=mapping_data["target_id"],
                    target_type=mapping_data["target_type"],
                    confidence=mapping_data["confidence"],
                    mapping_source=mapping_data["mapping_source"],
                    is_derived=mapping_data["is_derived"],
                    derivation_path=mapping_data.get("derivation_path")
                )
                entities_to_add.append(entity_mapping)
                
                # Create provenance record
                provenance = EntityMappingProvenance(
                    entity_mapping=entity_mapping,
                    relationship_mapping_path_id=provenance_data["relationship_mapping_path_id"],
                    execution_timestamp=provenance_data["execution_timestamp"],
                    executor_version=provenance_data["executor_version"]
                )
                provenance_to_add.append(provenance)
            
            # Add all records
            session.add_all(entities_to_add + provenance_to_add)
            await session.commit()
            
        except SQLAlchemyError:
            await session.rollback()
            raise
        finally:
            await session.close()

    async def log_execution_metric(self, metric_data: Dict[str, Any]) -> ExecutionMetric:
        """
        Log an execution metric.
        
        Args:
            metric_data: Dictionary containing metric data with keys:
                - mapping_session_id: ID of the mapping session
                - metric_type: Type of metric
                - metric_name: Name of the metric
                - metric_value: Numeric value (optional)
                - string_value: String value (optional)
                - timestamp: Metric timestamp
                
        Returns:
            ExecutionMetric: The created metric record
            
        Raises:
            SQLAlchemyError: If database operation fails
        """
        session = self.session_manager.get_async_cache_session()
        try:
            metric = ExecutionMetric(
                mapping_session_id=metric_data["mapping_session_id"],
                metric_type=metric_data["metric_type"],
                metric_name=metric_data["metric_name"],
                metric_value=metric_data.get("metric_value"),
                string_value=metric_data.get("string_value"),
                timestamp=metric_data["timestamp"]
            )
            
            session.add(metric)
            await session.commit()
            await session.refresh(metric)
            
            return metric
            
        except SQLAlchemyError:
            await session.rollback()
            raise
        finally:
            await session.close()