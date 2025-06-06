# Task: Resolve Configuration Loading for UKBB-HPA Protein Mapping

## 1. Task Objective
The primary objective is to ensure that the `UKBB_TO_HPA_PROTEIN_PIPELINE` correctly uses the full UK Biobank (UKBB) and Human Protein Atlas (HPA) datasets. This requires updating the `metamapper.db` database with the correct endpoint file paths specified in `/home/ubuntu/biomapper/configs/protein_config.yaml`. The ultimate success criterion is the pipeline running with the full datasets and producing a non-zero number of mapped protein identifiers.

## 2. Background
The `run_full_ukbb_hpa_mapping.py` script executes the `UKBB_TO_HPA_PROTEIN_PIPELINE`. Currently, despite `/home/ubuntu/biomapper/configs/protein_config.yaml` being updated with paths to the full UKBB and HPA datasets, the pipeline logs indicate it's still using older, test dataset paths. This is because the `MappingExecutor` reads endpoint configurations from `metamapper.db`, which has not been synchronized with the recent changes to `protein_config.yaml`.

We've identified that `biomapper/cli/metadata_commands.py` contains a `register_resources` command that seems responsible for loading YAML configurations into `metamapper.db`. However, this command appears to expect a top-level `"resources"` key in the YAML, while `/home/ubuntu/biomapper/configs/protein_config.yaml` defines data sources (endpoints) under a `"databases"` key.

## 3. Current Status
- `/home/ubuntu/biomapper/configs/protein_config.yaml` correctly points `UKBB_PROTEIN` and `HPA_OSP_PROTEIN` endpoints to the full dataset files:
    - UKBB: `/procedure/data/local_data/MAPPING_ONTOLOGIES/ukbb/UKBB_Protein_Meta.tsv`
    - HPA: `/procedure/data/local_data/MAPPING_ONTOLOGIES/isb_osp/hpa_osps.csv`
- The `run_full_ukbb_hpa_mapping.py` script, when run, still loads data from old test file paths, indicating `metamapper.db` is stale.
- The `MappingExecutor` does not itself handle the initial population or synchronization of `metamapper.db` from YAML files.
- The CLI command `biomapper.cli.metadata_commands.register_resources` is a strong candidate for updating `metamapper.db` but might require specific YAML structuring (e.g., a top-level "resources" key).

## 4. Problem Statement
The `metamapper.db` is not reflecting the updated endpoint configurations from `/home/ubuntu/biomapper/configs/protein_config.yaml`, causing the mapping pipeline to use incorrect (test) data files. We need to find and execute the correct procedure to synchronize `metamapper.db` with the YAML configuration, specifically for the endpoint definitions under the `"databases"` key.

## 5. Key Questions to Investigate
1.  How are different sections of `/home/ubuntu/biomapper/configs/protein_config.yaml` (e.g., `ontologies`, `databases`, `mapping_clients`, `mapping_strategies`) intended to be loaded into `metamapper.db`?
2.  Is `biomapper.cli.metadata_commands.register_resources` the correct tool for registering/updating endpoint definitions that are nested under the `"databases"` key in `protein_config.yaml`?
3.  If not, what other CLI commands (e.g., in `biomapper.cli.metadata_commands.py` or `biomapper.cli.metamapper_db_cli.py`) or internal mechanisms (e.g., involving `ResourceMetadataManager`) are responsible for this?
4.  Does `/home/ubuntu/biomapper/configs/protein_config.yaml` need to be restructured, or is there a specific command to target the `"databases"` section for updates?
5.  What are the precise steps to ensure the `UKBB_PROTEIN` and `HPA_OSP_PROTEIN` endpoint configurations in `metamapper.db` match those in the YAML file?

## 6. Proposed Investigation & Implementation Steps

### Step 1: Analyze Configuration Loading Mechanisms
   - **Action:** Review the code in `biomapper/cli/metadata_commands.py` and `biomapper/mapping/metadata/manager.py` (specifically `ResourceMetadataManager`).
   - **Goal:** Understand how these components parse YAML files and interact with `metamapper.db`. Determine if they handle keys like `"databases"` and their nested endpoint structures, or if they are strictly limited to a top-level `"resources"` key.
   - **Tools:** `view_code_item`.

### Step 2: Identify the Correct Update Procedure
   - **Action:** Based on Step 1, determine the exact CLI command(s) or Python script logic required to update `metamapper.db` with the endpoint definitions from `/home/ubuntu/biomapper/configs/protein_config.yaml`.
   - **Considerations:**
        - If `register_resources` is usable (perhaps with specific arguments or if it implicitly handles "databases").
        - If other commands in `metadata_commands.py` or `metamapper_db_cli.py` are more appropriate.
        - If a minor, temporary restructuring of `protein_config.yaml` (e.g., to add a "resources" section mirroring "databases") is a viable workaround for using an existing tool, provided it doesn't break other functionalities.
        - If no direct tool exists, outline the simplest script needed to achieve this, likely using `ResourceMetadataManager` or direct SQLAlchemy operations.
   - **Goal:** Define a clear, executable procedure.

### Step 3: (If Necessary) Prepare Configuration or Script
   - **Action:** If a configuration file restructuring or a new small script is needed, prepare it.
   - **Goal:** Have all components ready for the update.
   - **Tools:** `edit_file`, `write_to_file`.

### Step 4: Execute the Update Procedure
   - **Action:** Run the identified CLI command(s) or script to update `metamapper.db`.
   - **Goal:** Synchronize `metamapper.db` with `/home/ubuntu/biomapper/configs/protein_config.yaml`.
   - **Tools:** `run_command`.

### Step 5: Verify Database Update (Optional but Recommended)
   - **Action:** If possible, query `metamapper.db` (e.g., using `sqlite3` CLI or a small Python script with SQLAlchemy) to confirm that the file paths for `UKBB_PROTEIN` and `HPA_OSP_PROTEIN` endpoints are updated.
   - **Goal:** Confirm the database reflects the changes before running the full pipeline.
   - **Tools:** `run_command` (for `sqlite3`), potentially `write_to_file` and `run_command` (for a Python verification script).

### Step 6: Test by Re-running the Mapping Script
   - **Action:** Execute the `run_full_ukbb_hpa_mapping.py` script.
   - **Command:** `python /home/ubuntu/biomapper/scripts/run_full_ukbb_hpa_mapping.py`
   - **Goal:** Observe the script's log output for evidence that it's now using the correct full dataset file paths.
   - **Tools:** `run_command`.

### Step 7: Validate Mapping Results
   - **Action:** Check the output CSV file (`/home/ubuntu/biomapper/data/results/full_ukbb_to_hpa_mapping_results.csv`) and script logs.
   - **Goal:** Confirm that the pipeline now processes a significant number of identifiers and produces non-zero mapping results.
   - **Tools:** `view_file_outline` (for CSV), analysis of `run_command` output.

## 7. Input Context
-   **Primary Configuration File:** `/home/ubuntu/biomapper/configs/protein_config.yaml` (contains correct, full dataset paths for UKBB and HPA).
-   **Metamapper Database:** `/home/ubuntu/biomapper/metamapper.db` (currently contains stale endpoint configurations).
-   **Mapping Script:** `/home/ubuntu/biomapper/scripts/run_full_ukbb_hpa_mapping.py`
-   **Key CLI Modules:**
    -   `/home/ubuntu/biomapper/biomapper/cli/metadata_commands.py`
    -   `/home/ubuntu/biomapper/biomapper/cli/metamapper_db_cli.py`
-   **Key Library Modules:**
    -   `/home/ubuntu/biomapper/biomapper/mapping/metadata/manager.py` (`ResourceMetadataManager`)
    -   `/home/ubuntu/biomapper/biomapper/core/mapping_executor.py`
-   **Relevant Memory:** `MEMORY[20fc0c2a-ba90-4b41-b596-997c2919388a]` (configuring_ukbb_hpa_qin_mapping.md) might provide general context on how configs are structured or meant to be used.

## 8. Expected Outputs & Deliverables
1.  Clear identification of the correct procedure (CLI commands or script) to update `metamapper.db` from `/home/ubuntu/biomapper/configs/protein_config.yaml`.
2.  Successful execution of this procedure.
3.  Log output from `run_full_ukbb_hpa_mapping.py` demonstrating that it is loading data from:
    -   `/procedure/data/local_data/MAPPING_ONTOLOGIES/ukbb/UKBB_Protein_Meta.tsv`
    -   `/procedure/data/local_data/MAPPING_ONTOLOGIES/isb_osp/hpa_osps.csv`
4.  A non-zero number of successfully mapped identifiers in the output CSV and summary logs.
5.  Documentation of the identified update procedure for future reference (e.g., as a new memory or an update to existing documentation).

## 9. Success Criteria
-   The `run_full_ukbb_hpa_mapping.py` script successfully uses the full UKBB and HPA dataset file paths as defined in `/home/ubuntu/biomapper/configs/protein_config.yaml`.
-   The pipeline maps a significant number of identifiers (e.g., >0, ideally a substantial fraction of the 2923 input UKBB IDs).
-   The method for updating `metamapper.db` is clearly understood and documented.

## 10. Validation Requirements
-   Carefully inspect the log output of any CLI commands used to update the database.
-   Examine the log output of `run_full_ukbb_hpa_mapping.py` for lines indicating which files are being loaded for `UKBB_PROTEIN` and `HPA_OSP_PROTEIN`.
-   Analyze the summary statistics and the content of `/home/ubuntu/biomapper/data/results/full_ukbb_to_hpa_mapping_results.csv` to confirm successful mappings.

## 11. Error Recovery Instructions
-   **CLI Command Fails:** Analyze error messages. If it's due to YAML structure (e.g., missing "resources" key), revisit Step 2 and 3 to find alternatives or adapt the config.
-   **Database Query Fails (Verification Step):** Ensure `sqlite3` is installed and `metamapper.db` path is correct.
-   **Mapping Script Still Uses Old Paths:** This indicates the database update was not successful or did not target the correct tables/entries. Re-evaluate the update procedure (Step 2).
-   **Mapping Script Fails for Other Reasons:** Analyze new errors. They might be unrelated to config loading but could be masked by the previous issue.
-   **Zero Mappings Persist:** If paths are correct but mappings are zero, this points to a different issue in the mapping logic/strategy itself, which would be a subsequent problem to diagnose. For now, focus on ensuring correct data loading.

## 12. Next Steps (Upon Success)
-   Document the successful procedure for updating `metamapper.db` from `protein_config.yaml`.
-   Consider if this procedure should be integrated into a more common workflow or script if frequent updates are expected.
-   Proceed with further analysis of the mapping results if required by the USER.
