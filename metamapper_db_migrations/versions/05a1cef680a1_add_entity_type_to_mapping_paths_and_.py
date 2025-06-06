"""add_entity_type_to_mapping_paths_and_composite_unique_constraint

Revision ID: 05a1cef680a1
Revises: 6d519cfd7460
Create Date: 2025-06-05 05:09:13.576427

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '05a1cef680a1'
down_revision = '6d519cfd7460'
branch_labels = None
depends_on = None


def upgrade():
    """Add entity_type column and composite unique constraint.
    
    For SQLite, we need to recreate the table to add the NOT NULL column
    and change the unique constraint.
    """
    # Check if entity_type column already exists (in case initial migration already added it)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('mapping_paths')]
    
    if 'entity_type' in columns:
        # Column already exists, just ensure the constraint is correct
        # This might happen if the initial migration already included entity_type
        return
    
    # Step 1: Create a new table with the updated schema
    op.create_table(
        'mapping_paths_new',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('source_type', sa.String(), nullable=False),
        sa.Column('target_type', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('entity_type', sa.String(), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('priority', sa.Integer(), default=0),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('performance_score', sa.Float()),
        sa.Column('success_rate', sa.Float()),
        sa.Column('last_used', sa.DateTime()),
        sa.Column('last_discovered', sa.DateTime()),
        sa.Column('relationship_id', sa.Integer(), sa.ForeignKey('endpoint_relationships.id')),
        sa.UniqueConstraint('name', 'entity_type', name='uq_mapping_path_name_entity_type')
    )
    
    # Step 2: Copy data from old table to new table
    # Use 'protein' as default entity_type for existing records
    op.execute("""
        INSERT INTO mapping_paths_new (
            id, source_type, target_type, name, entity_type, description,
            priority, is_active, performance_score, success_rate,
            last_used, last_discovered, relationship_id
        )
        SELECT 
            id, source_type, target_type, name, 'protein', description,
            priority, is_active, performance_score, success_rate,
            last_used, last_discovered, relationship_id
        FROM mapping_paths
    """)
    
    # Step 3: Drop the old table
    op.drop_table('mapping_paths')
    
    # Step 4: Rename the new table
    op.rename_table('mapping_paths_new', 'mapping_paths')


def downgrade():
    """Remove entity_type column and restore original unique constraint.
    
    For SQLite, we need to recreate the table to remove the column
    and change the unique constraint back.
    """
    # Step 1: Create a table with the original schema
    op.create_table(
        'mapping_paths_old',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('source_type', sa.String(), nullable=False),
        sa.Column('target_type', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False, unique=True),
        sa.Column('description', sa.Text()),
        sa.Column('priority', sa.Integer(), default=0),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('performance_score', sa.Float()),
        sa.Column('success_rate', sa.Float()),
        sa.Column('last_used', sa.DateTime()),
        sa.Column('last_discovered', sa.DateTime()),
        sa.Column('relationship_id', sa.Integer(), sa.ForeignKey('endpoint_relationships.id'))
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