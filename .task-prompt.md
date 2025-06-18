# Task: Resolve Strategy Action Test Failures

## Objective
Fix a variety of errors (RuntimeError, TypeError, AttributeError, KeyError) occurring within unit tests for different strategy actions. These actions are fundamental components of the mapping strategy execution engine.

## Affected Files/Modules
- `tests/unit/core/strategy_actions/test_bidirectional_match.py`
- `tests/unit/core/strategy_actions/test_convert_identifiers_local.py`
- `tests/unit/core/strategy_actions/test_execute_mapping_path.py`
- `tests/unit/core/strategy_actions/test_filter_by_target_presence.py`
- `tests/unit/core/strategy_actions/test_resolve_and_match_forward.py`
- `tests/unit/core/strategy_actions/test_visualize_mapping_flow.py`

## Common Error(s)
- `RuntimeError: Action execution failed: object Mock can't be used in 'await' expression`
- `TypeError: the JSON object must be str, bytes or bytearray, not Mock`
- `TypeError: argument of type 'MockMappingResultBundle' is not iterable`
- `AttributeError`: Often related to module-level access or incorrect mocking (e.g., `<module 'biomapper.core.strategy_actions.resolve_and_match_forward' from ...`).
- `KeyError`: Missing keys, often in context or result data (e.g., `'total_input'` in `test_convert_identifiers_local.py`).

## Background/Context
Strategy actions are individual, reusable operations within a larger mapping strategy (e.g., converting identifiers, executing a sub-path, filtering results). The tests for these actions are failing due to issues that could stem from:
- Incorrect mocking or usage of asynchronous operations within the actions or their tests.
- Changes in how actions interact with the `ExecutionContext` or the data types they expect/produce.
- Refactoring within the action modules themselves that haven't been reflected in the tests.
- Problems with data serialization/deserialization (e.g., JSON handling).

## Debugging Guidance/Hypotheses

**For `RuntimeError: ... object Mock can't be used in 'await' expression` (e.g., in `test_bidirectional_match.py`):**
- This is a strong indicator that an `async` method is being called, but its mock is not an `AsyncMock` or a `MagicMock` returning an awaitable. 
- Review the action's `execute` method and any helper async methods. Ensure mocks for these are set up correctly (e.g., `AsyncMock(return_value=...)`).

**For `TypeError: the JSON object must be str, bytes or bytearray, not Mock` (e.g., in `test_convert_identifiers_local.py`, `test_filter_by_target_presence.py`):**
- This suggests that a function expecting a JSON string (e.g., `json.loads()` or a Pydantic model parsing a string) is instead receiving a Mock object.
- Trace where the data comes from. If it's from a mocked component (like a client or another service), ensure the mock's `return_value` is a properly formatted JSON string, not the mock itself or an un-serialized Python dict.

**For `TypeError: argument of type 'MockMappingResultBundle' is not iterable` (e.g., in `test_execute_mapping_path.py`):**
- The code is attempting to iterate over an object (likely a mock of `MappingResultBundle`) that is not iterable. 
- Check if `MappingResultBundle` is supposed to be iterable or if a specific attribute of it (e.g., a list of results) should be iterated. Adjust the test or mock accordingly.
- Ensure the mock for `MappingResultBundle` correctly emulates its iterable properties if needed.

**For `AttributeError` on modules (e.g., in `test_resolve_and_match_forward.py`, `test_visualize_mapping_flow.py`):**
- These can be tricky. It might indicate an issue with how the test is structured, how mocks are applied at the module level, or an import problem within the action module itself.
- Check if the attribute being accessed is genuinely missing or if a mock is interfering unexpectedly.
- Ensure that any functions or classes imported and used within the action are available and correctly mocked if they are external dependencies.

**For `KeyError` (e.g., `'total_input'`):**
- This implies that the action is trying to access a key in the `ExecutionContext` or a results dictionary that hasn't been set or is named differently.
- Verify the data flow: what populates the context, and what keys are guaranteed to be present when the action runs?
- Check the action's logic for accessing these keys and the test setup for providing them.

## Specific Error Examples
1.  `FAILED tests/unit/core/strategy_actions/test_bidirectional_match.py::TestBidirectionalMatchAction::test_basic_matching_many_to_many - RuntimeError: Action execution failed: object Mock can't be used in 'await' expression`
2.  `FAILED tests/unit/core/strategy_actions/test_convert_identifiers_local.py::TestConvertIdentifiersLocalAction::test_successful_conversion - TypeError: the JSON object must be str, bytes or bytearray, not Mock`
3.  `FAILED tests/unit/core/strategy_actions/test_execute_mapping_path.py::TestExecuteMappingPathAction::test_successful_execution - TypeError: argument of type 'MockMappingResultBundle' is not iterable`
4.  `FAILED tests/unit/core/strategy_actions/test_resolve_and_match_forward.py::TestResolveAndMatchForwardAction::test_basic_resolution_and_matching - AttributeError: <module 'biomapper.core.strategy_actions.resolve_and_match_forward' from ...`
5.  `FAILED tests/unit/core/strategy_actions/test_convert_identifiers_local.py::TestConvertIdentifiersLocalAction::test_empty_input_identifiers - KeyError: 'total_input'`

## Acceptance Criteria
- All unit tests for strategy actions in the listed 'Affected Files/Modules' pass successfully.
- Asynchronous operations within actions are correctly mocked and tested.
- Data type mismatches (especially around JSON and iterables) are resolved.
- Actions correctly interact with the `ExecutionContext` and handle expected data structures.
- `AttributeError`s related to module access or mocking are fixed.
