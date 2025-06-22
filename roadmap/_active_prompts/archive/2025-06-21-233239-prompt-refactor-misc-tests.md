# Task 4: Refactor Miscellaneous and Provenance Tests

## 1. Objective

Update a small number of miscellaneous, isolated test files that are failing due to the `MappingExecutor` refactoring. This includes tests for YAML strategy provenance, reverse mapping, and a disabled file related to result processing.

## 2. Context and Background

Alongside the major test modules, several smaller files contain tests that also import and use `MappingExecutor`. These tests, while smaller in scope, are important for verifying specific features. They need to be updated to work with the new service-oriented architecture.

One file, `_disabled_test_result_processor.py`, is of particular interest. It was disabled, but its contents may be valuable and could be refactored into new, working tests.

## 3. Prerequisites

- The agent should be able to quickly analyze small test files and identify the outdated API calls.

## 4. Task Breakdown

1.  **Refactor `test_yaml_strategy_provenance.py`:**
    - **Analysis:** This test likely checks the metadata and provenance information returned after a YAML strategy run.
    - **Action:** Update the call to `executor.execute_yaml_strategy` to use the modern signature. Verify that the structure of the provenance data in the result bundle is still correct.

2.  **Refactor `test_reverse_mapping.py`:**
    - **Analysis:** This test verifies reverse mapping logic.
    - **Action:** Update the `MappingExecutor` calls. The core logic of reverse mapping should now be within a service or strategy action; ensure the test correctly invokes the mapping and validates the reversed results.

3.  **Evaluate and Refactor `_disabled_test_result_processor.py`:**
    - **Analysis:** This file is disabled. Carefully read the tests within it. They likely test the processing and formatting of mapping results.
    - **Action:** Determine if the tests are still relevant. Result processing may now be handled by a `SaveResultsAction` or similar. If the tests are valuable, create a *new* test file (e.g., `tests/mapping/test_result_processing.py`) and rewrite the tests to target the new components. If the tests are obsolete, delete the disabled file.

### Target Files:

- `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/tests/test_yaml_strategy_provenance.py`
- `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/tests/mapping/test_reverse_mapping.py`
- `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/tests/mapping/_disabled_test_result_processor.py`

## 5. Implementation Requirements

- **Code Standards:** Use `pytest` and `unittest.mock`. Tests should be `async def`.
- **Decision Making:** For the disabled file, the agent is expected to make a judgment call on whether to refactor or delete the tests and justify its decision.

## 6. Validation and Success Criteria

- **Success:** All tests in the modified/newly created files pass.
- **Clarity:** The agent's decision regarding the disabled test file is clearly explained.

## 7. Feedback and Reporting

- Provide the `diff` for all modified files.
- If a new file was created, provide its full content.
- If the disabled file was deleted, state this and provide the justification.
- Provide the `pytest` output for the affected tests.
