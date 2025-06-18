# Task: Extract Strategy Configuration Loading into a `ConfigLoader` Component

## Objective
To improve the modularity of the `MappingExecutor`, extract the logic for loading and parsing mapping strategy YAML files into a dedicated `ConfigLoader` class. This will centralize configuration management and simplify the executor.

## Current Implementation
The `MappingExecutor` currently has a method `get_strategy` that reads a YAML file, parses it, and returns the strategy configuration. This logic is directly embedded within the executor.

## Refactoring Steps

1.  **Create the `ConfigLoader` Class:**
    *   Create a new file: `biomapper/core/engine_components/config_loader.py`.
    *   Define a `ConfigLoader` class in this file.
    *   Move the logic from `MappingExecutor.get_strategy` into a new method within `ConfigLoader`, for example, `load_strategy(self, strategy_name: str, strategies_config_path: str) -> dict`.
    *   The `ConfigLoader` should handle file reading, YAML parsing, and basic validation.

2.  **Update `MappingExecutor`:**
    *   In `biomapper/core/mapping_executor.py`, remove the `get_strategy` method.
    *   In the `MappingExecutor.__init__` method, create an instance of the new `ConfigLoader`:
        ```python
        self.config_loader = ConfigLoader()
        ```
    *   In the `execute_strategy` method, replace the call to `self.get_strategy(...)` with `self.config_loader.load_strategy(...)`.
    *   Add the required import: `from .engine_components.config_loader import ConfigLoader`.

## Acceptance Criteria
*   The `ConfigLoader` class is implemented in `biomapper/core/engine_components/config_loader.py`.
*   The `get_strategy` method is removed from `MappingExecutor`.
*   `MappingExecutor` uses an instance of `ConfigLoader` to load strategy configurations.
*   The application's functionality remains unchanged.
