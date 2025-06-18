# Task: Implement Logic for UKBB-HPA Strategy Actions

## 1. Task Objective
Replace the placeholder logic in the `LoadEndpointIdentifiersAction`, `ReconcileBidirectionalAction`, and `SaveBidirectionalResultsAction` classes with the actual implementation logic extracted from the `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/scripts/main_pipelines/run_full_ukbb_hpa_mapping_bidirectional.py` script.

## 2. Background & Context
The project has successfully refactored the `MappingExecutor` to use a YAML-based strategy system. Placeholder actions have been created and configured in the `UKBB_TO_HPA_BIDIRECTIONAL_EFFICIENT` strategy (see Memory `b6d49c4f-0cba-43cf-a6b0-53e27f40be10`). This task involves migrating the core business logic from the original monolithic script into these modular, reusable `StrategyAction` classes.

**Target Script for Logic Extraction:**
- `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/scripts/main_pipelines/run_full_ukbb_hpa_mapping_bidirectional.py`

**Target Action Files for Implementation:**
- `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/biomapper/core/strategy_actions/load_endpoint_identifiers_action.py`
- `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/biomapper/core/strategy_actions/reconcile_bidirectional_action.py`
- `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/biomapper/core/strategy_actions/save_bidirectional_results_action.py`

## 3. Detailed Steps & Requirements

### 3.1. Implement `LoadEndpointIdentifiersAction`
1.  **Analyze Source:** In `run_full_ukbb_hpa_mapping_bidirectional.py`, locate the code that loads the initial list of identifiers for an endpoint (e.g., `db_manager.get_all_identifiers_for_endpoint('UKBB')`).
2.  **Modify Action:** Open `load_endpoint_identifiers_action.py`.
3.  **Implement `async execute`:**
    *   Replace the placeholder logic (dummy list creation).
    *   Use the `executor.db_manager` instance to call the appropriate method for fetching identifiers.
    *   The `endpoint_name` for the query should come from `self.endpoint_name`, which was set during `__init__`.
    *   Store the returned list of identifiers into the `context` dictionary using `self.output_context_key` as the key.
    *   Ensure logging is in place to indicate which endpoint is being loaded.

### 3.2. Implement `ReconcileBidirectionalAction`
1.  **Analyze Source:** In the source script, find the section that processes the results of the forward (UKBB->HPA) and reverse (HPA->UKBB) mappings. This logic identifies pairs that successfully mapped in both directions. It likely involves iterating through mapping results, checking for reciprocal pairs, and compiling a new data structure.
2.  **Modify Action:** Open `reconcile_bidirectional_action.py`.
3.  **Implement `async execute`:**
    *   Replace the placeholder logic.
    *   Retrieve the forward and reverse mapping results from the `context` using `self.forward_mapping_key` and `self.reverse_mapping_key`. The data will likely be in the format produced by `RunGraphMappingAction`.
    *   Port the reconciliation logic from the script into this method.
    *   The final reconciled data structure (e.g., a list of reconciled pair objects/dictionaries, along with statistics) should be stored in the `context` under the key `self.output_reconciled_key`.

### 3.3. Implement `SaveBidirectionalResultsAction`
1.  **Analyze Source:** In the source script, locate the code responsible for saving the final, reconciled results. This typically involves creating a Pandas DataFrame, saving it to a CSV file, generating a JSON summary of the run, and saving that to a JSON file.
2.  **Modify Action:** Open `save_bidirectional_results_action.py`.
3.  **Implement `async execute`:**
    *   Replace the placeholder logic.
    *   Retrieve the reconciled data from `context[self.reconciled_data_key]` and the output directory path from `context[self.output_dir_key]`.
    *   Implement the logic to:
        *   Convert the reconciled data into a Pandas DataFrame.
        *   Construct the full output path for the CSV file using the output directory and `self.csv_filename`.
        *   Save the DataFrame to CSV.
        *   Generate the summary dictionary/JSON object.
        *   Construct the full output path for the JSON summary file using the output directory and `self.json_summary_filename`.
        *   Save the summary to the JSON file.
    *   Ensure all necessary imports (e.g., `pandas`, `os`) are present.

## 4. Success Criteria & Validation
-   The placeholder logic in all three action files is replaced with functional, ported code from the source script.
-   The actions correctly use the `executor` and `context` objects to access necessary data and services (like `db_manager`).
-   The actions correctly use their `self.params` (e.g., `self.endpoint_name`, `self.output_context_key`) to drive their behavior.
-   The modified actions are free of syntax errors and ready for runtime testing.
-   Conceptually, executing the `UKBB_TO_HPA_BIDIRECTIONAL_EFFICIENT` strategy should now produce the same results and output files as running the original script.

## 5. Implementation Requirements
-   All necessary imports must be added to the action files.
-   The code should adhere to the project's existing style and conventions.
-   The logic should be adapted to fit within the `async execute` methods of the action classes.

## 6. Error Recovery Instructions
-   If the data structures passed in the `context` are different from what the script logic expects, adapt the logic to match the context data.
-   If a required utility function from the script is not available in the action's scope, consider whether it should be moved to a shared `biomapper.utils` module and imported.
-   If the logic is complex, break it down into smaller private helper methods within the action class.

## 7. Feedback Format
-   **Summary of Changes:** For each of the three actions, describe the logic that was ported from the script.
-   **Files Modified:** List the three action files.
-   **Assumptions Made:** Note any assumptions made about data structures in the `context` or the availability of helper functions.
-   **Potential Issues/Questions:** Highlight any parts of the script logic that were difficult to port or may require further refactoring.
-   **Confidence Assessment:** Your confidence that the ported logic is correct and the actions are ready for testing.
