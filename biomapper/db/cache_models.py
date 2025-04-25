"""SQLAlchemy models for the mapping_cache.db managed by Alembic."""

import datetime
import json
import enum
from typing import List, Dict, Any, Optional

from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Float,
    Boolean,
    Text,
    ForeignKey,
    UniqueConstraint,
    Index,
    JSON,
    Enum
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base

# Create a new Base for cache models, independent of metamapper.db models
Base = declarative_base()

class EntityMapping(Base):
    """Entity mapping model for bidirectional mappings between ontologies."""

    __tablename__ = "entity_mappings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_id = Column(String, nullable=False)
    source_type = Column(String, nullable=False)
    target_id = Column(String, nullable=False)
    target_type = Column(String, nullable=False)
    confidence = Column(Float)
    mapping_source = Column(String)  # api, spoke, rag, ramp, etc.
    is_derived = Column(Boolean, default=False)
    derivation_path = Column(Text)  # JSON array of mapping IDs
    last_updated = Column(DateTime, default=datetime.datetime.utcnow)
    usage_count = Column(Integer, default=1)
    expires_at = Column(DateTime)

    # Bidirectional uniqueness constraint
    # Note: Removed postgresql_using='btree' from idx_usage_count for SQLite compatibility
    __table_args__ = (
        UniqueConstraint('source_id', 'source_type', 'target_id', 'target_type', name='uix_mapping'),
        Index('idx_source_lookup', 'source_id', 'source_type'),
        Index('idx_target_lookup', 'target_id', 'target_type'),
        Index('idx_usage_count', 'usage_count'), 
        Index('idx_expiration', 'expires_at')
    )

    # Relationships
    metadata_items = relationship("MappingMetadata", back_populates="mapping", cascade="all, delete-orphan")

    def __repr__(self):
        """String representation of the mapping."""
        return f"<EntityMapping {self.source_type}:{self.source_id} -> {self.target_type}:{self.target_id}>"

    @property
    def derivation_path_list(self) -> List[int]:
        """Get the derivation path as a list of mapping IDs."""
        if not self.derivation_path:
            return []
        return json.loads(self.derivation_path)

    @derivation_path_list.setter
    def derivation_path_list(self, path: List[int]) -> None:
        """Set the derivation path from a list of mapping IDs."""
        self.derivation_path = json.dumps(path) if path else None

    def to_dict(self) -> Dict[str, Any]:
        """Convert the mapping to a dictionary."""
        return {
            "id": self.id,
            "source_id": self.source_id,
            "source_type": self.source_type,
            "target_id": self.target_id,
            "target_type": self.target_type,
            "confidence": self.confidence,
            "mapping_source": self.mapping_source,
            "is_derived": self.is_derived,
            "derivation_path": self.derivation_path_list,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
            "usage_count": self.usage_count,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "metadata": {item.key: item.value for item in self.metadata_items}
        }

class MappingMetadata(Base):
    """Metadata associated with entity mappings."""

    __tablename__ = "mapping_metadata"

    mapping_id = Column(Integer, ForeignKey("entity_mappings.id", ondelete="CASCADE"), primary_key=True)
    key = Column(String, primary_key=True)
    value = Column(Text)

    # Relationship
    mapping = relationship("EntityMapping", back_populates="metadata_items")

    def __repr__(self) -> str:
        """String representation of the metadata."""
        return f"<MappingMetadata {self.mapping_id}:{self.key}={self.value}>"

# --- New Cache Models --- #

class EntityMappingProvenance(Base):
    """Links an EntityMapping result to the configuration path that generated it."""
    __tablename__ = "entity_mapping_provenance"
    id = Column(Integer, primary_key=True)
    entity_mapping_id = Column(Integer, ForeignKey("entity_mappings.id", ondelete="CASCADE"), nullable=False, index=True)

    # Link back to the configuration in metamapper.db by ID
    # Assumes RelationshipMappingPath IDs are stable.
    relationship_mapping_path_id = Column(Integer, nullable=False, index=True)

    execution_timestamp = Column(DateTime(timezone=True), server_default=func.now())
    executor_version = Column(String, nullable=True) # Optional: Git commit hash or app version

    # Relationship back to the specific mapping result
    entity_mapping = relationship("EntityMapping") #, back_populates="provenance") # Need to add provenance relation to EntityMapping if needed

    def __repr__(self):
        return f"<EntityMappingProvenance mapping_id={self.entity_mapping_id} path_id={self.relationship_mapping_path_id}>"

class PathExecutionStatus(enum.Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"
    TIMED_OUT = "timed_out"

class PathExecutionLog(Base):
    """Logs details about the execution attempt of a specific mapping path for a source entity."""
    __tablename__ = "path_execution_logs"

    id = Column(Integer, primary_key=True)
    # Link back to the configuration path attempted
    relationship_mapping_path_id = Column(Integer, nullable=False, index=True)
    source_entity_id = Column(String, nullable=False, index=True)
    source_entity_type = Column(String, nullable=False, index=True)
    start_time = Column(DateTime(timezone=True), nullable=False, default=func.now())
    end_time = Column(DateTime(timezone=True), nullable=True)
    duration_ms = Column(Integer, nullable=True)
    status = Column(Enum(PathExecutionStatus), nullable=False)
    # Optional: Store input/output details or error messages as JSON
    # input_details = Column(JSON, nullable=True)
    # output_details = Column(JSON, nullable=True)
    log_messages = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)

    # Index for querying logs by source entity
    __table_args__ = (Index("idx_log_source_entity", "source_entity_id", "source_entity_type"),)

    def __repr__(self):
        return f"<PathExecutionLog path_id={self.relationship_mapping_path_id} source={self.source_entity_type}:{self.source_entity_id} status={self.status}>"

# Placeholders for potential future models
class MappingPathHistory(Base):
    """(Placeholder) Tracks historical performance/usage of MappingPaths from metamapper.db."""
    __tablename__ = "mapping_path_history"
    id = Column(Integer, primary_key=True)
    # TBD - Define columns based on desired tracking (e.g., mapping_path_id, date, success_rate, avg_latency)
    pass

class PerformanceMetric(Base):
    """(Placeholder) Stores aggregated performance metrics for mapping resources or paths."""
    __tablename__ = "performance_metrics"
    id = Column(Integer, primary_key=True)
    # TBD - Define columns based on desired metrics (e.g., resource_id, metric_name, value, timestamp)
    pass
