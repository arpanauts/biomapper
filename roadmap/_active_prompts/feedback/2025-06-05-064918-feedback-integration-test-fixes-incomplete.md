# Feedback: Integration Test Interface and Async Error Fixes - INCOMPLETE

**Date:** 2025-06-05 06:49:18
**Prompt:** `2025-06-05-060125-prompt-fix-integration-test-interface-async-errors.md`
**Status:** ❌ NOT COMPLETED

## Executive Summary

The integration test issues described in the prompt have **NOT been resolved**. Both test files (`test_historical_id_mapping.py` and `test_yaml_strategy_ukbb_hpa.py`) continue to fail with the same or similar errors mentioned in the original prompt.

## Detailed Analysis

### 1. test_historical_id_mapping.py Issues

#### Original Error
```
TypeError: setup_mock_endpoints.<locals>.configure() missing 1 required positional argument: 'target_property'
```

#### Current Status
- The `configure` function in `conftest.py:127` correctly accepts 5 parameters including `target_property`
- The test file calls it with all 5 parameters correctly at line 73
- **However**, the test still fails with different errors:
  - The mapping result doesn't include a 'status' field as expected
  - Mock setup isn't returning the expected result structure
  - No paths are being executed (path_execution_order remains empty)

#### Test Output
```
AssertionError: Result should include status
assert 'status' in {'INVALID_ID': {...}, 'P01023': {...}, ...}
```

### 2. test_yaml_strategy_ukbb_hpa.py Issues

#### Original Errors
1. `AttributeError: 'async_generator' object has no attribute 'execute_yaml_strategy'`
2. `TypeError: get_db_manager() got an unexpected keyword argument 'metamapper_db_url'`

#### Current Status - BOTH ERRORS PERSIST

##### Error 1: Async Generator Issue
- The `mapping_executor` fixture (line 42-58) is incorrectly handling the `populated_db` fixture
- The fixture is yielding the executor object, but tests receive an async_generator instead
- All test methods fail with: `AttributeError: 'async_generator' object has no attribute 'execute_yaml_strategy'`

##### Error 2: get_db_manager Parameter Issue
- The `get_db_manager` function in `biomapper/db/session.py:140-178` only accepts:
  - `db_url: Optional[str] = None`
  - `echo: bool = False`
- It does NOT accept `metamapper_db_url` as a parameter
- The error would occur if any code tries to call it with this incorrect parameter

### 3. Async/Await Issues

#### Original Warning
```
RuntimeWarning: coroutine 'populated_db' was never awaited
```

#### Current Status
- The `populated_db` fixture is defined as an async fixture (line 14)
- It's being used by other fixtures but not properly awaited
- The fixture chain `populated_db` → `mapping_executor` isn't handling async properly

## Root Causes

1. **Fixture Dependency Chain**: The async fixture `populated_db` is not being properly consumed by dependent fixtures
2. **Incorrect Parameter Names**: Code is using `metamapper_db_url` instead of `db_url` when calling `get_db_manager`
3. **Mock Setup Issues**: The mocking in `test_historical_id_mapping.py` isn't creating the expected result structure
4. **Missing MappingExecutor Methods**: The test expects `initialize()` and `close()` methods that don't exist

## Required Fixes

### For test_yaml_strategy_ukbb_hpa.py:

1. **Fix the fixture chain** to properly handle async:
   ```python
   @pytest.fixture
   async def mapping_executor(populated_db):
       test_metamapper_db, test_cache_db = await populated_db  # Need to await if it's async
       # ... rest of fixture
   ```

2. **Fix get_db_manager calls** throughout the codebase:
   - Change `metamapper_db_url=...` to `db_url=...`

3. **Remove calls to non-existent methods**:
   - Remove `await executor.initialize()` 
   - Remove `await executor.close()`
   - Or implement these methods in MappingExecutor

### For test_historical_id_mapping.py:

1. **Fix the mock_mapping_executor fixture** to return proper result structure with 'status' field
2. **Fix the mock setup** to ensure paths are properly returned and executed

## Verification Steps

Run these commands to verify the issues:

```bash
# Check for the specific errors
poetry run pytest tests/integration/test_historical_id_mapping.py -v --tb=short
poetry run pytest tests/integration/test_yaml_strategy_ukbb_hpa.py -v --tb=short

# Check for async warnings
poetry run pytest tests/integration/ -W error::RuntimeWarning
```

## Impact

Until these issues are resolved:
- Integration tests cannot validate the mapping functionality
- CI/CD pipelines will fail on these tests
- Development of new features requiring these tests will be blocked

## Recommendation

The prompt instructions should be re-executed with focus on:
1. Properly handling async fixtures in the pytest fixture chain
2. Ensuring parameter names match function signatures
3. Creating proper mock objects that return expected data structures
4. Either implementing missing methods or removing calls to them