# Task: Integrate New Placeholder StrategyActions into UKBB-HPA YAML Strategy

## 1. Task Objective
Update the `UKBB_TO_HPA_BIDIRECTIONAL_EFFICIENT` mapping strategy within the `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/configs/mapping_strategies_config.yaml` file. This involves incorporating the newly created placeholder actions (`LoadEndpointIdentifiersAction`, `ReconcileBidirectionalAction`, `SaveBidirectionalResultsAction`) into the strategy's sequence with appropriate parameters.

## 2. Background & Context
Placeholder `StrategyAction` classes have been successfully created (see feedback file `2025-06-18-070000-feedback-refactor-mappingexecutor-ukbb-hpa-actions.md` and Memory `ee03b818-f83d-4435-b453-8d99344712ed`). These actions are:
-   `biomapper.core.strategy_actions.LoadEndpointIdentifiersAction`
-   `biomapper.core.strategy_actions.ReconcileBidirectionalAction`
-   `biomapper.core.strategy_actions.SaveBidirectionalResultsAction`

They are now ready to be configured within the `UKBB_TO_HPA_BIDIRECTIONAL_EFFICIENT` YAML strategy. This task focuses on modifying the YAML to orchestrate these actions, paving the way for their future implementation with actual logic from the `run_full_ukbb_hpa_mapping_bidirectional.py` script.

The general flow of the bidirectional mapping is:
1.  Load source (UKBB) identifiers.
2.  Load target (HPA) identifiers.
3.  Map source to target.
4.  Map target to source.
5.  Reconcile the bidirectional mappings.
6.  Save the results.

## 3. Detailed Steps & Requirements

1.  **Review Existing Strategy:**
    *   Examine the current structure of the `UKBB_TO_HPA_BIDIRECTIONAL_EFFICIENT` strategy in `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/configs/mapping_strategies_config.yaml`.
    *   Identify existing actions, particularly those related to graph mapping (likely `RunGraphMappingAction`).

2.  **Integrate `LoadEndpointIdentifiersAction`:**
    *   Add two instances of `LoadEndpointIdentifiersAction` at the beginning of the strategy:
        *   **Instance 1 (Loading UKBB Identifiers):**
            *   `action_class: biomapper.core.strategy_actions.LoadEndpointIdentifiersAction`
            *   `params:`
                *   `endpoint_name: "UKBB"` (Adjust if convention in `run_full_ukbb_hpa_mapping_bidirectional.py` differs)
                *   `output_context_key: "ukbb_input_identifiers"`
        *   **Instance 2 (Loading HPA Identifiers):**
            *   `action_class: biomapper.core.strategy_actions.LoadEndpointIdentifiersAction`
            *   `params:`
                *   `endpoint_name: "HPA"` (Adjust if convention differs)
                *   `output_context_key: "hpa_input_identifiers"`

3.  **Update `RunGraphMappingAction` Instances (if present):**
    *   The existing `RunGraphMappingAction` for UKBB -> HPA should now use `ukbb_input_identifiers` as its `input_ids_context_key`. Its `output_context_key` should be set to something like `"ukbb_to_hpa_mapping_results"`.
    *   The existing `RunGraphMappingAction` for HPA -> UKBB should use `hpa_input_identifiers` as its `input_ids_context_key`. Its `output_context_key` should be set to something like `"hpa_to_ukbb_mapping_results"`.
    *   Adjust these `output_context_key` names as needed for clarity and consistency.

4.  **Integrate `ReconcileBidirectionalAction`:**
    *   Add an instance of `ReconcileBidirectionalAction` after the two mapping actions.
    *   `action_class: biomapper.core.strategy_actions.ReconcileBidirectionalAction`
    *   `params:`
        *   `forward_mapping_key: "ukbb_to_hpa_mapping_results"` (must match output from UKBB->HPA mapping)
        *   `reverse_mapping_key: "hpa_to_ukbb_mapping_results"` (must match output from HPA->UKBB mapping)
        *   `output_reconciled_key: "reconciled_bidirectional_mappings"`

5.  **Integrate `SaveBidirectionalResultsAction`:**
    *   Add an instance of `SaveBidirectionalResultsAction` at the end of the strategy.
    *   `action_class: biomapper.core.strategy_actions.SaveBidirectionalResultsAction`
    *   `params:`
        *   `reconciled_data_key: "reconciled_bidirectional_mappings"` (must match output from reconciliation)
        *   `output_dir_key: "strategy_output_directory"` (This key is expected to be in the initial context provided to the `MappingExecutor.execute_strategy` method. The value will be the base path for saving results.)
        *   `csv_filename: "ukbb_hpa_bidirectional_reconciled.csv"`
        *   `json_summary_filename: "ukbb_hpa_bidirectional_summary.json"`

6.  **Verify YAML Structure and Context Flow:**
    *   Ensure the overall YAML syntax is correct.
    *   Double-check that `output_context_key` from one action correctly feeds into the `input_context_key` (or similarly named parameter) of subsequent actions.

## 4. Success Criteria & Validation
-   The `UKBB_TO_HPA_BIDIRECTIONAL_EFFICIENT` strategy in `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/configs/mapping_strategies_config.yaml` is successfully updated to include and configure the new placeholder actions.
-   The sequence of actions logically represents the bidirectional mapping pipeline.
-   All required parameters for the new actions are specified in the YAML.
-   The YAML file is syntactically valid.
-   The `MappingExecutor` should (conceptually) be able to parse this updated strategy definition without errors related to action configuration or missing parameters for the new actions.

## 5. Implementation Requirements
-   **Target File:** `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/configs/mapping_strategies_config.yaml`
-   Use appropriate tools for viewing and editing YAML.

## 6. Error Recovery Instructions
-   If YAML syntax errors are encountered, carefully validate the structure, indentation, and formatting. Online YAML validators can be helpful.
-   If unsure about specific parameter names or context keys for existing actions (like `RunGraphMappingAction`), make a reasonable assumption based on its likely function and document this. The primary focus is on correctly integrating the *new* actions.

## 7. Feedback Format
-   **Confirmation of YAML Update:** State whether the YAML file was successfully modified.
-   **Strategy Snippet:** Provide the updated YAML snippet for the `UKBB_TO_HPA_BIDIRECTIONAL_EFFICIENT` strategy.
-   **Context Key Flow:** Briefly describe or confirm the flow of data via context keys for the new actions.
-   **Potential Issues/Questions:** Note any ambiguities encountered or assumptions made (e.g., regarding parameters of existing actions or specific context key names).
-   **Confidence Assessment:** Your confidence that the YAML strategy is correctly configured for the new placeholder actions.
