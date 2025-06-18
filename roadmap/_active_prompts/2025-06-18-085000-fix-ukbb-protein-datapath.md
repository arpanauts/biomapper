# Task: Correct UKBB_PROTEIN Data File Path in protein_config.yaml

## 1. Task Objective
Update the `configs/protein_config.yaml` file to ensure the `UKBB_PROTEIN` endpoint correctly points to its data file at the actual location: `/home/ubuntu/biomapper/data/UKBB_Protein_Meta.tsv`.

## 2. Background Context
- The `run_full_ukbb_hpa_mapping.py` script (using the `UKBB_TO_HPA_BIDIRECTIONAL_EFFICIENT` strategy) is failing.
- The failure is a `FileNotFoundError` because the `LoadEndpointIdentifiersAction` for the `UKBB_PROTEIN` endpoint is trying to access `/procedure/data/local_data/UKBB_Protein_Meta.tsv`.
- The actual location of the file is `/home/ubuntu/biomapper/data/UKBB_Protein_Meta.tsv`.
- This indicates that the `file_path` for the `UKBB_PROTEIN` endpoint in `configs/protein_config.yaml` is incorrect.
- Previous attempts to set absolute paths (referenced in Checkpoint 16) for this endpoint were either incorrect or ineffective.

## 3. Detailed Plan

1.  **Identify the `UKBB_PROTEIN` Endpoint Configuration:**
    *   Open `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/configs/protein_config.yaml`.
    *   Locate the `database_endpoints` section.
    *   Find the entry for `UKBB_PROTEIN`.

2.  **Modify the `file_path`:**
    *   Within the `UKBB_PROTEIN` endpoint configuration, find the `connection_details` subsection.
    *   Update the `file_path` parameter to be `/home/ubuntu/biomapper/data/UKBB_Protein_Meta.tsv`.
    *   Ensure there are no typos and the path is exactly as specified.
    *   Save the `protein_config.yaml` file.

3.  **Re-run Database Population:**
    *   The `protein_config.yaml` file is read by `populate_metamapper_db.py` to configure endpoints in the database.
    *   Execute the command: `poetry run python scripts/setup_and_configuration/populate_metamapper_db.py --drop-all`
    *   CWD: `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/`

4.  **Re-run the Main Pipeline Script:**
    *   Execute the command: `poetry run python scripts/main_pipelines/run_full_ukbb_hpa_mapping.py`
    *   CWD: `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/`

5.  **Verify Output:**
    *   Check the contents of the directory `/home/ubuntu/biomapper/data/results/`.
    *   Expected files (if mappings are found):
        *   `ukbb_hpa_bidirectional_reconciled.csv`
        *   `ukbb_hpa_bidirectional_summary.json`

## 4. Acceptance Criteria

*   The `file_path` for the `UKBB_PROTEIN` endpoint in `configs/protein_config.yaml` is correctly updated to `/home/ubuntu/biomapper/data/UKBB_Protein_Meta.tsv`.
*   The `populate_metamapper_db.py` script runs successfully, reflecting the updated configuration.
*   The `run_full_ukbb_hpa_mapping.py` script runs successfully (exit code 0).
*   The output directory `/home/ubuntu/biomapper/data/results/` contains the expected `.csv` and `.json` files. If the directory is still empty but the script ran successfully, the script's log output should be captured to confirm if the `SaveBidirectionalResultsAction` reported "No reconciled data found to save".

## 5. Implementation Requirements

*   **Input files/data:**
    *   `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/configs/protein_config.yaml` (to be modified)
*   **Expected outputs:**
    *   Modified `protein_config.yaml` file.
    *   Confirmation of successful script executions.
    *   List of files in `/home/ubuntu/biomapper/data/results/` or relevant log output if empty and script succeeded.

## 6. Error Recovery Instructions

*   **YAML Syntax Errors:** If modifying `protein_config.yaml` introduces syntax errors, `populate_metamapper_db.py` will likely fail with a YAML parsing error. Carefully review the changes for correct YAML formatting.
*   **Script Execution Errors:** If `run_full_ukbb_hpa_mapping.py` still fails, capture the full error traceback. The error might indicate other path issues (e.g., for HPA_OSP_PROTEIN) or different problems.
*   **Output Still Missing (but script successful):** If the output directory remains empty even after the script runs successfully, provide the full log output from `run_full_ukbb_hpa_mapping.py`. This would indicate that the data loading and strategy execution occurred, but no reconciled mappings were found, necessitating the previously planned debugging of `ReconcileBidirectionalAction`.

## 7. Feedback Format

Please provide your feedback in a Markdown file with the following structure:

```markdown
# Feedback: Correct UKBB_PROTEIN Data File Path

## 1. Summary of Actions Taken
- Confirm modification of `file_path` for `UKBB_PROTEIN` in `protein_config.yaml`.
- Confirm execution of database population and main pipeline script.

## 2. Script Execution Results
- Provide exit codes and any brief, relevant output from the script runs.

## 3. Output Verification
- List files found in `/home/ubuntu/biomapper/data/results/`.
- If empty and script succeeded, provide key log lines from `run_full_ukbb_hpa_mapping.py` (especially from `SaveBidirectionalResultsAction`).

## 4. Code Modifications
- Show the diff or relevant section from `protein_config.yaml` that was changed.

## 5. Issues Encountered (if any)
- Detail any errors or unexpected behaviors.

## 6. Next Action Recommendation
- Suggest next steps based on the outcome.

## 7. Confidence Assessment
- Rate your confidence in the fix and the outcome.
```
