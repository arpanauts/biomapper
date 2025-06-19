"""Add enhancements to MappingSession model

Revision ID: f94a26d3b5c8
Revises: f82b31c04d37
Create Date: 2025-05-07 16:45:00.000000

"""

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = 'f94a26d3b5c8'
down_revision = 'f82b31c04d37'
branch_labels = None
depends_on = None


def upgrade():
    # Update the mapping_sessions table
    op.add_column('mapping_sessions', sa.Column('results_count', sa.Integer(), nullable=True))
    
    # Optional: Add more columns for enhanced metrics
    op.add_column('mapping_sessions', sa.Column('batch_size', sa.Integer(), nullable=True))
    op.add_column('mapping_sessions', sa.Column('max_concurrent_batches', sa.Integer(), nullable=True))
    op.add_column('mapping_sessions', sa.Column('total_execution_time', sa.Float(), nullable=True))
    op.add_column('mapping_sessions', sa.Column('success_rate', sa.Float(), nullable=True))
    
    # Create execution_metrics table for detailed metrics
    op.create_table(
        'execution_metrics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('mapping_session_id', sa.Integer(), nullable=False),
        sa.Column('metric_type', sa.String(length=50), nullable=False),
        sa.Column('metric_name', sa.String(length=100), nullable=False),
        sa.Column('metric_value', sa.Float(), nullable=True),
        sa.Column('string_value', sa.String(length=255), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['mapping_session_id'], ['mapping_sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create index for faster queries
    op.create_index('ix_execution_metrics_mapping_session_id', 'execution_metrics', ['mapping_session_id'], unique=False)
    op.create_index('ix_execution_metrics_metric_type', 'execution_metrics', ['metric_type'], unique=False)


def downgrade():
    # Drop new table
    op.drop_index('ix_execution_metrics_metric_type', table_name='execution_metrics')
    op.drop_index('ix_execution_metrics_mapping_session_id', table_name='execution_metrics')
    op.drop_table('execution_metrics')
    
    # Remove added columns
    op.drop_column('mapping_sessions', 'success_rate')
    op.drop_column('mapping_sessions', 'total_execution_time')
    op.drop_column('mapping_sessions', 'max_concurrent_batches')
    op.drop_column('mapping_sessions', 'batch_size')
    op.drop_column('mapping_sessions', 'results_count')