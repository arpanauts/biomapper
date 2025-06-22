# Task: Complete Refactoring of Remaining MappingExecutor Tests

## 1. Objective

Complete the refactoring of the `MappingExecutor` unit tests by addressing the files that were skipped during the initial effort. The goal is to migrate all remaining legacy tests to the new service-oriented architecture, ensuring full test coverage is restored.

## 2. Context and Background

The initial refactoring of `MappingExecutor` tests (`2025-06-22-000233-feedback-refactor-core-executor-tests.md`) successfully migrated the most critical tests but deferred work on several files due to time constraints. This task is to complete that work, bringing the entire test suite up to date with the new architecture.

## 3. Prerequisites

- The agent must be familiar with the new service-oriented architecture, including the roles of `MappingExecutor` as a facade and the various services it delegates to.
- Strong proficiency with `pytest` and `unittest.mock` is required.

## 4. Task Breakdown

Apply the following refactoring process to each of the target files listed below:

1.  **Analyze Existing Tests:** For each test in the file, identify why it is failing or what legacy internal method it relies on.
2.  **Determine the New Logic Location:** Identify which service now contains the business logic that the test was originally intended to cover (e.g., `MetadataQueryService`, `YamlStrategyExecutionService`, `CacheManager`).
3.  **Rewrite and Relocate the Test:**
    - If the logic is now in a service, add a new, focused test to that service's dedicated test file (e.g., `tests/unit/core/services/test_metadata_query_service.py`).
    - The new test must use dependency injection and mocking to isolate the service.
    - If the test is truly about `MappingExecutor`'s orchestration, rewrite it to mock the service dependencies and assert that the correct service methods are called.
4.  **Delete the Old Test/File:** Once the logic is covered by a new test, delete the old, failing test. If an entire test file becomes empty, delete the file.

### Target Files:

- `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/tests/core/test_mapping_executor_metadata.py`
- `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/tests/unit/core/test_mapping_executor_robust_features.py`
- `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/tests/unit/core/test_mapping_executor_utilities.py`

## 5. Implementation Requirements

- **Code Standards:** Follow existing code style. All new tests must be `async def` and use `pytest` and `unittest.mock`.
- **File Organization:** Place new service-level tests in their corresponding test files within `tests/unit/core/services/` or `tests/unit/core/engine_components/`.

## 6. Validation and Success Criteria

- **Success:** All tests in the target files are either successfully refactored and relocated, or are justifiably deleted. All new and modified tests must pass.
- **Validation Command:** Run `poetry run pytest` on any new or modified test files to ensure they pass.

## 7. Feedback and Reporting

- Provide a list of the original test files that were modified or deleted.
- Provide a list of the new or modified test files where the refactored tests now reside.
- For each new/modified test file, provide the `diff` of the changes.
- Provide the `pytest` output for all new/modified files to confirm they pass.
