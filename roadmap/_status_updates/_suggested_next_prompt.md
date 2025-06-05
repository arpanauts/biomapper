# Suggested Next Prompt for Biomapper Development

## 1. Context Brief

We have recently focused on defining and documenting a new system for YAML-defined mapping strategies in Biomapper. This involved creating technical notes on the strategy architecture (`/home/ubuntu/biomapper/roadmap/technical_notes/core_mapping_logic/yaml_defined_mapping_strategies.md`) and a specific guide for configuring UKBB/HPA/QIN protein mappings using these strategies (`/home/ubuntu/biomapper/roadmap/guides/configuring_ukbb_hpa_qin_mapping.md`). 

**Recent Update:** The `AttributeError` related to `metamapper_session` access within `MappingExecutor` has been **resolved** (see feedback `/home/ubuntu/biomapper/roadmap/_active_prompts/feedback/2025-06-05-033245-feedback-fix-metamapper-session-attr.md`). A new backlog item to address code duplication in `MappingExecutor` has also been created (`/home/ubuntu/biomapper/roadmap/0_backlog/refactor_mapping_executor_code_duplication.md`).

The next crucial step is to verify this fix and then proceed with implementing the core components that will execute YAML-defined strategies.

## 2. Initial Steps

1.  **Review Project Context:** Begin by thoroughly reviewing the main project context document: `/home/ubuntu/biomapper/CLAUDE.md`.
2.  **Review Latest Status:** Familiarize yourself with the most recent status update: `/home/ubuntu/biomapper/roadmap/_status_updates/2025-06-04-yaml-strategies-documentation-and-planning.md`.
3.  **Review Core Strategy Documents:**
    *   `/home/ubuntu/biomapper/roadmap/technical_notes/core_mapping_logic/yaml_defined_mapping_strategies.md` (for the overall strategy concept).
    *   `/home/ubuntu/biomapper/roadmap/guides/configuring_ukbb_hpa_qin_mapping.md` (for a concrete application and example YAML structure).

## 3. Work Priorities

The primary goals for the next session are to first verify the recent `MappingExecutor` fix and then to begin the implementation of the YAML-defined mapping strategy execution system. This involves:

1.  **Verify `MappingExecutor` Fix:**
    *   Run the test script: `poetry run python scripts/test_protein_yaml_strategy.py`.
    *   Confirm that the `AttributeError` related to `metamapper_session` is no longer present.
    *   Analyze any subsequent errors or output to guide the next steps in `MappingExecutor`'s YAML strategy handling.
2.  **Address Code Duplication in `MappingExecutor` (Optional - Low Priority for immediate next session, but keep in mind):**
    *   Review the code duplication noted in `/home/ubuntu/biomapper/roadmap/_active_prompts/feedback/2025-06-05-033245-feedback-fix-metamapper-session-attr.md` and the backlog item `/home/ubuntu/biomapper/roadmap/0_backlog/refactor_mapping_executor_code_duplication.md`.
    *   Consider refactoring if it impacts current development or clarity, otherwise, it can be a separate task.
3.  **Update `populate_metamapper_db.py` for Strategies:**
    *   Modify `/home/ubuntu/biomapper/scripts/populate_metamapper_db.py` to parse the new `mapping_strategies` section from entity configuration YAML files (e.g., `/home/ubuntu/biomapper/configs/protein_config.yaml`).
    *   Define how these strategies will be stored in `metamapper.db`. This might involve new SQLAlchemy models or adapting existing ones. Ensure the structure can store the ordered steps, `action.type`, and parameters for each strategy.
    *   Add validation for the `mapping_strategies` section to the `ConfigurationValidator`.
4.  **Enhance `MappingExecutor` for Strategy Execution:**
    *   Modify `/home/ubuntu/biomapper/biomapper/core/mapping_executor.py` to load a named mapping strategy (e.g., from `metamapper.db`).
    *   Implement the core loop within `MappingExecutor` to iterate through the steps of a loaded strategy.
    *   Design and implement the dispatch mechanism that takes an `action.type` string from a strategy step and calls the corresponding Python handler module/function.
5.  **Develop Initial Python Action Handler Modules:**
    *   Create a new directory, e.g., `/home/ubuntu/biomapper/biomapper/core/strategy_actions/`.
    *   Implement the first set of action handlers as Python modules/functions. Focus on:
        *   `CONVERT_IDENTIFIERS_LOCAL`: Takes an input list of identifiers, an `endpoint_context` (SOURCE or TARGET), and an `output_ontology_type`. It uses the endpoint's property configurations to convert identifiers locally within that endpoint's data.
        *   `EXECUTE_MAPPING_PATH`: Takes an input list of identifiers and a `path_name`. It executes a pre-defined mapping path (from `metamapper.db`) using the `MappingExecutor`'s existing path execution logic.

## 4. References

-   **Status Update:** `/home/ubuntu/biomapper/roadmap/_status_updates/2025-06-04-yaml-strategies-documentation-and-planning.md`
-   **YAML Strategy Definition:** `/home/ubuntu/biomapper/roadmap/technical_notes/core_mapping_logic/yaml_defined_mapping_strategies.md`
-   **UKBB/HPA/QIN Guide (Example Strategy):** `/home/ubuntu/biomapper/roadmap/guides/configuring_ukbb_hpa_qin_mapping.md`
-   **Protein Configuration File (to be augmented with strategies):** `/home/ubuntu/biomapper/configs/protein_config.yaml`
-   **Database Population Script (to be modified):** `/home/ubuntu/biomapper/scripts/populate_metamapper_db.py`
-   **Mapping Executor (to be modified):** `/home/ubuntu/biomapper/biomapper/core/mapping_executor.py`
-   **Database Models (may need new models for strategies):** `/home/ubuntu/biomapper/biomapper/db/models.py`

## 5. Workflow Integration

For this next phase, consider the following workflow:

1.  **Task: Verify `MappingExecutor` Fix**
    *   **Claude Prompt Idea:** "The `AttributeError` in `MappingExecutor` should now be fixed. Please run `poetry run python scripts/test_protein_yaml_strategy.py` from the `/home/ubuntu/biomapper` directory. Let's analyze the output to confirm the fix and see what the next error or behavior is."
2.  **Task: Update `populate_metamapper_db.py`**
    *   **Claude Prompt Idea:** "Please modify `/home/ubuntu/biomapper/scripts/populate_metamapper_db.py` to parse a new top-level `mapping_strategies` section in YAML configuration files. This section will contain a list of strategies, each with a name, description, and a list of ordered steps. Each step has a `step_id`, `description`, `action` (with `type` and other parameters). Design or adapt SQLAlchemy models in `/home/ubuntu/biomapper/biomapper/db/models.py` to store these strategies and their steps in `metamapper.db`. Update the `ConfigurationValidator` to validate this new section."
3.  **Task: Enhance `MappingExecutor`**
    *   **Claude Prompt Idea:** "Please enhance `/home/ubuntu/biomapper/biomapper/core/mapping_executor.py`. Add a method like `execute_yaml_strategy(strategy_name: str, input_ids: List[str], source_ontology: str, target_ontology: str)`. This method should load the named strategy from `metamapper.db`, iterate through its steps, and dispatch each `action.type` to a handler function (placeholder handlers initially). Define how data (the list of IDs) is passed between steps."
4.  **Task: Implement `CONVERT_IDENTIFIERS_LOCAL` Action Handler**
    *   **Claude Prompt Idea:** "Create a Python module in `/home/ubuntu/biomapper/biomapper/core/strategy_actions/` for the `CONVERT_IDENTIFIERS_LOCAL` action type. It should accept a list of input identifiers, an `endpoint_context` ('SOURCE' or 'TARGET'), an `input_ontology_type` (optional, may be inferred), and an `output_ontology_type`. The handler should use the `MappingExecutor`'s access to endpoint configurations and data to perform local identifier conversion within the specified endpoint context."
