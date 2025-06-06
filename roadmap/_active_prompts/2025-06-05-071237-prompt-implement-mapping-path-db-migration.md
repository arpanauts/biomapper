# Prompt: Implement Alembic Migration for `MappingPath` `entity_type` and Composite Unique Constraint

**Objective:** Populate the empty Alembic migration file `05a1cef680a1_add_entity_type_to_mapping_paths_and_.py` with the correct operations to update the `mapping_paths` table schema. This is critical to resolve the widespread `UNIQUE constraint failed: mapping_paths.name, mapping_paths.entity_type` errors in integration tests.

**Context:**
Feedback `2025-06-05-070219-feedback-comprehensive-integration-test-analysis.md` revealed that the migration file `biomapper/alembic/versions/metamapper/05a1cef680a1_add_entity_type_to_mapping_paths_and_.py` is empty. The `MappingPath` model in `biomapper/db/models.py` defines an `entity_type` column and a composite `UniqueConstraint('name', 'entity_type', name='uq_mapping_paths_name_entity_type')`, but these changes have not been translated into an executable Alembic migration script.

**Key Tasks:**

1.  **Locate Migration File:**
    *   The target file is `biomapper/alembic/versions/metamapper/05a1cef680a1_add_entity_type_to_mapping_paths_and_.py`.
    *   Confirm its `down_revision` and `branch_labels` are correctly set if this information is available or inferable (typically, `down_revision` points to the previous migration in the `metamapper` branch).

2.  **Implement `upgrade()` function:**
    *   **Add `entity_type` column:** Add a new `entity_type` column to the `mapping_paths` table. It should be a `String` type and `nullable=False`. Consider a `server_default` if appropriate for existing rows, though for SQLite, this might be complex during an `ALTER TABLE ADD COLUMN` if not all existing rows can satisfy `NOT NULL` immediately without a default. A common strategy for SQLite is to allow nulls initially, populate, then alter to not null, or recreate.
    *   **Drop Old Unique Constraint (If Necessary):** If there's an existing unique constraint solely on the `name` column of `mapping_paths` from a previous schema state, it must be dropped before the new composite unique constraint can be added. Identify its name if it exists.
    *   **Create Composite Unique Constraint:** Add the composite unique constraint `uq_mapping_paths_name_entity_type` on the `(name, entity_type)` columns.
    *   **SQLite Considerations:** Alembic operations on SQLite for constraints and adding NOT NULL columns can be tricky. You will likely need to use Alembic's batch mode operations (`op.batch_alter_table`) which handles the common pattern for SQLite: create a new table with the desired schema, copy data, drop the old table, and rename the new table.
        Example structure for batch operations:
        ```python
        with op.batch_alter_table('mapping_paths', schema=None) as batch_op:
            batch_op.add_column(sa.Column('entity_type', sa.String(), nullable=True)) # Add as nullable first
            # If populating entity_type for existing rows: batch_op.execute('UPDATE mapping_paths SET entity_type = ... WHERE ...')
            # Then, if making it not-nullable (requires table recreation by batch_op for SQLite):
            # batch_op.alter_column('entity_type', existing_type=sa.String(), nullable=False)
            
            # If dropping an old constraint by name:
            # batch_op.drop_constraint('old_constraint_name', type_='unique')
            
            batch_op.create_unique_constraint('uq_mapping_paths_name_entity_type', ['name', 'entity_type'])
        ```
        If adding `entity_type` as `nullable=False` from the start, ensure existing rows (if any in a dev DB) won't cause issues or provide a default during the data copy phase of table recreation.

3.  **Implement `downgrade()` function:**
    *   This function should reverse the operations in `upgrade()`.
    *   Drop the composite unique constraint `uq_mapping_paths_name_entity_type`.
    *   Re-add the old unique constraint on `name` (if it was dropped in `upgrade()`).
    *   Drop the `entity_type` column.
    *   Again, use `op.batch_alter_table` for SQLite compatibility.

4.  **Test the Migration:**
    *   After populating the migration script, apply it to a test database:
        *   `poetry run alembic -c biomapper/alembic/alembic.ini -x db_path=sqlite:///./test_metamapper.db upgrade head` (ensure `test_metamapper.db` is clean or a temporary DB for this test).
    *   Inspect the schema of `test_metamapper.db` using a SQLite browser or CLI to confirm the `entity_type` column and the composite unique constraint are present and correctly defined.
    *   Test the downgrade: `poetry run alembic -c biomapper/alembic/alembic.ini -x db_path=sqlite:///./test_metamapper.db downgrade -1` (or to the revision before this one).
    *   Inspect the schema again to confirm it has reverted.

5.  **Verify with Integration Tests (Subset):**
    *   After successfully applying the `upgrade` to your development/test database used by pytest:
    *   Run `poetry run pytest tests/integration/test_yaml_strategy_execution.py -k test_basic_linear_strategy` (or a few key tests from this file).
    *   Confirm that the `UNIQUE constraint failed: mapping_paths.name, mapping_paths.entity_type` error is **resolved** for these tests.

**Deliverables:**

*   The fully populated Alembic migration script: `biomapper/alembic/versions/metamapper/05a1cef680a1_add_entity_type_to_mapping_paths_and_.py`.
*   A clear explanation of the Alembic operations used, especially how SQLite limitations were handled.
*   Confirmation (e.g., pytest console output snippet) that at least one test from `test_yaml_strategy_execution.py` now passes without the unique constraint error after the migration is applied.

**Environment:**

*   Ensure all dependencies are installed using Poetry (`poetry install`).
*   Alembic commands should use the project's `alembic.ini`.
