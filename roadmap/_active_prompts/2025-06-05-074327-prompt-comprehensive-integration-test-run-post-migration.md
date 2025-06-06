# Prompt: Comprehensive Integration Test Run Post-Migration and Initial Fixes

**Objective:** Execute the entire Biomapper integration test suite to establish a new baseline of test health after the successful implementation of the `MappingPath` database migration and fixes to several specific test errors.

**Context:**
Two recent sets of fixes have been applied:
1.  **Database Migration (`05a1cef680a1_...`):** Successfully added `entity_type` to `mapping_paths` and the composite unique constraint `(name, entity_type)`. This resolved the widespread `UNIQUE constraint failed` errors. Feedback: `2025-06-05-073538-feedback-mapping-path-migration-implementation.md`.
2.  **Specific Test Fixes:** Resolved `TypeError` in `test_historical_id_mapping.py`, `async_generator` AttributeError, and `MappingExecutor.close()` AttributeError. Feedback: `2025-06-05-074101-feedback-integration-test-fixes-completed.md`.

**Key Issues to Verify/Identify:**

*   **New Primary Error:** The migration feedback indicated that tests previously failing with unique constraint violations (e.g., in `test_yaml_strategy_execution.py`) now fail with `output_ontology_type is required`. We need to see how widespread this error is.
*   **`test_historical_id_mapping.py`:** These tests were reported to now fail with mock-related issues (e.g., "no_mapping_found"). Confirm current status.
*   **SQLAlchemy Greenlet Errors:** These were observed previously. Determine if they persist, have changed, or were indeed side effects of the resolved database constraint issue.
*   **Overall Test Health:** Get a count of passed, failed, skipped, and errored tests across the entire suite.
*   **`pytest-asyncio` Decorators:** While an import was added, the feedback noted that `@pytest.fixture` might still be used instead of `@pytest_asyncio.fixture` for async fixtures in `conftest.py`. This is a lower priority for this run but keep in mind for general test health.

**Tasks:**

1.  **Ensure Clean Test Environment:**
    *   Verify that the development database (e.g., `metamapper.db` or the one used by pytest) has the latest migration (`05a1cef680a1_...`) applied. If necessary, re-apply:
        ```bash
        # (Ensure DB is clean or backed up if necessary before running downgrade/upgrade cycles)
        # Example: poetry run alembic -c biomapper/alembic/alembic.ini -x db_path=sqlite:///./metamapper.db downgrade base
        poetry run alembic -c biomapper/alembic/alembic.ini -x db_path=sqlite:///./metamapper.db upgrade head
        ```
    *   Ensure all project dependencies are up to date: `poetry install`.

2.  **Execute Full Integration Test Suite:**
    *   Run all tests in the `tests/integration` directory.
    *   Use verbose output and capture the full log.
        ```bash
        poetry run pytest tests/integration -v --log-cli-level=INFO > full_integration_test_run_YYYYMMDD_HHMMSS.log
        ```
        (Replace `YYYYMMDD_HHMMSS` with the current timestamp).

3.  **Analyze Test Results:**
    *   Provide a summary: Total tests, Passed, Failed, Errors, Skipped.
    *   List the primary new failure types observed, especially focusing on:
        *   The `output_ontology_type is required` error: Which test files/cases does it affect?
        *   Failures in `test_historical_id_mapping.py`: What are the specific mock-related errors now?
        *   Any persistent SQLAlchemy greenlet errors.
    *   Note any tests that were previously failing due to the unique constraint but are now passing or failing with a different, more specific error.

**Deliverables:**

*   The full log file from the test run (e.g., `full_integration_test_run_20250605_074500.log`).
*   A summary of the test results (total, passed, failed, errors, skipped).
*   A detailed breakdown of the new primary error types, including:
    *   The exact error messages.
    *   The test files and specific test cases affected by each major error type.
*   Confirmation of the status of `test_historical_id_mapping.py` failures.
*   Confirmation of whether SQLAlchemy greenlet errors are still present.

**Next Steps (Anticipated):**
Based on this comprehensive run, subsequent prompts will be generated to target the highest priority remaining failures.
