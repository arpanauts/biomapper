"""Add composite identifier handling tables

Revision ID: f82b31c04d37
Revises: 0ef4f72039f8
Create Date: 2025-05-06

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'f82b31c04d37'
down_revision = '0ef4f72039f8'  # Update this to match your latest migration
branch_labels = None
depends_on = None


def upgrade():
    # Create CompositePatternConfig table
    op.create_table(
        'composite_pattern_config',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('ontology_type', sa.String(), nullable=False),
        sa.Column('pattern', sa.String(), nullable=False),
        sa.Column('delimiters', sa.String(), nullable=False),
        sa.Column('mapping_strategy', sa.String(), nullable=False),
        sa.Column('keep_component_type', sa.Boolean(), nullable=False, default=True),
        sa.Column('component_ontology_type', sa.String(), nullable=True),
        sa.Column('priority', sa.Integer(), nullable=False, default=1),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    
    # Create CompositeProcessingStep table
    op.create_table(
        'composite_processing_step',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('pattern_id', sa.Integer(), nullable=False),
        sa.Column('step_type', sa.String(), nullable=False),
        sa.Column('parameters', sa.String(), nullable=True),
        sa.Column('order', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['pattern_id'], ['composite_pattern_config.id'], ),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    # Drop tables in reverse order to avoid foreign key constraints
    op.drop_table('composite_processing_step')
    op.drop_table('composite_pattern_config')
