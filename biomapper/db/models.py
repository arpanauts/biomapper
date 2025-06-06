"""SQLAlchemy models for the metamapper configuration database (metamapper.db)."""

import datetime
import json
from typing import Optional

from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    Boolean,
    Text,
    Float,
    UniqueConstraint,
    JSON,
)
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class EntityTypeConfig(Base):
    """Configuration for different entity type pairs."""

    __tablename__ = "entity_type_config"

    source_type = Column(String, primary_key=True)
    target_type = Column(String, primary_key=True)
    ttl_days = Column(Integer, default=365)
    confidence_threshold = Column(Float, default=0.7)  # Changed to Float

    def __repr__(self) -> str:
        """String representation of the config."""
        return f"<EntityTypeConfig {self.source_type}->{self.target_type}>"


class CacheStats(Base):
    """Cache usage statistics."""

    __tablename__ = "cache_stats"

    stats_date = Column(DateTime, primary_key=True)
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
    type = Column(String)  # e.g., 'database', 'api', 'file'
    primary_property_name = Column(String, nullable=True)  # Name of the primary identifier property
    connection_details = Column(Text, nullable=True)  # Store as JSON string or similar
    relationship_memberships = relationship("EndpointRelationshipMember", back_populates="endpoint", cascade="all, delete-orphan")
    # Relationships defined below if needed after other models


class MappingResource(Base):
    """Represents a resource used for mapping between ontologies."""

    __tablename__ = "mapping_resources"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(Text)
    resource_type = Column(String)  # e.g., 'api', 'database', 'internal_logic'
    api_endpoint = Column(String)  # URL if applicable
    base_url = Column(String)  # For API-based resources
    config_template = Column(Text)  # Store potential config keys/structure

    # --- New fields for enhanced architecture ---
    input_ontology_term = Column(String)  # e.g., 'UniProtKB', 'Gene_Name', 'UMLS_CUI'
    output_ontology_term = Column(String)  # e.g., 'UniProtKB', 'Gene_Name', 'UMLS_CUI'
    client_class_path = Column(
        String, nullable=True
    )  # Path to the client class, e.g., 'biomapper.mapping.clients.UniProtNameClient'
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
    members = relationship("EndpointRelationshipMember", back_populates="parent_relationship", cascade="all, delete-orphan")



class EndpointRelationshipMember(Base):
    __tablename__ = "endpoint_relationship_members"

    relationship_id = Column(Integer, ForeignKey("endpoint_relationships.id", ondelete="CASCADE"), primary_key=True)
    endpoint_id = Column(Integer, ForeignKey("endpoints.id", ondelete="CASCADE"), primary_key=True)
    role = Column(String, nullable=True)  # e.g., 'source_identifier', 'target_identifier'

    # Relationships
    parent_relationship = relationship("EndpointRelationship", back_populates="members")
    endpoint = relationship("Endpoint", back_populates="relationship_memberships")

    def __repr__(self) -> str:
        return f"<EndpointRelationshipMember r_id={self.relationship_id} e_id={self.endpoint_id} role='{self.role}'>"


class OntologyPreference(Base):
    """Specifies preferred ontologies for a relationship or endpoint."""

    __tablename__ = "ontology_preferences"

    id = Column(Integer, primary_key=True)
    relationship_id = Column(
        Integer, ForeignKey("endpoint_relationships.id"), nullable=True
    )
    endpoint_id = Column(
        Integer, ForeignKey("endpoints.id"), nullable=True
    )  # For default endpoint ontology
    ontology_name = Column(String, nullable=False)
    priority = Column(Integer, default=0)  # Lower number means higher priority
    # Relationships
    endpoint_relationship = relationship("EndpointRelationship")
    endpoint = relationship("Endpoint")


class MappingPath(Base):
    """Defines a sequence of steps to map between two ontologies."""

    __tablename__ = "mapping_paths"

    id = Column(Integer, primary_key=True)
    source_type = Column(String, nullable=False)  # e.g., 'Gene_Name'
    target_type = Column(String, nullable=False)  # e.g., 'UniProtKB_AC'
    name = Column(String, nullable=False)  # User-friendly name
    entity_type = Column(String, nullable=False) # e.g., 'protein', 'gene', 'test_optional'
    description = Column(Text)
    priority = Column(Integer, default=0)  # Lower number means higher priority
    is_active = Column(Boolean, default=True)
    performance_score = Column(
        Float, nullable=True
    )  # Metric combining speed, success rate, etc.
    success_rate = Column(Float, nullable=True)
    last_used = Column(DateTime)
    last_discovered = Column(DateTime)

    # Foreign key to EndpointRelationship
    relationship_id = Column(Integer, ForeignKey("endpoint_relationships.id"), nullable=True) # Made nullable=True for now, can be False if always required

    # Relationship to EndpointRelationship (optional, for easier access from MappingPath object)
    # endpoint_relationship = relationship("EndpointRelationship", back_populates="mapping_paths") # Requires back_populates on EndpointRelationship

    # Add relationship to steps
    steps = relationship(
        "MappingPathStep",
        back_populates="mapping_path",
        order_by="MappingPathStep.step_order",
        cascade="all, delete-orphan",
    )

    __table_args__ = (UniqueConstraint('name', 'entity_type', name='uq_mapping_path_name_entity_type'),)

    def __repr__(self):
        return f"<MappingPath id={self.id} name='{self.name}' entity_type='{self.entity_type}' {self.source_type}->{self.target_type}>"


class MappingPathStep(Base):
    """Represents a single step within a MappingPath."""

    __tablename__ = "mapping_path_steps"

    id = Column(Integer, primary_key=True)
    mapping_path_id = Column(Integer, ForeignKey("mapping_paths.id"), nullable=False)
    mapping_resource_id = Column(
        Integer, ForeignKey("mapping_resources.id"), nullable=False
    )
    step_order = Column(Integer, nullable=False)
    # Optional: Store specific configuration overrides for this step
    config_override = Column(JSON, nullable=True)
    description = Column(Text, nullable=True)  # Optional description for this step

    # Relationships
    mapping_path = relationship("MappingPath", back_populates="steps")
    mapping_resource = relationship("MappingResource")

    __table_args__ = (
        UniqueConstraint("mapping_path_id", "step_order", name="uix_path_step_order"),
    )

    def __repr__(self) -> str:
        return f"<MappingPathStep id={self.id} path={self.mapping_path_id} order={self.step_order} resource={self.mapping_resource_id}>"


class PropertyExtractionConfig(Base):
    """Configuration for extracting properties from mapping resources."""

    __tablename__ = "property_extraction_configs"

    id = Column(Integer, primary_key=True)
    resource_id = Column(Integer, ForeignKey("mapping_resources.id"), nullable=True)
    ontology_type = Column(String, nullable=False)
    property_name = Column(
        String, nullable=False
    )  # e.g., 'pref_name', 'synonym', 'description'
    extraction_method = Column(
        String, nullable=False
    )  # e.g., 'json_path', 'regex', 'xpath'
    extraction_pattern = Column(String, nullable=False)  # The actual pattern/path
    result_type = Column(String)  # Expected data type, e.g., 'string', 'list'
    transform_function = Column(
        String, nullable=True
    )  # Optional function to apply post-extraction
    priority = Column(
        Integer, default=0
    )  # For selecting among multiple patterns for the same property
    is_active = Column(Boolean, default=True)
    # entity_type = Column(String, default='metabolite') # Consider if needed, matches backup schema
    # ns_prefix = Column(String) # Consider if needed, matches backup schema
    # ns_uri = Column(String) # Consider if needed, matches backup schema
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    resource = relationship("MappingResource")

    __table_args__ = (
        UniqueConstraint(
            "resource_id", "ontology_type", "property_name", name="uix_prop_extract"
        ),
    )

    def __repr__(self) -> str:
        return f"<PropertyExtractionConfig id={self.id} resource={self.resource_id} ontology={self.ontology_type} property={self.property_name}>"


class EndpointPropertyConfig(Base):
    """Links an Endpoint and a specific property name to a PropertyExtractionConfig."""

    __tablename__ = "endpoint_property_configs"

    id = Column(Integer, primary_key=True)
    endpoint_id = Column(Integer, ForeignKey("endpoints.id"), nullable=False)
    property_name = Column(String(100), nullable=False)
    ontology_type = Column(String, nullable=True)  # The ontology type for this property
    is_primary_identifier = Column(Boolean, default=False, nullable=False)
    description = Column(String, nullable=True)
    data_type = Column(String, nullable=True)      # E.g., 'string', 'integer', 'boolean'
    property_extraction_config_id = Column(
        Integer, ForeignKey("property_extraction_configs.id"), nullable=False
    )

    endpoint = relationship("Endpoint")
    property_extraction_config = relationship("PropertyExtractionConfig")

    __table_args__ = (
        UniqueConstraint("endpoint_id", "property_name", name="uix_endpoint_prop_name"),
    )

    def __repr__(self) -> str:
        return f"<EndpointPropertyConfig id={self.id} endpoint={self.endpoint_id} property={self.property_name} config_id={self.property_extraction_config_id}>"


class OntologyCoverage(Base):
    """Defines which mapping resources support which ontology transitions."""

    __tablename__ = "ontology_coverage"

    resource_id = Column(Integer, ForeignKey("mapping_resources.id"), primary_key=True)
    source_type = Column(String, primary_key=True)
    target_type = Column(String, primary_key=True)
    support_level = Column(
        String, nullable=False
    )  # e.g., 'direct', 'api_lookup', 'inferred'

    resource = relationship("MappingResource")

    def __repr__(self) -> str:
        return f"<OntologyCoverage resource={self.resource_id} {self.source_type}->{self.target_type} ({self.support_level})>"


class RelationshipMappingPath(Base):
    """Links EndpointRelationships to specific MappingPaths for given ontology types."""

    __tablename__ = "relationship_mapping_paths"

    id = Column(Integer, primary_key=True)
    relationship_id = Column(
        Integer, ForeignKey("endpoint_relationships.id"), nullable=False
    )
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

    __table_args__ = (
        UniqueConstraint(
            "relationship_id",
            "source_ontology",
            "target_ontology",
            name="uix_rel_map_path",
        ),
    )

    def __repr__(self) -> str:
        return f"<RelationshipMappingPath id={self.id} rel={self.relationship_id} {self.source_ontology}->{self.target_ontology} via path={self.ontology_path_id}>"


class CompositePatternConfig(Base):
    """Configuration for handling composite identifiers.
    
    This table stores patterns and rules for identifying and processing
    composite identifiers that contain multiple distinct entities within
    a single string.
    """
    __tablename__ = 'composite_pattern_config'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, unique=True)
    description = Column(String, nullable=True)
    
    # Ontology type this pattern applies to (e.g., GENE_NAME, UNIPROTKB_AC)
    ontology_type = Column(String, nullable=False)
    
    # Regular expression pattern to identify composite identifiers
    pattern = Column(String, nullable=False)
    
    # Delimiters to split composite identifiers (comma-separated)
    delimiters = Column(String, nullable=False)
    
    # Strategy for mapping a composite identifier: first_match, all_matches, or combined
    mapping_strategy = Column(String, nullable=False)
    
    # When True, components are processed as the same ontology type
    keep_component_type = Column(Boolean, nullable=False, default=True)
    
    # If not keeping the same type, what ontology type to use for components
    component_ontology_type = Column(String, nullable=True)
    
    # Priority (lower number = higher priority)
    priority = Column(Integer, nullable=False, default=1)
    
    def __repr__(self) -> str:
        return f"<CompositePatternConfig id={self.id} name={self.name} type={self.ontology_type}>"


class CompositeProcessingStep(Base):
    """Steps for processing composite identifiers.
    
    This table defines the sequence of operations to apply when processing
    a composite identifier, such as splitting, cleaning, or transforming components.
    """
    __tablename__ = 'composite_processing_step'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    pattern_id = Column(Integer, ForeignKey('composite_pattern_config.id'), nullable=False)
    pattern = relationship("CompositePatternConfig", backref="processing_steps")
    
    # Step type: split, clean, transform, etc.
    step_type = Column(String, nullable=False)
    
    # Parameters for the step (JSON string)
    parameters = Column(String, nullable=True)
    
    # Order in the processing pipeline
    order = Column(Integer, nullable=False)
    
    def __repr__(self) -> str:
        return f"<CompositeProcessingStep id={self.id} pattern_id={self.pattern_id} type={self.step_type}>"


class Ontology(Base):
    """Represents a standardized ontology for identifier types."""
    
    __tablename__ = "ontologies"
    
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)  # e.g., "UNIPROTKB_AC_ONTOLOGY"
    description = Column(Text)
    identifier_prefix = Column(String, nullable=True)  # e.g., "UniProtKB:"
    namespace_uri = Column(String, nullable=True)  # URL/URI defining the ontology namespace
    version = Column(String, nullable=True)  # Version of the ontology
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationship to properties
    properties = relationship("Property", back_populates="ontology")
    
    def __repr__(self) -> str:
        return f"<Ontology id={self.id} name={self.name}>"


class Property(Base):
    """Defines a standardized property name linked to an ontology."""
    
    __tablename__ = "properties"
    
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)  # e.g., "UNIPROTKB_AC", "GENE_NAME", "ARIVALE_PROTEIN_ID"
    description = Column(Text)
    ontology_id = Column(Integer, ForeignKey("ontologies.id"), nullable=False)
    is_primary = Column(Boolean, default=False)  # Whether this is the primary identifier in the ontology
    data_type = Column(String, nullable=True)  # e.g., "string", "integer"
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    ontology = relationship("Ontology", back_populates="properties")
    
    __table_args__ = (
        UniqueConstraint("name", "ontology_id", name="uix_property_name_ontology"),
    )
    
    def __repr__(self) -> str:
        return f"<Property id={self.id} name={self.name} ontology_id={self.ontology_id}>"


class MappingSessionLog(Base):
    """Logs information about mapping sessions for tracking and debugging."""
    
    __tablename__ = "mapping_session_logs"
    
    id = Column(Integer, primary_key=True)
    source_endpoint = Column(String, nullable=False)
    target_endpoint = Column(String, nullable=False)
    source_property = Column(String, nullable=False)
    target_property = Column(String, nullable=False)
    identifier_count = Column(Integer, nullable=False)
    successful_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)
    validation_count = Column(Integer, default=0)  # Count of bidirectionally validated mappings
    start_time = Column(DateTime, default=func.now())
    end_time = Column(DateTime, nullable=True)
    runtime_seconds = Column(Float, nullable=True)
    cache_hit_count = Column(Integer, default=0)
    cache_miss_count = Column(Integer, default=0)
    use_cache = Column(Boolean, default=True)
    try_reverse_mapping = Column(Boolean, default=False)
    validation_enabled = Column(Boolean, default=False)
    error_message = Column(Text, nullable=True)
    status = Column(String, default="in_progress")  # in_progress, completed, failed
    additional_info = Column(JSON, nullable=True)  # Any additional session details
    
    def __repr__(self) -> str:
        return f"<MappingSessionLog id={self.id} {self.source_endpoint}->{self.target_endpoint} status={self.status}>"


class MappingStrategy(Base):
    """Defines YAML-configured multi-step mapping strategies."""
    
    __tablename__ = "mapping_strategies"
    
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)  # e.g., "UKBB_TO_HPA_PROTEIN_PIPELINE"
    description = Column(Text)
    entity_type = Column(String, nullable=False)  # e.g., "protein", "metabolite"
    default_source_ontology_type = Column(String, nullable=True)  # Default input ontology type
    default_target_ontology_type = Column(String, nullable=True)  # Default output ontology type
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationship to steps
    steps = relationship(
        "MappingStrategyStep",
        back_populates="strategy",
        order_by="MappingStrategyStep.step_order",
        cascade="all, delete-orphan",
    )
    
    def __repr__(self) -> str:
        return f"<MappingStrategy id={self.id} name={self.name} entity={self.entity_type}>"


class MappingStrategyStep(Base):
    """Represents a single step within a MappingStrategy."""
    
    __tablename__ = "mapping_strategy_steps"
    
    id = Column(Integer, primary_key=True)
    strategy_id = Column(Integer, ForeignKey("mapping_strategies.id"), nullable=False)
    step_id = Column(String, nullable=False)  # e.g., "S1_UKBB_NATIVE_TO_UNIPROT"
    step_order = Column(Integer, nullable=False)  # Numeric order for execution
    description = Column(Text, nullable=True)
    action_type = Column(String, nullable=False)  # e.g., "CONVERT_IDENTIFIERS_LOCAL"
    action_parameters = Column(JSON, nullable=True)  # JSON dict of parameters for the action
    is_required = Column(Boolean, nullable=False, default=True, server_default="true")  # Whether this step is required for strategy success
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationship
    strategy = relationship("MappingStrategy", back_populates="steps")
    
    __table_args__ = (
        UniqueConstraint("strategy_id", "step_id", name="uix_strategy_step_id"),
        UniqueConstraint("strategy_id", "step_order", name="uix_strategy_step_order"),
    )
    
    def __repr__(self) -> str:
        return f"<MappingStrategyStep id={self.id} strategy={self.strategy_id} step={self.step_id} order={self.step_order} action={self.action_type}>"
