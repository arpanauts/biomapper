"""Add endpoint health monitoring tables

Revision ID: endpoint_health_monitoring
Revises: 20250414_endpoint_mapping_schema
Create Date: 2025-04-18

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic
revision = 'endpoint_health_monitoring'
down_revision = '20250414_endpoint_mapping_schema'
branch_labels = None
depends_on = None


def upgrade():
    # Create endpoint_property_health table
    op.create_table(
        'endpoint_property_health',
        sa.Column('health_id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('endpoint_id', sa.Integer, nullable=False),
        sa.Column('ontology_type', sa.String, nullable=False),
        sa.Column('property_name', sa.String, nullable=False),
        sa.Column('extraction_success_count', sa.Integer, default=0),
        sa.Column('extraction_failure_count', sa.Integer, default=0),
        sa.Column('last_success_time', sa.DateTime),
        sa.Column('last_failure_time', sa.DateTime),
        sa.Column('avg_extraction_time_ms', sa.Float),
        sa.Column('extraction_error_types', sa.Text),  # JSON array of common errors
        sa.Column('sample_size', sa.Integer, default=0),
        sa.Column('last_updated', sa.DateTime, default=sa.func.current_timestamp()),
        
        # Add unique constraint
        sa.UniqueConstraint('endpoint_id', 'ontology_type', 'property_name', name='uix_endpoint_property_health'),
    )
    
    # Add index for faster endpoint lookup
    op.create_index('idx_endpoint_health', 'endpoint_property_health', ['endpoint_id'])
    
    # Add foreign key reference (if endpoints table exists)
    op.create_foreign_key(
        'fk_endpoint_property_health_endpoint',
        'endpoint_property_health', 'endpoints',
        ['endpoint_id'], ['endpoint_id'],
        ondelete='CASCADE'
    )
    
    # Create health_check_logs table
    op.create_table(
        'health_check_logs',
        sa.Column('log_id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('check_time', sa.DateTime, default=sa.func.current_timestamp()),
        sa.Column('endpoints_checked', sa.Integer, default=0),
        sa.Column('configs_checked', sa.Integer, default=0),
        sa.Column('success_count', sa.Integer, default=0),
        sa.Column('failure_count', sa.Integer, default=0),
        sa.Column('duration_ms', sa.Integer),
        sa.Column('status', sa.String),
        sa.Column('details', sa.Text),  # JSON object with additional details
    )
    
    # Add index for faster time-based queries
    op.create_index('idx_health_check_time', 'health_check_logs', ['check_time'])


def downgrade():
    # Drop indexes first
    op.drop_index('idx_endpoint_health', table_name='endpoint_property_health')
    op.drop_index('idx_health_check_time', table_name='health_check_logs')
    
    # Drop foreign keys
    op.drop_constraint('fk_endpoint_property_health_endpoint', 'endpoint_property_health', type_='foreignkey')
    
    # Drop tables
    op.drop_table('endpoint_property_health')
    op.drop_table('health_check_logs')