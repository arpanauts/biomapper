# Task: Organize Core Engine Components into Subfolder

## 1. Context and Background
As the `biomapper.core` package grows with refactored components from `mapping_executor.py` (like `StrategyHandler`, `PathFinder`, etc.), it's becoming beneficial to group these closely related "engine" or "service" modules into a dedicated subfolder for better organization and clarity.

## 2. Task Objective
1.  **Create Subfolder:** Create a new subfolder named `engine_components` within `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/biomapper/core/`.
    The new path will be: `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/biomapper/core/engine_components/`.
2.  **Move Modules:** Move the following existing modules from `biomapper/core/` into the new `biomapper/core/engine_components/` subfolder:
    *   `action_loader.py`
    *   `action_executor.py`
    *   `strategy_handler.py`
    *   `path_finder.py`
    *   `reversible_path.py`
3.  **Update Imports:** Update all import statements across the entire Biomapper codebase (including in `mapping_executor.py`, other core modules, tests, scripts, etc.) to reflect the new locations of these moved modules. For example, an import like `from biomapper.core.strategy_handler import StrategyHandler` would become `from biomapper.core.engine_components.strategy_handler import StrategyHandler`.
4.  **Verification:** Ensure the project still runs correctly and all tests pass after these changes.

## 3. Scope of Work
- Create the directory `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/biomapper/core/engine_components/`.
- Move the specified five Python files into this new directory.
- Perform a codebase-wide search and replace for import statements related to the moved files. Pay close attention to relative vs. absolute imports.
- Run `pytest` to confirm all tests pass.
- (Optional but recommended) Briefly run an example pipeline script (e.g., `run_full_ukbb_hpa_mapping.py`) to ensure basic functionality.

## 4. Deliverables
- The new directory structure with moved files.
- All necessary modifications to import statements throughout the codebase.
- A feedback file detailing the changes made and confirming test/pipeline execution.

## 5. Implementation Requirements
- Ensure that an `__init__.py` file exists or is created in `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/biomapper/core/engine_components/` if needed for Python to recognize it as a package (though typically for imports like `from biomapper.core.engine_components.module import Class`, it's not strictly necessary if `biomapper.core` is already a package, but good practice).
- Be meticulous with updating import paths. Errors here can break the application.

## 6. Feedback Requirements
Provide a feedback file in the standard format (`YYYY-MM-DD-HHMMSS-feedback-organize-core-components.md`) detailing:
- **Summary of Changes:** Confirmation of subfolder creation, file moves, and import updates.
- **Files Modified/Moved:** List all affected files.
- **Test Results:** Confirmation that `pytest` passes.
- **Validation:**
    - [ ] Subfolder `engine_components` created.
    - [ ] Specified modules moved to `engine_components`.
    - [ ] All import statements updated correctly.
    - [ ] All tests pass.
- **Potential Issues/Risks:** Any difficulties encountered with import resolution.
- **Completed Subtasks:** Checklist of work done.
