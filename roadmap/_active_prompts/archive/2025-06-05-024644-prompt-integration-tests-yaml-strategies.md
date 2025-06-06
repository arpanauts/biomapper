# Task: Integration Testing for YAML-Defined Mapping Strategies

## 1. Context & Goal:
With `MappingExecutor` enhanced to run strategies and core action handlers implemented, it's crucial to verify the end-to-end functionality of YAML-defined mapping strategies. This involves testing the entire pipeline: from parsing a YAML configuration with strategies, populating the `metamapper.db`, executing a named strategy via `MappingExecutor`, to validating the final output.

This task focuses on creating comprehensive integration tests for this system.

**Relevant Files & Modules:**
*   New test file: `/home/ubuntu/biomapper/tests/integration/test_yaml_strategy_execution.py`
*   Script for DB population: `/home/ubuntu/biomapper/scripts/populate_metamapper_db.py` (or its core functions).
*   Executor: `/home/ubuntu/biomapper/biomapper/core/mapping_executor.py`
*   Action handlers: `/home/ubuntu/biomapper/biomapper/core/strategy_actions.py` (if separated) or methods within `MappingExecutor`.
*   Test utilities: `pytest`, existing test fixtures.

## 2. Detailed Instructions:

### 2.1. Test Setup and Fixtures (`pytest`):
*   Create a new test file: `/home/ubuntu/biomapper/tests/integration/test_yaml_strategy_execution.py`.
*   **Database Fixture**:
    *   Set up a `pytest` fixture that provides a clean, populated `metamapper.db` for each test (or test session).
    *   This fixture should:
        *   Use a temporary SQLite file for `metamapper.db`.
        *   Programmatically call the necessary functions from `populate_metamapper_db.py` (e.g., `populate_from_configs` or `populate_entity_type`) to populate the DB using a test-specific YAML configuration file.
*   **Test YAML Configuration**:
    *   Create one or more small, focused YAML configuration files (e.g., `tests/integration/data/test_protein_strategy_config.yaml`).
    *   These YAML files should define:
        *   Minimal ontologies, databases, and mapping resources needed for the test strategies.
        *   At least one `entity_type` (e.g., "test_protein").
        *   Several `mapping_strategies` covering different scenarios, using the implemented action types.
        *   Mock file paths for any file-based `MappingResource` clients, pointing to small test data files (e.g., in `tests/integration/data/mock_client_files/`).
*   **`MappingExecutor` Instance**:
    *   A fixture to provide an initialized `MappingExecutor` instance configured to use the test `metamapper.db` and a test `mapping_cache.db`.

### 2.2. Test Cases:

Develop test cases for various scenarios, including:

*   **Basic Linear Strategy**:
    *   A strategy with a few `CONVERT_IDENTIFIERS_LOCAL` steps.
    *   Verify: Correct sequence of operations, final identifiers, and final ontology type.
*   **Strategy with `EXECUTE_MAPPING_PATH`**:
    *   Define a simple `mapping_paths` entry in the test YAML.
    *   Define a strategy that uses `EXECUTE_MAPPING_PATH` to run this path.
    *   Verify: The path is executed correctly within the strategy, and its output is used by subsequent steps.
*   **Strategy with `FILTER_IDENTIFIERS_BY_TARGET_PRESENCE`**:
    *   Set up a mock target resource (e.g., a small CSV file for `resource_name_for_check`).
    *   Test the filter action to ensure it correctly includes/excludes identifiers.
    *   Test with and without `conversion_path_to_match_ontology`.
*   **Strategy with Mixed Action Types**:
    *   Combine all core action types in a single strategy to test interaction.
*   **Strategy Not Found**:
    *   Test calling `MappingExecutor.execute_strategy` with a non-existent strategy name. Verify appropriate error handling (e.g., custom exception raised, specific return value like an empty or error-marked `MappingResultBundle`).
*   **Step Failure (if error handling is implemented in `MappingExecutor`)**:
    *   Simulate a failure within an action (e.g., a required resource for conversion is missing, a client fails).
    *   Verify that the `MappingExecutor` handles this gracefully based on its defined error strategy (e.g., stops execution, logs error, includes error in `MappingResultBundle`).
*   **Empty Initial Identifiers**:
    *   Test running a strategy with an empty list of `initial_identifiers`. Verify correct behavior (e.g., no errors, empty result bundle or appropriate status).
*   **Ontology Type Mismatches**:
    *   Test scenarios where `current_source_ontology_type` might not align with an action's expectations if not handled by explicit parameters (e.g., `input_ontology_type` in `CONVERT_IDENTIFIERS_LOCAL`).

### 2.3. Assertions:
*   For each test case, assert:
    *   The final list of identifiers in the `MappingResultBundle` is as expected.
    *   The final `current_source_ontology_type` (or equivalent status in the bundle) matches the expected output type of the last successful step.
    *   The provenance information within the `MappingResultBundle` accurately reflects the steps taken, their parameters, input/output counts, and status (success, failure, not_implemented).
    *   No unexpected errors or exceptions occurred unless specifically tested for.

### 2.4. Mocking External Dependencies:
*   If any action handlers make external calls (e.g., to web APIs), these should be mocked using `unittest.mock` or `pytest-mock`. For the currently defined core actions, this is less likely as they focus on local resources or `MappingPath` execution. However, ensure file system interactions for file-based clients use controlled test files.

## 3. Expected Outcome:
*   A new integration test suite in `/home/ubuntu/biomapper/tests/integration/test_yaml_strategy_execution.py`.
*   Reliable tests covering the successful execution of various YAML-defined strategies and common error cases.
*   Increased confidence in the correctness of the YAML strategy execution subsystem, from configuration parsing to final output.

## 4. Feedback File:
Create a Markdown feedback file named `YYYY-MM-DD-HHMMSS-feedback-integration-tests-yaml-strategies.md` in `/home/ubuntu/biomapper/roadmap/_active_prompts/feedback/` documenting:
*   Structure of the test suite and fixtures.
*   Any challenges in setting up test data (YAML, mock files, DB population for tests).
*   Coverage achieved and any scenarios identified as difficult to test.
*   Confirmation of test suite readiness and any notable findings from initial test runs.
