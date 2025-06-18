# Task: Resolve Integration & Strategy Orchestration Issues

## Objective
Address `ModuleNotFoundError` for `scripts.populate_metamapper_db` in integration tests and fix `TypeError`s related to asynchronous context managers in `StrategyOrchestrator` tests.

## Affected Files/Modules
- `tests/integration/test_yaml_strategy_execution.py`
- `tests/core/engine_components/test_strategy_orchestrator.py`

## Common Error(s)
- `ModuleNotFoundError: No module named 'scripts.populate_metamapper_db'`
- `TypeError: 'coroutine' object does not support the asynchronous context manager protocol`

## Background/Context
**ModuleNotFoundError:**
The `scripts` directory, containing `populate_metamapper_db.py`, is not currently configured as a Python package (it lacks `__init__.py` files). This prevents direct import of the script as a module in the integration tests. The script is likely intended to be run as a command-line tool.

**TypeError with Async Context Managers:**
Tests for `StrategyOrchestrator` are failing with `TypeError: 'coroutine' object does not support the asynchronous context manager protocol`. This typically occurs when an `async def` function that is *not* a proper asynchronous context manager is used with `async with`. An asynchronous context manager requires `__aenter__` and `__aexit__` methods, or to be a generator decorated with `@asynccontextmanager` from `contextlib`.

## Debugging Guidance/Hypotheses

**For `ModuleNotFoundError: No module named 'scripts.populate_metamapper_db'`:**
- **Option 1 (Recommended for scripts): Run as Subprocess:** Modify the integration tests to execute `populate_metamapper_db.py` using `subprocess.run()` or `asyncio.create_subprocess_exec`. This aligns with how standalone scripts are typically invoked and tested. Remember that the script auto-discovers configs and takes `--drop-all` (Memory `[631e6476-8513-4727-aa46-494041b7b79b]`).
- **Option 2 (Make `scripts` a package):** Add empty `__init__.py` files to `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/scripts/` and `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/scripts/setup_and_configuration/`. This would allow imports like `from scripts.setup_and_configuration import populate_metamapper_db`. Ensure the project root is in `sys.path` (Poetry usually handles this).
- **Investigate Test Setup:** See how `tests/integration/test_yaml_strategy_execution.py` attempts to use or invoke the script. The fix will depend on this current approach.

**For `TypeError: 'coroutine' object does not support the asynchronous context manager protocol`:**
- **Review Async Context Managers:** Examine the objects being used with `async with` in `tests/core/engine_components/test_strategy_orchestrator.py`. 
- **Check for `@asynccontextmanager`:** If the object is an async generator function intended for context management, ensure it's decorated with `@asynccontextmanager` from the `contextlib` module and uses `yield` appropriately.
- **Verify `__aenter__` and `__aexit__`:** If it's a class, ensure it correctly implements the `async def __aenter__(self):` and `async def __aexit__(self, exc_type, exc_val, exc_tb):` methods.
- **Mocking:** If mocks are involved, ensure the mock object is configured to behave like a proper async context manager (e.g., its `__aenter__` returns an awaitable, or the mock itself is an `AsyncMock` configured appropriately).

## Specific Error Examples
1.  `ERROR tests/integration/test_yaml_strategy_execution.py::TestYAMLStrategyExecution::test_basic_linear_strategy - ModuleNotFoundError: No module named 'scripts.populate_metamapper_db'`
2.  `FAILED tests/core/engine_components/test_strategy_orchestrator.py::TestStrategyOrchestrator::test_successful_strategy_execution - TypeError: 'coroutine' object does not support the asynchronous context manager protocol`
3.  `FAILED tests/core/engine_components/test_strategy_orchestrator.py::TestStrategyOrchestrator::test_strategy_failure_required_step - TypeError: 'coroutine' object does not support the asynchronous context manager protocol`

## Acceptance Criteria
- Integration tests in `tests/integration/test_yaml_strategy_execution.py` can successfully invoke or utilize the `populate_metamapper_db.py` script, resolving the `ModuleNotFoundError`.
- All tests in `tests/core/engine_components/test_strategy_orchestrator.py` pass, with `TypeError`s related to async context managers resolved.
- The chosen solution for the `ModuleNotFoundError` is robust and aligns with good testing practices for scripts.
- Asynchronous context managers are correctly implemented and used in the strategy orchestrator tests.
