"""SQLAlchemy models for the metamapper configuration database (metamapper.db)."""

import datetime
from typing import Optional

from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    Boolean,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


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
    def steps(self) -> list:
        """Get the path steps as a list of dictionaries."""
        if not self.path_steps:
            return []
        try:
            return json.loads(self.path_steps)
        except json.JSONDecodeError:
            # Handle potential malformed JSON, perhaps log an error
            return []

    @steps.setter
    def steps(self, steps_list: list) -> None:
        """Set the path steps from a list of dictionaries."""
        self.path_steps = json.dumps(steps_list) if steps_list else '[]'

    def __repr__(self) -> str:
        return f"<MappingPath {self.id}: {self.source_type} -> {self.target_type}>"


class PropertyExtractionConfig(Base):
    """Configuration for extracting properties from mapping resources."""
    __tablename__ = "property_extraction_configs"

    id = Column(Integer, primary_key=True)
    resource_id = Column(Integer, ForeignKey("mapping_resources.id"), nullable=False)
    ontology_type = Column(String, nullable=False)
    property_name = Column(String, nullable=False) # e.g., 'pref_name', 'synonym', 'description'
    extraction_method = Column(String, nullable=False) # e.g., 'json_path', 'regex', 'xpath'
    extraction_pattern = Column(String, nullable=False) # The actual pattern/path
    result_type = Column(String) # Expected data type, e.g., 'string', 'list'
    transform_function = Column(String, nullable=True) # Optional function to apply post-extraction
    priority = Column(Integer, default=0) # For selecting among multiple patterns for the same property
    is_active = Column(Boolean, default=True)
    # entity_type = Column(String, default='metabolite') # Consider if needed, matches backup schema
    # ns_prefix = Column(String) # Consider if needed, matches backup schema
    # ns_uri = Column(String) # Consider if needed, matches backup schema
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    resource = relationship("MappingResource")

    __table_args__ = (UniqueConstraint('resource_id', 'ontology_type', 'property_name', name='uix_prop_extract'),)

    def __repr__(self) -> str:
        return f"<PropertyExtractionConfig id={self.id} resource={self.resource_id} ontology={self.ontology_type} property={self.property_name}>"


class EndpointPropertyConfig(Base):
    """Configuration for extracting properties from endpoints."""
    __tablename__ = "endpoint_property_configs"

    config_id = Column(Integer, primary_key=True)
    endpoint_id = Column(Integer, ForeignKey("endpoints.id"), nullable=False)
    ontology_type = Column(String, nullable=False) # The ontology type *within* the endpoint data
    property_name = Column(String, nullable=False) # The property name to extract
    extraction_method = Column(String, nullable=False) # e.g., 'column_name', 'json_path'
    extraction_pattern = Column(String, nullable=False) # The column name or path
    transform_method = Column(String, nullable=True) # Optional transformation

    endpoint = relationship("Endpoint")

    __table_args__ = (UniqueConstraint('endpoint_id', 'ontology_type', 'property_name', name='uix_endpoint_prop_extract'),)

    def __repr__(self) -> str:
        return f"<EndpointPropertyConfig id={self.config_id} endpoint={self.endpoint_id} ontology={self.ontology_type} property={self.property_name}>"


class OntologyCoverage(Base):
    """Defines which mapping resources support which ontology transitions."""
    __tablename__ = "ontology_coverage"

    resource_id = Column(Integer, ForeignKey("mapping_resources.id"), primary_key=True)
    source_type = Column(String, primary_key=True)
    target_type = Column(String, primary_key=True)
    support_level = Column(String, nullable=False) # e.g., 'direct', 'api_lookup', 'inferred'

    resource = relationship("MappingResource")

    def __repr__(self) -> str:
        return f"<OntologyCoverage resource={self.resource_id} {self.source_type}->{self.target_type} ({self.support_level})>"


class RelationshipMappingPath(Base):
    """Links EndpointRelationships to specific MappingPaths for given ontology types."""
    __tablename__ = "relationship_mapping_paths"

    id = Column(Integer, primary_key=True)
    relationship_id = Column(Integer, ForeignKey("endpoint_relationships.id"), nullable=False)
    source_ontology = Column(String, nullable=False)
    target_ontology = Column(String, nullable=False)
    ontology_path_id = Column(Integer, ForeignKey("mapping_paths.id"), nullable=False)
    performance_score = Column(Float, nullable=True)
    success_rate = Column(Float, default=1.0)
    usage_count = Column(Integer, default=0)
    last_used = Column(DateTime, nullable=True)
    last_discovered = Column(DateTime, default=func.now())

    endpoint_relationship = relationship("EndpointRelationship")
    mapping_path = relationship("MappingPath", foreign_keys=[ontology_path_id])

    __table_args__ = (UniqueConstraint('relationship_id', 'source_ontology', 'target_ontology', name='uix_rel_map_path'),)

    def __repr__(self) -> str:
        return f"<RelationshipMappingPath id={self.id} rel={self.relationship_id} {self.source_ontology}->{self.target_ontology} via path={self.ontology_path_id}>"
