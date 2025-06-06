"""add_entity_type_to_mapping_paths_and_composite_unique_constraint

Revision ID: 05a1cef680a1
Revises: 8c18fa5c32a9
Create Date: 2025-06-05 05:09:13.576427

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '05a1cef680a1'
down_revision = '8c18fa5c32a9'
branch_labels = None
depends_on = None


def upgrade():
    # Use batch mode for SQLite compatibility
    with op.batch_alter_table('mapping_paths', schema=None) as batch_op:
        # Add entity_type column as nullable first
        batch_op.add_column(sa.Column('entity_type', sa.String(), nullable=True))
        
        # Set a default value for existing rows
        # Since this is for mapping paths, we'll use 'protein' as a reasonable default
        # This can be adjusted based on the actual data
        batch_op.execute("UPDATE mapping_paths SET entity_type = 'protein' WHERE entity_type IS NULL")
        
        # Now make the column NOT NULL (this will trigger table recreation in SQLite)
        batch_op.alter_column('entity_type', 
                            existing_type=sa.String(), 
                            nullable=False)
        
        # Drop any existing unique constraint on just 'name' if it exists
        # Note: SQLite doesn't support dropping constraints, but batch mode handles this
        # by recreating the table
        try:
            batch_op.drop_constraint('uq_mapping_paths_name', type_='unique')
        except:
            # If the constraint doesn't exist, that's fine
            pass
        
        # Create the new composite unique constraint
        batch_op.create_unique_constraint('uq_mapping_path_name_entity_type', 
                                        ['name', 'entity_type'])


def downgrade():
    # Use batch mode for SQLite compatibility
    with op.batch_alter_table('mapping_paths', schema=None) as batch_op:
        # Drop the composite unique constraint
        batch_op.drop_constraint('uq_mapping_path_name_entity_type', type_='unique')
        
        # Recreate the old unique constraint on just 'name' if it existed
        # This is optional - only do this if we know it existed before
        # batch_op.create_unique_constraint('uq_mapping_paths_name', ['name'])
        
        # Drop the entity_type column
        batch_op.drop_column('entity_type')
