"""add_is_required_to_mapping_strategy_steps

Revision ID: 8c18fa5c32a9
Revises: f94a26d3b5c8
Create Date: 2025-06-05 03:30:12.452300

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8c18fa5c32a9'
down_revision = 'f94a26d3b5c8'
branch_labels = None
depends_on = None


def upgrade():
    # Add is_required column to mapping_strategy_steps table
    op.add_column('mapping_strategy_steps', 
        sa.Column('is_required', sa.Boolean(), nullable=False, server_default=sa.true())
    )


def downgrade():
    # Remove is_required column from mapping_strategy_steps table
    op.drop_column('mapping_strategy_steps', 'is_required')
