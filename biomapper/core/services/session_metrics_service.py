import logging
import json
from typing import Dict, Any, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from biomapper.db.cache_models import MappingSession, ExecutionMetric, PathExecutionStatus
from biomapper.core.exceptions import CacheStorageError, ErrorCode
from biomapper.core.utils.time_utils import get_current_utc_time


class SessionMetricsService:
    """
    Service for handling the creation, updating, and storage of mapping session logs and execution metrics.
    
    This service centralizes logic previously located in private methods within MappingExecutor,
    improving separation of concerns and maintainability.
    """
    
    def __init__(self):
        """Initialize the SessionMetricsService with a logger."""
        self.logger = logging.getLogger(__name__)
    
    async def create_mapping_session_log(
        self,
        session: AsyncSession,
        source_endpoint_name: str,
        target_endpoint_name: str,
        source_property_name: str,
        target_property_name: str,
        use_cache: bool,
        try_reverse_mapping: bool,
        input_count: int,
        max_cache_age_days: Optional[int] = None,
    ) -> MappingSession:
        """
        Create a new mapping session log entry.
        
        Args:
            session: Active database session
            source_endpoint_name: Name of the source endpoint
            target_endpoint_name: Name of the target endpoint
            source_property_name: Property name for source
            target_property_name: Property name for target
            use_cache: Whether caching is enabled
            try_reverse_mapping: Whether reverse mapping is enabled
            input_count: Number of input identifiers
            max_cache_age_days: Maximum cache age in days
            
        Returns:
            MappingSession object with generated ID
            
        Raises:
            CacheStorageError: If database operation fails
        """
        try:
            now = get_current_utc_time()
            
            # Create parameters JSON
            parameters = json.dumps({
                "source_property_name": source_property_name,
                "target_property_name": target_property_name,
                "use_cache": use_cache,
                "try_reverse_mapping": try_reverse_mapping,
                "input_count": input_count,
                "max_cache_age_days": max_cache_age_days,
            })
            
            log_entry = MappingSession(
                source_endpoint=source_endpoint_name,
                target_endpoint=target_endpoint_name,
                parameters=parameters,
                start_time=now,
                status="running"
            )
            session.add(log_entry)
            await session.flush()  # Ensure ID is generated
            await session.commit() # Commit to make it visible to other sessions
            return log_entry
        except SQLAlchemyError as e:
            self.logger.error(f"[{ErrorCode.CACHE_STORAGE_ERROR.name}] Cache storage error creating mapping session log. (original_exception={type(e).__name__}: {e})", exc_info=True)
            raise CacheStorageError(
                f"[{ErrorCode.CACHE_STORAGE_ERROR.name}] Failed to create mapping session log entry. (original_exception={type(e).__name__}: {e})",
                details={
                    "source_endpoint": source_endpoint_name,
                    "target_endpoint": target_endpoint_name,
                    "input_count": input_count,
                },
            ) from e
    
    async def update_mapping_session_log(
        self,
        session: AsyncSession,
        session_id: int,
        status: PathExecutionStatus,
        end_time: datetime,
        results_count: int = 0,
        error_message: Optional[str] = None,
    ):
        """
        Update the status and end time of a mapping session log.
        
        Args:
            session: Active database session
            session_id: ID of the MappingSession to update
            status: New status for the session
            end_time: End time for the session
            results_count: Number of results obtained
            error_message: Optional error message if the session failed
        
        Raises:
            CacheStorageError: If database operation fails
        """
        try:
            log_entry = await session.get(MappingSession, session_id)
            if log_entry:
                log_entry.status = status.value if isinstance(status, PathExecutionStatus) else status
                log_entry.end_time = end_time
                log_entry.results_count = results_count
                if error_message:
                    log_entry.error_message = error_message
                await session.commit()
                self.logger.info(f"Updated mapping session log ID {session_id} with status {status}")
            else:
                self.logger.warning(f"Mapping session log ID {session_id} not found for update.")
        except SQLAlchemyError as e:
            self.logger.error(f"[{ErrorCode.CACHE_STORAGE_ERROR.name}] Cache storage error updating mapping session log. (original_exception={type(e).__name__}: {e})", exc_info=True)
            raise CacheStorageError(
                f"[{ErrorCode.CACHE_STORAGE_ERROR.name}] Failed to update mapping session log entry. (original_exception={type(e).__name__}: {e})",
                details={"session_id": session_id},
            ) from e
    
    async def save_metrics_to_database(
        self,
        session: AsyncSession,
        session_id: int,
        metric_type: str,
        metrics: Dict[str, Any]
    ) -> None:
        """
        Save performance metrics to the database for analysis and reporting.
        
        Args:
            session: Active database session
            session_id: ID of the MappingSession
            metric_type: Type of metrics being saved
            metrics: Dictionary of metrics to save
        """
        try:
            # Update session-level metrics if appropriate
            if metric_type == "mapping_execution":
                mapping_session = await session.get(MappingSession, session_id)
                if mapping_session:
                    mapping_session.batch_size = metrics.get("batch_size")
                    mapping_session.max_concurrent_batches = metrics.get("max_concurrent_batches")
                    mapping_session.total_execution_time = metrics.get("total_execution_time")
                    mapping_session.success_rate = metrics.get("success_rate")
            
            # Save detailed metrics
            for metric_name, metric_value in metrics.items():
                # Skip non-numeric metrics or complex objects
                if isinstance(metric_value, (dict, list)):
                    continue
                    
                metric_entry = ExecutionMetric(
                    mapping_session_id=session_id,
                    metric_type=metric_type,
                    metric_name=metric_name,
                    timestamp=datetime.utcnow()
                )
                
                # Set the appropriate value field based on type
                if isinstance(metric_value, (int, float)):
                    metric_entry.metric_value = float(metric_value)
                elif metric_value is not None:
                    metric_entry.string_value = str(metric_value)
                    
                session.add(metric_entry)
                
            await session.commit()
            self.logger.debug(f"Saved {len(metrics)} metrics to database for session {session_id}")
                
        except Exception as e:
            self.logger.warning(f"Failed to save metrics to database: {str(e)}")
            # Don't raise the exception - we don't want to fail the mapping process due to metrics errors