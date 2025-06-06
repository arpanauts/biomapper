# Prompt: Resolve `UNIQUE constraint failed: mapping_paths.name, mapping_paths.entity_type` in Integration Tests

**Objective:** Investigate and resolve the `UNIQUE constraint failed: mapping_paths.name, mapping_paths.entity_type` error occurring in `tests/integration/test_yaml_strategy_execution.py`. This involves analyzing how `MappingPath` entities are created during test setup and ensuring that duplicate `(name, entity_type)` pairs are not inserted in violation of the composite unique constraint, or re-evaluating the constraint if necessary.

**Context:** This issue was identified in feedback `2025-06-05-060018-feedback-verify-integration-tests.md`. The previous attempt to fix a unique constraint on `mapping_paths.name` by adding `entity_type` and a composite key has shifted the error to this new composite key. The specific error occurs when trying to insert duplicate `(name, entity_type)` combinations like `('gene_to_uniprot', 'test_protein')`.

**Key Tasks:**

1.  **Analyze Test Setup:**
    *   Thoroughly review `tests/integration/test_yaml_strategy_execution.py` and any related fixtures (e.g., in `tests/conftest.py` or `biomapper/testing/fixtures.py`) or data population scripts used by these tests.
    *   Focus on how `MappingPath` instances are created and populated, specifically their `name` and `entity_type` fields, during the setup phase of these tests.

2.  **Identify Root Cause of Duplicates:**
    *   Determine precisely why the test setup is attempting to insert `MappingPath` records with identical `(name, entity_type)` pairs.
    *   Consider if this is due to: 
        *   Loops creating multiple identical paths.
        *   Shared test data across parameterized tests without sufficient variation.
        *   Fixture scopes leading to unintended re-insertion of data.

3.  **Implement Solution (Option A: Modify Test Data/Setup - Preferred if constraint is valid):**
    *   If the composite unique constraint on `(name, entity_type)` is deemed correct and necessary for application integrity:
        *   Modify the test data generation logic or test setup procedures to ensure that unique `(name, entity_type)` combinations are used when creating `MappingPath` entries for the tests.
        *   This might involve techniques like: 
            *   Using unique suffixes/prefixes for names or entity types in test data.
            *   Ensuring test parameterization generates distinct data.
            *   Cleaning up previously inserted conflicting data between test runs or within test setups if applicable (though fresh DBs per test are common).

4.  **Implement Solution (Option B: Re-evaluate/Modify Constraint - If current constraint is too strict):**
    *   If, after investigation, the current composite unique constraint is found to be overly restrictive for valid testing scenarios or conflicts with intended application logic (e.g., the same mapping path name *should* be usable for different underlying relationship_ids even with the same entity_type):
        *   Clearly document the rationale for why the constraint needs modification.
        *   Propose a revised constraint strategy for the `MappingPath` model. This could involve adding another field to the composite key, removing the constraint, or changing its nature.
        *   **If this path is chosen, obtain explicit approval/feedback before proceeding with schema changes.**
        *   If approved, implement the necessary changes to the `MappingPath` model in `biomapper/db/models.py`.
        *   Create a new Alembic migration script to apply these schema changes to the database.
        *   Update `scripts/populate_metamapper_db.py` if the default data population is affected.

5.  **Verification:**
    *   Run `pytest tests/integration/test_yaml_strategy_execution.py` (or the specific failing tests within this file).
    *   Confirm that all `sqlalchemy.exc.IntegrityError: (sqlite3.IntegrityError) UNIQUE constraint failed: mapping_paths.name, mapping_paths.entity_type` errors are resolved.

**Deliverables:**

*   Modified Python files (primarily test files, but potentially model/migration files if Option B is pursued and approved).
*   A new Alembic migration file (only if Option B is pursued and approved).
*   Confirmation (e.g., pytest console output snippet) that the specific unique constraint errors in `test_yaml_strategy_execution.py` are resolved.
*   A clear and concise explanation of:
    *   The root cause of the duplicate `(name, entity_type)` insertions in the tests.
    *   The implemented solution, detailing changes made and justifying the chosen approach (Option A or B).

**Environment:**

*   Ensure all dependencies are installed using Poetry (`poetry install`).
*   Tests should be run using `pytest` from the project root.
