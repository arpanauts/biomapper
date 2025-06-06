# Task: Enhance MappingExecutor for YAML Strategy Execution

## Context:
Biomapper's `MappingExecutor` currently supports iterative mapping based on `MappingPath` objects. The system has been extended to parse and store YAML-defined mapping strategies (consisting of `MappingStrategy` and `MappingStrategyStep` records) into the `metamapper.db` via `scripts/populate_metamapper_db.py`.

The objective of this task is to enable `MappingExecutor` to load these explicit, multi-step strategies from the database and execute them.

## Target File:
`/home/ubuntu/biomapper/biomapper/core/mapping_executor.py`

## Detailed Instructions:

1.  **New Public Method for Strategy Execution:**
    *   Add a new public asynchronous method: 
        ```python
        async def execute_strategy(
            self,
            strategy_name: str,
            initial_identifiers: List[str],
            source_ontology_type: Optional[str] = None,
            target_ontology_type: Optional[str] = None,
            # Consider adding entity_type if not implicitly available
        ) -> 'MappingResultBundle': # Assuming MappingResultBundle or similar
        ```
    *   This method will be the primary entry point for executing a named mapping strategy.

2.  **Strategy Loading Logic (within `execute_strategy`):
    *   Use `self.async_metamapper_session` to query `metamapper.db`.
    *   Retrieve the `MappingStrategy` record matching `strategy_name` and its `is_active` flag is true.
    *   Eagerly load its associated `MappingStrategyStep` records, ensuring they are ordered by `step_order`.
    *   If the strategy is not found or not active, raise an appropriate custom exception (e.g., `StrategyNotFoundError` or `InactiveStrategyError`).
    *   Determine the effective `source_ontology_type` and `target_ontology_type` for the strategy execution:
        *   Prioritize the `source_ontology_type` and `target_ontology_type` arguments passed to `execute_strategy`.
        *   If an argument is `None`, fall back to the `default_source_ontology_type` or `default_target_ontology_type` defined in the loaded `MappingStrategy` record.
        *   If still `None` after checking defaults, this might indicate an issue or require specific handling based on the actions in the strategy. Log a warning or raise an error if essential types are missing.

3.  **Execution Loop and State Management (within `execute_strategy`):
    *   Initialize `current_identifiers: List[str] = list(initial_identifiers)`.
    *   Initialize `current_source_ontology_type: str` with the effective source ontology type determined above.
    *   Initialize an empty `MappingResultBundle` (or a similar comprehensive result object) to accumulate results, step-by-step provenance, and overall summary information. This bundle should track the evolution of identifiers and their associated metadata through the strategy.
    *   Iterate through the loaded `MappingStrategyStep` objects in their prescribed order.

4.  **Step Dispatching Mechanism:
    *   For each `MappingStrategyStep`:
        *   Extract `action_type` (e.g., "CONVERT_IDENTIFIERS_LOCAL") and `action_parameters` (the JSONB field from the step).
        *   Implement a dispatch mechanism, such as a dictionary mapping `action_type` strings to corresponding private handler methods within `MappingExecutor`:
            ```python
            action_handlers = {
                "CONVERT_IDENTIFIERS_LOCAL": self._handle_convert_identifiers_local,
                "EXECUTE_MAPPING_PATH": self._handle_execute_mapping_path,
                "FILTER_IDENTIFIERS_BY_TARGET_PRESENCE": self._handle_filter_identifiers_by_target_presence,
                # Add other action types as they are defined
            }
            ```
        *   Look up the handler method using `action_type`. If no handler is found for a given `action_type`, log an error, mark the step as failed in the provenance, and decide whether to halt execution or skip the step.
        *   Call the handler method, passing necessary context: `current_identifiers`, `action_parameters`, `current_source_ontology_type`, the strategy's overall `target_ontology_type`, and details from the current step (e.g., `step_id`, `description` for logging/provenance).

5.  **Data Flow and Provenance Update:
    *   Each action handler method is expected to perform an operation and return:
        *   An updated list of identifiers (which becomes `current_identifiers` for the next step).
        *   An updated `current_source_ontology_type` if the action changes the nature of the identifiers (e.g., after a conversion).
        *   Provenance information for the step executed (e.g., input/output counts, resources used, status, errors).
    *   After each step handler returns, update `current_identifiers` and `current_source_ontology_type`.
    *   Append the step's provenance to the main `MappingResultBundle`.

6.  **Placeholder Action Handlers (Initial Implementation):
    *   For this task, the actual logic of action handlers (`_handle_convert_identifiers_local`, etc.) can be placeholders (stubs).
    *   These stubs should log that they were called, along with the received parameters.
    *   They should clearly indicate they are not yet implemented (e.g., by setting a 'not_implemented' status in their provenance contribution).
    *   For testing the loop, a stub might return the input identifiers unchanged or an empty list.
    *   The detailed implementation of these handlers will be covered in a subsequent, separate task.

7.  **Final Result:
    *   After iterating through all steps (or if execution is halted due to an error), the `execute_strategy` method should return the populated `MappingResultBundle`.

8.  **Error Handling and Logging:
    *   Implement robust error handling within the execution loop. If a step fails:
        *   Log the error comprehensively.
        *   Record the failure in the step's provenance within the `MappingResultBundle`.
        *   Decide on a failure strategy: either halt the entire strategy execution and return the partial `MappingResultBundle`, or allow the strategy to continue with the next step (if appropriate for the error type).
    *   Ensure detailed logging throughout the strategy execution process (e.g., starting strategy, starting/ending each step, parameters, counts, errors).

9.  **Integration with Existing `MappingExecutor` Infrastructure:
    *   Ensure the new methods and logic integrate cleanly with existing `MappingExecutor` components: `async_metamapper_session`, `cache_session_factory`, logging setup, and any existing result/provenance structures.
    *   The `MappingResultBundle` should ideally be an evolution of, or compatible with, any existing result objects returned by `MappingExecutor` to maintain consistency.

10. **Entity Type Consideration:**
    *   The `MappingStrategy` is associated with an `entity_type` (e.g., 'protein', 'metabolite'). The `MappingExecutor` is typically instantiated for a specific `entity_type` (passed to its `__init__`). Ensure this context is available and used if necessary by action handlers or logging.

## Testing Considerations (for the implementer):
*   Create or use existing simple YAML strategies in a config file (e.g., `configs/protein_config.yaml`) that use a sequence of the placeholder action types.
*   Update or create a test script (e.g., `scripts/test_protein_yaml_strategy.py`) to instantiate `MappingExecutor` and call the new `execute_strategy` method with various inputs to verify the loop, dispatching, and placeholder behavior.

## Deliverables:
*   The modified `/home/ubuntu/biomapper/biomapper/core/mapping_executor.py` file with the new `execute_strategy` method and placeholder action handlers.
*   Definition of the `MappingResultBundle` (if new or significantly changed) or clear documentation on how existing result structures are used/extended for strategy provenance.
*   Any new custom exception classes (e.g., `StrategyNotFoundError`).
