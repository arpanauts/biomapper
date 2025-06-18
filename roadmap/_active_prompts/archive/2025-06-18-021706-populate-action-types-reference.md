# Prompt: Comprehensively Update ACTION_TYPES_REFERENCE.md with Implemented Strategy Actions

**Objective:**

Update the `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/docs/ACTION_TYPES_REFERENCE.md` file by comprehensively populating the "Implemented Action Types" section. This involves identifying all existing `StrategyAction` classes, their usage in YAML configurations, and documenting them according to the established format.

**Background:**

The `ACTION_TYPES_REFERENCE.md` document serves as a central reference for all available `StrategyAction` types within the Biomapper framework. The "Implemented Action Types" section currently contains placeholder content and needs to be populated with accurate information about all actions that are actually implemented and usable in mapping strategies.

**Key Files and Directories to Inspect:**

1.  **Action Implementations:** `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/biomapper/core/strategy_actions/`
    *   Each Python module (e.g., `some_action.py`) in this directory likely defines one or more classes inheriting from `BaseStrategyAction`.
2.  **Action Registration (for dynamic loading):** `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/biomapper/core/strategy_actions/__init__.py`
    *   The `__all__` list here indicates which action classes are intended for export and dynamic loading.
3.  **YAML Strategy Configurations:** `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/configs/mapping_strategies_config.yaml`
    *   This file shows how actions are used in practice. Look for `action_class_path` specifications and simple `type` aliases (e.g., `type: "CONVERT_IDENTIFIERS_LOCAL"`).
4.  **Target Documentation File:** `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/docs/ACTION_TYPES_REFERENCE.md`

**Tasks:**

1.  **Identify All Implemented Action Classes:**
    *   Scan the `biomapper/core/strategy_actions/` directory (excluding `base_action.py`, `__init__.py`, and `CLAUDE.md`).
    *   For each Python module found, identify the class(es) that inherit from `BaseStrategyAction`.
    *   Note the full class path for each action (e.g., `biomapper.core.strategy_actions.my_action_module.MyActionClass`).

2.  **Determine YAML Usage and Aliases:**
    *   Review `configs/mapping_strategies_config.yaml`.
    *   For each identified action class, determine if it's primarily invoked via its full `action_class_path` or if it has a common simple `type` alias (e.g., `CONVERT_IDENTIFIERS_LOCAL`). Some core actions might be aliased directly in the `MappingExecutor`'s logic if not found as a class path.

3.  **Gather Action Details:**
    *   For each action, determine:
        *   **Purpose:** A concise (1-2 sentence) description of what the action does.
        *   **Key Parameters:** List the main parameters the action expects in its `params` dictionary (from its `__init__` method or common YAML usage). Indicate if parameters are optional or required where obvious.
        *   **YAML Usage Example:** A short, illustrative YAML snippet showing how the action is configured within a strategy step, including its `action_class_path` or `type` alias and example parameters.

4.  **Format the Documentation:**
    *   Structure the information for each action using the following Markdown format (consistent with the existing template in `ACTION_TYPES_REFERENCE.md`):

        ```markdown
        *   **`[Full Python Class Path]`**
            *   **YAML Type Alias (if any):** `[SIMPLE_TYPE_ALIAS]` (or "N/A" if always used with class path)
            *   **Purpose:** [Concise description of the action's purpose.]
            *   **Key Parameters:**
                *   `param_name_1`: (type, e.g., string, list, boolean) [Description of parameter]
                *   `param_name_2`: (type) [Description of parameter] (optional)
                *   ...
            *   **Example YAML Usage:**
                ```yaml
                action:
                  # if using class path:
                  action_class_path: "biomapper.core.strategy_actions.module_name.ActionClass"
                  # if using type alias:
                  # type: "ACTION_ALIAS"
                  params:
                    param_name_1: "example_value"
                    param_name_2: true
                    # ... other example params
                ```
        ```

5.  **Update `ACTION_TYPES_REFERENCE.md`:**
    *   Replace the placeholder content within the "Implemented Action Types" section of `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/docs/ACTION_TYPES_REFERENCE.md` with the comprehensively compiled and formatted list of actions.
    *   Ensure the introductory text for the "Implemented Action Types" section (which explains dynamic loading and the need for updates) is retained or slightly adjusted if necessary.

**Deliverable:**

The primary deliverable is the updated content for the "Implemented Action Types" section of `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/docs/ACTION_TYPES_REFERENCE.md`. Provide this as a single block of Markdown text ready to be pasted into the document.

**Important Considerations:**

*   Be thorough. The goal is to capture *all* genuinely implemented and usable actions.
*   If an action appears to be defined but is not used in `mapping_strategies_config.yaml` or registered in `__init__.py`, make a note of it; it might be deprecated or experimental.
*   Focus on actions that are part of the core mapping framework. Helper classes or utilities within the `strategy_actions` directory that are not `BaseStrategyAction` subclasses should not be listed.
*   The list should be organized alphabetically by the action's primary identifier (e.g., class name or prominent alias).
