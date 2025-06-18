# Task: Centralize Database Session Management in a `SessionManager`

## Objective
To improve database connection management and adhere to the single responsibility principle, extract all SQLAlchemy session creation logic from `MappingExecutor` into a dedicated `SessionManager` class.

## Current Implementation
The `MappingExecutor` currently contains several methods for creating and managing database sessions, such as `_get_session`, `_get_async_session`, and the sessionmaker setup in the `__init__` method. This mixes database concerns with orchestration logic.

## Refactoring Steps

1.  **Create the `SessionManager` Class:**
    *   Create a new file: `biomapper/core/engine_components/session_manager.py`.
    *   Define a `SessionManager` class.
    *   The `__init__` method should take the database URLs (`metamapper_db_url`, `mapping_cache_db_url`) and `echo_sql` flag.
    *   Move all engine creation (`create_engine`, `create_async_engine`) and sessionmaker configuration logic from `MappingExecutor.__init__` into the `SessionManager.__init__`.
    *   Move the `_get_session` and `_get_async_session` methods from `MappingExecutor` into the `SessionManager`, making them public methods (`get_session`, `get_async_session`).

2.  **Update `MappingExecutor`:**
    *   In `biomapper/core/mapping_executor.py`, remove the `_get_session` and `_get_async_session` methods.
    *   In `MappingExecutor.__init__`, remove all the engine and sessionmaker setup logic.
    *   Instantiate the `SessionManager` in `MappingExecutor.__init__`:
        ```python
        self.session_manager = SessionManager(
            metamapper_db_url=self.metamapper_db_url,
            mapping_cache_db_url=self.mapping_cache_db_url,
            echo_sql=echo_sql
        )
        ```
    *   Update all calls from `self._get_session()` to `self.session_manager.get_session()` and `self._get_async_session()` to `self.session_manager.get_async_session()`.
    *   Add the necessary import: `from .engine_components.session_manager import SessionManager`.

## Acceptance Criteria
*   A `SessionManager` class is implemented in `biomapper/core/engine_components/session_manager.py`.
*   All database session and engine creation logic is removed from `MappingExecutor`.
*   `MappingExecutor` uses an instance of `SessionManager` to obtain database sessions.
*   The application's database interactions function as before.
