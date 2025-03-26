"""SQLAlchemy models for the resource metadata system."""

import datetime
import enum
import json
from typing import Any, Dict, List, Optional, Union

from sqlalchemy import (
    Boolean, Column, DateTime, Enum, Float, ForeignKey, 
    Integer, String, Text, UniqueConstraint
)
from sqlalchemy.orm import relationship

from biomapper.db.models import Base


class ResourceType(str, enum.Enum):
    """Types of mapping resources in the system."""
    
    CACHE = "cache"
    GRAPH = "graph"
    API = "api"
    DATASET = "dataset"
    OTHER = "other"


class SupportLevel(str, enum.Enum):
    """Level of support for a particular ontology type."""
    
    NONE = "none"
    PARTIAL = "partial"
    FULL = "full"


class OperationType(str, enum.Enum):
    """Types of operations that can be performed on resources."""
    
    LOOKUP = "lookup"
    MAP = "map"
    SYNC = "sync"
    UPDATE = "update"
    DELETE = "delete"
    OTHER = "other"


class OperationStatus(str, enum.Enum):
    """Status of an operation."""
    
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"
    PENDING = "pending"
    CANCELED = "canceled"


class ResourceMetadata(Base):
    """Metadata for a mapping resource."""
    
    __tablename__ = "resource_metadata"
    
    id = Column(Integer, primary_key=True)
    resource_name = Column(String, nullable=False, unique=True)
    resource_type = Column(Enum(ResourceType), nullable=False)
    connection_info = Column(Text)  # JSON string with connection details
    priority = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    last_sync = Column(DateTime)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, 
                         onupdate=datetime.datetime.utcnow)
    
    # Relationships
    ontology_coverage = relationship("OntologyCoverage", back_populates="resource",
                                     cascade="all, delete-orphan")
    performance_metrics = relationship("PerformanceMetrics", back_populates="resource",
                                       cascade="all, delete-orphan")
    operation_logs = relationship("OperationLog", back_populates="resource",
                                  cascade="all, delete-orphan")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        conn_info = {}
        if self.connection_info:
            try:
                conn_info = json.loads(self.connection_info)
            except json.JSONDecodeError:
                conn_info = {"error": "Invalid JSON"}
        
        return {
            "id": self.id,
            "resource_name": self.resource_name,
            "resource_type": self.resource_type.value,
            "connection_info": conn_info,
            "priority": self.priority,
            "is_active": self.is_active,
            "last_sync": self.last_sync,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ResourceMetadata":
        """Create from dictionary representation."""
        conn_info = data.get("connection_info", {})
        if isinstance(conn_info, dict):
            conn_info = json.dumps(conn_info)
        
        return cls(
            resource_name=data["resource_name"],
            resource_type=data["resource_type"],
            connection_info=conn_info,
            priority=data.get("priority", 0),
            is_active=data.get("is_active", True),
            last_sync=data.get("last_sync"),
        )


class OntologyCoverage(Base):
    """Ontology coverage for a resource."""
    
    __tablename__ = "ontology_coverage"
    __table_args__ = (UniqueConstraint("resource_id", "ontology_type"),)
    
    id = Column(Integer, primary_key=True)
    resource_id = Column(Integer, ForeignKey("resource_metadata.id"), nullable=False)
    ontology_type = Column(String, nullable=False)
    support_level = Column(Enum(SupportLevel), nullable=False)
    entity_count = Column(Integer)
    last_updated = Column(DateTime)
    
    # Relationships
    resource = relationship("ResourceMetadata", back_populates="ontology_coverage")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "id": self.id,
            "resource_id": self.resource_id,
            "ontology_type": self.ontology_type,
            "support_level": self.support_level.value,
            "entity_count": self.entity_count,
            "last_updated": self.last_updated,
        }


class PerformanceMetrics(Base):
    """Performance metrics for operations."""
    
    __tablename__ = "performance_metrics"
    __table_args__ = (
        UniqueConstraint("resource_id", "operation_type", "source_type", "target_type"),
    )
    
    id = Column(Integer, primary_key=True)
    resource_id = Column(Integer, ForeignKey("resource_metadata.id"), nullable=False)
    operation_type = Column(Enum(OperationType), nullable=False)
    source_type = Column(String)
    target_type = Column(String)
    avg_response_time_ms = Column(Float)
    success_rate = Column(Float)  # 0.0 to 1.0
    sample_count = Column(Integer, default=0)
    last_updated = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Relationships
    resource = relationship("ResourceMetadata", back_populates="performance_metrics")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "id": self.id,
            "resource_id": self.resource_id,
            "operation_type": self.operation_type.value,
            "source_type": self.source_type,
            "target_type": self.target_type,
            "avg_response_time_ms": self.avg_response_time_ms,
            "success_rate": self.success_rate,
            "sample_count": self.sample_count,
            "last_updated": self.last_updated,
        }
    
    def update_metrics(self, response_time_ms: float, success: bool) -> None:
        """Update metrics with a new operation result."""
        if self.sample_count is None:
            self.sample_count = 0
        
        if self.avg_response_time_ms is None:
            self.avg_response_time_ms = response_time_ms
        else:
            # Compute weighted average
            total = self.avg_response_time_ms * self.sample_count
            new_avg = (total + response_time_ms) / (self.sample_count + 1)
            self.avg_response_time_ms = new_avg
        
        if self.success_rate is None:
            self.success_rate = 1.0 if success else 0.0
        else:
            # Update success rate
            total_success = self.success_rate * self.sample_count
            new_success = (total_success + (1.0 if success else 0.0)) / (self.sample_count + 1)
            self.success_rate = new_success
        
        # Increment sample count
        self.sample_count += 1
        
        # Update timestamp
        self.last_updated = datetime.datetime.utcnow()


class OperationLog(Base):
    """Log of mapping operations for analysis."""
    
    __tablename__ = "operation_logs"
    
    id = Column(Integer, primary_key=True)
    resource_id = Column(Integer, ForeignKey("resource_metadata.id"), nullable=False)
    operation_type = Column(Enum(OperationType), nullable=False)
    source_type = Column(String)
    target_type = Column(String)
    query = Column(Text)  # Simplified query representation
    response_time_ms = Column(Integer)
    status = Column(Enum(OperationStatus), nullable=False)
    error_message = Column(Text)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Relationships
    resource = relationship("ResourceMetadata", back_populates="operation_logs")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "id": self.id,
            "resource_id": self.resource_id,
            "operation_type": self.operation_type.value,
            "source_type": self.source_type,
            "target_type": self.target_type,
            "query": self.query,
            "response_time_ms": self.response_time_ms,
            "status": self.status.value,
            "error_message": self.error_message,
            "timestamp": self.timestamp,
        }
