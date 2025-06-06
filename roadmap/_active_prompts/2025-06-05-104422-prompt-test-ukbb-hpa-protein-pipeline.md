# Task: Test and Verify UKBB to HPA Protein Mapping Pipeline

## 1. Task Objective
Execute the `UKBB_TO_HPA_PROTEIN_PIPELINE` mapping strategy defined in `/home/ubuntu/biomapper/configs/protein_config.yaml` with a set of sample UKBB Protein Assay IDs. Verify that the pipeline correctly converts these IDs to HPA Gene Symbols (now acting as HPA OSP Native IDs), considering recent configuration changes. Document the execution process, inputs, outputs, and any encountered issues.

## 2. Background and Context
We are currently focused on developing and verifying the protein identifier mapping capabilities of the Biomapper application, specifically the pipeline to map UK Biobank (UKBB) protein assay identifiers to Human Protein Atlas (HPA) identifiers.

Recent work involved:
- Reviewing the `protein_config.yaml` file.
- Identifying that the HPA data file (`hpa_osps.csv`) uses gene symbols, not specific "HPAOSP_" prefixed IDs.
- Updating `protein_config.yaml` to:
    - Change the `identifier_prefix` for `HPA_OSP_PROTEIN_ID_ONTOLOGY` from `"HPAOSP_"` to `"Gene:"`.
    - Update the `description` for `HPA_OSP_PROTEIN_ID_ONTOLOGY` to reflect the use of gene symbols.
    - Correct the `delimiter` from `","` to `"\t"` and `type` from `"file_csv"` to `"file_tsv"` for the `hpa_osp` endpoint and its associated `GenericFileLookupClient` configurations.
- Manually tracing the `UKBB_TO_HPA_PROTEIN_PIPELINE` with sample data, which suggested the logic is plausible.

The column name for UKBB Assay IDs in the source file (`UKBB_Protein_Meta.tsv`) might be `Assay` rather than `Assay_ID` as currently configured in `protein_config.yaml` under `databases.ukbb.properties.mappings.UKBB_PROTEIN_ASSAY_ID_ONTOLOGY.column`. This needs to be verified and potentially adjusted in the `protein_config.yaml` before execution if it's indeed `Assay`.

## 3. Prerequisites
- The Biomapper Python environment must be set up with all necessary dependencies installed (assume Poetry is used for environment management).
- The `${DATA_DIR}` environment variable must be correctly set and point to the directory containing `procedure/data/local_data/...`.
- The mapping database (`metamapper.db`) should be up-to-date with any necessary migrations or schema.
- The `protein_config.yaml` file at `/home/ubuntu/biomapper/configs/protein_config.yaml` must contain the latest reviewed changes (delimiter, HPA ontology prefix).

## 4. Input Context
- **Configuration File:** `/home/ubuntu/biomapper/configs/protein_config.yaml` (absolute path)
- **Mapping Strategy Name:** `UKBB_TO_HPA_PROTEIN_PIPELINE`
- **Sample UKBB Protein Assay IDs (from `UKBB_Protein_Meta.tsv`):**
    - "AARSD1"
    - "ABHD14B"
    - "ABL1"
    - "ACAA1"
    - "ACAN"
    - "ACE2"
    *(These are the actual values to be used as input for the mapping)*
- **Relevant Data Files (ensure paths are correct relative to `${DATA_DIR}` as defined in `protein_config.yaml`):**
    - UKBB data: `${DATA_DIR}/../../../../procedure/data/local_data/MAPPING_ONTOLOGIES/ukbb/UKBB_Protein_Meta.tsv`
    - HPA data: `${DATA_DIR}/../../../../procedure/data/local_data/MAPPING_ONTOLOGIES/isb_osp/hpa_osps.csv`

## 5. Key Files for Review (Absolute Paths)
- `/home/ubuntu/biomapper/configs/protein_config.yaml`
- `/home/ubuntu/biomapper/biomapper/mapping_strategies/mapping_executor.py` (Core execution logic)
- `/home/ubuntu/biomapper/biomapper/mapping_strategies/actions/` (Relevant action handlers like `convert_identifiers_local.py`, `execute_mapping_path.py`, `filter_identifiers_by_target_presence.py`)
- `/home/ubuntu/biomapper/biomapper/resources.py` (For how clients and endpoints are loaded)
- `/home/ubuntu/biomapper/biomapper/config_loader.py` (For how YAML configurations are parsed)

## 6. Task Breakdown and Implementation Steps

### Step 1: Verify UKBB Assay ID Column Name
1.  Inspect the header of the UKBB data file: `/home/ubuntu/biomapper/procedure/data/local_data/MAPPING_ONTOLOGIES/ukbb/UKBB_Protein_Meta.tsv`.
2.  Determine the exact column name for UKBB Protein Assay IDs.
3.  If the column name is `Assay` (or anything other than `Assay_ID`), update the `/home/ubuntu/biomapper/configs/protein_config.yaml` file:
    *   Locate the `databases.ukbb.properties.mappings.UKBB_PROTEIN_ASSAY_ID_ONTOLOGY` section.
    *   Change the `column` value from `"Assay_ID"` to the correct column name (e.g., `"Assay"`).
    *   Provide the diff of the change made to `protein_config.yaml`. If no change is needed, state that.

### Step 2: Prepare Python Script for Execution
1.  Create a new Python script (e.g., `/home/ubuntu/biomapper/scripts/test_ukbb_hpa_pipeline.py`).
2.  The script should:
    a.  Initialize the Biomapper application context (load configurations, set up logging, etc.). This might involve using helper functions from your test suite or a dedicated script runner setup if available.
    b.  Instantiate the `MappingExecutor`.
    c.  Define the list of sample UKBB Protein Assay IDs: `["AARSD1", "ABHD14B", "ABL1", "ACAA1", "ACAN", "ACE2"]`.
    d.  Call the `MappingExecutor.execute_strategy_by_name()` method with the strategy name `UKBB_TO_HPA_PROTEIN_PIPELINE` and the sample input IDs.
    e.  Print the input IDs.
    f.  Print the final mapped output.
    g.  Include robust error handling to catch and print any exceptions during execution.

### Step 3: Execute the Script
1.  Run the script from the Biomapper project root (e.g., `poetry run python scripts/test_ukbb_hpa_pipeline.py`).
2.  Capture all console output, including logs and any error messages.

## 7. Expected Outputs and Deliverables
1.  **Confirmation of UKBB Assay ID Column Name:** A statement confirming the column name used for UKBB Assay IDs and, if necessary, the diff of the change made to `/home/ubuntu/biomapper/configs/protein_config.yaml`.
2.  **Python Script:** The content of `/home/ubuntu/biomapper/scripts/test_ukbb_hpa_pipeline.py`.
3.  **Execution Log:** Full console output from running the script. This should include:
    *   The input UKBB Assay IDs.
    *   The final list of mapped HPA Gene Symbols (prefixed with "Gene:").
    *   Any intermediate logging from the `MappingExecutor` or actions (if verbosity is enabled).
    *   Any errors or exceptions encountered.
4.  **Verification:** A statement confirming whether the output matches the expected output based on our manual trace (primarily for "ABHD14B" -> "Gene:ALS2", other mappings will depend on full data).
    *   Expected for "ABHD14B": "Gene:ALS2"
    *   For other inputs, the output will depend on their presence in HPA data and UniProt history.

## 8. Success Criteria
- The `UKBB_TO_HPA_PROTEIN_PIPELINE` strategy executes without unhandled exceptions.
- The script produces a list of mapped identifiers.
- For the input "ABHD14B", the output includes "Gene:ALS2".
- All deliverables listed above are provided.

## 9. Error Recovery and Debugging Guidance
- **Configuration Errors:** Double-check paths and names in `protein_config.yaml`. Ensure `${DATA_DIR}` is correctly expanded. Verify delimiters and column names match the actual data files.
- **`FileNotFoundError`:** Verify that `${DATA_DIR}` is set and the relative paths in `protein_config.yaml` correctly point to `UKBB_Protein_Meta.tsv` and `hpa_osps.csv`.
- **`KeyError` or `IndexError` during file parsing:** This likely indicates a mismatch between configured column names/delimiters and the actual file format. Review Step 1 and the client configurations in `protein_config.yaml`.
- **`NoMappingFoundError`:** This is expected if an identifier cannot be converted or filtered at any step. The final output might be smaller than the input list.
- **Async/Await issues (`MissingGreenlet` etc.):** Ensure that any database operations within the execution path are correctly handled with `async/await` and that the `MappingExecutor` and its actions are compatible with the async event loop if database interactions occur. (Note: The current trace suggests local file lookups, but `UniProtHistoricalResolverClient` might be async).
- **Logging:** Increase logging verbosity in the `MappingExecutor` or relevant action handlers if debugging is needed to trace the flow of identifiers.

## 10. Communication
Provide all outputs and a summary of the execution. If errors occur, provide detailed error messages and the step where the error occurred. If the UKBB column name needed adjustment, highlight this clearly.
