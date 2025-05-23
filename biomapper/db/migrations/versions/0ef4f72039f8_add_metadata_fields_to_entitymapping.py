"""Add metadata fields to EntityMapping

Revision ID: 0ef4f72039f8
Revises: 57ffe7f9bdab
Create Date: 2025-04-30 17:22:58.912170

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0ef4f72039f8"
down_revision = "57ffe7f9bdab"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table("entity_mappings", schema=None) as batch_op:
        batch_op.add_column(sa.Column("confidence_score", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("mapping_path_details", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("hop_count", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("mapping_direction", sa.String(), nullable=True))

    with op.batch_alter_table("path_execution_logs", schema=None) as batch_op:
        batch_op.alter_column(
            "source_entity_id", existing_type=sa.VARCHAR(), nullable=True
        )

    with op.batch_alter_table("path_log_mapping_associations", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_path_log_mapping_associations_input_identifier"),
            ["input_identifier"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_path_log_mapping_associations_log_id"),
            ["log_id"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_path_log_mapping_associations_output_identifier"),
            ["output_identifier"],
            unique=False,
        )

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table("path_log_mapping_associations", schema=None) as batch_op:
        batch_op.drop_index(
            batch_op.f("ix_path_log_mapping_associations_output_identifier")
        )
        batch_op.drop_index(batch_op.f("ix_path_log_mapping_associations_log_id"))
        batch_op.drop_index(
            batch_op.f("ix_path_log_mapping_associations_input_identifier")
        )

    with op.batch_alter_table("path_execution_logs", schema=None) as batch_op:
        batch_op.alter_column(
            "source_entity_id", existing_type=sa.VARCHAR(), nullable=False
        )

    with op.batch_alter_table("entity_mappings", schema=None) as batch_op:
        batch_op.drop_column("mapping_direction")
        batch_op.drop_column("hop_count")
        batch_op.drop_column("mapping_path_details")
        batch_op.drop_column("confidence_score")

    # ### end Alembic commands ###
