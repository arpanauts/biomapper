# Task: Fix Failing Service-Level Unit Tests

## 1. Objective

Resolve the test failures in `tests/unit/core/services/test_metadata_query_service.py`. These tests were created during a previous refactoring but are failing due to incorrect assumptions about the underlying service's API, specifically regarding SQLAlchemy's `scalar()` vs. `scalar_one_or_none()` return behavior.

## 2. Context and Background

During the refactoring of the core `MappingExecutor` tests, several new test suites were created for the new service classes. The feedback file `2025-06-22-000233-feedback-refactor-core-executor-tests.md` identified that the tests for `MetadataQueryService` are unreliable because the mocks do not accurately reflect the behavior of the SQLAlchemy session they are simulating. This task is a high-priority fix to stabilize this new test suite.

## 3. Prerequisites

- The agent must understand how to use `unittest.mock` to create mock objects for SQLAlchemy sessions.
- Familiarity with the difference between `session.execute(...).scalar()` and `session.execute(...).scalar_one_or_none()` is crucial.

## 4. Task Breakdown

1.  **Navigate to the Target File:**
    - Open `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/tests/unit/core/services/test_metadata_query_service.py`.

2.  **Analyze Failing Tests:**
    - Run `poetry run pytest tests/unit/core/services/test_metadata_query_service.py` to see the current failures.
    - Examine the test failures and identify the exact lines where mock setups or assertions are incorrect.

3.  **Correct Mock Implementations:**
    - Locate the mock setup for the `AsyncSession`.
    - For tests where the service is expected to call `scalar_one_or_none()`, ensure the mock is configured to return a value from that method call.
    - For tests where `scalar()` is used, ensure the mock reflects that. The feedback suggests the service uses `scalar_one_or_none()`, so you will likely need to adjust the mocks to match this.
    - **Example:** If the mock setup is `mock_session.execute.return_value.scalar.return_value = ...`, it may need to be changed to `mock_session.execute.return_value.scalar_one_or_none.return_value = ...`.

4.  **Verify All Tests Pass:**
    - Rerun the pytest command and ensure all tests in the file now pass.

## 5. Implementation Requirements

- **Target File:** `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/tests/unit/core/services/test_metadata_query_service.py`
- **Code Standards:** Maintain existing test structure and style. Use `unittest.mock` for all mocking.

## 6. Validation and Success Criteria

- **Primary Success Criterion:** All tests in `test_metadata_query_service.py` pass successfully.
- **Validation Command:** `poetry run pytest tests/unit/core/services/test_metadata_query_service.py`

## 7. Feedback and Reporting

- Provide the `diff` of the changes made to the test file.
- Provide the output of the final, successful `pytest` run for the file.
