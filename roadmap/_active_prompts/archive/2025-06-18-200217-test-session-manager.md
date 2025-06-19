# Task: Create Unit Tests for `SessionManager`

## Objective
To validate the database connection and session management logic, create unit tests for the `SessionManager` component.

## Location for Tests
Create a new test file: `tests/core/engine_components/test_session_manager.py`

## Test Strategy
- Use `pytest` and `unittest.mock`.
- Mock the SQLAlchemy functions `create_async_engine` and `sessionmaker` to prevent actual database connections.
- Mock `pathlib.Path` to test the directory creation logic without touching the filesystem.

## Test Cases

1.  **Test Initialization:**
    - Instantiate `SessionManager` with mock DB URLs.
    - Assert that `create_async_engine` is called twice (once for metamapper, once for cache) with the correct, async-converted URLs and the `echo_sql` flag.
    - Assert that `sessionmaker` is called twice with the correct engines.
    - Assert that the internal `_ensure_db_directories` method was called.

2.  **Test `_get_async_url`:**
    - Test with a `sqlite:///` URL and assert it's correctly converted to `sqlite+aiosqlite:///`.
    - Test with a non-SQLite URL (e.g., `postgresql+asyncpg://...`) and assert it is returned unchanged.

3.  **Test `_ensure_db_directories`:**
    - Mock `pathlib.Path`.
    - Call the method with `sqlite` URLs and assert that `Path().parent.mkdir()` is called.
    - Call the method with non-`sqlite` URLs and assert that `mkdir()` is not called.

4.  **Test Session Getters:**
    - Call `get_async_metamapper_session()` and assert that it calls the `MetamapperSessionFactory`.
    - Call `get_async_cache_session()` and assert that it calls the `CacheSessionFactory`.

5.  **Test Compatibility Properties:**
    - Access the `async_metamapper_session` property and assert it returns the `MetamapperSessionFactory` itself.
    - Access the `async_cache_session` property and assert it returns the `CacheSessionFactory` itself.

## Acceptance Criteria
- A new test file `tests/core/engine_components/test_session_manager.py` is created.
- The tests validate the correct setup of SQLAlchemy engines and sessions without making real DB connections.
- All tests pass successfully.
