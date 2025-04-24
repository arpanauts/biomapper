"""SQLAlchemy models for the mapping cache database."""

import datetime
import json
from typing import Any, Dict, List, Optional, Union

from sqlalchemy import (
    Boolean, Column, Date, DateTime, Float, ForeignKey, Index, Integer, String, Table, Text, UniqueConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

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
    __table_args__ = (
        UniqueConstraint('source_id', 'source_type', 'target_id', 'target_type', name='uix_mapping'),
        Index('idx_source_lookup', 'source_id', 'source_type'),
        Index('idx_target_lookup', 'target_id', 'target_type'),
        Index('idx_usage_count', 'usage_count', postgresql_using='btree'),
        Index('idx_expiration', 'expires_at')
    )

    # Relationships
    metadata_items = relationship("MappingMetadata", back_populates="mapping", cascade="all, delete-orphan")

    def __repr__(self) -> str:
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


class EntityTypeConfig(Base):
    """Configuration for different entity type pairs."""

    __tablename__ = "entity_type_config"

    source_type = Column(String, primary_key=True)
    target_type = Column(String, primary_key=True)
    ttl_days = Column(Integer, default=365)
    confidence_threshold = Column(Float, default=0.7)

    def __repr__(self) -> str:
        """String representation of the config."""
        return f"<EntityTypeConfig {self.source_type}->{self.target_type}>"


class CacheStats(Base):
    """Cache usage statistics."""

    __tablename__ = "cache_stats"

    stats_date = Column(Date, primary_key=True)
    hits = Column(Integer, default=0)
    misses = Column(Integer, default=0)
    direct_lookups = Column(Integer, default=0)
    derived_lookups = Column(Integer, default=0)
    api_calls = Column(Integer, default=0)
    transitive_derivations = Column(Integer, default=0)

    def __repr__(self) -> str:
        """String representation of the stats."""
        return f"<CacheStats {self.stats_date} hits={self.hits} misses={self.misses}>"


class TransitiveJobLog(Base):
    """Log of transitive relationship building jobs."""

    __tablename__ = "transitive_job_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_date = Column(DateTime, default=datetime.datetime.utcnow)
    mappings_processed = Column(Integer, default=0)
    new_mappings_created = Column(Integer, default=0)
    duration_seconds = Column(Float)
    status = Column(String)

    def __repr__(self) -> str:
        """String representation of the job log."""
        return f"<TransitiveJobLog {self.id} date={self.job_date} status={self.status}>"


class Endpoint(Base):
    """Represents a data source or target endpoint."""
    __tablename__ = "endpoints"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(Text)
    type = Column(String) # e.g., 'database', 'api', 'file'
    connection_details = Column(Text, nullable=True) # Store as JSON string or similar
    # Relationships defined below if needed after other models

class MappingResource(Base):
    """Represents a resource used for mapping between ontologies."""
    __tablename__ = "mapping_resources"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(Text)
    resource_type = Column(String) # e.g., 'api', 'database', 'internal_logic'
    api_endpoint = Column(String) # URL if applicable
    # Relationships defined below if needed

class EndpointRelationship(Base):
    """Defines a relationship between two endpoints."""
    __tablename__ = "endpoint_relationships"

    id = Column(Integer, primary_key=True)
    source_endpoint_id = Column(Integer, ForeignKey("endpoints.id"), nullable=False)
    target_endpoint_id = Column(Integer, ForeignKey("endpoints.id"), nullable=False)
    description = Column(Text)
    # Relationships
    source_endpoint = relationship("Endpoint", foreign_keys=[source_endpoint_id])
    target_endpoint = relationship("Endpoint", foreign_keys=[target_endpoint_id])

class OntologyPreference(Base):
    """Specifies preferred ontologies for a relationship or endpoint."""
    __tablename__ = "ontology_preferences"

    id = Column(Integer, primary_key=True)
    relationship_id = Column(Integer, ForeignKey("endpoint_relationships.id"), nullable=True)
    endpoint_id = Column(Integer, ForeignKey("endpoints.id"), nullable=True) # For default endpoint ontology
    ontology_name = Column(String, nullable=False)
    priority = Column(Integer, default=0) # Lower number means higher priority
    # Relationships
    endpoint_relationship = relationship("EndpointRelationship")
    endpoint = relationship("Endpoint")

class MappingPath(Base):
    """Defines a sequence of steps to map between two ontologies."""
    __tablename__ = "mapping_paths"

    id = Column(Integer, primary_key=True)
    source_type = Column(String, nullable=False)
    target_type = Column(String, nullable=False)
    path_steps = Column(Text, nullable=False) # JSON containing step details
    performance_score = Column(Float, nullable=True)
    success_rate = Column(Float, nullable=True)
    usage_count = Column(Integer, default=0)
    last_used = Column(DateTime)
    last_discovered = Column(DateTime)

    @property
    def steps(self) -> List[Dict[str, Any]]:
        """Get the path steps as a list of dictionaries."""
        if not self.path_steps:
            return []
        try:
            return json.loads(self.path_steps)
        except json.JSONDecodeError:
            # Handle potential malformed JSON, perhaps log an error
            return []

    @steps.setter
    def steps(self, steps_list: List[Dict[str, Any]]) -> None:
        """Set the path steps from a list of dictionaries."""
        self.path_steps = json.dumps(steps_list) if steps_list else '[]'

    def __repr__(self) -> str:
        return f"<MappingPath {self.id}: {self.source_type} -> {self.target_type}>"
