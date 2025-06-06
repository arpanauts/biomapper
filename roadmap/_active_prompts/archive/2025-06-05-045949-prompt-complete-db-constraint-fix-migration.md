# Prompt: Complete Database Constraint Fix for MappingPath with Alembic Migration

**Date:** 2025-06-05
**Version:** 1.0
**Project:** Biomapper
**Related Prompts/Feedback:** `2025-06-05-045445-prompt-fix-integration-test-db-constraints.md`, `feedback-cleanup-mapping-executor.md` (re: integration test failures)

## 1. Goal

To finalize the fix for the `UNIQUE constraint failed: mapping_paths.name` error occurring during integration tests. This involves creating, applying, and verifying an Alembic migration script for the schema changes made to the `MappingPath` model in `biomapper/db/models.py`.

**Context:** The `MappingPath` model has been updated to:
- Add an `entity_type: String` column.
- Change the unique constraint on `name` to be a composite unique constraint on `(name, entity_type)`.
The `scripts/populate_metamapper_db.py` script has also been updated to populate this new `entity_type` field.

## 2. Tasks

### 2.1. Generate Alembic Revision

1.  Navigate to the root directory of the `biomapper` project (where `alembic.ini` is located).
2.  Run the Alembic command to generate a new revision file:
    ```bash
    alembic revision -m "add_entity_type_to_mapping_path_and_composite_unique_constraint"
    ```
3.  Locate the newly generated migration script in the `biomapper/alembic/versions/` directory.

### 2.2. Implement the Migration Script

Open the new migration script and implement the `upgrade()` and `downgrade()` functions.

**Key Considerations for Implementation:**

*   **`entity_type` column length:** Choose an appropriate length for the `String` type (e.g., `sa.String(255)`).
*   **`nullable=False` for `entity_type`:** Since test databases are typically created fresh, and `populate_mapping_paths` now provides `entity_name`, the column can be `nullable=False` from the start. If handling existing databases with data, a `server_default` or making it temporarily nullable then backfilling data would be needed, but this is likely not required for the immediate goal of fixing test DBs.
*   **Constraint Naming:** The new composite unique constraint was named `uq_mapping_path_name_entity_type` in `models.py`. Use this name in the migration.
*   **Dropping Old Constraint:** SQLAlchemy's `unique=True` on a column without an explicit name in `__table_args__` results in an auto-generated constraint name. Alembic's autogenerate feature (when run with `--autogenerate` for model diffs) usually handles detecting the change from a `Column(unique=True)` to a `UniqueConstraint` in `__table_args__`. For a manually written migration based on model changes already made:
    *   The `upgrade` function will need to explicitly add the new column and the new composite unique constraint.
    *   It will also need to **drop the old single-column unique constraint on `name`**. If the old constraint was implicitly named, you might need to inspect a database schema generated *before* your `models.py` changes to find its name, or rely on Alembic's batch mode for SQLite if direct dropping by name is problematic.
    *   Alembic's batch operations are often preferred for SQLite to handle its limitations with `ALTER TABLE`.

**`upgrade()` function:**

```python
import sqlalchemy as sa
from alembic import op

def upgrade():
    # For SQLite, use batch mode to handle constraints and column additions
    with op.batch_alter_table('mapping_paths', schema=None) as batch_op:
        batch_op.add_column(sa.Column('entity_type', sa.String(length=255), nullable=False, server_default='DEFAULT_PLACEHOLDER')) # Add server_default initially for safety if any DBs have rows
        
        # Attempt to drop the old unique constraint on 'name'. 
        # The actual name might vary if it was auto-generated. Inspect an old schema if this fails.
        # Common auto-generated names could be 'uq_mapping_paths_name' or based on an index name like 'ix_mapping_paths_name'.
        # If the constraint was unnamed, this step is tricky. For now, assume it might have been named or an index existed.
        try:
            batch_op.drop_constraint('uq_mapping_paths_name', type_='unique') # Replace 'uq_mapping_paths_name' if known
        except Exception as e:
            print(f"Could not drop old unique constraint on name directly, it might not exist or be named differently: {e}")
            # If it was an unnamed unique=True, it might be tied to an index. 
            # Alternatively, SQLite might not allow dropping it easily this way if it's an implicit part of the column def.
            # For test DBs, this might not be an issue as they are rebuilt.

        batch_op.create_unique_constraint('uq_mapping_path_name_entity_type', ['name', 'entity_type'])

    # If server_default was used, alter column to remove it after initial data population (if applicable)
    # For fresh test DBs, this might not be strictly necessary if populated correctly from the start.
    with op.batch_alter_table('mapping_paths', schema=None) as batch_op:
        batch_op.alter_column('entity_type', server_default=None)

```

**`downgrade()` function:**

```python
import sqlalchemy as sa
from alembic import op

def downgrade():
    with op.batch_alter_table('mapping_paths', schema=None) as batch_op:
        batch_op.drop_constraint('uq_mapping_path_name_entity_type', type_='unique')
        
        # Re-create the old unique constraint on 'name'.
        # If the original was an unnamed `unique=True` on the column, this recreates that behavior.
        batch_op.create_unique_constraint('uq_mapping_paths_name', ['name']) # Or whatever the old name was, or let it be auto-named if that's how it was.
        
        batch_op.drop_column('entity_type')
```

*(Self-correction during prompt generation: The `server_default` in `upgrade` is a safety for existing data; for test DBs that are rebuilt, it's less critical. The main challenge is robustly dropping the old `unique=True` constraint if its name isn't known. For test environments, ensuring the test DBs are completely fresh before applying migrations is key.)*

**Revised `upgrade()` for simplicity assuming fresh test DBs (primary goal):**
```python
# In migration script upgrade():
    with op.batch_alter_table('mapping_paths', schema=None) as batch_op:
        batch_op.add_column(sa.Column('entity_type', sa.String(length=255), nullable=False))
        # Assuming the old unique=True on 'name' is implicitly handled by schema definition changes
        # or that fresh DBs won't have the old constraint to begin with if models.py is the source of truth.
        # For robust migration on existing DBs, dropping the old constraint by name is better.
        # If the old constraint was simply `name = Column(String, unique=True, ...)` without explicit __table_args__,
        # and now `name` is `Column(String, nullable=False, ...)` and the unique constraint is in `__table_args__`,
        # Alembic autogenerate would typically handle dropping the old column-defined unique and adding the new table-arg one.
        # Since we are writing manually based on model changes already made:
        # We must ensure the old constraint is GONE before the new one is made if they conflict.
        # The safest is to try to drop it by a commonly auto-generated name or inspect schema.
        # However, if tests always start with a new DB from models, this might not manifest as an error.
        batch_op.create_unique_constraint('uq_mapping_path_name_entity_type', ['name', 'entity_type'])
```
*Final thought for migration script: The most robust way if `autogenerate` wasn't used is to inspect an old DB state for the exact constraint name to drop. If that's not feasible, for test DBs, ensuring they are built from the new model definition might sidestep the issue of dropping an old constraint.* The `models.py` change (removing `unique=True` from `name` column) is key. When a new DB is created from models, it won't have the old constraint. The migration ensures *existing* DBs are updated. For tests, this means the test DB setup needs to correctly apply migrations up to `head`.

### 2.3. Test the Migration

1.  Ensure you have a test database configured that Alembic can target.
2.  Apply the migration:
    ```bash
    alembic upgrade head
    ```
3.  Inspect the database schema (e.g., using a DB browser or SQLAlchemy Inspector) to verify:
    *   The `mapping_paths` table has the new `entity_type` column.
    *   The old unique constraint on `name` alone is gone.
    *   The new composite unique constraint `uq_mapping_path_name_entity_type` exists on `(name, entity_type)`.
4.  Test the downgrade:
    ```bash
    alembic downgrade -1 
    ```
5.  Inspect the schema again to ensure it has reverted correctly.
6.  Upgrade back to head: `alembic upgrade head`.

### 2.4. Verify the Fix

1.  Ensure your test environment is configured to use a database that has the migrations applied (i.e., test fixtures should build the DB and run `alembic upgrade head`).
2.  Run the full suite of integration tests, particularly those that were failing with the `UNIQUE constraint failed: mapping_paths.name` error.
3.  Confirm that these tests now pass.

## 3. Acceptance Criteria

- An Alembic migration script is created that successfully applies the schema changes to `mapping_paths` (adds `entity_type`, creates composite unique constraint `(name, entity_type)`, removes old unique constraint on `name`).
- The migration script's `upgrade()` and `downgrade()` functions work correctly and are reversible.
- After applying the migration, the integration tests that were previously failing due to `UNIQUE constraint failed: mapping_paths.name` now pass.
- The database schema correctly reflects the `MappingPath` model, including the new column and composite unique constraint.

## 4. Deliverables

- The new Alembic migration script file.
- Confirmation that integration tests pass after the migration is applied.

## 5. Potential Challenges

- **Determining the name of the old unique constraint to drop:** If it was auto-generated and not explicitly named, finding the correct name might require inspecting an older version of the database schema.
- **SQLite limitations with ALTER TABLE:** Using `op.batch_alter_table()` is crucial for SQLite, but complex changes can still be tricky. Ensure thorough testing.
- **Test environment setup:** Ensuring the test fixtures correctly initialize the database and apply all migrations up to `head` before tests run.

By completing these steps, the database schema will correctly support the intended uniqueness for mapping paths, scoped by their entity type, resolving the critical integration test failures.
