# Feature Idea: Refactor Code Duplication in MappingExecutor

## Core Concept / Problem
The feedback file `/home/ubuntu/biomapper/roadmap/_active_prompts/feedback/2025-06-05-033245-feedback-fix-metamapper-session-attr.md` noted apparent code duplication within `/home/ubuntu/biomapper/biomapper/core/mapping_executor.py`. Specifically, methods like `execute_yaml_strategy` appear to be defined multiple times. This can lead to confusion, maintenance overhead, and potential inconsistencies if changes are not applied to all duplicates.

## Intended Goal / Benefit
- Improve code clarity and maintainability of `mapping_executor.py`.
- Reduce the risk of introducing bugs due to inconsistent updates to duplicated code.
- Ensure a single source of truth for method implementations within the class.

## Initial Thoughts / Requirements / Context
- **File to Refactor:** `/home/ubuntu/biomapper/biomapper/core/mapping_executor.py`.
- **Task:** 
    - Identify all instances of duplicated methods or significant code blocks.
    - Consolidate duplicated logic into single, well-defined methods.
    - Ensure all call sites are updated to use the consolidated methods.
    - Verify that the refactoring does not alter existing functionality (other than fixing bugs related to inconsistent duplicates if any).
- This refactoring is a code quality improvement and does not directly add new features but supports overall project health.
