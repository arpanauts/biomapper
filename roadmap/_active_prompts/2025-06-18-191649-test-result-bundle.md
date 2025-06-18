# Task: Create Unit Tests for `MappingResultBundle`

## Objective
To validate the correctness of our primary result-tracking object, create unit tests for the `MappingResultBundle` class.

## Location for Tests
Create a new test file: `tests/core/models/test_result_bundle.py`

## Test Cases

1.  **Test Initialization**: Instantiate a `MappingResultBundle` and assert that all its initial properties (e.g., `strategy_name`, `initial_identifiers`, `execution_status`, `start_time`) are set correctly.
2.  **Test `add_step_result` for Success**: Add a successful step result. Assert that:
    *   The `step_results` and `provenance` lists are updated.
    *   The `completed_steps` count is incremented.
    *   `current_identifiers` and `current_ontology_type` are updated correctly.
3.  **Test `add_step_result` for Failure**: Add a failed step result. Assert that the `failed_steps` count is incremented.
4.  **Test `finalize` on Success**: Call `finalize()` with a 'completed' status. Assert that `execution_status` and `end_time` are set correctly.
5.  **Test `finalize` on Failure**: Call `finalize()` with a 'failed' status and an error message. Assert that `execution_status` and `error` are set correctly.
6.  **Test `to_dict` Method**: Call `to_dict()` on a finalized result bundle and assert that the resulting dictionary contains the correct keys and values, including a calculated `duration_seconds`.

## Acceptance Criteria
*   A new test file `tests/core/models/test_result_bundle.py` is created.
*   The tests cover all public methods of the `MappingResultBundle` class.
*   All tests pass successfully.
