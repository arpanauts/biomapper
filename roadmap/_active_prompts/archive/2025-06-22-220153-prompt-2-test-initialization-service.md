# Prompt: Create Unit Tests for `InitializationService`

## Goal
Create a comprehensive suite of unit tests for the new `InitializationService` located at `biomapper/core/engine_components/initialization_service.py`. This service is critical as it's responsible for creating all low-level components, and it currently has no test coverage.

## Context
The `InitializationService` was recently rebuilt from scratch to be the single source of truth for component creation. Its primary method, `create_components`, takes a configuration dictionary and instantiates over a dozen services and managers. Your task is to validate that this process works correctly under various configurations.

## Requirements

1.  **Create Test File:**
    -   Create a new file at `tests/unit/core/engine_components/test_initialization_service.py`.

2.  **Test Structure:**
    -   Use `pytest` and the `unittest.mock` library.
    -   Create a test class, e.g., `TestInitializationService`.
    -   Use a `setup_method` or fixtures to instantiate `InitializationService` for each test.

3.  **Test Scenarios:**
    -   **Test Default Creation:**
        -   Call `create_components` with an empty config dictionary (`{}`).
        -   Assert that the returned `components` dictionary is not None and contains all expected keys (e.g., 'session_manager', 'checkpoint_service', etc.).
        -   Assert that each component in the dictionary is an instance of its expected class.
    -   **Test Custom Configuration:**
        -   Create a sample `config` dictionary with custom values (e.g., a specific `metamapper_db_url`, `checkpoint_enabled=True`).
        -   Use `unittest.mock.patch` to mock the constructors of the underlying services (e.g., `SessionManager`, `CheckpointService`).
        -   Call `create_components` with your custom config.
        -   Assert that the mocked constructors were called with the correct arguments from your config.
    -   **Test Component Dependencies:**
        -   Verify that components are created with the correct dependencies. For example, assert that `CacheManager` is initialized with the `SessionManager` instance created in the same run.

4.  **Coverage:**
    -   Aim for high test coverage of the `create_components` method and the various `_create_*` helper methods within `InitializationService`.
    -   Ensure every component creation path is tested.

## Files to Modify
-   **Create:** `tests/unit/core/engine_components/test_initialization_service.py`

## Success Criteria
-   The new test file is created and populated with comprehensive unit tests.
-   The tests validate both default and custom configuration scenarios.
-   The tests verify the correct instantiation and wiring of components.
-   All tests pass when run with `pytest`.
