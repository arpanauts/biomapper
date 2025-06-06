# Task: Implement Initial Action Handlers for MappingExecutor

## Context:
Biomapper's `MappingExecutor` is being enhanced to load and execute YAML-defined mapping strategies (this core execution loop is covered in a separate task: `2025-06-05-024644-prompt-enhance-mapping-executor.md`). This task focuses on implementing the Python logic for the initial set of `action.type` primitives that these strategies will invoke.

These handlers will be private asynchronous methods within the `MappingExecutor` class.

## Target File:
`/home/ubuntu/biomapper/biomapper/core/mapping_executor.py`

## Detailed Instructions:

Implement the following private asynchronous handler methods. Each handler should:
*   Accept parameters such as `current_identifiers: List[str]`, `action_params: Dict[str, Any]` (parsed from the strategy step's `action_parameters` JSON), `current_source_ontology_type: str`, the strategy's overall `target_ontology_type: str`, and `current_step_info: Dict[str, Any]` (containing `step_id`, `description` etc. for logging/provenance).
*   Return a tuple: `(updated_identifiers: List[str], updated_source_ontology_type: str, step_provenance_data: Dict[str, Any])`.
*   `step_provenance_data` should be a dictionary detailing the execution of this step (inputs, outputs, parameters, status, errors, resources used) to be merged into the main `MappingResultBundle`.
*   Utilize `self.async_metamapper_session` for database queries against `metamapper.db`.
*   Utilize `self.cache_session_factory` for accessing the mapping cache if/when appropriate.
*   Perform comprehensive logging.

### 1. `async def _handle_convert_identifiers_local(self, current_identifiers: List[str], action_params: Dict[str, Any], current_source_ontology_type: str, strategy_target_ontology_type: str, current_step_info: Dict[str, Any]) -> Tuple[List[str], str, Dict[str, Any]]:`

    *   **Action Description**: Converts identifiers between ontologies using local `MappingResource` instances that represent direct lookups (e.g., file-based clients, simple database table lookups, not complex multi-step paths).
    *   **Parameters from `action_params` (YAML `action.parameters`):**
        *   `output_ontology_type` (str, required): The target ontology type for this conversion.
        *   `input_ontology_type` (str, optional): Specifies the input ontology type for this conversion. If not provided, it's inferred from `endpoint_context` and `current_source_ontology_type` / `strategy_target_ontology_type`.
        *   `endpoint_context` (str, required, e.g., 'SOURCE', 'TARGET'): As validated by `populate_metamapper_db.py`. Helps determine the actual input ontology if `input_ontology_type` is not explicit. If `endpoint_context` is 'SOURCE', the input is `current_source_ontology_type`. If 'TARGET', the input is effectively `strategy_target_ontology_type` (though this usually means converting *from* the strategy's target perspective, which might be less common for a forward pass; clarify if this implies a reverse lookup capability or if it's mainly for context).
        *   `resource_name` (str, optional): The specific name of a `MappingResource` to use for this conversion. If provided, use this resource directly. If not, the system needs to discover a suitable resource.
    *   **Logic**:
        1.  **Determine Actual Input Ontology Type**: 
            *   If `action_params.get('input_ontology_type')` is provided, use it.
            *   Else, if `action_params['endpoint_context'] == 'SOURCE'`, the input type is `current_source_ontology_type`.
            *   Else, if `action_params['endpoint_context'] == 'TARGET'`, this needs careful interpretation. It might mean the `current_identifiers` are already notionally related to the target side, and we're converting them further. Or, it could imply the `current_identifiers` (from source) should be converted as if they were target identifiers. For now, assume it means the input is `current_source_ontology_type` but the conversion is conceptually happening *towards* or *at* the target context defined by `output_ontology_type`.
        2.  **Identify `MappingResource`**:
            *   If `resource_name` is in `action_params`, query `metamapper.db` for an active `MappingResource` with this name. Validate that its client type is suitable for local conversion (e.g., `FileLookupClient`, `ArivaleMetadataLookupClient`, or a new generic `LocalDbLookupClient`).
            *   If `resource_name` is not provided, query `metamapper.db` for active `MappingResource`s that:
                *   Can convert from the determined `actual_input_ontology_type` to `action_params['output_ontology_type']`.
                *   Have a client type suitable for local conversion.
                *   If multiple are found, there needs to be a selection strategy (e.g., use the first one, or require `resource_name` if ambiguous, log a warning).
            *   If no suitable resource is found, record an error in provenance and return `current_identifiers` unchanged.
        3.  **Perform Conversion**: 
            *   Instantiate the client from the chosen `MappingResource` (using `client_factory` logic if available, or direct instantiation based on `client_type` and `client_config`).
            *   Invoke the client's mapping method (e.g., `map_ids`, `get_metadata_batch`) with `current_identifiers`.
            *   The client should return a mapping result (e.g., a dictionary or list of tuples).
        4.  **Process Results**: 
            *   Extract the converted identifiers from the client's output.
            *   Handle cases where identifiers are not mapped (e.g., keep original, drop, or include as unmapped based on client behavior or step configuration).
        5.  **Return**: 
            *   `updated_identifiers`: The list of successfully converted identifiers.
            *   `updated_source_ontology_type`: This will be `action_params['output_ontology_type']`.
            *   `step_provenance_data`: Details including resource used, input/output counts, errors.

### 2. `async def _handle_execute_mapping_path(self, current_identifiers: List[str], action_params: Dict[str, Any], current_source_ontology_type: str, strategy_target_ontology_type: str, current_step_info: Dict[str, Any]) -> Tuple[List[str], str, Dict[str, Any]]:`

    *   **Action Description**: Executes a pre-defined, multi-step `MappingPath` stored in `metamapper.db`.
    *   **Parameters from `action_params`:**
        *   `path_name` (str, required): The name of the `MappingPath` to execute.
    *   **Logic**:
        1.  **Retrieve `MappingPath`**: Query `metamapper.db` for the `MappingPath` (and its `MappingPathStep`s) matching `action_params['path_name']`. Ensure it's active.
        2.  **Determine Path's Target Ontology**: The `MappingPath` itself has a `target_type` (its final output ontology).
        3.  **Execute Path**: 
            *   Invoke the `MappingExecutor`'s existing internal logic for executing a mapping path (e.g., `self.map_identifiers_via_path` or `_execute_mapping_path_internal`, adapting as necessary). This logic already handles iterating through path steps, client invocation, and caching.
            *   The `source_ontology_type` for this path execution is `current_source_ontology_type`.
            *   The `target_ontology_type` for this path execution is the `target_type` of the loaded `MappingPath`.
        4.  **Process Results**: The path execution should yield a list of mapped identifiers and provenance.
        5.  **Return**: 
            *   `updated_identifiers`: The list of identifiers resulting from the path execution.
            *   `updated_source_ontology_type`: This will be the `target_type` of the executed `MappingPath`.
            *   `step_provenance_data`: Summary of the path execution (path name, input/output counts, status from the path's own result bundle).

### 3. `async def _handle_filter_identifiers_by_target_presence(self, current_identifiers: List[str], action_params: Dict[str, Any], current_source_ontology_type: str, strategy_target_ontology_type: str, current_step_info: Dict[str, Any]) -> Tuple[List[str], str, Dict[str, Any]]:`

    *   **Action Description**: Filters `current_identifiers` by checking if they (or their mapped equivalents) exist in a specified target dataset/resource. This is often used to pre-filter identifiers before a more complex or resource-intensive step, ensuring they have a potential counterpart in the target context.
    *   **Parameters from `action_params`:**
        *   `ontology_type_to_match` (str, required): The ontology type in the target context against which presence is checked.
        *   `resource_name_for_check` (str, required): The name of a `MappingResource` (e.g., a file client) that provides the set of identifiers of `ontology_type_to_match` from the target context.
        *   `conversion_path_to_match_ontology` (str, optional): If `current_identifiers` (which are of `current_source_ontology_type`) need to be converted to `ontology_type_to_match` before the check, this parameter specifies the name of a `MappingPath` to perform this conversion.
        *   `endpoint_context` (str, required, must be 'TARGET' as per validation): Confirms this operation is related to the target side of the overall strategy.
    *   **Logic**:
        1.  **Prepare Identifiers for Checking (`ids_for_check_map`)**: 
            *   Initialize `ids_for_check_map: Dict[str, List[str]] = {orig_id: [] for orig_id in current_identifiers}` to store original IDs and their versions to be checked for presence.
            *   If `conversion_path_to_match_ontology` is provided:
                *   Execute this path to convert `current_identifiers` (from `current_source_ontology_type`) to `ontology_type_to_match`. This might use `_handle_execute_mapping_path` or similar internal logic.
                *   Populate `ids_for_check_map`: for each original ID, add its converted equivalents (if any) to its list in the map.
            *   Else (no conversion path, `current_source_ontology_type` is assumed to be directly comparable or is `ontology_type_to_match`):
                *   For each `orig_id` in `current_identifiers`, add `orig_id` itself to `ids_for_check_map[orig_id]`.
        2.  **Load Target Identifier Set**: 
            *   Retrieve the `MappingResource` specified by `resource_name_for_check`.
            *   Instantiate its client.
            *   Use the client to fetch all identifiers from the target resource (e.g., load all keys from a file). This set should consist of identifiers of type `ontology_type_to_match`. Store this as `target_presence_set: Set[str]`.
        3.  **Filter**: 
            *   `filtered_identifiers: List[str] = []`.
            *   Iterate through `current_identifiers` (the original list passed to the handler).
            *   For each `original_id`, check if any of the identifiers in `ids_for_check_map[original_id]` are present in `target_presence_set`.
            *   If there's at least one match, add `original_id` to `filtered_identifiers`.
        4.  **Return**: 
            *   `updated_identifiers`: The `filtered_identifiers` list.
            *   `updated_source_ontology_type`: Remains `current_source_ontology_type` (as this step only filters, doesn't change identifier type).
            *   `step_provenance_data`: Details like resources used, input/output counts, number filtered out.

## General Requirements for All Handlers:
*   **Idempotency (where applicable)**: Consider if actions can be made idempotent or if caching strategies can prevent re-computation if the same step with the same inputs is encountered.
*   **Configuration**: Handlers should be configurable via `action_params`. Avoid hardcoding values that should come from the YAML strategy definition.
*   **Logging**: Implement detailed logging for each handler: entry, parameters, key decisions, resources used, errors, and exit.
*   **Error Handling**: Gracefully handle errors (e.g., resource not found, client error, unexpected data) and record them in the `step_provenance_data`.

## Testing Considerations (for the implementer):
*   Create specific YAML strategies in `configs/protein_config.yaml` (or a new test config file) that exercise each of these action handlers with various parameter combinations.
*   Ensure `metamapper.db` is populated with necessary `MappingResource` and `MappingPath` test data that these handlers would rely on.
*   Update `scripts/test_protein_yaml_strategy.py` to call `MappingExecutor.execute_strategy` with these test strategies and verify: 
    *   Correctness of output identifiers.
    *   Accuracy of the `updated_source_ontology_type`.
    *   Completeness and correctness of the `step_provenance_data` and the overall `MappingResultBundle`.

## Deliverables:
*   The modified `/home/ubuntu/biomapper/biomapper/core/mapping_executor.py` file with the implemented action handler methods.
*   Updated or new test data in YAML configuration files and potentially `metamapper.db` population scripts to support testing these handlers.
*   Updated test scripts that demonstrate the functionality of these handlers.
