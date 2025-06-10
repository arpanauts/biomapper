# Prompt: Resolve SQLAlchemy Async Context (greenlet_spawn) Errors

**Objective:** Fix the `sqlalchemy.exc.MissingGreenlet: greenlet_spawn has not been called` errors occurring in `test_yaml_strategy_ukbb_hpa.py`.

**Context:**
The comprehensive test run (feedback `2025-06-05-075841-feedback-post-migration-test-analysis.md`) identified that 3 tests in `test_yaml_strategy_ukbb_hpa.py` are failing with `MissingGreenlet` errors. This indicates that SQLAlchemy's async operations are being attempted outside of a properly managed asyncio event loop or async task context, often related to test fixture setup or how async functions are called within the test or the code under test.

**Affected Tests in `test_yaml_strategy_ukbb_hpa.py`:**

*   `test_execute_yaml_strategy_basic`
*   `test_execute_yaml_strategy_with_progress_callback`
*   `test_action_handlers_placeholder_behavior`

**Error Details:**

*   **Message:** `sqlalchemy.exc.MissingGreenlet: greenlet_spawn has not been called; can't call await_only() here. Was IO attempted in an unexpected place?`
*   **Occurrence:** All failures occur during step `S1_UKBB_NATIVE_TO_UNIPROT` when executing the `CONVERT_IDENTIFIERS_LOCAL` action.

**Key Areas to Investigate and Fix:**

1.  **Test Fixture Review (`tests/integration/conftest.py`, `tests/integration/test_yaml_strategy_ukbb_hpa.py` specific fixtures):**
    *   **`@pytest_asyncio.fixture`:** Ensure all fixtures that are `async def` or `yield` async resources (like database sessions or executors that manage them) are decorated with `@pytest_asyncio.fixture` and not `@pytest.fixture`. The previous feedback mentioned `pytest-asyncio` import was added but decorators might not have been updated.
    *   **Session Management:** Examine how the SQLAlchemy async session is created, provided to the `MappingExecutor` or action handlers, and managed throughout its lifecycle within the tests. Ensure it's properly awaited and closed/disposed of.
    *   **Executor Instantiation:** Verify that the `mapping_executor` fixture correctly instantiates and yields/returns a `MappingExecutor` that is configured with a properly managed async database session.

2.  **`MappingExecutor` and `CONVERT_IDENTIFIERS_LOCAL` Action Handler:**
    *   Review the `MappingExecutor.execute_yaml_strategy` method and the `ConvertIdentifiersLocalAction.execute` method (or its equivalent).
    *   Ensure that any database calls within these methods are correctly `await`ed and that the session used is the one passed in, which should be managed by the async test fixture.
    *   Pay close attention to how the `db_session` is accessed and used within the `CONVERT_IDENTIFIERS_LOCAL` action, as the error occurs during this step.

3.  **Test Function Structure:**
    *   Ensure the failing test functions (`test_execute_yaml_strategy_basic`, etc.) are defined as `async def` and that calls to async methods (like `executor.execute_yaml_strategy`) are `await`ed.

**Potential Solutions:**

*   **Correct Fixture Decorators:** Change `@pytest.fixture` to `@pytest_asyncio.fixture` for all relevant async fixtures.
*   **Ensure Proper `await`ing:** Double-check that all coroutines are `await`ed, especially when interacting with the database session or executor methods.
*   **Session Scope:** Ensure the async session's scope is correctly managed. For example, if a session is created in a fixture, it should be available and active when the code under test (e.g., `CONVERT_IDENTIFIERS_LOCAL`) tries to use it.
*   **SQLAlchemy Async Engine/Session Setup:** Verify the global or fixture-level setup of SQLAlchemy's async engine and sessionmaker (`AsyncSession`) follows best practices for `pytest-asyncio`.

**Verification:**

*   After applying fixes, re-run the affected tests specifically:
    ```bash
    poetry run pytest tests/integration/test_yaml_strategy_ukbb_hpa.py -k "test_execute_yaml_strategy_basic or test_execute_yaml_strategy_with_progress_callback or test_action_handlers_placeholder_behavior" -v
    ```
*   Confirm that the `MissingGreenlet` errors are resolved.

**Deliverables:**

*   Modified Python files (likely `tests/integration/conftest.py`, `tests/integration/test_yaml_strategy_ukbb_hpa.py`, and potentially core application code like `biomapper/core/mapping_executor.py` or action handlers if the issue lies there).
*   A clear explanation of the fixes applied and the root cause identified.
*   Confirmation (e.g., pytest console output snippets) that the `MissingGreenlet` errors are resolved for the targeted tests.

**Environment:**

*   Assume YAML parameter issues (from prompt `...-fix-yaml-strategy-parameters.md`) are being addressed separately or have been fixed, as the `CONVERT_IDENTIFIERS_LOCAL` action needs to be reached for this greenlet error to manifest.
