# Prompt: Fix Mock Configuration Issues in Historical ID Mapping Tests

**Objective:** Resolve test failures in `test_historical_id_mapping.py` caused by mock endpoints and paths not returning the expected results, leading to assertions failing with "no_mapping_found" or incorrect behavior.

**Context:**
The comprehensive test run (feedback `2025-06-05-075841-feedback-post-migration-test-analysis.md`) shows that 3 tests in `test_historical_id_mapping.py` are failing. While previous TypeErrors were resolved, the tests now fail at the assertion level because the mock setup does not lead to the expected mapping outcomes.

**Affected Tests in `test_historical_id_mapping.py`:**

*   `test_mapping_with_historical_resolution`
    *   **Error:** `AssertionError: Expected successful mapping for P01023, got no_mapping_found`
*   `test_path_selection_order`
    *   **Error:** `AssertionError: Expected at least two path executions` (implies mocks aren't triggering multiple paths as intended)
*   `test_error_handling`
    *   **Error:** `AssertionError: Expected ERROR status, got no_mapping_found` (implies error conditions aren't being correctly simulated by mocks)

**Key Areas to Investigate and Fix:**

1.  **`setup_mock_endpoints` Fixture (`tests/integration/conftest.py` or `biomapper/testing/fixtures.py`):
    *   Review how this fixture (and its internal `configure` function) sets up mock `Endpoint` and `MappingPath` objects in the test database.
    *   Ensure that the mock data being inserted (e.g., endpoint names, supported ontologies, path details, source/target properties) accurately reflects what the tests expect to find and use.
    *   Verify that the `source_property` and `target_property` arguments passed during `configure` calls in the tests align with the properties defined in the mock `MappingPath` objects.

2.  **Test-Specific Mock Configuration:**
    *   **`test_mapping_with_historical_resolution`:**
        *   This test likely expects a specific primary path to fail (or not find a direct mapping) and then a historical/secondary path to succeed for identifier `P01023`.
        *   Ensure the mock paths are set up with appropriate `priority` and that the data returned by the (mocked) `CSVAdapter` or `LocalDBAdapter` for these paths will lead to the expected resolution.
    *   **`test_path_selection_order`:**
        *   This test requires at least two mapping paths to be executed. The mock setup must provide multiple viable paths for the input, and their `priority` should be distinct to test the ordering.
        *   The data returned by adapters for these paths should be configured to allow both paths to proceed far enough to be considered "executed."
    *   **`test_error_handling`:**
        *   This test expects an `ERROR` status. The mock setup needs to simulate a condition that would lead to an unrecoverable error during mapping (e.g., a required path failing, an adapter throwing an exception that isn't caught and handled as a non-critical failure).

3.  **Adapter Mocking (If applicable):**
    *   If `CSVAdapter` or `LocalDBAdapter` are being directly mocked (e.g., using `unittest.mock.patch`), ensure their `map_identifiers` or `get_data_for_ids` methods are configured to return data consistent with the test's expectations for each specific path and input.
    *   For historical resolution, the adapter for the "current" path might need to return an empty result or indicate no mapping, while the adapter for the "historical" path returns a successful mapping.

4.  **Data Consistency:**
    *   Ensure the identifiers used in test assertions (e.g., `P01023`) are present in the mock data sources (e.g., mock CSV files or data returned by mocked adapter methods) in a way that aligns with the test's logic.

**Verification:**

*   After applying fixes, re-run the affected tests specifically:
    ```bash
    poetry run pytest tests/integration/test_historical_id_mapping.py -k "test_mapping_with_historical_resolution or test_path_selection_order or test_error_handling" -v
    ```
*   Confirm that the assertion errors are resolved and the tests pass as expected.

**Deliverables:**

*   Modified Python files (primarily `tests/integration/test_historical_id_mapping.py` and potentially `tests/integration/conftest.py` or other fixture files if `setup_mock_endpoints` is changed).
*   A clear explanation of the fixes applied to the mock configurations for each test.
*   Confirmation (e.g., pytest console output snippets) that the targeted tests now pass.

**Environment:**

*   Assume other major test blockers (YAML parameters, async issues) are being addressed separately.
