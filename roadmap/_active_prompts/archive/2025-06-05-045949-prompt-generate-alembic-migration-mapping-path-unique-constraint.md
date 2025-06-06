# Prompt: Generate Alembic Migration for MappingPath Unique Constraint

**Date:** 2025-06-05
**Version:** 1.0
**Project:** Biomapper - YAML Strategy Execution Enhancement
**Goal:** Create and implement an Alembic migration script to apply schema changes to the `mapping_paths` table, resolving the `UNIQUE constraint failed: mapping_paths.name` error in integration tests.

## 1. Background

The `mapping_paths.name` column currently has a `UNIQUE` constraint that applies only to the `name` field. This causes errors when different test configurations (e.g., for different entity types) attempt to define mapping paths with the same name.

Recent changes to `biomapper/db/models.py` have updated the `MappingPath` model to:
1. Add a new `entity_type: String` column.
2. Remove the `unique=True` attribute from the `name` column.
3. Add a composite `UniqueConstraint` on `(name, entity_type)` via `__table_args__`.

Additionally, `scripts/populate_metamapper_db.py` has been updated to populate this new `entity_type` field during data insertion.

This prompt guides the creation of the necessary Alembic migration to reflect these model changes in the database schema.

## 2. Task Description

The primary task is to generate a new Alembic revision and implement its `upgrade()` and `downgrade()` functions to modify the `mapping_paths` table schema.

### 2.1. Generate Alembic Revision

- Navigate to the root directory of the `biomapper` project (where `alembic.ini` is located).
- Run the Alembic command to generate a new revision file. A descriptive message should be used for the revision.
  ```bash
  alembic revision -m "add_entity_type_to_mapping_paths_and_composite_unique_constraint"
  ```

### 2.2. Implement `upgrade()` Function

The `upgrade()` function in the newly generated migration script should perform the following operations on the `mapping_paths` table:

1.  **Add the `entity_type` column:**
    *   Name: `entity_type`
    *   Type: `sa.String()` (or `sa.String(length=...)` if a specific length is desired, though often not strictly enforced by SQLite/PostgreSQL for `String` without length).
    *   Nullable: `False`.
    *   **Important for existing data (if any, though test DBs are fresh):** If this migration were to run on a DB with existing data, you'd need a `server_default` (e.g., `server_default=''`) for non-nullable string columns or make it nullable first, populate, then alter to non-nullable. For fresh test DBs, `nullable=False` from the start is fine.

2.  **Drop the existing unique constraint on the `name` column.**
    *   SQLAlchemy's `unique=True` on a column often auto-generates a constraint name (e.g., `uq_mapping_paths_name`, `ix_mapping_paths_name`, or a provider-specific name). You might need to inspect an existing schema or rely on Alembic's batch mode operations to correctly identify and drop it if it wasn't explicitly named in the model before.
    *   If the constraint was implicitly created, finding its exact name might be tricky. A common pattern for `op.drop_constraint` requires the constraint name.
    *   Alternatively, using `op.alter_column` to set `unique=False` on the `name` column might be an approach if supported directly for removing uniqueness by Alembic for your specific backend, but typically constraints are dropped explicitly.
    *   **Recommended approach for `upgrade`:** If the old constraint name is unknown, you might need to use batch operations for SQLite compatibility if you were to modify the column directly. However, since `unique=True` was on the column definition, Alembic's autogenerate might not pick up the removal of `unique=True` and the addition of `__table_args__` correctly without hints or manual scripting. For this migration, assume you can find the name or that dropping it by column reference is possible (less likely).
    *   **Let's assume the original constraint was implicitly named based on the column.** If `MappingPath.name` was `Column(String, unique=True, name='mapping_path_name_key', nullable=False)`, the constraint name would be `mapping_path_name_key`. If no `name` kwarg was in `unique=True`, it's auto-generated. For this task, we will try to drop it by a conventional name. If that fails during testing, it will need adjustment.

3.  **Create the new composite unique constraint on `(name, entity_type)`:**
    *   Name for the constraint: `uq_mapping_path_name_entity_type` (matching the model).
    *   Columns: `['name', 'entity_type']`.
    *   Table: `mapping_paths`.

**Order of operations in `upgrade()`:**
   a. `op.add_column('mapping_paths', sa.Column('entity_type', sa.String(), nullable=False, server_default='placeholder_entity_type'))`
      *Note: Using `server_default` makes it robust for tables with existing data. For fresh test DBs, it's less critical but good practice. You might remove `server_default` after data backfill in a multi-step migration, or if you are certain no data exists / data will be populated correctly.* For this project, since test DBs are ephemeral, `nullable=False` without `server_default` should be acceptable.
   b. `op.drop_constraint('uq_mapping_paths_name', 'mapping_paths', type_='unique')`
      *This assumes the old constraint was named `uq_mapping_paths_name`. If it was auto-generated differently (e.g. `mapping_paths_name_key`), this name needs to be accurate. If the original model did not have an explicit `UniqueConstraint` in `__table_args__` but just `unique=True` on the column, the name is database-dependent. For SQLite, `unique=True` creates an index that enforces uniqueness. You might need to drop an index: `op.drop_index('ix_mapping_paths_name', table_name='mapping_paths')` if it was an index-based constraint.* **Let's proceed with `drop_constraint` and refine if tests show it's an index.**
   c. `op.create_unique_constraint('uq_mapping_path_name_entity_type', 'mapping_paths', ['name', 'entity_type'])`

### 2.3. Implement `downgrade()` Function

The `downgrade()` function should revert the schema changes made by `upgrade()`:

1.  **Drop the composite unique constraint on `(name, entity_type)`:**
    *   Use `op.drop_constraint('uq_mapping_path_name_entity_type', 'mapping_paths', type_='unique')`.

2.  **Re-create the unique constraint on the `name` column:**
    *   Use `op.create_unique_constraint('uq_mapping_paths_name', 'mapping_paths', ['name'])`. (Or `op.create_index` if it was an index).

3.  **Drop the `entity_type` column:**
    *   Use `op.drop_column('mapping_paths', 'entity_type')`.

## 3. Acceptance Criteria

- A new Alembic migration script is generated in `biomapper/alembic/versions/`.
- The `upgrade()` function correctly adds the `entity_type` column, removes the old unique constraint on `name`, and adds the new composite unique constraint on `(name, entity_type)`.
- The `downgrade()` function correctly reverts these changes.
- After applying the migration (`alembic upgrade head`), the `mapping_paths` table schema in a test database reflects the new structure.
- Integration tests that previously failed with `UNIQUE constraint failed: mapping_paths.name` now pass (assuming the test data uses distinct `(name, entity_type)` pairs where names might have previously clashed).
- The migration script is well-commented, explaining the purpose of each operation.

## 4. Implementation Notes

- Pay close attention to the exact names of constraints, especially when dropping them. If a constraint was not explicitly named in the model, its database-generated name might vary.
- Test the migration thoroughly on a development database (SQLite is fine) by running `alembic upgrade head` and `alembic downgrade -1` multiple times.
- Inspect the schema before and after applying the migration using a DB browser or appropriate SQLAlchemy reflection to confirm changes.
- For SQLite, managing constraints can sometimes be tricky. Alembic's batch mode (`with op.batch_alter_table(...) as batch_op:`) is often recommended for SQLite schema operations, as SQLite has limited `ALTER TABLE` capabilities. This allows Alembic to recreate the table with the new schema and copy data over. Consider if batch mode is needed for dropping the old constraint or adding the new one if direct operations fail.
  Example for batch mode (conceptual for dropping a constraint on a column):
  ```python
  # In upgrade()
  with op.batch_alter_table('mapping_paths', schema=None) as batch_op:
      batch_op.drop_constraint('original_constraint_name_if_known', type_='unique') # or batch_op.alter_column('name', unique=False)
      batch_op.create_unique_constraint('uq_mapping_path_name_entity_type', ['name', 'entity_type'])
  ```
  However, adding a column is usually fine. The main complexity is altering existing constraints.

## 5. Deliverables

- The path to the new, fully implemented Alembic migration script.
- Confirmation that the migration applies and reverts correctly.
- Confirmation that integration tests pass after the migration (or identification of any remaining issues).
