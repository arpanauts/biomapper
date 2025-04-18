"""
Property health tracking system for endpoint configurations.

This module provides components for tracking the health of property extraction
configurations, including success/failure rates, timing, and error categorization.
"""

import time
import json
import logging
import datetime
from enum import Enum
from typing import Dict, List, Any, Optional, Union, Tuple

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from biomapper.db.models_health import EndpointPropertyHealth
from biomapper.db.session import get_session

logger = logging.getLogger(__name__)


class ErrorCategory(Enum):
    """Standard categories for extraction errors."""
    
    PATTERN_SYNTAX = "pattern_syntax"  # Error in the pattern syntax
    MISSING_COLUMN = "missing_column"  # Referenced column doesn't exist
    NO_MATCH = "no_match"             # Pattern didn't match any data
    TYPE_ERROR = "type_error"         # Type conversion error
    TRANSFORM_ERROR = "transform_error"  # Error in transform function
    CONNECTION_ERROR = "connection_error"  # Error connecting to external service
    TIMEOUT = "timeout"               # Operation timed out
    UNKNOWN = "unknown"               # Uncategorized error


class ErrorCategorizer:
    """Categorizes error messages into standard types."""
    
    @staticmethod
    def categorize(error_message: str) -> str:
        """
        Categorize an error message into a standard type.
        
        Args:
            error_message: The error message to categorize
            
        Returns:
            Standard error category
        """
        error_message = error_message.lower()
        
        if any(word in error_message for word in ["pattern", "regex", "syntax"]):
            return ErrorCategory.PATTERN_SYNTAX.value
            
        if any(word in error_message for word in ["column", "field", "not found", "missing"]):
            return ErrorCategory.MISSING_COLUMN.value
            
        if any(word in error_message for word in ["no match", "not match", "zero matches"]):
            return ErrorCategory.NO_MATCH.value
            
        if any(word in error_message for word in ["type", "convert", "cast"]):
            return ErrorCategory.TYPE_ERROR.value
            
        if any(word in error_message for word in ["transform", "function"]):
            return ErrorCategory.TRANSFORM_ERROR.value
            
        if any(word in error_message for word in ["connect", "connection", "network"]):
            return ErrorCategory.CONNECTION_ERROR.value
            
        if any(word in error_message for word in ["timeout", "timed out", "too slow"]):
            return ErrorCategory.TIMEOUT.value
            
        return ErrorCategory.UNKNOWN.value


class PropertyHealthTracker:
    """
    Tracks health metrics for endpoint property configurations.
    
    This class records extraction attempts and updates health metrics
    in the database, including success/failure rates, timing, and error
    categorization.
    """
    
    def __init__(self, db_session: Optional[Session] = None):
        """
        Initialize the health tracker.
        
        Args:
            db_session: SQLAlchemy session (optional, will create one if not provided)
        """
        self.db_session = db_session
        self.session_owner = db_session is None
        self._metrics_buffer: List[Dict[str, Any]] = []
        self.buffer_size = 10  # Number of metrics to buffer before flushing
        
    def __enter__(self):
        """Context manager entry."""
        if self.session_owner and self.db_session is None:
            self.db_session = get_session()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.flush_metrics()
        if self.session_owner and self.db_session is not None:
            self.db_session.close()
            self.db_session = None
    
    def record_extraction_attempt(
        self,
        endpoint_id: int,
        ontology_type: str,
        property_name: str,
        success: bool,
        execution_time_ms: int,
        error_message: Optional[str] = None
    ) -> bool:
        """
        Record an extraction attempt and update health metrics.
        
        Args:
            endpoint_id: ID of the endpoint
            ontology_type: Ontology type
            property_name: Property name
            success: Whether the extraction was successful
            execution_time_ms: Execution time in milliseconds
            error_message: Error message if extraction failed
            
        Returns:
            bool: True if the record was successfully queued, False otherwise
        """
        try:
            # Create a metrics record
            metric = {
                "endpoint_id": endpoint_id,
                "ontology_type": ontology_type,
                "property_name": property_name,
                "success": success,
                "execution_time_ms": execution_time_ms,
                "error_message": error_message,
                "timestamp": datetime.datetime.utcnow()
            }
            
            # Add to buffer
            self._metrics_buffer.append(metric)
            
            # Flush if buffer is full
            if len(self._metrics_buffer) >= self.buffer_size:
                self.flush_metrics()
                
            return True
            
        except Exception as e:
            logger.error(f"Error recording extraction attempt: {e}")
            return False
    
    def flush_metrics(self) -> bool:
        """
        Flush buffered metrics to the database.
        
        Returns:
            bool: True if the metrics were successfully flushed, False otherwise
        """
        if not self._metrics_buffer:
            return True
            
        if self.db_session is None:
            logger.error("No database session available")
            return False
            
        try:
            # Group metrics by endpoint+ontology+property
            grouped_metrics: Dict[Tuple[int, str, str], List[Dict[str, Any]]] = {}
            for metric in self._metrics_buffer:
                key = (metric["endpoint_id"], metric["ontology_type"], metric["property_name"])
                if key not in grouped_metrics:
                    grouped_metrics[key] = []
                grouped_metrics[key].append(metric)
                
            # Process each group
            for (endpoint_id, ontology_type, property_name), metrics in grouped_metrics.items():
                # Get or create health record
                health_record = self.db_session.query(EndpointPropertyHealth).filter_by(
                    endpoint_id=endpoint_id,
                    ontology_type=ontology_type,
                    property_name=property_name
                ).first()
                
                if not health_record:
                    health_record = EndpointPropertyHealth(
                        endpoint_id=endpoint_id,
                        ontology_type=ontology_type,
                        property_name=property_name
                    )
                    self.db_session.add(health_record)
                
                # Update metrics
                success_count = sum(1 for m in metrics if m["success"])
                failure_count = len(metrics) - success_count
                
                health_record.extraction_success_count += success_count
                health_record.extraction_failure_count += failure_count
                
                # Update timestamps
                successful_metrics = [m for m in metrics if m["success"]]
                failed_metrics = [m for m in metrics if not m["success"]]
                
                if successful_metrics:
                    health_record.last_success_time = max(m["timestamp"] for m in successful_metrics)
                
                if failed_metrics:
                    health_record.last_failure_time = max(m["timestamp"] for m in failed_metrics)
                
                # Update average execution time
                total_time = sum(m["execution_time_ms"] for m in metrics)
                if health_record.avg_extraction_time_ms is None:
                    health_record.avg_extraction_time_ms = total_time / len(metrics)
                else:
                    # Weighted average based on sample size
                    old_weight = health_record.sample_size
                    new_weight = len(metrics)
                    health_record.avg_extraction_time_ms = (
                        (health_record.avg_extraction_time_ms * old_weight) + total_time
                    ) / (old_weight + new_weight)
                
                # Track error types
                error_types = health_record.error_types_list
                for metric in failed_metrics:
                    if metric["error_message"]:
                        error_type = ErrorCategorizer.categorize(metric["error_message"])
                        if error_type not in error_types:
                            error_types.append(error_type)
                
                health_record.error_types_list = error_types
                health_record.sample_size += len(metrics)
                health_record.last_updated = datetime.datetime.utcnow()
            
            # Commit changes
            self.db_session.commit()
            
            # Clear buffer
            self._metrics_buffer.clear()
            
            return True
            
        except SQLAlchemyError as e:
            logger.error(f"Database error flushing metrics: {e}")
            self.db_session.rollback()
            return False
            
        except Exception as e:
            logger.error(f"Error flushing metrics: {e}")
            return False