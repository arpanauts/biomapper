"""initial_metamapper_schema

Revision ID: 6d519cfd7460
Revises: 
Create Date: 2025-06-05 05:15:01.892850

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6d519cfd7460'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema.
    
    This migration:
    1. Adds the entity_type column to mapping_paths table
    2. Removes the existing unique constraint on the name column 
    3. Creates a new composite unique constraint on (name, entity_type)
    
    For SQLite, we completely recreate the table to ensure proper constraint handling.
    """
    # Step 1: Create a temporary table with the new schema
    op.create_table(
        'mapping_paths_new',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('source_type', sa.String(), nullable=False),
        sa.Column('target_type', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('entity_type', sa.String(), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('priority', sa.Integer()),
        sa.Column('is_active', sa.Boolean()),
        sa.Column('performance_score', sa.Float()),
        sa.Column('success_rate', sa.Float()),
        sa.Column('last_used', sa.DateTime()),
        sa.Column('last_discovered', sa.DateTime()),
        sa.Column('relationship_id', sa.Integer()),
        sa.UniqueConstraint('name', 'entity_type', name='uq_mapping_path_name_entity_type')
    )
    
    # Step 2: Copy data from old table to new table, adding default entity_type
    op.execute("""
        INSERT INTO mapping_paths_new (
            id, source_type, target_type, name, entity_type, description, 
            priority, is_active, performance_score, success_rate, 
            last_used, last_discovered, relationship_id
        )
        SELECT 
            id, source_type, target_type, name, 'default_entity_type', description,
            priority, is_active, performance_score, success_rate,
            last_used, last_discovered, relationship_id
        FROM mapping_paths
    """)
    
    # Step 3: Drop the old table
    op.drop_table('mapping_paths')
    
    # Step 4: Rename the new table
    op.rename_table('mapping_paths_new', 'mapping_paths')

    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema.
    
    This reverses the migration by:
    1. Dropping the composite unique constraint on (name, entity_type)
    2. Re-creating the unique constraint on the name column
    3. Dropping the entity_type column
    
    For SQLite, we completely recreate the table to restore the original schema.
    """
    # Step 1: Create a temporary table with the original schema
    op.create_table(
        'mapping_paths_old',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('source_type', sa.String(), nullable=False),
        sa.Column('target_type', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False, unique=True),
        sa.Column('description', sa.Text()),
        sa.Column('priority', sa.Integer()),
        sa.Column('is_active', sa.Boolean()),
        sa.Column('performance_score', sa.Float()),
        sa.Column('success_rate', sa.Float()),
        sa.Column('last_used', sa.DateTime()),
        sa.Column('last_discovered', sa.DateTime()),
        sa.Column('relationship_id', sa.Integer())
    )
    
    # Step 2: Copy data from current table to old table, dropping entity_type
    op.execute("""
        INSERT INTO mapping_paths_old (
            id, source_type, target_type, name, description, 
            priority, is_active, performance_score, success_rate, 
            last_used, last_discovered, relationship_id
        )
        SELECT 
            id, source_type, target_type, name, description,
            priority, is_active, performance_score, success_rate,
            last_used, last_discovered, relationship_id
        FROM mapping_paths
    """)
    
    # Step 3: Drop the current table
    op.drop_table('mapping_paths')
    
    # Step 4: Rename the old table
    op.rename_table('mapping_paths_old', 'mapping_paths')

    # ### end Alembic commands ###
