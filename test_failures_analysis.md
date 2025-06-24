# Test Failures Analysis

## Grouped by Module/Component

### 1. YAML Strategy Tests
- `tests/test_yaml_strategy_provenance.py` (1 failure)
- `tests/integration/test_yaml_strategy_execution.py` (22 errors)
- `tests/integration/test_yaml_strategy_ukbb_hpa.py` (1 failure + 5 errors)

### 2. Mapping Executor Tests
- `tests/core/test_mapping_executor_lifecycle.py` (3 failures)
- `tests/core/engine_components/test_mapping_executor_builder.py` (3 failures)
- `tests/core/engine_components/test_mapping_executor_initializer.py` (15 failures)
- `tests/unit/core/test_mapping_executor_robust_features.py` (1 failure + 17 errors)
- `tests/unit/core/test_mapping_executor_utilities.py` (20 errors)

### 3. Session Manager Tests
- `tests/core/engine_components/test_session_manager.py` (5 failures)

### 4. Path Finding Tests
- `tests/unit/core/test_path_finder.py` (7 errors)

### 5. Mapping Service Tests
- `tests/unit/core/services/test_mapping_step_execution_service.py` (4 failures)
- `tests/mapping/test_reverse_mapping.py` (1 failure)

### 6. Integration Tests
- `tests/integration/test_historical_id_mapping.py` (2 errors)
- `tests/core/test_bidirectional_mapping_optimization.py` (1 failure)

### 7. Metadata Tests
- `tests/core/test_metadata_population.py` (4 errors)

### 8. Client Tests
- `tests/mapping/clients/arivale/test_arivale_lookup.py` (1 failure)
- `tests/mapping/arango/test_arango_store.py` (2 failures)

## Summary
- Total: 45 failures + 72 errors = 117 test issues
- 8 major component groups
- Most failures in: Mapping Executor components (46 issues)