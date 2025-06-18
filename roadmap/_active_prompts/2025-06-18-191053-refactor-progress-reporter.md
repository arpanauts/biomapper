# Task: Refactor Progress Reporting into a Dedicated `ProgressReporter` Component

## Objective
To further modularize the `MappingExecutor`, extract the progress reporting logic into a dedicated `ProgressReporter` class. This will improve separation of concerns by isolating the mechanism for reporting progress from the core mapping orchestration logic.

## Current Implementation
The `MappingExecutor` currently has a private method `_report_progress` that handles sending progress updates. This logic is tightly coupled with the executor's implementation.

## Refactoring Steps

1.  **Create the `ProgressReporter` Class:**
    *   Create a new file: `biomapper/core/engine_components/progress_reporter.py`.
    *   Inside this file, define a `ProgressReporter` class.
    *   The class should have an `__init__` method that accepts an optional `progress_callback` function.
    *   Create a public method `report(self, progress_data: dict)` that will contain the logic from the current `_report_progress` method.

2.  **Update `MappingExecutor`:**
    *   In `biomapper/core/mapping_executor.py`, remove the `_report_progress` method.
    *   In the `MappingExecutor.__init__` method, instantiate the new `ProgressReporter`:
        ```python
        self.progress_reporter = ProgressReporter(progress_callback=self.progress_callback)
        ```
    *   Update all calls from `self._report_progress(...)` to `self.progress_reporter.report(...)` throughout the `MappingExecutor` class.
    *   Add the necessary import: `from .engine_components.progress_reporter import ProgressReporter`.

## Acceptance Criteria
*   The `ProgressReporter` class is implemented in `biomapper/core/engine_components/progress_reporter.py`.
*   The `_report_progress` method is removed from `MappingExecutor`.
*   `MappingExecutor` uses an instance of `ProgressReporter` for all progress reporting.
*   The application's functionality remains unchanged.
