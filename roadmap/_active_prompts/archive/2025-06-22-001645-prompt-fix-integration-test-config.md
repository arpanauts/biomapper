# Task: Fix Failing Integration Tests Due to Configuration Issues

## 1. Objective

Resolve the 20 failing integration tests by fixing the underlying test data and configuration problems. The tests have already been updated to be compatible with the new service-oriented API, but they are failing because of issues in the test environment itself.

## 2. Context and Background

The feedback from the integration test refactoring (`2025-06-22-000236-feedback-refactor-integration-tests.md`) clearly states that while API compatibility is fixed, numerous tests are still failing. The root cause is identified as missing test data files, incorrect YAML strategy configurations, or other environment-related setup problems. This is the highest priority task to stabilize the test suite, as it will validate the end-to-end functionality of the refactored application.

## 3. Prerequisites

- The agent must be able to analyze `pytest` error logs to identify the root cause of test failures (e.g., `FileNotFoundError`, `KeyError` from config, assertion errors from unexpected data).
- Familiarity with the project's test data structure in `tests/integration/data/` and the YAML configurations is required.

## 4. Task Breakdown

1.  **Run the Integration Test Suite:**
    - Execute `poetry run pytest tests/integration/` to get a baseline of the current failures.

2.  **Systematically Debug Failures:**
    - For each failing test, examine the error message.
    - **If `FileNotFoundError`:** The test is likely missing a required mock data file. Create or locate the necessary file in `tests/integration/data/`.
    - **If `KeyError` or `ValidationError`:** The issue is likely in a `mapping_strategies_config.yaml` or `protein_config.yaml` file used by the test. Verify that all keys, endpoints, and paths are correctly defined.
    - **If `AssertionError`:** The test is running but producing unexpected results. This could still be a data issue. Inspect the input data and the results to see where the discrepancy lies.

3.  **Fix Configurations and Data:**
    - Make the necessary corrections to the data files and YAML configurations.
    - Do **not** change the application code. The goal is to fix the test environment, not the code under test.

4.  **Iterate and Validate:**
    - Rerun the tests after each fix to ensure it was successful and did not introduce new regressions.
    - Continue until all integration tests are passing.

## 5. Implementation Requirements

- **Target Directories:** 
    - `tests/integration/`
    - `tests/integration/data/`
    - Any YAML configuration files used by the integration tests.
- **Code Standards:** Maintain existing file structures and formats.

## 6. Validation and Success Criteria

- **Primary Success Criterion:** All tests in the `tests/integration/` directory pass successfully.
- **Validation Command:** `poetry run pytest tests/integration/`

## 7. Feedback and Reporting

- Provide a summary of the types of configuration issues you fixed (e.g., "Fixed 5 missing data files," "Corrected 3 endpoint names in strategy configs").
- Provide the final output of the `pytest tests/integration/` run showing that all tests pass.
