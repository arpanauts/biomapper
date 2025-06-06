# Task: Create Python Script for Full UKBB to HPA Protein Mapping

## 1. Task Objective

The primary objective is to create a new Python script named `run_full_ukbb_hpa_mapping.py` located in the `/home/ubuntu/biomapper/scripts/` directory. This script will utilize the `MappingExecutor` from the `biomapper` library to execute the `UKBB_TO_HPA_PROTEIN_PIPELINE` strategy (defined in `/home/ubuntu/biomapper/configs/protein_config.yaml`) on a user-specified, full UKBB protein dataset. The script should read UKBB Protein Assay IDs, process them through the pipeline, and save the comprehensive mapping results to a CSV file.

**Success Criteria:**
*   A Python script `scripts/run_full_ukbb_hpa_mapping.py` is created.
*   The script can successfully load UKBB Protein Assay IDs from a specified TSV file.
*   The script correctly initializes and uses the `MappingExecutor` to run the `UKBB_TO_HPA_PROTEIN_PIPELINE`.
*   The script processes the input IDs and saves the mapping results (including input ID, mapped HPA ID, status, and last step) to a CSV file.
*   The script includes basic logging for progress and errors.
*   The script is well-commented and includes placeholders for user-configurable file paths.

## 2. Input Context

*   **Project Root:** `/home/ubuntu/biomapper/`
*   **Biomapper Library:** The script will use the `biomapper` library, assumed to be installed and accessible in the Python environment (managed by Poetry).
*   **Configuration File (for reference):** `/home/ubuntu/biomapper/configs/protein_config.yaml`. This file defines:
    *   The `UKBB_PROTEIN` endpoint (currently pointing to a test file: `/home/ubuntu/biomapper/data/UKBB_Protein_Meta_test.tsv`, with Assay IDs in the "Assay" column).
    *   The `HPA_OSP_PROTEIN` endpoint (using `/home/ubuntu/biomapper/data/isb_osp/hpa_osps.csv`).
    *   The `UKBB_TO_HPA_PROTEIN_PIPELINE` strategy.
*   **Existing Test Script (for reference):** `/home/ubuntu/biomapper/scripts/test_ukbb_hpa_pipeline.py`.
*   **Full UKBB Protein Data File:** The user will provide the path to this file. The script should have a clear placeholder for this. For development, a copy of the test file can be used initially.
*   **HPA Data File:** `/home/ubuntu/biomapper/data/isb_osp/hpa_osps.csv` (as per `protein_config.yaml`).

## 3. Prerequisites

*   The `biomapper` Python environment (managed by Poetry) must be active when running the script.
*   The MetaMapper database (specified in `settings.metamapper_db_url`) must be populated with the `UKBB_TO_HPA_PROTEIN_PIPELINE` strategy. The script should ideally check for this.
*   The `DATA_DIR` environment variable should point to `/home/ubuntu/biomapper/data` or be configurable within the script.
*   The user must have read access to the input UKBB data file and write access to the output directory.

## 4. Detailed Steps & Requirements

The Python script `scripts/run_full_ukbb_hpa_mapping.py` should perform the following:

1.  **Imports and Setup:**
    *   Standard library: `asyncio`, `logging`, `os`, `sys`.
    *   Path handling: `from pathlib import Path`.
    *   Third-party: `import pandas as pd`.
    *   Biomapper: `from biomapper.core.mapping_executor import MappingExecutor`, `from biomapper.config import settings`.
    *   Add project root to `sys.path` for correct module resolution: `sys.path.insert(0, str(Path(__file__).resolve().parent.parent))`.
    *   Configure logging (INFO level, timestamped format).

2.  **Configuration Variables (at the top of the script):**
    *   `FULL_UKBB_DATA_FILE_PATH = "/home/ubuntu/biomapper/data/YOUR_FULL_UKBB_PROTEIN_DATA.tsv"` (Add a prominent comment: `# IMPORTANT: User must change this path to their actual full UKBB protein data TSV file.`)
    *   `UKBB_ID_COLUMN_NAME = "Assay"`
    *   `HPA_DATA_FILE_PATH_CONFIRMATION = "/home/ubuntu/biomapper/data/isb_osp/hpa_osps.csv"` (Comment: `# Confirm this is the correct HPA dataset for the full run.`)
    *   `OUTPUT_RESULTS_DIR = "/home/ubuntu/biomapper/data/results/"`
    *   `OUTPUT_RESULTS_FILENAME = "full_ukbb_to_hpa_mapping_results.csv"`
    *   `OUTPUT_RESULTS_FILE_PATH = os.path.join(OUTPUT_RESULTS_DIR, OUTPUT_RESULTS_FILENAME)`
    *   `DEFAULT_DATA_DIR = "/home/ubuntu/biomapper/data"`

3.  **Helper Function: `check_strategy_exists(executor, strategy_name)` (Optional but Recommended):**
    *   Similar to `check_strategy_in_database` in the test script, to verify `UKBB_TO_HPA_PROTEIN_PIPELINE` is loaded. This can be simplified to use an executor method if available, or query the DB directly.

4.  **Main Asynchronous Function (e.g., `async def run_full_mapping()`):**
    *   **Environment Setup:**
        *   Ensure `OUTPUT_RESULTS_DIR` exists using `os.makedirs(OUTPUT_RESULTS_DIR, exist_ok=True)`.
        *   Set `os.environ['DATA_DIR']` to `DEFAULT_DATA_DIR` if not already set.
    *   **Load Input UKBB IDs:**
        *   Log the `FULL_UKBB_DATA_FILE_PATH` being used.
        *   Use `pd.read_csv(FULL_UKBB_DATA_FILE_PATH, sep='\t')` to load the TSV.
        *   Extract unique identifiers from the `UKBB_ID_COLUMN_NAME` column. Handle potential `KeyError` if column not found.
        *   Convert to a list: `input_identifiers = df[UKBB_ID_COLUMN_NAME].unique().tolist()`.
        *   Log the number of unique identifiers loaded. If zero, log a warning and potentially exit.
    *   **Initialize `MappingExecutor`:**
        *   `executor = await MappingExecutor.create(metamapper_db_url=settings.metamapper_db_url, mapping_cache_db_url=settings.cache_db_url, echo_sql=False, enable_metrics=True)`.
        *   Log successful creation.
    *   **(Optional) Check Strategy:** Call `await check_strategy_exists(executor, "UKBB_TO_HPA_PROTEIN_PIPELINE")`. If not found, log error and exit.
    *   **Execute Mapping Strategy:**
        *   `result = await executor.execute_yaml_strategy(...)` with:
            *   `strategy_name="UKBB_TO_HPA_PROTEIN_PIPELINE"`
            *   `source_endpoint_name="UKBB_PROTEIN"`
            *   `target_endpoint_name="HPA_OSP_PROTEIN"`
            *   `input_identifiers=input_identifiers`
            *   `use_cache=True` (Enable caching for full runs)
            *   `progress_callback=lambda curr, total, status: logger.info(f"Progress: {curr}/{total} - {status}")`
    *   **Process and Save Results:**
        *   Extract `mapped_data = result.get('mapped_data', [])`.
        *   Create a list of dictionaries (`output_rows`) for the output CSV. Each dictionary should contain:
            *   `Input_UKBB_Assay_ID`
            *   `Final_Mapped_HPA_ID` (derived from the last successful mapping step in `item['history']`)
            *   `Mapping_Status` (e.g., 'MAPPED', 'UNMAPPED', 'FILTERED_OUT', 'ERROR_DURING_PIPELINE')
            *   `Final_Step_ID_Reached`
            *   `Error_Message` (if any error occurred for this specific ID during its pipeline processing)
        *   *Detailed parsing logic for `item['history']` is needed here. The last entry in `history` usually contains the final state. If `success` is true and `action_type` is a conversion, `output_data` should have the mapped value. If filtered, status should reflect that.*
        *   Convert `output_rows` to a pandas DataFrame.
        *   Save DataFrame to CSV: `output_df.to_csv(OUTPUT_RESULTS_FILE_PATH, index=False)`.
        *   Log path to saved results.
        *   Log summary from `result.get('summary', {})`.
    *   **Cleanup:** `await executor.async_dispose()` in a `finally` block.

5.  **Main Execution Block:**
    *   `if __name__ == "__main__":`
    *   Call `asyncio.run(run_full_mapping())`.
    *   Include `try-except Exception as e` around `run_full_mapping()` to catch and log any top-level errors.

## 5. Expected Outputs & Success Criteria

*   **Primary Output:** A CSV file saved to `/home/ubuntu/biomapper/data/results/full_ukbb_to_hpa_mapping_results.csv`.
    *   Columns: `Input_UKBB_Assay_ID`, `Final_Mapped_HPA_ID`, `Mapping_Status`, `Final_Step_ID_Reached`, `Error_Message`.
*   **Console Output:** Informative logs showing script progress, number of IDs loaded, summary of mapping results, path to the output file, and any errors.
*   **Success:** The script runs to completion without unhandled exceptions, processes all input IDs, and generates the output CSV file in the specified format. The mapping results should be consistent with the `UKBB_TO_HPA_PROTEIN_PIPELINE` logic.

## 6. Error Recovery Instructions

*   **File Not Found:** If `FULL_UKBB_DATA_FILE_PATH` is incorrect, the script should log a clear error and exit gracefully.
*   **Database Connection Issues:** If `MappingExecutor` cannot connect to databases, it will raise an exception. The script's top-level try-except should catch this and log it.
*   **Missing Strategy:** If `UKBB_TO_HPA_PROTEIN_PIPELINE` is not in the database, the script should inform the user to run `scripts/populate_metamapper_db.py`.
*   **API Errors (within pipeline):** The `MappingExecutor` and individual clients (like `UniProtHistoricalResolverClient`) should handle transient API errors. The script should report IDs that failed due to persistent errors in the pipeline (via `Error_Message` column).
*   **Memory Issues:** If the full UKBB dataset is extremely large, loading all IDs into memory at once might be an issue. For this version, assume it's manageable. If this occurs, a future enhancement would be to process the input file in chunks.

## 7. Validation & Testing

*   **Initial Test:** Run the script with `FULL_UKBB_DATA_FILE_PATH` temporarily set to `/home/ubuntu/biomapper/data/UKBB_Protein_Meta_test.tsv`. The output should be comparable to the results obtained from `scripts/test_ukbb_hpa_pipeline.py` (though the output format will be different as per requirements here).
*   **Check Output CSV:** Verify the CSV structure and content.
    *   Are all input IDs present?
    *   Are `Final_Mapped_HPA_ID` values correct for known test cases (e.g., CFH_TEST, ALS2_TEST)?
    *   Is `Mapping_Status` correctly assigned?
*   **Log Review:** Check logs for any unexpected errors or warnings.
*   **Test with a larger subset (if available):** If a medium-sized subset of the full data is available, test with that to check performance and memory usage.

## 8. Additional Information (Optional)

*   The script should be designed to be robust for potentially large datasets, primarily through efficient use of the `MappingExecutor` (which has internal batching for API calls) and by enabling `use_cache=True`.
*   Ensure all file paths are handled using `os.path.join` or `pathlib` for cross-platform compatibility (though the primary target is Linux).
*   The logic for parsing `item['history']` to determine `Final_Mapped_HPA_ID` and `Mapping_Status` is critical and needs careful implementation. Refer to how `MappingExecutor` structures its results.
    *   An `input_id` might be successfully processed by some steps but filtered out by a later step (e.g., `FILTER_IDENTIFIERS_BY_TARGET_PRESENCE`). This should be reflected in the `Mapping_Status`.
    *   An error might occur mid-pipeline for a specific ID; this should also be captured.
