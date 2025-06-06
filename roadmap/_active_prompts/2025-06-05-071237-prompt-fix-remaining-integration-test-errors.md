# Prompt: Fix Remaining Integration Test Errors (Mocks, Async, API Mismatches)

**Objective:** Resolve the outstanding `TypeError`, `AttributeError` (async), and API mismatch issues in `test_historical_id_mapping.py` and `test_yaml_strategy_ukbb_hpa.py`, as detailed in feedback `2025-06-05-070219-feedback-comprehensive-integration-test-analysis.md`.

**Context:**
This prompt assumes that the critical database unique constraint violations are being addressed by prompt `2025-06-05-071237-prompt-implement-mapping-path-db-migration.md`. The fixes here should be developed and tested against a codebase where the database schema is correct.

The feedback `2025-06-05-070219-...` indicates several issues persist:
- `TypeError` in `test_historical_id_mapping.py` related to `setup_mock_endpoints`.
- `AttributeError: 'async_generator' object has no attribute 'execute_yaml_strategy'` in `test_yaml_strategy_ukbb_hpa.py`.
- `AttributeError: 'MappingExecutor' object has no attribute 'close'` in `test_full_yaml_strategy_workflow` (within `test_yaml_strategy_ukbb_hpa.py`).
- Discrepancies regarding `pytest-asyncio` usage in `conftest.py`.

**Key Tasks:**

1.  **`test_historical_id_mapping.py` - Mock Configuration (`setup_mock_endpoints`):**
    *   **Error:** `TypeError: setup_mock_endpoints.<locals>.configure() missing 1 required positional argument: 'target_property'`.
    *   **Action:**
        *   Locate the `setup_mock_endpoints` fixture (likely in `tests/conftest.py` or `biomapper/testing/fixtures.py`) and the `configure` function it uses internally.
        *   Identify the exact signature of this `configure` function.
        *   Modify the calls to `configure` from within `test_historical_id_mapping.py` (or from the `setup_mock_endpoints` fixture if the call is indirect) to ensure all required arguments, including `target_property`, are correctly passed.

2.  **`test_yaml_strategy_ukbb_hpa.py` - Async Issues & `MappingExecutor` Usage:**
    *   **Error 1:** `AttributeError: 'async_generator' object has no attribute 'execute_yaml_strategy'`.
    *   **Action:**
        *   Review the `mapping_executor` fixture and the `populated_db` fixture it depends on (likely in `tests/conftest.py` or `tests/integration/conftest.py`).
        *   Ensure that all async fixtures are decorated with `@pytest_asyncio.fixture` instead of `@pytest.fixture` if they use `async def` or `yield`.
        *   Verify that if `populated_db` yields data (like DB URLs or sessions), the `mapping_executor` fixture correctly `await`s or consumes this data and then properly instantiates and `yields` or returns an actual `MappingExecutor` instance, not an `async_generator` itself where an instance is expected.
        *   Test functions using these async fixtures must be `async def` and use `await` when calling methods on the executor if those methods are async.

    *   **Error 2:** `AttributeError: 'MappingExecutor' object has no attribute 'close'` (in `test_full_yaml_strategy_workflow`).
    *   **Action:**
        *   Determine if `MappingExecutor` is intended to have a `close()` method (e.g., for releasing resources like database connections if not managed by context managers elsewhere).
        *   If a `close()` method is a valid requirement for `MappingExecutor`'s lifecycle, implement it. It should likely be an `async def close(self):` method if it handles async resources.
        *   If `MappingExecutor` is not intended to have a `close()` method (e.g., its resources are managed by context managers like `async with session:`), then remove the `await executor.close()` call from the `test_full_yaml_strategy_workflow` test.

3.  **General `pytest-asyncio` Usage:**
    *   Perform a review of `tests/conftest.py` and any other relevant `conftest.py` files in `tests/integration/` to ensure all fixtures defined with `async def` or that `yield` and are intended for async tests are decorated with `@pytest_asyncio.fixture`.

4.  **Verification:**
    *   Run `poetry run pytest tests/integration/test_historical_id_mapping.py -v` to confirm the `TypeError` is resolved.
    *   Run `poetry run pytest tests/integration/test_yaml_strategy_ukbb_hpa.py -v` to confirm the `AttributeError`s are resolved.
    *   If changes were made to `conftest.py`, consider running the full `tests/integration/` suite or a broader subset to catch any unintended side effects.

**Deliverables:**

*   Modified Python files (primarily test files like `test_historical_id_mapping.py`, `test_yaml_strategy_ukbb_hpa.py`, and fixture files like `conftest.py`). Potentially `biomapper/core/mapping_executor.py` if `close()` is added.
*   A clear explanation of the fixes applied for each issue.
*   Confirmation (e.g., pytest console output snippets) that the specified tests now pass or that the specific errors are resolved.

**Environment:**

*   Ensure all dependencies are installed using Poetry (`poetry install`).
*   Tests should be run using `pytest` from the project root.
*   **This work should ideally be based on a codebase where the database migration from prompt `2025-06-05-071237-prompt-implement-mapping-path-db-migration.md` has been successfully applied and verified.**
