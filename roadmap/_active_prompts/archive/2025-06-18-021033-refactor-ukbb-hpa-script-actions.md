# Task: Refactor UKBB-HPA Pipeline Script to Utilize Modular Strategy Actions

**Source Prompt Reference:** This task is defined by Cascade based on USER request to refactor the UKBB-HPA pipeline.

## 1. Task Objective
Refactor the `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/scripts/main_pipelines/run_full_ukbb_hpa_mapping_bidirectional.py` script and its associated YAML strategy (`UKBB_TO_HPA_BIDIRECTIONAL_EFFICIENT` in `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/configs/mapping_strategies_config.yaml`). The goal is to move custom logic from the Python script into modular `StrategyAction` classes and update the YAML strategy accordingly. The refactored pipeline should produce the same CSV and JSON summary outputs as the original script and be configured to run on full datasets.

## 2. Prerequisites
-   [ ] The `MappingExecutor` class has been successfully refactored to include robust execution features directly (as per feedback in `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/roadmap/_active_prompts/feedback/2025-06-15-175500-feedback-simplify-mapping-executor.md`).
-   [ ] The `protein_config.yaml` file (located in `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/configs/`) should have its `UKBB_PROTEIN` and `HPA_OSP_PROTEIN` endpoint definitions (specifically `connection_details.file_path` or similar) pointing to the **full dataset files**, not sample/test files.
    -   **Action:** Before starting, verify these paths. If they need updating, modify `protein_config.yaml` and then run `python /home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/scripts/populate_metamapper_db.py` to update `metamapper.db`. Document any changes made to `protein_config.yaml` in your feedback.
-   [ ] Familiarity with the `StrategyAction` development guide (see `_starter_prompt.md` if available, or `biomapper.core.strategy_actions.base_action.BaseStrategyAction`).

## 3. Context from Previous Attempts (if applicable)
N/A - This is a new refactoring task.

## 4. Task Decomposition

1.  **Create/Update `LoadEndpointIdentifiersAction`:**
    *   **Location:** `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/biomapper/core/strategy_actions/load_endpoint_identifiers_action.py` (create if not exists).
    *   **Functionality:** This action should load identifiers from a specified endpoint.
    *   **`__init__(self, params: dict)`:**
        *   Accept `endpoint_name` (str, required): Name of the endpoint to load from.
        *   Accept `ontology_type_name` (str, optional): Specific ontology type to load. If not provided, consider defaulting to the endpoint's primary ontology or a configured default.
        *   Accept `output_context_key` (str, required, e.g., "initial_source_identifiers"): The key under which the list of loaded identifiers will be stored in the execution context.
    *   **`async execute(self, context: dict, executor: 'MappingExecutor') -> dict:`:**
        *   Use `executor.load_endpoint_identifiers(endpoint_name=self.endpoint_name, ontology_type_name=self.ontology_type_name)` to fetch identifiers.
        *   Store the returned list in `context[self.output_context_key]`.
        *   Return the updated `context`.

2.  **Create `FormatAndSaveResultsAction`:**
    *   **Location:** `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/biomapper/core/strategy_actions/format_and_save_results_action.py` (create).
    *   **Functionality:** This action will replicate the results processing, DataFrame creation, CSV saving, and JSON summary saving logic currently in `run_full_ukbb_hpa_mapping_bidirectional.py` (approx. lines 224-261).
    *   **`__init__(self, params: dict)`:**
        *   Accept `mapped_data_context_key` (str, required, e.g., "mapped_identifiers_with_source"): Key for mapped data in context.
        *   Accept `unmapped_source_context_key` (str, required, e.g., "final_unmapped_source"): Key for unmapped source data.
        *   Accept `new_target_context_key` (str, optional, e.g., "final_new_targets"): Key for new target data.
        *   Accept `source_id_column_name` (str, default "source_id"): Column name for source IDs in DataFrame.
        *   Accept `target_id_column_name` (str, default "target_id"): Column name for target IDs in DataFrame.
        *   Accept `mapping_type_column_name` (str, default "mapping_type"): Column name for mapping type.
        *   Accept `output_csv_path` (str, required): Path to save the CSV file. Should support `${OUTPUT_DIR}`.
        *   Accept `output_json_summary_path` (str, required): Path to save the JSON summary. Should support `${OUTPUT_DIR}`.
        *   Accept `execution_id_context_key` (str, optional, e.g., "execution_id"): Key for execution ID in context.
    *   **`async execute(self, context: dict, executor: 'MappingExecutor') -> dict:`:**
        *   Retrieve data from context using the provided keys.
        *   Replicate the DataFrame creation logic from the script.
        *   Resolve `${OUTPUT_DIR}` in `output_csv_path` and `output_json_summary_path` (e.g., using `os.path.expandvars` if `OUTPUT_DIR` is an env var, or via `executor.resolve_path_param(path_param)` if such a utility exists/is added).
        *   Save the DataFrame to CSV.
        *   Replicate the summary statistics calculation and logging.
        *   Save the JSON summary file.
        *   Return the context (possibly updated with paths to saved files or summary stats if needed by later actions).

3.  **Update YAML Strategy (`UKBB_TO_HPA_BIDIRECTIONAL_EFFICIENT`):**
    *   **File:** `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/configs/mapping_strategies_config.yaml`
    *   **Modifications:**
        *   **Add First Step:** Insert the `LoadEndpointIdentifiersAction` as the very first step.
            *   `action_class_path`: `biomapper.core.strategy_actions.load_endpoint_identifiers_action.LoadEndpointIdentifiersAction`
            *   `params`:
                *   `endpoint_name: "${SOURCE_ENDPOINT_NAME}"` (This implies SOURCE_ENDPOINT_NAME needs to be available as a strategy execution parameter or resolved globally) - For now, assume it can be hardcoded if not easily parameterizable: `"UKBB_PROTEIN"`
                *   `ontology_type_name: "PROTEIN_UNIPROTKB_AC_ONTOLOGY"` (Matches `default_source_ontology_type`)
                *   `output_context_key: "initial_source_identifiers"`
        *   **Replace/Augment Result Handling:**
            *   Review existing steps `S5_GENERATE_MAPPING_SUMMARY`, `S6_EXPORT_RESULTS`, `S7_GENERATE_DETAILED_REPORT`, `S8_VISUALIZE_FLOW`.
            *   Add a new step using `FormatAndSaveResultsAction` towards the end of the strategy to handle the CSV and JSON summary outputs previously managed by the script. This might replace `S6_EXPORT_RESULTS` if the new action covers CSV export, or be added alongside. Ensure the input context keys for this action align with what previous steps in the strategy produce.
            *   Ensure all file path parameters in these actions (e.g., `output_file` in existing actions, `output_csv_path`, `output_json_summary_path` in the new action) use a placeholder like `${OUTPUT_DIR}/filename.ext`.
        *   The `input_from` parameter in existing actions like `S4_CONVERT_TO_HPA_GENES` might need to be adjusted if the context keys change due to the new `LoadEndpointIdentifiersAction` or other modifications. For example, if `S1_BIDIRECTIONAL_UNIPROT_MATCH` expects its input from `initial_source_identifiers`, ensure this is provided.

4.  **Refactor `run_full_ukbb_hpa_mapping_bidirectional.py` Script:**
    *   **File:** `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/scripts/main_pipelines/run_full_ukbb_hpa_mapping_bidirectional.py`
    *   **Modifications:**
        *   Remove the explicit call to `executor.load_endpoint_identifiers(...)` (lines 197-206 approx.). This is now handled by the first step in the YAML strategy.
        *   Remove the custom result processing, DataFrame creation, CSV saving, and JSON summary saving logic (lines 224-261 approx.). This is now handled by the `FormatAndSaveResultsAction` in the YAML strategy.
        *   Ensure the `OUTPUT_RESULTS_DIR` (script variable, line 66) is made available for `${OUTPUT_DIR}` expansion within the strategy. One way is to pass it as a parameter to `executor.execute_yaml_strategy_robust` if the executor supports substituting such parameters into action configs. Alternatively, ensure `os.environ['OUTPUT_DIR']` (set on line 135) is accessible and used by actions for path expansion. The executor or actions should be responsible for resolving this.
        *   The script should now be much simpler: initialize executor, (optionally) load input identifiers if the strategy *doesn't* do it (but the goal is for the strategy to do it), execute the YAML strategy, and perhaps log final metrics.

## 5. Implementation Requirements
-   **Action Class Paths:** Use fully qualified paths for `action_class_path` in the YAML (e.g., `biomapper.core.strategy_actions.new_action.NewAction`).
-   **Parameter Expansion:** Ensure that `${OUTPUT_DIR}` in YAML action parameters is correctly expanded to the path defined in the script (e.g., `/home/ubuntu/biomapper/data/results/`). This might require a utility in the `MappingExecutor` or `BaseStrategyAction` to resolve such placeholders from environment variables or executor-level parameters. If `os.path.expandvars` is used, ensure `OUTPUT_DIR` is set as an environment variable accessible to the action.
-   **Context Keys:** Be consistent with context keys used to pass data between actions.
-   **Backward Compatibility:** While refactoring, try not to break other strategies, though the focus is on `UKBB_TO_HPA_BIDIRECTIONAL_EFFICIENT`.
-   **Testing:** After changes, manually run the `run_full_ukbb_hpa_mapping_bidirectional.py` script. Verify that:
    *   It runs without errors.
    *   The CSV output (`ukbb_to_hpa_mapping_results_efficient.csv` or similar, depending on the final path in YAML) is generated correctly and matches the structure of the original script's output.
    *   The JSON summary output (`full_ukbb_to_hpa_mapping_bidirectional_summary.json` or similar) is generated and contains the expected summary statistics.
    *   Other outputs from the strategy (detailed report, flow visualization) are still generated correctly.

## 6. Error Recovery Instructions
-   **Import Errors:** Ensure new action classes are correctly placed and importable. Check `sys.path` if necessary, though standard project structure should handle this.
-   **YAML Parsing Errors:** Validate YAML syntax carefully.
-   **Action Execution Errors:** Test each new/modified action individually if possible, or add detailed logging within actions during development.
-   **Path Resolution Errors:** If `${OUTPUT_DIR}` doesn't expand, investigate how parameters are passed to actions and how paths are resolved.

## 7. Success Criteria and Validation
Task is complete when:
-   [ ] `LoadEndpointIdentifiersAction` is created and functional.
-   [ ] `FormatAndSaveResultsAction` (or equivalent) is created and functional, replicating the script's CSV and JSON summary output logic.
-   [ ] `mapping_strategies_config.yaml` is updated for `UKBB_TO_HPA_BIDIRECTIONAL_EFFICIENT` strategy to use the new actions and `${OUTPUT_DIR}` for paths.
-   [ ] `run_full_ukbb_hpa_mapping_bidirectional.py` is refactored to remove the delegated logic.
-   [ ] Running the modified script successfully executes the mapping and produces CSV and JSON summary outputs identical in structure and content (for a given input) to those produced by the original script.
-   [ ] The script runs using full datasets (verified by checking `protein_config.yaml` paths).

## 8. Feedback Requirements
Create a detailed Markdown feedback file at:
`/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/roadmap/_active_prompts/feedback/YYYY-MM-DD-HHMMSS-feedback-refactor-ukbb-hpa-script-actions.md`

**Mandatory Feedback Sections:**
-   **Execution Status:** [COMPLETE_SUCCESS | PARTIAL_SUCCESS | FAILED_WITH_RECOVERY_OPTIONS | FAILED_NEEDS_ESCALATION]
-   **Completed Subtasks:** Checklist from "Task Decomposition".
-   **Details of Changes:**
    -   Paths to new/modified action files.
    -   Diff or summary of changes to `mapping_strategies_config.yaml` for the `UKBB_TO_HPA_BIDIRECTIONAL_EFFICIENT` strategy.
    -   Diff or summary of changes to `run_full_ukbb_hpa_mapping_bidirectional.py`.
    -   Confirmation of `protein_config.yaml` paths for full datasets (and if `populate_metamapper_db.py` was run).
-   **Strategy for `${OUTPUT_DIR}` Resolution:** Briefly explain how `${OUTPUT_DIR}` in YAML is resolved by the actions.
-   **Issues Encountered:** Detailed error descriptions with context.
-   **Testing Performed:** Describe how the refactored pipeline was tested and confirm output validation.
-   **Next Action Recommendation:** Specific follow-up needed.
-   **Confidence Assessment:** Quality, testing coverage, risk level.
-   **Environment Changes:** Any files created, permissions changed, etc.
-   **Lessons Learned:** Patterns that worked or should be avoided.
