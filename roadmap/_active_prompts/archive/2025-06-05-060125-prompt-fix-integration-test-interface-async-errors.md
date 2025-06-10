# Prompt: Fix Test Interface Mismatches and Async Handling in Integration Tests

**Objective:** Resolve `TypeError`, `AttributeError`, and `RuntimeWarning` (async/await) issues identified in `test_historical_id_mapping.py` and `test_yaml_strategy_ukbb_hpa.py` during integration test runs, as reported in feedback `2025-06-05-060018-feedback-verify-integration-tests.md`.

**Context & Specific Errors to Address:**

1.  **File: `tests/integration/test_historical_id_mapping.py`**
    *   **Error:** `TypeError: setup_mock_endpoints.<locals>.configure() missing 1 required positional argument: 'target_property'`
    *   **Analysis:** The `setup_mock_endpoints` fixture (or a function it calls, like `configure`) has an updated signature that is not being matched by the test calls.

2.  **File: `tests/integration/test_yaml_strategy_ukbb_hpa.py`**
    *   **Error 1:** `AttributeError: 'async_generator' object has no attribute 'execute_yaml_strategy'`
    *   **Analysis:** An object expected to be an executor instance (on which `execute_yaml_strategy` is called) is instead an unhandled `async_generator`. This typically happens when an async fixture yielding the executor is not correctly awaited or its result not properly extracted.
    *   **Error 2:** `TypeError: get_db_manager() got an unexpected keyword argument 'metamapper_db_url'`
    *   **Analysis:** The `get_db_manager` function's signature has changed, and the test is calling it with an outdated or incorrect keyword argument.

3.  **General (Potentially affecting multiple test files, including the above):**
    *   **Warning:** `RuntimeWarning: coroutine 'populated_db' was never awaited`
    *   **Analysis:** The `populated_db` async fixture (and potentially others) is not being correctly consumed (awaited) by the tests or fixtures that depend on it.

**Key Tasks:**

1.  **Address `test_historical_id_mapping.py` (`setup_mock_endpoints` TypeError):**
    *   Locate the definition of the `setup_mock_endpoints` fixture (likely in `tests/conftest.py` or `biomapper/testing/fixtures.py`) and the `configure` function it might be using.
    *   Identify the current expected signature for `configure` or how `setup_mock_endpoints` should be invoked.
    *   Update the calls within `test_historical_id_mapping.py` to provide all required arguments, including `target_property`, in the correct manner.

2.  **Address `test_yaml_strategy_ukbb_hpa.py` (AttributeError & TypeError):**
    *   **`AttributeError` (async_generator):**
        *   Examine how the test obtains the object that is supposed to have the `execute_yaml_strategy` method. This object is likely provided by an async fixture (e.g., `populated_db` or a fixture that uses it).
        *   Ensure that the async fixture is correctly awaited (e.g., using `async for` if it yields multiple items, or `await fixture_name` if `pytest-asyncio`'s auto-awaiting is not in effect or misconfigured for the specific fixture type). The result of the await should be the actual executor instance.
    *   **`TypeError` (`get_db_manager`):**
        *   Inspect the current function signature of `get_db_manager` (likely located in `biomapper/core/db_manager.py` or a similar core module).
        *   Update the calls to `get_db_manager` within `test_yaml_strategy_ukbb_hpa.py` to use the correct and current keyword arguments. Remove or rename `metamapper_db_url` as per the current signature.

3.  **Address General `RuntimeWarning` (`'populated_db' was never awaited`):**
    *   Identify all uses of the `populated_db` async fixture across the test suite (especially in the failing test files).
    *   For each usage, ensure it's correctly consumed. If `populated_db` is an `async def` fixture that `yields`, tests using it should typically be `async def` and use `async for val in populated_db:` or `val = await populated_db` depending on how `pytest-asyncio` handles it and what the fixture yields.
    *   If `pytest-asyncio` is configured for `Mode.STRICT` (as indicated in logs), ensure all test functions using async fixtures are themselves marked `async` and use `await` appropriately.

4.  **Verification:**
    *   Run `pytest tests/integration/test_historical_id_mapping.py` and `pytest tests/integration/test_yaml_strategy_ukbb_hpa.py` individually.
    *   Confirm that the specified `TypeError`, `AttributeError`, and `RuntimeWarning` messages are no longer present in the output for these files.
    *   If feasible, run the broader integration test suite (or relevant parts) to check for wider resolution of the async warnings.

**Deliverables:**

*   Modified Python test files (primarily `test_historical_id_mapping.py` and `test_yaml_strategy_ukbb_hpa.py`, but potentially `conftest.py` or other fixture files if the definitions need adjustment).
*   Confirmation (e.g., pytest console output snippets) that the specified `TypeError`, `AttributeError`, and `RuntimeWarning` issues are resolved in the targeted files.
*   A brief explanation of the fixes applied for each category of error/warning.

**Note on Execution Order & Dependencies:**

*   While this prompt focuses on test code and async handling, the overall health of the integration test suite also depends on resolving database-level issues (like unique constraint violations) which are being addressed in a separate prompt (`2025-06-05-060125-prompt-fix-mapping-path-constraint-violations.md`).
*   The fixes from this prompt are essential, but a completely clean test run will likely require fixes from both prompts. It's advisable to re-run tests after both sets of changes are applied.

**Environment:**

*   Ensure all dependencies are installed using Poetry (`poetry install`).
*   Tests should be run using `pytest` from the project root.
