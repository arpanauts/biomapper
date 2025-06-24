# Test Fix Tasks for Sub-Agents

## Task 1: Fix YAML Strategy Tests
**Branch**: `fix-yaml-strategy`
**Files to fix**:
- `tests/test_yaml_strategy_provenance.py` (1 failure)
- `tests/integration/test_yaml_strategy_execution.py` (22 errors)
- `tests/integration/test_yaml_strategy_ukbb_hpa.py` (1 failure + 5 errors)

**Instructions**:
1. Navigate to worktree: `cd worktrees/fix-yaml-strategy`
2. Run affected tests: `poetry run pytest tests/test_yaml_strategy_provenance.py tests/integration/test_yaml_strategy_execution.py tests/integration/test_yaml_strategy_ukbb_hpa.py -v`
3. Common issues to check:
   - Missing imports or incorrect module paths
   - Mock setup issues
   - Async function handling
   - Database session management

## Task 2: Fix Mapping Executor Tests
**Branch**: `fix-mapping-executor`
**Files to fix**:
- `tests/core/test_mapping_executor_lifecycle.py` (3 failures)
- `tests/core/engine_components/test_mapping_executor_builder.py` (3 failures)
- `tests/core/engine_components/test_mapping_executor_initializer.py` (15 failures)
- `tests/unit/core/test_mapping_executor_robust_features.py` (1 failure + 17 errors)
- `tests/unit/core/test_mapping_executor_utilities.py` (20 errors)

**Instructions**:
1. Navigate to worktree: `cd worktrees/fix-mapping-executor`
2. Run affected tests individually first
3. Focus on:
   - Mock coordinator setup (LifecycleCoordinator, MappingCoordinatorService, etc.)
   - Proper AsyncMock vs MagicMock usage
   - Missing method implementations in mocks

## Task 3: Fix Session Manager Tests
**Branch**: `fix-session-manager`
**Files to fix**:
- `tests/core/engine_components/test_session_manager.py` (5 failures)

**Instructions**:
1. Navigate to worktree: `cd worktrees/fix-session-manager`
2. Run: `poetry run pytest tests/core/engine_components/test_session_manager.py -v`
3. Check for:
   - SQLAlchemy session factory setup
   - Async context manager mocking
   - Property vs method access issues

## Task 4: Fix Path Finder Tests
**Branch**: `fix-path-finder`
**Files to fix**:
- `tests/unit/core/test_path_finder.py` (7 errors)

**Instructions**:
1. Navigate to worktree: `cd worktrees/fix-path-finder`
2. Run: `poetry run pytest tests/unit/core/test_path_finder.py -v`
3. TypeError issues suggest:
   - Constructor signature mismatch
   - Missing required arguments
   - Import issues

## Task 5: Fix Mapping Service Tests
**Branch**: `fix-mapping-services`
**Files to fix**:
- `tests/unit/core/services/test_mapping_step_execution_service.py` (4 failures)
- `tests/mapping/test_reverse_mapping.py` (1 failure)

**Instructions**:
1. Navigate to worktree: `cd worktrees/fix-mapping-services`
2. Run tests separately
3. Check for:
   - Service initialization issues
   - Mock client setup
   - Reverse mapping logic

## Task 6: Fix Integration Tests
**Branch**: `fix-integration-tests`
**Files to fix**:
- `tests/integration/test_historical_id_mapping.py` (2 errors)
- `tests/core/test_bidirectional_mapping_optimization.py` (1 failure)

**Instructions**:
1. Navigate to worktree: `cd worktrees/fix-integration-tests`
2. These likely need full database setup
3. Check for:
   - Database fixture issues
   - Missing test data
   - Async execution context

## Task 7: Fix Metadata Tests
**Branch**: `fix-metadata-tests`
**Files to fix**:
- `tests/core/test_metadata_population.py` (4 errors)

**Instructions**:
1. Navigate to worktree: `cd worktrees/fix-metadata-tests`
2. Run: `poetry run pytest tests/core/test_metadata_population.py -v`
3. Focus on:
   - Metadata field population
   - Cache result handling

## Task 8: Fix Client Tests
**Branch**: `fix-client-tests`
**Files to fix**:
- `tests/mapping/clients/arivale/test_arivale_lookup.py` (1 failure)
- `tests/mapping/arango/test_arango_store.py` (2 failures)

**Instructions**:
1. Navigate to worktree: `cd worktrees/fix-client-tests`
2. Run tests individually
3. Issues might be:
   - External service dependencies
   - Network/connection mocking
   - Client configuration

## General Debugging Tips
1. Run with `-vvs` for verbose output
2. Check imports first: `python -c "import <module>"`
3. Look for common patterns:
   - `AttributeError: Mock object has no attribute` → Add to mock spec
   - `TypeError` → Check constructor signatures
   - `ImportError` → Fix module paths
4. Use `pytest --tb=short` for concise tracebacks
5. Fix one test at a time, then run the whole module