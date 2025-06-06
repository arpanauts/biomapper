# Task: Implement `is_required` field for `MappingStrategyStep`

**Source Prompt Reference:** This task is defined by the prompt: `/home/ubuntu/biomapper/roadmap/_active_prompts/2025-06-05-054845-prompt-implement-is-required-field-mappingstrategystep.md`

## 1. Task Objective
Enhance the `MappingStrategyStep` model by adding an `is_required` boolean field. This field will control whether a failure in this step causes the entire mapping strategy to fail or allows it to continue. This involves updating the database model, creating an Alembic migration for `metamapper.db`, modifying database population scripts, updating the `MappingExecutor` (primarily `execute_yaml_strategy`), and adding/updating relevant tests.

## 2. Prerequisites
- [ ] Biomapper project checked out to the latest version.
- [ ] Poetry environment set up and dependencies installed (`poetry install`).
- [ ] Alembic infrastructure for `metamapper.db` is functional (established by migration `6d519cfd7460`).
- [ ] Familiarity with SQLAlchemy models, Alembic migrations, and `MappingExecutor` logic.
- [ ] Access to relevant files: `/home/ubuntu/biomapper/biomapper/db/models.py`, `/home/ubuntu/biomapper/scripts/populate_metamapper_db.py`, `/home/ubuntu/biomapper/biomapper/core/mapping_executor.py`, `/home/ubuntu/biomapper/metamapper_db_migrations/`.

## 3. Context from Previous Attempts (if applicable)
- N/A. This is a new feature implementation.
- This task was previously identified (MEMORY[b8239b50-f7c4-401f-924e-982c402a28ae]) but not yet actioned.

## 4. Task Decomposition
1.  **Update `MappingStrategyStep` Model:**
    *   In `/home/ubuntu/biomapper/biomapper/db/models.py`:
        *   Add a new field `is_required: Column[bool]` to the `MappingStrategyStep` model.
        *   Set `default=True` and `nullable=False` for this new field.
2.  **Create Alembic Migration:**
    *   Generate a new Alembic revision for the `metamapper_db_migrations` environment: `poetry run alembic revision -m add_is_required_to_mapping_strategy_step` (run from `/home/ubuntu/biomapper/metamapper_db_migrations/` or with appropriate `--config` and `x-arg` for path).
    *   Implement the `upgrade()` function to add the `is_required` column to the `mapping_strategy_steps` table (defaulting to `True` for existing rows).
    *   Implement the `downgrade()` function to remove the `is_required` column.
    *   Test the migration locally: `upgrade head`, `downgrade -1`, `upgrade head`.
3.  **Update Database Population Script:**
    *   In `/home/ubuntu/biomapper/scripts/populate_metamapper_db.py`:
        *   Modify the `populate_mapping_strategy_steps` function (or equivalent) to accept and set the `is_required` field when creating `MappingStrategyStep` instances.
        *   Update any example strategy definitions or test data generation to include this new field. Consider making some steps optional (`is_required=False`) in test data for comprehensive testing.
4.  **Modify `MappingExecutor`:**
    *   In `/home/ubuntu/biomapper/biomapper/core/mapping_executor.py`:
        *   Focus on the `execute_yaml_strategy` method (and by extension, the `StrategyAction` execution flow).
        *   When a `StrategyAction` (or the step itself) encounters an error or returns an empty result set:
            *   Check the `is_required` flag of the current `MappingStrategyStep`.
            *   If `is_required` is `True`, the strategy should fail as it currently does (e.g., raise an exception or propagate the error).
            *   If `is_required` is `False`, the error should be logged (e.g., as a warning), and the strategy should proceed to the next step, potentially with the input identifiers from *before* the optional step was attempted.
        *   Consider how to handle the `current_identifiers` if an optional step fails or produces no results. Should they revert to the state before the optional step, or pass on the (empty) results? This needs a clear design decision; a common approach is to use the identifiers from *before* the optional step.
5.  **Update/Add Unit and Integration Tests:**
    *   Add unit tests for `MappingExecutor` to verify the new logic for `is_required=True` vs `is_required=False` steps.
        *   Test scenarios where an optional step fails but the strategy continues.
        *   Test scenarios where a required step fails and the strategy stops.
    *   Update integration tests or add new ones that use YAML strategies with optional steps to ensure end-to-end functionality.
    *   Ensure `scripts/test_optional_steps.py` (if still relevant or adaptable) correctly tests this new DB-driven `is_required` flag, or create a new test script for YAML strategies.

## 5. Implementation Requirements
- **Input files/data:** As listed in Prerequisites and Task Decomposition.
- **Expected outputs:**
    *   Modified Python files as described.
    *   A new Alembic migration script in `/home/ubuntu/biomapper/metamapper_db_migrations/versions/`.
    *   Updated/new test files.
- **Code standards:** Adhere to PEP 8, type hinting, existing project conventions.
- **Validation requirements:** All tests (unit and integration) must pass. Manual verification of strategy execution with optional steps.

## 6. Error Recovery Instructions
- **Alembic Migration Generation/Execution Fails:**
    *   Consult Alembic documentation. Ensure correct `env.py` configuration for `metamapper_db_migrations`.
    *   For SQLite, complex operations like adding a non-nullable column without a server default might require batch operations or table recreation patterns if simple `op.add_column` fails (though `server_default` in SQLAlchemy should translate to SQL default).
- **Logic Errors in `MappingExecutor`:**
    *   Use detailed logging and debuggers. Pay close attention to the flow of `current_identifiers` when optional steps are processed.
- **Test Failures:**
    *   Analyze test failures to pinpoint issues in model, migration, or executor logic.

## 7. Success Criteria and Validation
Task is complete when:
- [ ] `MappingStrategyStep` model in `models.py` includes the `is_required` field.
- [ ] A new, functional Alembic migration for `metamapper.db` adds the `is_required` column.
- [ ] `populate_metamapper_db.py` can populate the `is_required` field.
- [ ] `MappingExecutor.execute_yaml_strategy` correctly handles the `is_required` flag:
    -   Fails the strategy if a required step fails.
    -   Logs a warning and continues if an optional step fails, using appropriate identifiers for the next step.
- [ ] All existing tests pass, and new tests covering the `is_required` functionality also pass.
- [ ] The changes are well-documented with comments and docstrings where necessary.

## 8. Feedback Requirements
Create a detailed Markdown feedback file at:
`[PROJECT_ROOT]/roadmap/_active_prompts/feedback/YYYY-MM-DD-HHMMSS-feedback-implement-is-required-field.md`

**Mandatory Feedback Sections:**
- **Execution Status:** [COMPLETE_SUCCESS | PARTIAL_SUCCESS | FAILED_WITH_RECOVERY_OPTIONS | FAILED_NEEDS_ESCALATION]
- **Completed Subtasks:** (checklist from Task Decomposition)
- **Link to Alembic Migration File:** (relative path from project root)
- **Key Design Decisions Made:** (e.g., how `current_identifiers` are handled after a failed optional step)
- **Summary of Changes to `MappingExecutor`:**
- **Test Results Summary:** (unit and integration, including new tests)
- **Issues Encountered:** (and how they were resolved)
- **Next Action Recommendation:**
- **Confidence Assessment:**
- **Environment Changes:** (e.g., new migration file created)
