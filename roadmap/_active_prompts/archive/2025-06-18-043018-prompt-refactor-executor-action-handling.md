# Task: Refactor MappingExecutor for Action Handling & Fix Registration Error

## 1. Context and Background
The primary mapping logic in Biomapper is orchestrated by `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/biomapper/core/mapping_executor.py`. This file has grown to over 5000 lines, making it difficult to maintain and for LLMs to process effectively.

A recent fix for `StrategyAction` import errors (detailed in feedback `2025-06-18-042501-feedback-fix-strategyaction-import-error.md`) revealed a subsequent issue: the `MappingExecutor` fails to correctly register or instantiate strategy actions defined in YAML configurations via `action_class_path`. The `run_full_ukbb_hpa_mapping.py` script encounters this error after the import fixes.

The goal is to begin refactoring `mapping_executor.py` by extracting the logic related to strategy definition parsing and action discovery/loading/execution into a new, more focused module. This refactoring effort must also resolve the identified action registration error.

## 2. Task Objective
1.  **Refactor:** Identify and extract the components within `mapping_executor.py` responsible for:
    *   Loading strategy definitions (e.g., from the database via `metamapper_db_url`).
    *   Parsing the `actions` list within a strategy configuration.
    *   Dynamically discovering, importing, and instantiating `StrategyAction` classes based on the `action_class_path` specified in the strategy YAML.
    *   Managing the execution sequence of these actions.
    Move this logic into one or more new, well-defined Python modules/classes within the `biomapper.core` package (e.g., `biomapper.core.strategy_handler.py` or similar).
2.  **Fix Bug:** Ensure the refactored action handling mechanism correctly resolves the current action registration/instantiation error, allowing strategies with custom actions (defined by `action_class_path`) to be loaded and executed by `run_full_ukbb_hpa_mapping.py`.
3.  **Integrate:** Update the main `mapping_executor.py` to utilize these new refactored components.

## 3. Scope of Work
- **Analysis:**
    - Thoroughly analyze `mapping_executor.py` to pinpoint all code related to fetching strategy configurations, parsing strategy steps (actions), dynamically loading action classes, and instantiating them.
    - Understand how `ActionContext` is created and passed between actions.
- **Design New Module(s):**
    - Propose a clean structure for the new module(s) (e.g., a `StrategyHandler` class, an `ActionLoader` class, etc.).
    - Define clear interfaces between the main `MappingExecutor` and these new components.
- **Implementation:**
    - Create the new Python file(s) in `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/biomapper/core/`.
    - Carefully move the identified logic from `mapping_executor.py` to the new module(s).
    - Implement the fix for the action registration error within this new, refactored code. This might involve correcting how class paths are resolved, how modules are imported, or how classes are instantiated.
    - Modify `mapping_executor.py` to delegate strategy and action handling responsibilities to the new module(s). The aim is to reduce the size and complexity of `mapping_executor.py` in this area.
- **Testing:**
    - Ensure all existing unit tests for `MappingExecutor` that cover strategy execution and action handling continue to pass after the refactoring. Update them as necessary to reflect the new structure.
    - Write new unit tests specifically for the extracted module(s) to ensure their functionality is thoroughly tested in isolation.
    - Verify that `scripts/main_pipelines/run_full_ukbb_hpa_mapping.py` can now successfully load the strategy (e.g., `UKBB_HPA_MAPPING_STRATEGY_V1` from `configs/mapping_strategies_config.yaml`) and proceed past the point where the action registration error previously occurred. The script should ideally start executing the actions.

## 4. Deliverables
- The modified (and now smaller in the relevant sections) `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/biomapper/core/mapping_executor.py`.
- New Python file(s) for the refactored strategy/action handling logic (e.g., `biomapper/core/strategy_handler.py`).
- Updated and new unit tests.
- A feedback file detailing the changes, design decisions, bug fix verification, and test results.

## 5. Implementation Requirements
- Adhere to Python best practices (PEP 8, clear naming, good documentation/comments).
- Ensure the dynamic loading of action classes is robust and secure.
- Maintain existing functionality of the `MappingExecutor` not directly related to this refactoring.
- Changes should be well-encapsulated.

## 6. Error Recovery Instructions
- Work iteratively. Commit changes frequently.
- If major issues arise, be prepared to revert to a stable state and re-evaluate the approach for the problematic section.
- Ensure comprehensive logging within the new components to aid debugging.

## 7. Feedback Requirements
Provide a feedback file in the standard format (`YYYY-MM-DD-HHMMSS-feedback-refactor-executor-action-handling.md`) detailing:
- **Summary of Changes:** Overview of the refactoring and bug fix.
- **Design of New Module(s):** Explanation of the new structure and classes.
- **Bug Fix Details:** How the action registration error was resolved.
- **Files Modified/Created:** List all affected files.
- **Test Results:** Summary of `pytest` execution, highlighting new and updated tests. Confirmation that `run_full_ukbb_hpa_mapping.py` progresses.
- **Validation:**
    - [ ] Action registration error is resolved.
    - [ ] `run_full_ukbb_hpa_mapping.py` successfully loads and starts executing strategies with `action_class_path` actions.
    - [ ] Relevant sections of `mapping_executor.py` are now delegated to new modules.
- **Potential Issues/Risks:** Any new concerns or areas for future improvement.
- **Completed Subtasks:** Checklist of work done.
- **Issues Encountered:** Any problems faced.
- **Next Action Recommendation:** What should be focused on next in the `MappingExecutor` refactoring or pipeline validation.
- **Confidence Assessment:** Confidence in the refactoring and fix.
- **Environment Changes:** Files created/moved.
- **Lessons Learned:** Insights from the task.
