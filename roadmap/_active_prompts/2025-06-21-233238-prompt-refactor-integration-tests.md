# Task 3: Update Integration Tests for New Executor API

## 1. Objective

Update the suite of integration tests to work with the refactored `MappingExecutor` and its new, leaner API. These tests are critical for verifying that end-to-end mapping workflows function correctly, but they currently fail because they use outdated methods for invoking mapping strategies.

## 2. Context and Background

Our integration tests instantiate a `MappingExecutor` and use it to run full mapping pipelines (e.g., UKBB to HPA). The recent refactoring of `MappingExecutor` changed its public API, especially for executing YAML strategies. The tests need to be updated to use the new method signatures and conventions, ensuring our most important user journeys are continuously validated.

## 3. Prerequisites

- The agent must be familiar with the `execute_yaml_strategy` method and how to pass it parameters like `initial_context`.
- Understanding of the project's `pytest` fixtures, especially those in `tests/integration/conftest.py`, is required.

## 4. Task Breakdown

For each of the target files, perform the following:

1.  **Identify Failing Calls:** Locate the lines where `MappingExecutor` methods are called. These are likely the points of failure.
2.  **Update Method Calls:** Refactor the test to use the modern `MappingExecutor` API. For YAML strategies, this typically means calling `executor.execute_yaml_strategy(...)` and passing runtime parameters (like output paths) via the `initial_context` dictionary.
3.  **Update `conftest.py`:** The fixtures in `tests/integration/conftest.py` might be instantiating `MappingExecutor` in an old way or providing outdated helper functions. Update these fixtures to align with the new architecture.
4.  **Verify Assertions:** Ensure that the test assertions are still valid. The structure of the `MappingResultBundle` returned by the executor should be consistent, but it's good to double-check that the tests are still asserting the correct outcomes.

### Target Files:

- `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/tests/integration/conftest.py`
- `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/tests/integration/historical/test_ukbb_historical_mapping.py`
- `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/tests/integration/test_uniprot_mapping_end_to_end.py`
- `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/tests/integration/test_yaml_strategy_ukbb_hpa.py`
- `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/tests/integration/test_ukbb_to_arivale_integration.py`
- `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/tests/integration/test_yaml_strategy_execution.py`

## 5. Implementation Requirements

- **Focus:** The primary goal is to fix the integration tests by updating API calls. Avoid refactoring the internal logic of the tests unless necessary to make them pass.
- **Real Services:** Unlike unit tests, these integration tests should use real services and a real (test) database to verify the entire stack works together.

## 6. Validation and Success Criteria

- **Success:** All tests within the `tests/integration/` directory pass when run with `poetry run pytest tests/integration/`.
- **No Skipped Tests:** Remove any `pytest.mark.skip` markers that were added to temporarily disable these tests.

## 7. Feedback and Reporting

- Provide a `diff` for each modified file.
- Confirm that the entire integration test suite passes by providing the summary output from `pytest`.
