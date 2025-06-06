# Prompt: Update Project Documentation for YAML Strategies and `is_required` Feature

**Objective:**
Update all relevant project documentation to accurately reflect the implementation of YAML-defined mapping strategies, the new action handlers, and the `is_required` field for optional strategy steps.

**Context:**
Biomapper has recently incorporated a powerful YAML-based system for defining multi-step mapping strategies, executed by the `MappingExecutor`. Key features include various action types (`CONVERT_IDENTIFIERS_LOCAL`, `EXECUTE_MAPPING_PATH`, `FILTER_IDENTIFIERS_BY_TARGET_PRESENCE`) and an `is_required` flag on strategy steps to control execution flow on step failure. Comprehensive documentation is needed for users and developers.

**Key Tasks:**

1.  **Update YAML Schema Documentation:**
    *   **Location:** (Identify where YAML schema/structure is or should be documented, e.g., in `docs/`, a dedicated `SCHEMA.md`, or within strategy configuration examples.)
    *   **Content:**
        *   Clearly document the `is_required` field for `mapping_strategy_steps`: its purpose, boolean type, default value (`true`), and behavior when set to `false`.
        *   Provide clear examples of how to use `is_required` in a YAML strategy definition.
        *   Ensure documentation for `action_parameters` for each action type (`CONVERT_IDENTIFIERS_LOCAL`, `EXECUTE_MAPPING_PATH`, `FILTER_IDENTIFIERS_BY_TARGET_PRESENCE`) is complete and accurate, reflecting the implemented handlers.

2.  **Update `MappingExecutor` Documentation:**
    *   **Location:** Docstrings within `biomapper/core/mapping_executor.py`, and potentially Sphinx-generated API documentation.
    *   **Content:**
        *   Update the docstring for `execute_yaml_strategy` to explain its overall functionality, including how it handles `is_required`.
        *   Ensure docstrings for the (now implemented) private action handlers (`_handle_convert_identifiers_local`, etc.) clearly describe their function, parameters, and return values if they are to be part of internal API documentation.
        *   Document the structure and content of the `MappingResultBundle`.

3.  **Update User Guides / Tutorials (if applicable):**
    *   **Location:** (Identify any user-facing guides, tutorials, or README sections that explain how to define and use mapping strategies.)
    *   **Content:**
        *   Add a section or update existing sections on defining YAML mapping strategies.
        *   Include examples demonstrating the use of different action types and the `is_required` flag for creating robust and flexible mapping workflows.
        *   Explain how to interpret the results from `MappingResultBundle`.

4.  **Update README.md:**
    *   **Location:** `/home/ubuntu/biomapper/README.md`
    *   **Content:**
        *   Briefly mention the YAML strategy execution capabilities as a key feature.
        *   Link to more detailed documentation if appropriate.

5.  **Update Developer Documentation (if applicable):**
    *   **Location:** (Any internal design documents or developer guides.)
    *   **Content:**
        *   Document the architecture of the `MappingExecutor` and its interaction with YAML strategies and action handlers.
        *   Explain how to add new action handlers in the future.

**Acceptance Criteria:**
*   Documentation for the `is_required` field in YAML strategy steps is clear, accurate, and includes examples.
*   Documentation for `action_parameters` for all implemented action types is complete.
*   `MappingExecutor` and `MappingResultBundle` documentation is updated and accurate.
*   User-facing guides (if any) effectively explain how to create and use YAML strategies, including optional steps.
*   README and other relevant documents reflect the new capabilities.
*   All documentation is well-written, easy to understand, and consistent with existing project documentation standards.

**Relevant Files/Locations:**
*   `biomapper/core/mapping_executor.py` (for docstrings)
*   `docs/` directory (for Sphinx documentation, user guides, API docs)
*   `README.md`
*   Example YAML configuration files (as part of documentation or linked)
*   Any existing schema definition files (e.g., `SCHEMA.md`).

**Notes/Considerations:**
*   Strive for clarity and provide practical examples.
*   Consider the different audiences for documentation (end-users vs. developers).
*   Ensure consistency in terminology and formatting.
*   This task is best performed after the action handlers are implemented and the `is_required` feature is fully tested, to ensure documentation reflects the final state.
