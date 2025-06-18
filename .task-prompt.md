# Task: Resolve `AttributeError: _load_client` in Various Test Suites

## Objective
Resolve all `AttributeError: ... object has no attribute '_load_client'` errors across various test suites. This involves refactoring affected tests to correctly use the new `ClientManager.get_client_instance()` method for client loading and mocking.

## Affected Files/Modules (Primary Focus)
- `tests/test_yaml_strategy_provenance.py`
- `tests/core/test_bidirectional_mapping_optimization.py`
- `tests/integration/test_yaml_strategy_ukbb_hpa.py`
- `tests/mapping/test_reverse_mapping.py`
- `tests/unit/core/test_mapping_executor_robust_features.py`
- `tests/integration/test_historical_id_mapping.py`
- `tests/core/test_mapping_executor_metadata.py`
- `tests/core/test_metadata_population.py`

## Common Error(s)
- `AttributeError: '...' object has no attribute '_load_client'`

## Background/Context
The core mapping component has been refactored, and client loading responsibilities have been moved to the `ClientManager` component. The private `_load_client` method (and its helper `_load_client_class`) no longer exists directly on the main component. Tests that attempt to call or mock this old method will fail.

The correct approach is to interact with the component's `client_manager.get_client_instance(resource)` for obtaining client instances or `client_manager._load_client_class(path_string)` if testing the class loading logic directly (though the latter is an internal method of `ClientManager` itself).

## Debugging Guidance/Hypotheses
- Ensure `patch.object` targets are updated from `component, "_load_client"` to `component.client_manager, "get_client_instance"`.
- If `_load_client_class` was being tested or mocked directly, the target should now be `component.client_manager, "_load_client_class"`.
- The `get_client_instance` method is asynchronous and expects a `MappingResource` object as an argument. Ensure mocks (return values, side effects) are compatible.

## Specific Error Examples
1.  `FAILED tests/test_yaml_strategy_provenance.py::TestYAMLStrategyProvenanceTracking::test_trace_mapping_chain_simple - AttributeError: '...' object has no attribute '_load_client'`
2.  `FAILED tests/core/test_bidirectional_mapping_optimization.py::TestBidirectionalMappingOptimization::test_path_caching - AttributeError: '...' object has no attribute '_load_client'`

## Acceptance Criteria
- All tests in the listed 'Affected Files/Modules' that previously failed with the `AttributeError: ... '_load_client'` now pass.
- Component instances in tests correctly utilize `ClientManager` for client-related operations.
- Mocks are updated to reflect the new `ClientManager` API.
