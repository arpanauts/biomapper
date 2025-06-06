# Prompt: Enhance Test Fixtures for Endpoint and CSV Adapter Configurations

**Objective:** Resolve 11 test failures by enhancing test fixtures to correctly configure endpoint properties and CSV adapter file paths.

**Context:**
The final comprehensive test run (feedback `2025-06-05-085420-feedback-final-comprehensive-test-analysis.md`) identified two categories of failures related to incomplete test fixture setup:
1.  **Endpoint Configuration Issues (7 tests):** Missing ontology type configurations (specifically, `EndpointPropertyConfig` for 'hgnc' ontology type seems to be a recurring need).
2.  **CSV Adapter File Path Issues (4 tests):** The CSV adapter requires a `file_path` in the endpoint configuration, which is missing for some test setups.

Addressing these fixture issues is the top priority and is expected to fix 11 of the 18 remaining failing tests.

**Key Tasks & Affected Files/Fixtures:**

This will likely involve modifying `tests/integration/conftest.py` or other relevant fixture files where `Endpoint`, `EndpointConfig`, and `EndpointPropertyConfig` objects are created for tests.

1.  **Enhance Endpoint Property Configuration:**
    *   **Requirement:** Ensure that when test `Endpoint` objects are created, their associated `EndpointConfig` and `EndpointPropertyConfig` are fully populated, especially for ontology types like 'hgnc' if tests expect them.
    *   **Action:** Review fixtures that create endpoints (e.g., `setup_mock_endpoints`, `populated_db`, or specific endpoint creation utilities within `conftest.py`).
    *   Modify these fixtures to create `EndpointPropertyConfig` instances for relevant ontology types (e.g., 'hgnc') and link them to the `EndpointConfig`.
    *   The error messages from the 7 failing tests due to "Endpoint Configuration Issues" should guide which specific ontology types and properties are missing.

2.  **Add `file_path` for CSV Adapter Endpoints:**
    *   **Requirement:** Endpoints intended to be used with a `CSVAdapter` need a `file_path` attribute in their configuration that points to the relevant CSV data file.
    *   **Action:** Identify the fixtures that set up endpoints used in tests involving the `CSVAdapter` (these are the 4 tests failing with "CSV Adapter File Path Issues").
    *   Modify these fixtures to include a `file_path` in the `EndpointConfig`'s `adapter_config` dictionary when the `adapter_type` is `CSVAdapter`.
        ```python
        # Example conceptual change in a fixture:
        endpoint_config.adapter_config = {
            "adapter_type": "CSVAdapter",
            "file_path": "/path/to/test_data.csv", # Ensure this path is correct for the test environment
            "delimiter": ",",
            # ... other csv adapter params
        }
        ```
    *   Ensure the specified `file_path` points to an actual, accessible CSV file containing appropriate data for the test.

**Affected Test Categories (from feedback `2025-06-05-085420-...`):**

*   **Endpoint Configuration Issues (7 tests):** These tests likely involve strategies or direct calls that query for endpoint properties related to specific ontology types (e.g., 'hgnc') which are not defined in the fixtures.
*   **CSV Adapter File Path Issues (4 tests):** These tests use strategies or mapping paths that utilize an endpoint configured with `CSVAdapter` but lack the `file_path`.

**Verification:**

*   After modifying the fixtures, re-run the 11 tests identified in the feedback as failing due to these two categories.
    *   Obtain the specific list of these 11 failing tests from the `final_full_integration_test_run_20250605_084500.log` mentioned in the feedback.
*   Confirm that these 11 tests now pass.

**Deliverables:**

*   Modified Python fixture files (e.g., `tests/integration/conftest.py`).
*   A clear explanation of the changes made to the fixtures to address both endpoint property configurations and CSV adapter file paths.
*   Confirmation (e.g., pytest console output snippets) that the 11 targeted tests now pass.

**Environment:**

*   Ensure all dependencies are installed using Poetry (`poetry install`).
*   The database should have the latest migrations applied.
