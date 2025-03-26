"""Performance monitoring and telemetry for the mapping cache."""

import datetime
import logging
import time
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from biomapper.db.session import get_db_manager


logger = logging.getLogger(__name__)


class CacheEventType(str, Enum):
    """Types of cache events."""

    HIT = "hit"
    MISS = "miss"
    ADD = "add"
    DELETE = "delete"
    LOOKUP = "lookup"
    DERIVE = "derive"
    API_CALL = "api_call"
    ERROR = "error"


@dataclass
class CacheEvent:
    """Record of a cache event."""

    event_type: CacheEventType
    timestamp: float
    entity_type: Optional[str] = None
    duration_ms: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None
    
    @property
    def formatted_timestamp(self) -> str:
        """Get formatted timestamp string.
        
        Returns:
            ISO formatted timestamp
        """
        dt = datetime.datetime.fromtimestamp(self.timestamp)
        return dt.isoformat()


class CacheMonitor:
    """Monitor for tracking cache performance."""

    def __init__(
        self,
        enabled: bool = True,
        max_events: int = 1000,
        log_events: bool = True,
    ):
        """Initialize cache monitor.
        
        Args:
            enabled: Whether monitoring is enabled
            max_events: Maximum number of events to store in memory
            log_events: Whether to log events to the logger
        """
        self.enabled = enabled
        self.max_events = max_events
        self.log_events = log_events
        self.events: List[CacheEvent] = []
        self.stats: Dict[str, Dict[str, Any]] = {}
        self.start_time = time.time()
    
    def record_event(
        self,
        event_type: CacheEventType,
        entity_type: Optional[str] = None,
        duration_ms: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record a cache event.
        
        Args:
            event_type: Type of event
            entity_type: Entity type involved in the event
            duration_ms: Duration of the operation in milliseconds
            metadata: Additional event metadata
        """
        if not self.enabled:
            return
        
        event = CacheEvent(
            event_type=event_type,
            timestamp=time.time(),
            entity_type=entity_type,
            duration_ms=duration_ms,
            metadata=metadata or {},
        )
        
        # Add to events list with size limit
        self.events.append(event)
        if len(self.events) > self.max_events:
            self.events = self.events[-self.max_events:]
        
        # Update stats
        self._update_stats(event)
        
        # Log event if configured
        if self.log_events:
            self._log_event(event)
    
    def _update_stats(self, event: CacheEvent) -> None:
        """Update cache statistics with a new event.
        
        Args:
            event: Cache event
        """
        # Initialize stats if this is the first time seeing this event type
        if event.event_type not in self.stats:
            self.stats[event.event_type] = {
                "count": 0,
                "by_entity_type": {},
                "durations_ms": [],
                "avg_duration_ms": None,
            }
        
        # Update general stats
        stat = self.stats[event.event_type]
        stat["count"] += 1
        
        # Update entity type stats if available
        if event.entity_type:
            if event.entity_type not in stat["by_entity_type"]:
                stat["by_entity_type"][event.entity_type] = 0
            stat["by_entity_type"][event.entity_type] += 1
        
        # Update duration stats if available
        if event.duration_ms is not None:
            stat["durations_ms"].append(event.duration_ms)
            # Keep only the last 100 durations to avoid memory issues
            if len(stat["durations_ms"]) > 100:
                stat["durations_ms"] = stat["durations_ms"][-100:]
            
            # Recalculate average
            stat["avg_duration_ms"] = sum(stat["durations_ms"]) / len(stat["durations_ms"])
        
        # Calculate hit ratio if we have both hits and misses
        if CacheEventType.HIT in self.stats and CacheEventType.MISS in self.stats:
            hits = self.stats[CacheEventType.HIT]["count"]
            misses = self.stats[CacheEventType.MISS]["count"]
            total = hits + misses
            
            if total > 0:
                self.stats["hit_ratio"] = hits / total
    
    def _log_event(self, event: CacheEvent) -> None:
        """Log a cache event.
        
        Args:
            event: Cache event
        """
        msg_parts = [f"Cache {event.event_type.value}"]
        
        if event.entity_type:
            msg_parts.append(f"type={event.entity_type}")
        
        if event.duration_ms is not None:
            msg_parts.append(f"duration={event.duration_ms:.2f}ms")
        
        if event.metadata:
            for key, value in event.metadata.items():
                if key != "traceback":  # Skip verbose tracebacks
                    msg_parts.append(f"{key}={value}")
        
        msg = " ".join(msg_parts)
        
        if event.event_type == CacheEventType.ERROR:
            logger.error(msg)
            if event.metadata and "traceback" in event.metadata:
                logger.debug(event.metadata["traceback"])
        elif event.event_type == CacheEventType.HIT:
            logger.debug(msg)
        else:
            logger.info(msg)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics.
        
        Returns:
            Dictionary of cache statistics
        """
        if not self.enabled:
            return {}
        
        # Calculate additional stats
        result = {
            "events": {key: value["count"] for key, value in self.stats.items()},
            "uptime_seconds": time.time() - self.start_time,
        }
        
        # Add hit ratio if available
        if "hit_ratio" in self.stats:
            result["hit_ratio"] = self.stats["hit_ratio"]
        elif CacheEventType.HIT in self.stats and CacheEventType.MISS in self.stats:
            hits = self.stats[CacheEventType.HIT]["count"]
            misses = self.stats[CacheEventType.MISS]["count"]
            total = hits + misses
            
            if total > 0:
                result["hit_ratio"] = hits / total
            else:
                result["hit_ratio"] = None
        else:
            result["hit_ratio"] = None
        
        # Add performance stats
        performance = {}
        for event_type, stat in self.stats.items():
            if stat["avg_duration_ms"] is not None:
                performance[event_type] = {
                    "avg_ms": stat["avg_duration_ms"],
                    "samples": len(stat["durations_ms"]),
                }
        
        result["performance"] = performance
        
        return result
    
    def get_recent_events(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent cache events.
        
        Args:
            limit: Maximum number of events to return
            
        Returns:
            List of recent events
        """
        if not self.enabled:
            return []
        
        events = []
        for event in self.events[-limit:]:
            events.append({
                "type": event.event_type,
                "timestamp": event.formatted_timestamp,
                "entity_type": event.entity_type,
                "duration_ms": event.duration_ms,
                "metadata": event.metadata,
            })
        
        return events
    
    @contextmanager
    def track_operation(
        self,
        operation_type: CacheEventType,
        entity_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Context manager for tracking operation duration.
        
        Args:
            operation_type: Type of operation
            entity_type: Entity type involved in the operation
            metadata: Additional operation metadata
            
        Yields:
            Context for the operation
        """
        if not self.enabled:
            yield
            return
        
        start_time = time.time()
        error = None
        
        try:
            yield
        except Exception as e:
            error = e
            if metadata is None:
                metadata = {}
            
            metadata["error"] = str(e)
            metadata["traceback"] = logging.traceback.format_exc()
            
            self.record_event(
                event_type=CacheEventType.ERROR,
                entity_type=entity_type,
                metadata=metadata,
            )
            
            raise
        finally:
            end_time = time.time()
            duration_ms = (end_time - start_time) * 1000
            
            if error is None:
                self.record_event(
                    event_type=operation_type,
                    entity_type=entity_type,
                    duration_ms=duration_ms,
                    metadata=metadata,
                )


# Global monitor instance
_global_monitor = CacheMonitor()


def get_monitor() -> CacheMonitor:
    """Get the global cache monitor.
    
    Returns:
        Global cache monitor instance
    """
    return _global_monitor


def reset_monitor(enabled: bool = True) -> None:
    """Reset the global cache monitor.
    
    Args:
        enabled: Whether monitoring should be enabled
    """
    global _global_monitor
    _global_monitor = CacheMonitor(enabled=enabled)


@contextmanager
def track_cache_operation(
    operation_type: CacheEventType,
    entity_type: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
):
    """Context manager for tracking a cache operation.
    
    Args:
        operation_type: Type of operation
        entity_type: Entity type involved in the operation
        metadata: Additional operation metadata
    
    Yields:
        Context for the operation
    """
    with get_monitor().track_operation(
        operation_type=operation_type,
        entity_type=entity_type,
        metadata=metadata,
    ):
        yield


def record_cache_hit(entity_type: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> None:
    """Record a cache hit.
    
    Args:
        entity_type: Entity type involved in the hit
        metadata: Additional hit metadata
    """
    get_monitor().record_event(
        event_type=CacheEventType.HIT,
        entity_type=entity_type,
        metadata=metadata,
    )


def record_cache_miss(entity_type: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> None:
    """Record a cache miss.
    
    Args:
        entity_type: Entity type involved in the miss
        metadata: Additional miss metadata
    """
    get_monitor().record_event(
        event_type=CacheEventType.MISS,
        entity_type=entity_type,
        metadata=metadata,
    )


def record_api_call(
    entity_type: Optional[str] = None,
    duration_ms: Optional[float] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """Record an API call.
    
    Args:
        entity_type: Entity type involved in the API call
        duration_ms: Duration of the API call in milliseconds
        metadata: Additional API call metadata
    """
    get_monitor().record_event(
        event_type=CacheEventType.API_CALL,
        entity_type=entity_type,
        duration_ms=duration_ms,
        metadata=metadata,
    )


def get_cache_stats() -> Dict[str, Any]:
    """Get cache statistics.
    
    Returns:
        Dictionary of cache statistics
    """
    return get_monitor().get_stats()


def get_recent_cache_events(limit: int = 10) -> List[Dict[str, Any]]:
    """Get recent cache events.
    
    Args:
        limit: Maximum number of events to return
        
    Returns:
        List of recent events
    """
    return get_monitor().get_recent_events(limit=limit)
