# Task: Implement `is_required` Field for Mapping Strategy Steps

## 1. Context & Goal:
The `MappingExecutor`'s `execute_strategy` method currently treats all steps in a mapping strategy as mandatory. If a step fails, the entire strategy execution halts. This was a temporary measure because the `MappingStrategyStep` model in `metamapper.db` and the YAML configuration did not yet support an `is_required` flag.

This task is to introduce an `is_required` boolean field to the `MappingStrategyStep` model, update the database population script to handle it, and modify `MappingExecutor` to respect this flag. This will allow strategy designers to define optional steps that, if they fail, do not necessarily halt the entire strategy.

**Relevant Files & Modules:**
*   Database Models: `/home/ubuntu/biomapper/biomapper/db/models.py`
*   Database Population: `/home/ubuntu/biomapper/scripts/populate_metamapper_db.py`
*   Mapping Executor: `/home/ubuntu/biomapper/biomapper/core/mapping_executor.py`
*   Alembic migration environment.
*   Relevant test files (e.g., `/home/ubuntu/biomapper/tests/integration/test_yaml_strategy_execution.py` and potentially unit tests for `MappingExecutor`).

## 2. Detailed Instructions:

### 2.1. Database Model Update:
*   In `/home/ubuntu/biomapper/biomapper/db/models.py`:
    *   Add a new field `is_required: Mapped[bool]` to the `MappingStrategyStep` SQLAlchemy model.
    *   Set a default value of `True` for this field to ensure backward compatibility with existing strategies in the database that won't have this field populated initially.
    *   Ensure the field can be `nullable=False` with a server default if appropriate, or handle the default in application logic.

### 2.2. Database Migration (Alembic):
*   Generate a new Alembic migration script to add the `is_required` column to the `mapping_strategy_steps` table.
    *   Command: `poetry run alembic revision -m "add_is_required_to_mapping_strategy_steps"`
*   Edit the generated migration script:
    *   Implement the `upgrade()` function to add the `is_required` column with `server_default=sa.true()` and `nullable=False`.
    *   Implement the `downgrade()` function to remove the column.
*   Apply the migration: `poetry run alembic upgrade head`.

### 2.3. Update `populate_metamapper_db.py`:
*   **Configuration Validator (`ConfigurationValidator._validate_mapping_strategies`)**:
    *   Modify the validation logic for strategy steps.
    *   The `is_required` field in the YAML for a step should be optional.
    *   If present, it must be a boolean value.
*   **Population Logic (e.g., within `_populate_mapping_strategies_and_steps`)**:
    *   When creating `MappingStrategyStep` instances, read the `is_required` value from the step's YAML definition.
    *   If `is_required` is not present in the YAML for a step, it should default to `True` when populating the database object (this aligns with the model's default).

### 2.4. Update `MappingExecutor.execute_strategy`:
*   In `/home/ubuntu/biomapper/biomapper/core/mapping_executor.py`:
    *   Modify the loop that executes strategy steps.
    *   When a step's action handler indicates a failure (e.g., by returning a result with `status='failed'` or raising a specific exception that the executor catches per step):
        *   Check the `is_required` attribute of the current `MappingStrategyStep` object (loaded from the database).
        *   If `is_required` is `True`, then the strategy execution should halt (as it currently does), and the overall strategy result should reflect this failure.
        *   If `is_required` is `False`, the failure should be logged in the `MappingResultBundle` for that step, but the `MappingExecutor` should proceed to the next step in the strategy. The `current_identifiers` and `current_source_ontology_type` should likely remain unchanged from before the failed optional step.

### 2.5. Update Tests:
*   **Integration Tests (`test_yaml_strategy_execution.py`)**:
    *   Add new test strategies to `test_protein_strategy_config.yaml` (or a similar test config file) that include steps with `is_required: false`.
    *   Create new test cases to verify:
        *   A failing *optional* step allows the strategy to continue.
        *   A failing *required* step halts the strategy.
        *   The `MappingResultBundle` correctly records the outcome of optional failed steps.
*   **Consider Unit Tests**: If `MappingExecutor` has unit tests, add specific tests for the logic handling `is_required`.

## 3. Expected Outcome:
*   The `MappingStrategyStep` model and database schema are updated with an `is_required` field.
*   `populate_metamapper_db.py` correctly parses and stores the `is_required` flag from YAML configurations.
*   `MappingExecutor` correctly handles step failures based on the `is_required` flag, allowing strategies with optional steps to continue execution even if an optional step fails.
*   Tests are updated to verify this new behavior.

## 4. Feedback File:
Create a Markdown feedback file named `YYYY-MM-DD-HHMMSS-feedback-implement-is-required-field.md` in `/home/ubuntu/biomapper/roadmap/_active_prompts/feedback/` documenting:
*   Confirmation of model and schema changes.
*   Details of how `populate_metamapper_db.py` was updated.
*   Explanation of changes to `MappingExecutor` logic.
*   Summary of new/updated tests and their results.
*   Any challenges encountered and how they were resolved.
