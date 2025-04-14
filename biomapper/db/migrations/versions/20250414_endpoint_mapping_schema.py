"""Endpoint-mapping architecture schema.

Revision ID: 02_endpoint_mapping_schema
Create Date: 2025-04-14

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector


# revision identifiers, used by Alembic.
revision = '02_endpoint_mapping_schema'
down_revision = '01_initial_schema'
branch_labels = None
depends_on = None


def upgrade():
    """Create endpoint-mapping architecture schema."""
    # Only create tables if they don't exist
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    tables = inspector.get_table_names()
    
    # Endpoints table - defines actual data sources (not mapping tools)
    if 'endpoints' not in tables:
        op.create_table(
            'endpoints',
            sa.Column('endpoint_id', sa.Integer, primary_key=True),
            sa.Column('name', sa.String, nullable=False, unique=True),
            sa.Column('description', sa.String, nullable=True),
            sa.Column('endpoint_type', sa.String, nullable=False),  # e.g., "database", "file", "api", "graph"
            sa.Column('connection_info', sa.String, nullable=True),  # JSON with connection details
            sa.Column('created_at', sa.DateTime, server_default=sa.func.current_timestamp()),
            sa.Column('last_updated', sa.DateTime, nullable=True),
        )
        
        # Index for faster lookups
        op.create_index(
            'idx_endpoints_name',
            'endpoints',
            ['name']
        )
    
    # Mapping Resources table - defines mapping tools/services (not data endpoints)
    if 'mapping_resources' not in tables:
        op.create_table(
            'mapping_resources',
            sa.Column('resource_id', sa.Integer, primary_key=True),
            sa.Column('name', sa.String, nullable=False, unique=True),
            sa.Column('resource_type', sa.String, nullable=False),  # e.g., "api", "database", "local"
            sa.Column('connection_info', sa.String, nullable=True),  # JSON with connection details
            sa.Column('priority', sa.Integer, nullable=True),
            sa.Column('created_at', sa.DateTime, server_default=sa.func.current_timestamp()),
            sa.Column('last_updated', sa.DateTime, nullable=True),
        )
        
        # Index for faster lookups
        op.create_index(
            'idx_mapping_resources_name',
            'mapping_resources',
            ['name']
        )
    
    # Endpoint Relationships table - defines relationships between endpoints
    if 'endpoint_relationships' not in tables:
        op.create_table(
            'endpoint_relationships',
            sa.Column('relationship_id', sa.Integer, primary_key=True),
            sa.Column('name', sa.String, nullable=False),
            sa.Column('description', sa.String, nullable=True),
            sa.Column('created_at', sa.DateTime, server_default=sa.func.current_timestamp()),
        )
        
        # Index for faster lookups
        op.create_index(
            'idx_endpoint_relationships_name',
            'endpoint_relationships',
            ['name']
        )
    
    # Endpoint Relationship Members table - maps endpoints to relationships
    if 'endpoint_relationship_members' not in tables:
        op.create_table(
            'endpoint_relationship_members',
            sa.Column('relationship_id', sa.Integer, nullable=False),
            sa.Column('endpoint_id', sa.Integer, nullable=False),
            sa.Column('role', sa.String, nullable=False),  # e.g., "source", "target", "intermediate"
            sa.Column('priority', sa.Integer, nullable=True),
            sa.ForeignKeyConstraint(['relationship_id'], ['endpoint_relationships.relationship_id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['endpoint_id'], ['endpoints.endpoint_id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('relationship_id', 'endpoint_id'),
        )
        
        # Index for faster lookups
        op.create_index(
            'idx_endpoint_relationship_members_endpoint',
            'endpoint_relationship_members',
            ['endpoint_id']
        )
    
    # Endpoint Ontology Preferences table - defines preferred ontology types for endpoints
    if 'endpoint_ontology_preferences' not in tables:
        op.create_table(
            'endpoint_ontology_preferences',
            sa.Column('endpoint_id', sa.Integer, nullable=False),
            sa.Column('ontology_type', sa.String, nullable=False),
            sa.Column('preference_level', sa.Integer, nullable=False),
            sa.ForeignKeyConstraint(['endpoint_id'], ['endpoints.endpoint_id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('endpoint_id', 'ontology_type'),
        )
        
        # Index for faster lookups
        op.create_index(
            'idx_endpoint_ontology_preferences_endpoint',
            'endpoint_ontology_preferences',
            ['endpoint_id']
        )
    
    # Ontology Coverage table - maps which ontologies each mapping resource supports
    if 'ontology_coverage' not in tables:
        op.create_table(
            'ontology_coverage',
            sa.Column('resource_id', sa.Integer, nullable=False),
            sa.Column('source_type', sa.String, nullable=False),
            sa.Column('target_type', sa.String, nullable=False),
            sa.Column('support_level', sa.String, nullable=False),  # e.g., "full", "partial"
            sa.ForeignKeyConstraint(['resource_id'], ['mapping_resources.resource_id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('resource_id', 'source_type', 'target_type'),
        )
        
        # Index for faster lookups
        op.create_index(
            'idx_ontology_coverage_resource',
            'ontology_coverage',
            ['resource_id']
        )
        op.create_index(
            'idx_ontology_coverage_types',
            'ontology_coverage',
            ['source_type', 'target_type']
        )
    
    # Performance Metrics table - tracks success rates and response times for mapping resources
    if 'performance_metrics' not in tables:
        op.create_table(
            'performance_metrics',
            sa.Column('metric_id', sa.Integer, primary_key=True),
            sa.Column('resource_id', sa.Integer, nullable=False),
            sa.Column('source_type', sa.String, nullable=False),
            sa.Column('target_type', sa.String, nullable=False),
            sa.Column('success_count', sa.Integer, server_default='0'),
            sa.Column('failure_count', sa.Integer, server_default='0'),
            sa.Column('avg_response_time', sa.Float, nullable=True),
            sa.Column('last_updated', sa.DateTime, nullable=True),
            sa.ForeignKeyConstraint(['resource_id'], ['mapping_resources.resource_id'], ondelete='CASCADE'),
        )
        
        # Index for faster lookups
        op.create_index(
            'idx_performance_metrics_resource',
            'performance_metrics',
            ['resource_id']
        )
        op.create_index(
            'idx_performance_metrics_types',
            'performance_metrics',
            ['source_type', 'target_type']
        )
    
    # Endpoint Property Configs table - defines how to extract specific properties from endpoints
    if 'endpoint_property_configs' not in tables:
        op.create_table(
            'endpoint_property_configs',
            sa.Column('config_id', sa.Integer, primary_key=True),
            sa.Column('endpoint_id', sa.Integer, nullable=False),
            sa.Column('ontology_type', sa.String, nullable=False),
            sa.Column('property_name', sa.String, nullable=False),
            sa.Column('extraction_method', sa.String, nullable=False),  # e.g., "column", "query", "path"
            sa.Column('extraction_pattern', sa.String, nullable=False),  # JSON with extraction details
            sa.Column('transform_method', sa.String, nullable=True),
            sa.ForeignKeyConstraint(['endpoint_id'], ['endpoints.endpoint_id'], ondelete='CASCADE'),
            sa.UniqueConstraint('endpoint_id', 'ontology_type', 'property_name'),
        )
        
        # Index for faster lookups
        op.create_index(
            'idx_endpoint_property_configs_endpoint',
            'endpoint_property_configs',
            ['endpoint_id']
        )
        op.create_index(
            'idx_endpoint_property_configs_ontology',
            'endpoint_property_configs',
            ['ontology_type']
        )
    
    # Mapping Cache table - stores results of mapping operations
    if 'mapping_cache' not in tables:
        op.create_table(
            'mapping_cache',
            sa.Column('mapping_id', sa.Integer, primary_key=True),
            sa.Column('source_id', sa.String, nullable=False),
            sa.Column('source_type', sa.String, nullable=False),
            sa.Column('target_id', sa.String, nullable=False),
            sa.Column('target_type', sa.String, nullable=False),
            sa.Column('confidence', sa.Float, nullable=False),
            sa.Column('mapping_path', sa.String, nullable=True),  # JSON describing the path taken
            sa.Column('resource_id', sa.Integer, nullable=True),  # Which resource performed this mapping
            sa.Column('created_at', sa.DateTime, server_default=sa.func.current_timestamp()),
            sa.ForeignKeyConstraint(['resource_id'], ['mapping_resources.resource_id'], ondelete='SET NULL'),
        )
        
        # Index for faster lookups
        op.create_index(
            'idx_mapping_cache_source',
            'mapping_cache',
            ['source_id', 'source_type']
        )
        op.create_index(
            'idx_mapping_cache_target',
            'mapping_cache',
            ['target_id', 'target_type']
        )
        op.create_index(
            'idx_mapping_cache_lookup',
            'mapping_cache',
            ['source_id', 'source_type', 'target_type']
        )
    
    # Relationship Mappings table - links mapping cache entries to endpoint relationships
    if 'relationship_mappings' not in tables:
        op.create_table(
            'relationship_mappings',
            sa.Column('relationship_id', sa.Integer, nullable=False),
            sa.Column('mapping_id', sa.Integer, nullable=False),
            sa.ForeignKeyConstraint(['relationship_id'], ['endpoint_relationships.relationship_id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['mapping_id'], ['mapping_cache.mapping_id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('relationship_id', 'mapping_id'),
        )
        
        # Index for faster lookups
        op.create_index(
            'idx_relationship_mappings_relationship',
            'relationship_mappings',
            ['relationship_id']
        )
    
    # Mapping Paths table - stores discovered mapping paths between ontology types
    if 'mapping_paths' not in tables:
        op.create_table(
            'mapping_paths',
            sa.Column('path_id', sa.Integer, primary_key=True),
            sa.Column('source_type', sa.String, nullable=False),
            sa.Column('target_type', sa.String, nullable=False),
            sa.Column('path_steps', sa.String, nullable=False),  # JSON array of steps
            sa.Column('confidence', sa.Float, nullable=False),
            sa.Column('usage_count', sa.Integer, server_default='0'),
            sa.Column('last_used', sa.DateTime, nullable=True),
            sa.Column('discovered_date', sa.DateTime, server_default=sa.func.current_timestamp()),
        )
        
        # Index for faster lookups
        op.create_index(
            'idx_mapping_paths_lookup',
            'mapping_paths',
            ['source_type', 'target_type']
        )


def downgrade():
    """Revert schema changes."""
    # Drop tables in reverse order to respect foreign key constraints
    op.drop_table('mapping_paths')
    op.drop_table('relationship_mappings')
    op.drop_table('mapping_cache')
    op.drop_table('endpoint_property_configs')
    op.drop_table('performance_metrics')
    op.drop_table('ontology_coverage')
    op.drop_table('endpoint_ontology_preferences')
    op.drop_table('endpoint_relationship_members')
    op.drop_table('endpoint_relationships')
    op.drop_table('mapping_resources')
    op.drop_table('endpoints')
