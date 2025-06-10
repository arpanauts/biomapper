# Task: Verify Integration Test Suite and Analyze Failures

**Source Prompt Reference:** This task is defined by the prompt: `/home/ubuntu/biomapper/roadmap/_active_prompts/2025-06-05-054843-prompt-verify-integration-tests.md`

## 1. Task Objective
Run the full Biomapper integration test suite to verify the fix for the `mapping_paths.name` unique constraint (implemented via Alembic migration `6d519cfd7460_initial_metamapper_schema.py`) and to identify and categorize any other outstanding integration test failures.

## 2. Prerequisites
- [ ] Biomapper project checked out to the latest version containing all recent changes (CSVAdapter optimization, Alembic migration for `mapping_paths`, legacy executor refactor).
- [ ] Poetry environment is set up and dependencies are installed (`poetry install`). This includes `pytest` and `pytest-asyncio`.
- [ ] The Alembic migration `6d519cfd7460` (or `head`) for `metamapper_db_migrations` has been applied to any test database templates, or tests are confirmed to apply migrations automatically.
- [ ] Access to a terminal in the `/home/ubuntu/biomapper/` directory.

## 3. Context from Previous Attempts (if applicable)
- N/A. This is the first full verification run after recent major fixes.
- Previously, integration tests were failing due to `UNIQUE constraint failed: mapping_paths.name`. This specific issue is expected to be resolved.

## 4. Task Decomposition
1.  **Ensure Environment is Ready:**
    *   Verify `poetry install` has been run recently to include `cachetools` and other dependencies.
    *   Confirm how test databases are handled: if they are created fresh and migrations applied, or if a template DB needs manual migration.
2.  **Execute Integration Tests:**
    *   Run the command `poetry run pytest tests/integration`.
3.  **Collect Test Results:**
    *   Capture the full output of the pytest command, including the summary of passed, failed, and errored tests.
4.  **Analyze Failures (if any):**
    *   For each failed or errored test:
        *   Identify the specific error message and traceback.
        *   Determine if the failure is related to the old `mapping_paths.name` constraint (should not be).
        *   Categorize the failure (e.g., new database issue, logic error in code, test setup problem, environment issue).
        *   Provide a brief hypothesis for the cause of each distinct failure.

## 5. Implementation Requirements
- **Input files/data:** The Biomapper codebase, particularly `tests/integration/`.
- **Expected outputs:**
    *   A feedback markdown file detailing the execution status, test summary, and analysis of any failures.
    *   Full console output from the `pytest` command.
- **Code standards:** N/A (test execution task).
- **Validation requirements:** The feedback file must accurately reflect the test outcomes.

## 6. Error Recovery Instructions
- **Pytest Command Fails to Start:**
    *   Check Poetry environment activation and dependencies. Run `poetry install`.
    *   Verify `pytest` and `pytest-asyncio` are installed.
- **Database Connection Errors During Tests:**
    *   Ensure database services (if any external ones are used by tests, though typically SQLite is used) are running.
    *   Verify database connection strings and test setup logic for database creation/migration.
- **Massive Unexpected Failures:**
    *   Stop and report immediately. This might indicate a fundamental issue with the environment or a recent breaking change not caught by unit tests.

## 7. Success Criteria and Validation
Task is complete when:
- [ ] The integration test suite has been executed to completion.
- [ ] A feedback file is produced containing:
    - [ ] Overall test execution status (e.g., all pass, X failed).
    - [ ] A summary of passed/failed/errored tests.
    - [ ] For each failure/error: the test name, error message, and a brief analysis/hypothesis of the cause.
    - [ ] Confirmation that the `UNIQUE constraint failed: mapping_paths.name` issue is resolved.
- [ ] The full console output of the `pytest` run is provided.

## 8. Feedback Requirements
Create a detailed Markdown feedback file at:
`[PROJECT_ROOT]/roadmap/_active_prompts/feedback/YYYY-MM-DD-HHMMSS-feedback-verify-integration-tests.md`

**Mandatory Feedback Sections:**
- **Execution Status:** [TEST_RUN_COMPLETE_ALL_PASS | TEST_RUN_COMPLETE_WITH_FAILURES | TEST_RUN_FAILED_TO_EXECUTE]
- **Test Summary:** (e.g., X passed, Y failed, Z errors in W.Xs)
- **Detailed Failure Analysis (if any):**
    *   For each failed/errored test:
        *   Test Name/Path
        *   Error Message & Traceback (key parts)
        *   Analysis/Hypothesis of Cause
        *   Is it related to `mapping_paths.name` constraint? (Expected: No)
- **Confirmation of `mapping_paths.name` Constraint Fix:** (explicit statement)
- **Full Pytest Console Output:** (as an attachment or embedded in a collapsible section)
- **Next Action Recommendation:** (e.g., address specific new failures, proceed with other tasks if all pass)
- **Environment Changes:** (any setup steps taken, e.g., manual DB migration if performed)
- **Lessons Learned:** (any insights from the test run)
