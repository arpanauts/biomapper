# Prompt for Database Administrator AI Agent

**Task Objective:**

Apply the latest auto-generated Alembic migration to the `mapping_cache.db`. This migration will update the `entity_mappings` table to include a new `path_execution_log_id` column, aligning the database schema with recent changes in the application's data models.

**Context:**

The `biomapper` application has been refactored to improve cache management. As part of this effort, the `EntityMapping` SQLAlchemy model in `biomapper/db/cache_models.py` was updated to include a foreign key relationship to the `path_execution_logs` table. An Alembic migration script has already been generated to reflect this change and is ready to be applied.

**Implementation Steps:**

1.  **Navigate to the project's root directory:**
    ```bash
    cd /home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper
    ```

2.  **Apply the database migration:**
    Execute the `alembic upgrade head` command, specifying the correct configuration file for the cache database. This will apply the latest migration script found in `biomapper/db/migrations/versions`.
    ```bash
    alembic -c biomapper/db/migrations/alembic.ini upgrade head
    ```

**Validation Steps:**

1.  **Connect to the SQLite database:**
    Use the `sqlite3` CLI to connect to the cache database. The database file is located at `data/mapping_cache.db`.
    ```bash
    sqlite3 data/mapping_cache.db
    ```

2.  **Verify the schema change:**
    Once inside the SQLite prompt, run the following `PRAGMA` command to inspect the columns of the `entity_mappings` table.
    ```sql
    PRAGMA table_info(entity_mappings);
    ```

3.  **Confirm the new column:**
    Examine the output from the `PRAGMA` command. Confirm that a column named `path_execution_log_id` is present in the table schema.

**Error Recovery:**

*   If the `alembic upgrade` command fails, immediately run `alembic downgrade -1` using the same configuration file to revert the failed migration and leave the database in a stable state.
*   Capture and report the full error message from the failed command for further diagnosis.

**Feedback:**

Please provide a summary of the outcome, confirming whether the migration was applied successfully and the `path_execution_log_id` column was verified. If an error occurred, please include the captured error logs.
