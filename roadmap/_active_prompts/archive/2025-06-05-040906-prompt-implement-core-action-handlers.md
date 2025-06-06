# Prompt: Implement Core Action Handlers in MappingExecutor

**Objective:**
Implement the actual logic for the core action handlers within the `MappingExecutor` class, replacing the current placeholder implementations. These handlers are crucial for executing YAML-defined mapping strategies.

**Context:**
The `MappingExecutor.execute_yaml_strategy` method currently dispatches to placeholder asynchronous action handlers: `_handle_convert_identifiers_local`, `_handle_execute_mapping_path`, and `_handle_filter_identifiers_by_target_presence`. This task involves filling in these handlers with their intended functionality, utilizing existing Biomapper components like database clients, mapping path execution logic, and identifier conversion utilities.

**Key Tasks:**

1.  **Implement `_handle_convert_identifiers_local`:**
    *   **File:** `biomapper/core/mapping_executor.py`
    *   **Logic:**
        *   Retrieve `source_ontology_type`, `target_ontology_type`, and `client_settings` from `step.action_parameters`.
        *   Utilize an appropriate local client (e.g., from `biomapper.clients`) to perform identifier conversion based on the provided parameters. This might involve loading local mapping files or data.
        *   Update `current_identifiers` with the converted identifiers.
        *   Update `current_source_ontology_type` to the `target_ontology_type` of this conversion step.
        *   Return a dictionary with results, including `converted_identifiers`, `num_converted`, `num_unconverted`.

2.  **Implement `_handle_execute_mapping_path`:**
    *   **File:** `biomapper/core/mapping_executor.py`
    *   **Logic:**
        *   Retrieve `mapping_path_name` from `step.action_parameters`.
        *   Use the `MappingExecutor`'s existing capabilities (or a refactored version of its mapping path execution logic, possibly from `map_identifiers_async`) to execute the specified mapping path.
        *   This will involve querying `metamapper.db` for the path details and then executing its steps.
        *   Update `current_identifiers` with the results of the mapping path execution.
        *   Update `current_source_ontology_type` based on the target ontology of the executed mapping path.
        *   Return a dictionary with results, including `mapped_identifiers`, `num_mapped`, `num_unmapped`.

3.  **Implement `_handle_filter_identifiers_by_target_presence`:**
    *   **File:** `biomapper/core/mapping_executor.py`
    *   **Logic:**
        *   Retrieve `target_endpoint_name`, `target_ontology_type`, and optionally `conversion_path_to_match_ontology` from `step.action_parameters`.
        *   If `conversion_path_to_match_ontology` is provided, first convert `current_identifiers` to the `target_ontology_type` using that mapping path (similar to `_handle_execute_mapping_path` but only for temporary conversion, not updating `current_source_ontology_type` permanently from this sub-step).
        *   Query the specified `target_endpoint_name` (likely using a client or direct DB query via `biomapper.db.queries`) to check for the presence of the (potentially converted) identifiers.
        *   Filter `current_identifiers` (the original ones before temporary conversion, if any) to retain only those that were found in the target.
        *   Return a dictionary with results, including `filtered_identifiers`, `num_retained`, `num_discarded`.

**Acceptance Criteria:**
*   All three placeholder action handlers in `MappingExecutor` are replaced with functional implementations.
*   The implementations correctly use `step.action_parameters` to guide their logic.
*   The `current_identifiers` and `current_source_ontology_type` are correctly updated by each handler as appropriate.
*   The integration tests in `tests/integration/test_yaml_strategy_execution.py` pass, demonstrating the correct functioning of these handlers within strategy execution.
*   Each handler returns a structured dictionary with relevant metrics and results for inclusion in the `MappingResultBundle`.

**Relevant Files:**
*   `biomapper/core/mapping_executor.py`
*   `biomapper/clients/` (for local conversion clients)
*   `biomapper/db/queries.py` (potentially for filter target presence checks)
*   `biomapper/config.py` (for accessing client settings or database configurations if needed)

**Notes/Considerations:**
*   Ensure all database interactions are asynchronous (`async/await`).
*   Leverage existing Biomapper utilities and clients as much as possible to avoid code duplication.
*   Pay close attention to error handling within each handler. If a handler encounters an issue, it should raise an appropriate exception (e.g., `MappingExecutionError`) that can be caught by the main `execute_yaml_strategy` loop.
*   The `is_required` flag logic is handled by the main loop; these handlers should focus on performing their action and reporting success/failure.
