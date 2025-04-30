"""
Health-aware property extractor integration for endpoint configurations.

This module provides a health-tracking wrapper around property extraction
functions, automatically recording extraction attempts for health monitoring.
"""

import time
import json
import logging
import functools
from typing import Dict, List, Any, Optional, Union, Callable, Awaitable, TypeVar

from biomapper.mapping.health.tracker import PropertyHealthTracker, ErrorCategorizer

logger = logging.getLogger(__name__)

T = TypeVar("T")


class HealthTrackingPropertyExtractor:
    """
    Wrapper that adds health tracking to property extraction functions.

    This class wraps property extraction functions or methods to automatically
    track extraction attempts for health monitoring.
    """

    def __init__(self, health_tracker: Optional[PropertyHealthTracker] = None):
        """
        Initialize the health tracking extractor.

        Args:
            health_tracker: Property health tracker instance (optional)
        """
        self.health_tracker = health_tracker or PropertyHealthTracker()

    def track_extraction(self, func: Callable[..., T]) -> Callable[..., T]:
        """
        Decorator to track property extraction.

        Args:
            func: The function to wrap

        Returns:
            Wrapped function with health tracking
        """

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Extract endpoint_id, ontology_type, and property_name from args or kwargs
            endpoint_id = kwargs.get("endpoint_id")
            ontology_type = kwargs.get("ontology_type")
            property_name = kwargs.get("property_name")

            # Try to extract from args if not in kwargs
            if endpoint_id is None and len(args) > 0:
                endpoint_id = args[0]
            if ontology_type is None and len(args) > 1:
                ontology_type = args[1]
            if property_name is None and len(args) > 2:
                property_name = args[2]

            # If we couldn't extract the params, just call the function
            if any(x is None for x in [endpoint_id, ontology_type, property_name]):
                logger.warning(
                    "Could not extract endpoint_id, ontology_type, or property_name for health tracking"
                )
                return func(*args, **kwargs)

            # Track extraction
            start_time = time.time()
            success = False
            error_message = None

            try:
                # Call the original function
                result = func(*args, **kwargs)
                success = bool(result)
                return result

            except Exception as e:
                error_message = str(e)
                logger.error(f"Error extracting property: {error_message}")
                raise

            finally:
                # Record the extraction attempt
                execution_time_ms = int((time.time() - start_time) * 1000)
                self.health_tracker.record_extraction_attempt(
                    endpoint_id=endpoint_id,
                    ontology_type=ontology_type,
                    property_name=property_name,
                    success=success,
                    execution_time_ms=execution_time_ms,
                    error_message=error_message,
                )

        return wrapper

    def track_async_extraction(
        self, func: Callable[..., Awaitable[T]]
    ) -> Callable[..., Awaitable[T]]:
        """
        Decorator to track async property extraction.

        Args:
            func: The async function to wrap

        Returns:
            Wrapped async function with health tracking
        """

        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract endpoint_id, ontology_type, and property_name from args or kwargs
            endpoint_id = kwargs.get("endpoint_id")
            ontology_type = kwargs.get("ontology_type")
            property_name = kwargs.get("property_name")

            # Try to extract from args if not in kwargs
            if endpoint_id is None and len(args) > 0:
                endpoint_id = args[0]
            if ontology_type is None and len(args) > 1:
                ontology_type = args[1]
            if property_name is None and len(args) > 2:
                property_name = args[2]

            # If we couldn't extract the params, just call the function
            if any(x is None for x in [endpoint_id, ontology_type, property_name]):
                logger.warning(
                    "Could not extract endpoint_id, ontology_type, or property_name for health tracking"
                )
                return await func(*args, **kwargs)

            # Track extraction
            start_time = time.time()
            success = False
            error_message = None

            try:
                # Call the original function
                result = await func(*args, **kwargs)
                success = bool(result)
                return result

            except Exception as e:
                error_message = str(e)
                logger.error(f"Error extracting property: {error_message}")
                raise

            finally:
                # Record the extraction attempt
                execution_time_ms = int((time.time() - start_time) * 1000)
                self.health_tracker.record_extraction_attempt(
                    endpoint_id=endpoint_id,
                    ontology_type=ontology_type,
                    property_name=property_name,
                    success=success,
                    execution_time_ms=execution_time_ms,
                    error_message=error_message,
                )

        return wrapper


# Convenience function for property extraction with health tracking
async def extract_property_with_health_tracking(
    endpoint_id: int,
    ontology_type: str,
    property_name: str,
    data: Any,
    extraction_func: Callable[[Any, Any], Awaitable[Any]],
    config: Any,
    health_tracker: Optional[PropertyHealthTracker] = None,
) -> Any:
    """
    Extract a property with health tracking.

    Args:
        endpoint_id: ID of the endpoint
        ontology_type: Ontology type
        property_name: Property name
        data: Data to extract from
        extraction_func: Function that performs the actual extraction
        config: Extraction configuration
        health_tracker: Optional health tracker instance

    Returns:
        Extracted property value
    """
    # Use a default tracker if none is provided
    tracker = health_tracker or PropertyHealthTracker()

    # Track extraction
    start_time = time.time()
    success = False
    error_message = None

    try:
        # Call the extraction function
        result = await extraction_func(data, config)
        success = bool(result)
        return result

    except Exception as e:
        error_message = str(e)
        logger.error(f"Error extracting property: {error_message}")
        raise

    finally:
        # Record the extraction attempt
        execution_time_ms = int((time.time() - start_time) * 1000)
        tracker.record_extraction_attempt(
            endpoint_id=endpoint_id,
            ontology_type=ontology_type,
            property_name=property_name,
            success=success,
            execution_time_ms=execution_time_ms,
            error_message=error_message,
        )
