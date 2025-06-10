# Prompt: Fix Missing Required Parameters in YAML Strategy Configurations

**Objective:** Resolve test failures caused by missing or incorrect parameters in YAML strategy files used by integration tests, primarily in `test_yaml_strategy_execution.py`.

**Context:**
The comprehensive test run (feedback `2025-06-05-075841-feedback-post-migration-test-analysis.md`) revealed that 17 tests are failing due to action handlers requiring parameters not provided or misnamed in the YAML strategy definitions. This is now the primary blocker for a large portion of the `test_yaml_strategy_execution.py` suite.

**Key Tasks & Affected Files:**

1.  **Identify YAML Strategy Files:**
    *   The YAML strategy files are likely located in a directory like `tests/integration/data/strategies/` or a similar path within the `tests` directory. You will need to locate the specific YAML files used by the failing tests listed below.

2.  **Fix `output_ontology_type` for `CONVERT_IDENTIFIERS_LOCAL` (14 tests):**
    *   **Error:** `Strategy action CONVERT_IDENTIFIERS_LOCAL failed: output_ontology_type is required`
    *   **Action:** For each `CONVERT_IDENTIFIERS_LOCAL` step in the affected YAML strategy files, add the `output_ontology_type` parameter. 
        *   **Value:** The appropriate value for `output_ontology_type` might depend on the specific test's intent. Analyze the test case or the strategy's goal. Common ontology types in this project include 'uniprot', 'ensembl', 'hgnc', 'ncbigene'. If unclear, start with a common default like `'uniprot'` or consult the surrounding strategy steps for clues about the target ontology.
    *   **Affected Tests in `test_yaml_strategy_execution.py` (these use various YAML files that need updating):**
        *   `test_basic_linear_strategy`
        *   `test_mixed_action_strategy`
        *   `test_empty_initial_identifiers`
        *   `test_ontology_type_tracking`
        *   `test_filter_with_conversion_path`
        *   `test_all_optional_strategy`
        *   `test_mixed_required_optional_strategy`
        *   `test_optional_fail_first_strategy`
        *   `test_optional_fail_last_strategy`
        *   `test_multiple_optional_failures_strategy`
        *   `test_required_fail_after_optional_strategy`
        *   `test_all_optional_fail_strategy`
        *   `test_mapping_result_bundle_tracking`
        *   (One more test, identify from logs if not listed here but failing with the same error)

3.  **Fix `path_name` for `EXECUTE_MAPPING_PATH` (1 test):**
    *   **Error:** `Strategy action EXECUTE_MAPPING_PATH failed: path_name is required`
    *   **Action:** In the YAML strategy file used by `test_strategy_with_execute_mapping_path` (in `test_yaml_strategy_execution.py`), find the `EXECUTE_MAPPING_PATH` action. If it uses `mapping_path_name`, rename this parameter to `path_name`.
    *   **Affected Test:** `test_strategy_with_execute_mapping_path`

4.  **Fix `endpoint_context` for `FILTER_IDENTIFIERS_BY_TARGET_PRESENCE` (1 test):**
    *   **Error:** `endpoint_context must be 'TARGET', got: None`
    *   **Action:** In the YAML strategy file used by `test_strategy_with_filter_action` (in `test_yaml_strategy_execution.py`), find the `FILTER_IDENTIFIERS_BY_TARGET_PRESENCE` action. Add or ensure it has the parameter `endpoint_context: 'TARGET'`.
    *   **Affected Test:** `test_strategy_with_filter_action`

**Example YAML Modification (Conceptual):**
```yaml
# Before (for CONVERT_IDENTIFIERS_LOCAL)
steps:
  - name: S1_Convert
    action_type: CONVERT_IDENTIFIERS_LOCAL
    parameters:
      input_ontology_type: 'some_input_type'
      # output_ontology_type is missing

# After
steps:
  - name: S1_Convert
    action_type: CONVERT_IDENTIFIERS_LOCAL
    parameters:
      input_ontology_type: 'some_input_type'
      output_ontology_type: 'uniprot' # Or other appropriate value
```

**Verification:**
*   After modifying the YAML files, re-run the specifically affected tests to confirm the parameter-related errors are resolved.
    *   Example: `poetry run pytest tests/integration/test_yaml_strategy_execution.py -k test_basic_linear_strategy`
    *   Example: `poetry run pytest tests/integration/test_yaml_strategy_execution.py -k test_strategy_with_execute_mapping_path`
    *   Example: `poetry run pytest tests/integration/test_yaml_strategy_execution.py -k test_strategy_with_filter_action`
*   Ideally, run all tests in `tests/integration/test_yaml_strategy_execution.py` to see the broader impact.

**Deliverables:**

*   A list of all YAML files modified.
*   The modified YAML files themselves (or diffs).
*   Confirmation (e.g., pytest console output snippets) that the specified parameter errors are resolved for the targeted tests.

**Environment:**

*   Ensure all dependencies are installed using Poetry (`poetry install`).
*   The database should have the latest migration applied.
