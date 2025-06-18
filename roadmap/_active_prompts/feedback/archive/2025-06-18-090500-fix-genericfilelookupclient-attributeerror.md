# Task: Fix AttributeError in GenericFileLookupClient

## 1. Task Objective
Resolve the `AttributeError: 'GenericFileLookupClient' object has no attribute '_file_path_key'` occurring in `biomapper.mapping.clients.generic_file_client.GenericFileLookupClient`.

## 2. Background Context
- After fixing the database population script, the UKBB-HPA pipeline now progresses past client initialization.
- It now fails when `GenericFileLookupClient` is used, specifically when it tries to determine the file path for its data.
- The error `AttributeError: 'GenericFileLookupClient' object has no attribute '_file_path_key'` indicates that the client class is missing an expected attribute, `_file_path_key`.
- This attribute is likely intended to store the name of the key within the client's configuration dictionary that specifies the data file's path (e.g., the string "file_path").
- The `GenericFileLookupClient` is initialized with a `config` dictionary passed from `MappingExecutor`, which originates from `protein_config.yaml`. For example:
  ```yaml
  # protein_config.yaml snippet for a mapping_client
  config:
    file_path: "/path/to/data.tsv"
    key_column: "Key"
    value_column: "Value"
  ```

## 3. Detailed Plan

1.  **Analyze `GenericFileLookupClient`:**
    *   Open `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/biomapper/mapping/clients/generic_file_client.py`.
    *   Examine the `__init__` method and any methods involved in loading or accessing the data file.
    *   Identify where `self._file_path_key` is being accessed and why it's not set.

2.  **Formulate a Fix:**
    *   The most likely fix is to ensure `_file_path_key` is defined for instances of `GenericFileLookupClient`.
    *   This could be done by:
        *   Adding it as a class attribute: `_file_path_key = "file_path"`.
        *   Setting it in the `__init__` method: `self._file_path_key = "file_path"` (or potentially making it configurable via `__init__` parameters if different clients might use different key names, though "file_path" is standard in `protein_config.yaml`).
    *   The client should then use this attribute to get the actual file path from its configuration, e.g., `actual_path = self.config.get(self._file_path_key)`.

3.  **Test the Fix:**
    *   **Re-run Main Pipeline:** Execute `poetry run python scripts/main_pipelines/run_full_ukbb_hpa_mapping.py`.
    *   The pipeline should now progress past the point where the `AttributeError` occurred.

4.  **Verify Output:**
    *   If the pipeline completes successfully, check for the expected output files in `/home/ubuntu/biomapper/data/results/`:
        *   `ukbb_hpa_bidirectional_reconciled.csv`
        *   `ukbb_hpa_bidirectional_summary.json`

## 4. Acceptance Criteria

*   The `AttributeError` in `GenericFileLookupClient` is resolved.
*   The `run_full_ukbb_hpa_mapping.py` script executes successfully (exit code 0).
*   The final output mapping files (`ukbb_hpa_bidirectional_reconciled.csv` and `ukbb_hpa_bidirectional_summary.json`) are generated in the correct output directory.

## 5. Implementation Requirements

*   **Input files/data:**
    *   `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/biomapper/mapping/clients/generic_file_client.py` (to be modified)
*   **Expected outputs:**
    *   Modified `generic_file_client.py`.
    *   Confirmation of successful full pipeline execution.
    *   List of files in `/home/ubuntu/biomapper/data/results/`.

## 6. Error Recovery Instructions

*   **Python/Logic Errors:** If the fix introduces new errors, capture the traceback and re-analyze the client's logic.
*   **Downstream Pipeline Errors:** If the pipeline fails at a later stage, capture the new error. This would indicate the current bug is fixed, but another one exists.

## 7. Feedback Format

Please provide your feedback in a Markdown file following the standard project format, detailing the fix, verification steps, and the final pipeline execution result (including output file listing if successful).
