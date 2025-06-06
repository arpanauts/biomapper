# Prompt: Refactor Legacy `MappingExecutor.execute_strategy` and Handlers

**Date:** 2025-06-05
**Version:** 1.0
**Project:** Biomapper
**Related Prompts/Feedback:** `2025-06-05-045445-prompt-refactor-execute-strategy.md` (original intent), `feedback-cleanup-mapping-executor.md` (confirming preservation of these methods), `feedback-unit-tests-strategy-actions.md` (confirming `StrategyAction` classes are unit-tested).

## 1. Goal

Refactor the legacy `MappingExecutor.execute_strategy` method and its associated handler methods (`_handle_convert_identifiers_local`, `_handle_execute_mapping_path`, `_handle_filter_identifiers_by_target_presence`) to utilize the new, unit-tested `StrategyAction` classes. This will unify mapping logic, remove placeholder implementations, and ensure that all mapping execution paths leverage the robust, tested `StrategyAction` framework while maintaining backward compatibility for existing callers of `execute_strategy`.

**Context:**
- The `MappingExecutor.execute_strategy` method and its handlers were preserved during a recent cleanup for backward compatibility (as per `feedback-cleanup-mapping-executor.md`).
- These handlers are currently placeholders or use older logic.
- New `StrategyAction` classes (`ConvertIdentifiersLocalAction`, `ExecuteMappingPathAction`, `FilterByTargetPresenceAction`) have been implemented and unit-tested, and are already used by the YAML-based strategy execution (`execute_yaml_strategy`).

## 2. Tasks

### 2.1. Analyze `execute_strategy` and Handler Signatures

1.  Review the current implementation and signature of `MappingExecutor.execute_strategy`.
2.  Identify how it's called externally (e.g., `scripts/test_optional_steps.py`) and the structure of its `steps` argument (which is a list of dictionaries, not `MappingStrategyStep` objects).
3.  For each preserved handler method:
    *   `_handle_convert_identifiers_local(self, current_results: MappingResultBundle, step_config: Dict, context: Dict) -> MappingResultBundle:`
    *   `_handle_execute_mapping_path(self, current_results: MappingResultBundle, step_config: Dict, context: Dict) -> MappingResultBundle:`
    *   `_handle_filter_identifiers_by_target_presence(self, current_results: MappingResultBundle, step_config: Dict, context: Dict) -> MappingResultBundle:`
    Carefully document their existing parameters (`step_config`, `context`) and expected return values (`MappingResultBundle`).

### 2.2. Refactor Handler Methods

For each of the three handler methods (`_handle_convert_identifiers_local`, `_handle_execute_mapping_path`, `_handle_filter_identifiers_by_target_presence`):

1.  **Map `step_config` to `StrategyAction` parameters:**
    *   Determine how the dictionary-based `step_config` (from the legacy `execute_strategy` format) maps to the parameters required by the corresponding `StrategyAction` constructor (e.g., `ConvertIdentifiersLocalAction`, `ExecuteMappingPathAction`, `FilterByTargetPresenceAction`). This will involve extracting values like `action_type`, `source_ontology_type`, `target_ontology_type`, `mapping_path_name`, `resource_name`, etc., from `step_config`.
2.  **Create `ActionContext`:**
    *   Instantiate an `ActionContext` object. The `db_session` will come from `self.session_factory()`. The `mapping_run_id` might need to be handled (e.g., generated or passed through if `execute_strategy` supports it, otherwise a default/None).
3.  **Instantiate and Execute `StrategyAction`:**
    *   Create an instance of the appropriate `StrategyAction` class using the mapped parameters and the `ActionContext`.
    *   Call the `execute(current_results, strategy_step_mock)` method of the action. The `current_results` is passed directly. For `strategy_step_mock`, you'll need to create a mock or a simple object that provides the necessary attributes expected by the action class if it uses them (e.g., `is_required`, `output_target_ontology_type`). The legacy `step_config` might contain this information.
4.  **Adapt Results:**
    *   Ensure the `MappingResultBundle` returned by the `StrategyAction.execute()` method is compatible with what the legacy `execute_strategy` flow expects. This should generally be compatible.
5.  **Replace Placeholder/Old Logic:**
    *   Remove the old placeholder or legacy logic within the handler method and replace it with the invocation of the corresponding `StrategyAction`.

**Example Snippet (Conceptual for `_handle_convert_identifiers_local`):**
```python
# Inside MappingExecutor
async def _handle_convert_identifiers_local(self, current_results: MappingResultBundle, step_config: Dict, context: Dict) -> MappingResultBundle:
    async with self.session_factory() as session:
        action_context = ActionContext(db_session=session, mapping_run_id=context.get('mapping_run_id')) # Adjust mapping_run_id as needed

        # Create a mock/simplified strategy_step object from step_config
        # This mock needs to provide attributes like 'is_required', 'name', 'action_type', 'action_config', etc.
        # that ConvertIdentifiersLocalAction might expect from a MappingStrategyStep object.
        mock_strategy_step = MagicMock(spec=MappingStrategyStep)
        mock_strategy_step.name = step_config.get('name', 'legacy_convert_step')
        mock_strategy_step.action_type = ActionType.CONVERT_IDENTIFIERS_LOCAL # or from step_config
        mock_strategy_step.is_required = step_config.get('is_required', True)
        mock_strategy_step.action_config = step_config # Pass the whole step_config as action_config
        # Add other necessary attributes based on ConvertIdentifiersLocalAction's needs

        action = ConvertIdentifiersLocalAction(
            params=ConvertIdentifiersLocalParams(
                # Extract and map from step_config here...
                # e.g., input_ontology_type=step_config.get('input_ontology_type'),
                # output_ontology_type=step_config.get('output_ontology_type'),
                # endpoint_context_config_name=step_config.get('endpoint_context_config_name')
            ),
            context=action_context
        )
        return await action.execute(current_results, strategy_step=mock_strategy_step)
```

### 2.3. Update `execute_strategy` Method

1.  Ensure `execute_strategy` correctly calls these refactored handler methods.
2.  Verify that the overall flow of `execute_strategy` (looping through steps, passing `current_results`, handling `is_required` from `step_config`) remains intact and works with the refactored handlers.

### 2.4. Ensure Backward Compatibility

1.  Thoroughly test the refactored `execute_strategy` using existing test scripts like `scripts/test_optional_steps.py` or by creating new test cases that mimic how it was called previously.
2.  Confirm that it produces the same results and behavior as before the refactoring for a set of defined legacy strategy step configurations.

### 2.5. Add/Update Unit Tests

1.  Write new unit tests for `MappingExecutor.execute_strategy` specifically testing its ability to correctly dispatch to and process results from the refactored handlers (which now use `StrategyAction` classes).
2.  These tests should mock the `StrategyAction` classes themselves (or their `execute` methods) to verify that `execute_strategy` and the handlers correctly instantiate and call them with appropriate parameters derived from the legacy `step_config`.
3.  Ensure coverage for different step types and configurations passed via the legacy `steps` argument of `execute_strategy`.

## 3. Acceptance Criteria

- The handler methods (`_handle_convert_identifiers_local`, `_handle_execute_mapping_path`, `_handle_filter_identifiers_by_target_presence`) are refactored to use their corresponding `StrategyAction` classes.
- All placeholder or old logic within these handlers is removed.
- `MappingExecutor.execute_strategy` correctly utilizes these refactored handlers.
- Backward compatibility for `execute_strategy` is maintained: existing scripts or callers using the legacy step format should continue to work and produce the same results.
- Unit tests are added for `MappingExecutor.execute_strategy` to verify its correct operation with the refactored handlers and `StrategyAction` delegation.
- The refactoring leads to a cleaner, more unified mapping execution logic within `MappingExecutor`.

## 4. Deliverables

- Updated `biomapper/core/mapping_executor.py` file with the refactored methods.
- New/updated unit test files for `MappingExecutor.execute_strategy`.
- Confirmation of backward compatibility (e.g., successful run of relevant test scripts).

## 5. Potential Challenges

- **Mapping `step_config`:** Accurately mapping the free-form `step_config` dictionary (from legacy `execute_strategy` calls) to the structured parameters required by `StrategyAction` classes and the attributes of a `MappingStrategyStep`-like object might be complex.
- **`ActionContext` Creation:** Ensuring the `ActionContext` is created correctly, especially `mapping_run_id`, if the legacy path didn't explicitly manage it.
- **Mocking `strategy_step` for Actions:** `StrategyAction.execute` takes `strategy_step: MappingStrategyStep`. A suitable mock or adapter object will need to be created from `step_config` to pass to the actions.

This refactoring is a key step in modernizing `MappingExecutor` and ensuring all mapping operations benefit from the robust, tested, and extensible `StrategyAction` framework.
