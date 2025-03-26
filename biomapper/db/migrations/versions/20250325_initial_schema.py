"""Initial schema for SQLite mapping cache.

Revision ID: 01_initial_schema
Create Date: 2025-03-25

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector


# revision identifiers, used by Alembic.
revision = '01_initial_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """Create initial schema."""
    # Only create tables if they don't exist
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    tables = inspector.get_table_names()
    
    # Entity Mappings table
    if 'entity_mappings' not in tables:
        op.create_table(
            'entity_mappings',
            sa.Column('id', sa.Integer, primary_key=True),
            sa.Column('source_id', sa.String, nullable=False),
            sa.Column('source_type', sa.String, nullable=False),
            sa.Column('target_id', sa.String, nullable=False),
            sa.Column('target_type', sa.String, nullable=False),
            sa.Column('confidence', sa.Float, nullable=False),
            sa.Column('mapping_source', sa.String, nullable=False),
            sa.Column('is_derived', sa.Boolean, default=False),
            sa.Column('derivation_path', sa.String, nullable=True),
            sa.Column('last_updated', sa.DateTime, nullable=False),
            sa.Column('expires_at', sa.DateTime, nullable=True),
        )
        
        # Index for faster lookups
        op.create_index(
            'idx_entity_mappings_source',
            'entity_mappings',
            ['source_id', 'source_type']
        )
        op.create_index(
            'idx_entity_mappings_target',
            'entity_mappings',
            ['target_id', 'target_type']
        )
        op.create_index(
            'idx_entity_mappings_bidirectional',
            'entity_mappings',
            ['source_id', 'source_type', 'target_type']
        )
        op.create_index(
            'idx_entity_mappings_expiration',
            'entity_mappings',
            ['expires_at']
        )
    
    # Mapping Metadata table
    if 'mapping_metadata' not in tables:
        op.create_table(
            'mapping_metadata',
            sa.Column('id', sa.Integer, primary_key=True),
            sa.Column('mapping_id', sa.Integer, nullable=False),
            sa.Column('key', sa.String, nullable=False),
            sa.Column('value', sa.String, nullable=False),
            sa.ForeignKeyConstraint(['mapping_id'], ['entity_mappings.id'], ondelete='CASCADE'),
        )
        
        op.create_index(
            'idx_mapping_metadata_mapping_id',
            'mapping_metadata',
            ['mapping_id']
        )
    
    # Entity Type Configuration table
    if 'entity_type_config' not in tables:
        op.create_table(
            'entity_type_config',
            sa.Column('id', sa.Integer, primary_key=True),
            sa.Column('entity_type', sa.String, nullable=False, unique=True),
            sa.Column('ttl_days', sa.Integer, nullable=True),
            sa.Column('priority', sa.Integer, nullable=True),
            sa.Column('description', sa.String, nullable=True),
        )
    
    # Cache Statistics table
    if 'cache_stats' not in tables:
        op.create_table(
            'cache_stats',
            sa.Column('id', sa.Integer, primary_key=True),
            sa.Column('date', sa.Date, nullable=False, unique=True),
            sa.Column('hits', sa.Integer, default=0),
            sa.Column('misses', sa.Integer, default=0),
            sa.Column('hit_ratio', sa.Float, nullable=True),
            sa.Column('direct_lookups', sa.Integer, default=0),
            sa.Column('derived_lookups', sa.Integer, default=0),
            sa.Column('api_calls', sa.Integer, default=0),
            sa.Column('transitive_derivations', sa.Integer, default=0),
        )
    
    # Transitive Job Log table
    if 'transitive_job_log' not in tables:
        op.create_table(
            'transitive_job_log',
            sa.Column('id', sa.Integer, primary_key=True),
            sa.Column('job_id', sa.String, nullable=False),
            sa.Column('start_time', sa.DateTime, nullable=False),
            sa.Column('end_time', sa.DateTime, nullable=True),
            sa.Column('status', sa.String, nullable=False),
            sa.Column('mappings_created', sa.Integer, default=0),
            sa.Column('error_message', sa.String, nullable=True),
            sa.Column('parameters', sa.String, nullable=True),  # JSON string of parameters
        )


def downgrade():
    """Revert schema changes."""
    # Drop tables in reverse order to respect foreign key constraints
    op.drop_table('transitive_job_log')
    op.drop_table('cache_stats')
    op.drop_table('entity_type_config')
    op.drop_table('mapping_metadata')
    op.drop_table('entity_mappings')
