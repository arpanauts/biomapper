"""
ExecutionSessionService - Manages the lifecycle of mapping execution sessions.

This service handles execution lifecycle events (start, complete, fail) and
progress reporting. It provides a clean interface for tracking execution state
and reporting progress to registered callbacks.
"""

import logging
from typing import Any, Dict, Optional, List, Callable
from datetime import datetime

from biomapper.core.services.execution_lifecycle_service import ExecutionLifecycleService

logger = logging.getLogger(__name__)


class ExecutionSessionService:
    """
    Service that manages execution sessions and progress reporting.
    
    This service is responsible for:
    - Managing execution lifecycle events (start, complete, fail)
    - Reporting progress updates
    - Managing progress callbacks
    - Tracking execution metadata
    
    It delegates to ExecutionLifecycleService for actual progress reporting
    while providing a focused interface for session management.
    """
    
    def __init__(
        self,
        execution_lifecycle_service: ExecutionLifecycleService,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize the ExecutionSessionService.
        
        Args:
            execution_lifecycle_service: Service for progress reporting
            logger: Optional logger instance
        """
        self.lifecycle_service = execution_lifecycle_service
        self.logger = logger or logging.getLogger(__name__)
        
        # Track active sessions
        self._active_sessions: Dict[str, Dict[str, Any]] = {}
        
        self.logger.info("ExecutionSessionService initialized")
    
    # Session Lifecycle Management
    
    async def start_session(
        self, 
        execution_id: str, 
        execution_type: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Start a new execution session.
        
        Args:
            execution_id: Unique identifier for the execution
            execution_type: Type of execution (e.g., 'mapping', 'strategy', 'batch')
            metadata: Optional metadata about the execution
        """
        # Track session
        self._active_sessions[execution_id] = {
            'execution_type': execution_type,
            'started_at': datetime.utcnow(),
            'metadata': metadata or {},
            'status': 'active'
        }
        
        # Report progress
        progress_data = {
            'event': 'execution_started',
            'execution_id': execution_id,
            'execution_type': execution_type,
            'metadata': metadata or {},
            'timestamp': datetime.utcnow().isoformat()
        }
        await self.report_progress(progress_data)
        
        self.logger.info(f"Started {execution_type} session: {execution_id}")
    
    async def complete_session(
        self, 
        execution_id: str,
        result_summary: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Complete an execution session successfully.
        
        Args:
            execution_id: Unique identifier for the execution
            result_summary: Optional summary of results
        """
        if execution_id not in self._active_sessions:
            self.logger.warning(f"Completing unknown session: {execution_id}")
            execution_type = 'unknown'
        else:
            session = self._active_sessions[execution_id]
            execution_type = session['execution_type']
            session['status'] = 'completed'
            session['completed_at'] = datetime.utcnow()
        
        # Report progress
        progress_data = {
            'event': 'execution_completed',
            'execution_id': execution_id,
            'execution_type': execution_type,
            'result_summary': result_summary or {},
            'timestamp': datetime.utcnow().isoformat()
        }
        await self.report_progress(progress_data)
        
        # Remove from active sessions
        self._active_sessions.pop(execution_id, None)
        
        self.logger.info(f"Completed {execution_type} session: {execution_id}")
    
    async def fail_session(
        self, 
        execution_id: str,
        error: Exception,
        error_context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Mark an execution session as failed.
        
        Args:
            execution_id: Unique identifier for the execution
            error: The exception that caused the failure
            error_context: Optional context about the error
        """
        if execution_id not in self._active_sessions:
            self.logger.warning(f"Failing unknown session: {execution_id}")
            execution_type = 'unknown'
        else:
            session = self._active_sessions[execution_id]
            execution_type = session['execution_type']
            session['status'] = 'failed'
            session['failed_at'] = datetime.utcnow()
            session['error'] = str(error)
        
        # Report progress
        progress_data = {
            'event': 'execution_failed',
            'execution_id': execution_id,
            'execution_type': execution_type,
            'error': str(error),
            'error_type': type(error).__name__,
            'error_context': error_context or {},
            'timestamp': datetime.utcnow().isoformat()
        }
        await self.report_progress(progress_data)
        
        # Remove from active sessions
        self._active_sessions.pop(execution_id, None)
        
        self.logger.error(f"Failed {execution_type} session {execution_id}: {error}")
    
    # Progress Reporting
    
    async def report_progress(self, progress_data: Dict[str, Any]) -> None:
        """
        Report progress update.
        
        Args:
            progress_data: Progress information to report
        """
        # Add timestamp if not present
        if 'timestamp' not in progress_data:
            progress_data['timestamp'] = datetime.utcnow().isoformat()
        
        # Log progress at appropriate level
        event_type = progress_data.get('event', progress_data.get('type', 'unknown'))
        if 'error' in progress_data or 'failed' in event_type:
            self.logger.warning(f"Progress: {event_type} - {progress_data}")
        else:
            self.logger.debug(f"Progress: {event_type}")
        
        # Delegate to lifecycle service
        await self.lifecycle_service.report_progress(progress_data)
    
    async def report_batch_progress(
        self,
        batch_number: int,
        total_batches: int,
        items_processed: int,
        total_items: int,
        batch_metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Report progress for batch processing operations.
        
        Args:
            batch_number: Current batch number
            total_batches: Total number of batches
            items_processed: Number of items processed so far
            total_items: Total number of items to process
            batch_metadata: Optional metadata about the batch
        """
        await self.lifecycle_service.report_batch_progress(
            batch_number=batch_number,
            total_batches=total_batches,
            items_processed=items_processed,
            total_items=total_items,
            batch_metadata=batch_metadata
        )
    
    # Callback Management
    
    def add_progress_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """
        Add a callback function to be called on progress updates.
        
        Args:
            callback: Function that takes a progress dict as argument
        """
        self.lifecycle_service.add_progress_callback(callback)
        self.logger.debug(f"Progress callback added: {getattr(callback, '__name__', 'anonymous')}")
    
    def remove_progress_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """
        Remove a progress callback function.
        
        Args:
            callback: Function to remove from callbacks
        """
        self.lifecycle_service.remove_progress_callback(callback)
        self.logger.debug(f"Progress callback removed: {getattr(callback, '__name__', 'anonymous')}")
    
    # Session Query Methods
    
    def get_active_sessions(self) -> List[str]:
        """
        Get list of currently active session IDs.
        
        Returns:
            List of active execution IDs
        """
        return list(self._active_sessions.keys())
    
    def get_session_info(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a specific session.
        
        Args:
            execution_id: Unique identifier for the execution
            
        Returns:
            Session information if found, None otherwise
        """
        return self._active_sessions.get(execution_id)
    
    def is_session_active(self, execution_id: str) -> bool:
        """
        Check if a session is currently active.
        
        Args:
            execution_id: Unique identifier for the execution
            
        Returns:
            True if session is active, False otherwise
        """
        return execution_id in self._active_sessions