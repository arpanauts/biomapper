# Documentation: Phase 3 Bidirectional Reconciliation Scripts

This document provides an overview and operational guide for two key scripts involved in Phase 3 of the Biomapper project:

1.  `phase3_bidirectional_reconciliation.py`: The main Python script that performs bidirectional reconciliation of mapping results.
2.  `test_phase3_bidirectional.sh`: A shell script designed to test the functionality of `phase3_bidirectional_reconciliation.py`.

## 1. `phase3_bidirectional_reconciliation.py`

### 1.1. Overview

The `phase3_bidirectional_reconciliation.py` script is a crucial component of the Biomapper pipeline. Its primary purpose is to reconcile the results from two preceding mapping phases:

*   **Phase 1:** Forward mapping (e.g., UKBB entities to Arivale entities).
*   **Phase 2:** Reverse mapping (e.g., Arivale entities back to UKBB entities).

By comparing these forward and reverse mappings, the script validates the relationships, identifies discrepancies, and produces a comprehensive, reconciled mapping table. This table includes detailed information about the validation status of each mapping, confidence scores, and how one-to-many relationships are handled.

**Key Features:**

*   **Bidirectional Validation:** Compares forward and reverse mappings to assign a validation status (e.g., "Validated: Bidirectional exact match", "Conflict", "Unmapped").
*   **Dynamic Column Naming:** Accepts command-line arguments to specify the names of key identifier columns in the input files, allowing flexibility for different datasets.
*   **One-to-Many Relationship Handling:**
    *   Identifies if a source entity maps to multiple target entities (`is_one_to_many_source`).
    *   Identifies if a target entity is mapped from multiple source entities (`is_one_to_many_target`).
    *   Outputs columns (`all_forward_mapped_target_ids`, `all_reverse_mapped_source_ids`) that list all associated entities in such cases, typically as semicolon-separated strings.
*   **Comprehensive Output:** Generates a detailed TSV file with numerous columns, including original source/target identifiers, mapping metadata (method, confidence, hops), validation status, and flags for relationship types.
*   **Statistics Generation:** Calculates and logs summary statistics about the reconciliation process (e.g., number of bidirectional matches, conflicts, unmapped entities).

### 1.2. Role in Biomapper Project

This script represents Phase 3 of the mapping pipeline. It takes the individual, directional mapping results from earlier phases and synthesizes them into a more reliable and validated set of bidirectional mappings. The output of this script is often the final mapping artifact used for downstream analyses, providing a clearer picture of how entities from two different datasets correspond to each other.

### 1.3. High-Level Flowchart

```mermaid
graph TD
    A[Start: phase3_bidirectional_reconciliation.py] --> B{Parse Command-Line Arguments};
    B -- Input File Paths, Output Dir, Column Names --> C[main function];
    C --> D[Load Mapping Results: phase1_df, phase2_df];
    D --> E[Create Mapping Indexes: ukbb_to_arivale_index, arivale_to_ukbb_index];
    E --> F[Perform Bidirectional Validation];
    F -- Iterate through forward_df, use indexes for lookup --> G{For each source entity:};
    G --> H{Compare forward mapping(s) with reverse mapping(s)};
    H --> I[Determine Validation Status];
    I --> J[Populate Reconciled DataFrame: IDs, metadata, validation status, one-to-many flags, all_mapped_ids];
    J --> K[Calculate Mapping Statistics];
    K --> L[Save Reconciled DataFrame to TSV];
    L --> M[Save Statistics to File/Log];
    M --> Z[End];
```

### 1.4. Updating for New Datasets (Usage Guide)

To use `phase3_bidirectional_reconciliation.py` with new datasets, you need to provide it with the correct input files and specify the relevant column names from your Phase 1 and Phase 2 mapping outputs.

**Prerequisites:**

1.  **Phase 1 Mapping Results File:** A TSV file containing the results of your forward mapping (e.g., SourceDatasetA to TargetDatasetB).
2.  **Phase 2 Mapping Results File:** A TSV file containing the results of your reverse mapping (e.g., TargetDatasetB back to SourceDatasetA).
3.  These files must contain the necessary identifier columns and standard metadata columns (see below).

**Command-Line Execution:**

```bash
python /path/to/biomapper/scripts/phase3_bidirectional_reconciliation.py \
    --phase1_results "/path/to/your_phase1_results.tsv" \
    --phase2_results "/path/to/your_phase2_results.tsv" \
    --output_dir "/path/to/your_output_directory/" \
    --phase1_source_id_col "NameOf_Phase1_SourceID_Column" \
    --phase1_source_ontology_col "NameOf_Phase1_SourceOntologyID_Column" \
    --phase1_mapped_id_col "NameOf_Phase1_MappedTargetID_Column" \
    --phase2_source_id_col "NameOf_Phase2_SourceID_Column" \
    --phase2_source_ontology_col "NameOf_Phase2_SourceOntologyID_Column" \
    --phase2_mapped_id_col "NameOf_Phase2_MappedSourceID_Column"
```

**Explanation of Key Command-Line Arguments:**

*   `--phase1_results`: Path to your Phase 1 (forward mapping) TSV file.
*   `--phase2_results`: Path to your Phase 2 (reverse mapping) TSV file.
*   `--output_dir`: Directory where the reconciled output TSV and any log/statistics files will be saved.
*   `--phase1_source_id_col`: The name of the column in your Phase 1 results file that contains the primary identifier of the *original source* entities (e.g., if mapping UKBB proteins, this might be `Assay` or a specific UKBB protein ID column).
*   `--phase1_source_ontology_col`: The name of the column in your Phase 1 results file that contains the ontology identifier used for mapping from the source (e.g., `UniProt` AC for UKBB proteins).
*   `--phase1_mapped_id_col`: The name of the column in your Phase 1 results file that contains the identifier of the *target* entity to which the source was mapped (e.g., `ARIVALE_PROTEIN_ID`).
*   `--phase2_source_id_col`: The name of the column in your Phase 2 results file that contains the primary identifier of the *original source* entities for the reverse mapping (this would be an ID from the target dataset of Phase 1, e.g., `ARIVALE_PROTEIN_ID`).
*   `--phase2_source_ontology_col`: The name of the column in your Phase 2 results file that contains the ontology identifier used for mapping from this entity (e.g., `UniProt` AC for Arivale proteins).
*   `--phase2_mapped_id_col`: The name of the column in your Phase 2 results file that contains the identifier of the *target* entity to which it was mapped back (this would be an ID from the original source dataset of Phase 1, e.g., `Assay`).

**Standard Metadata Columns Expected in Input Files:**

The script expects the following metadata columns to be present in both Phase 1 and Phase 2 input files with these exact names (as defined by `DEFAULT_..._COL` constants in the script):

*   `mapping_method`
*   `confidence_score`
*   `hop_count`
*   `notes`
*   `mapping_path_details_json`

Ensure your Phase 1 and Phase 2 mapping scripts generate outputs containing these columns with the specified names.

**Output:**

The primary output is a TSV file named `phase3_bidirectional_reconciliation_results.tsv` within the specified output directory. Key columns include:
* Original source and target IDs (based on your input column names).
* `bidirectional_validation_status`: The outcome of the reconciliation.
* `is_one_to_many_source`: Boolean, true if the original source ID from Phase 1 maps to multiple distinct target IDs after reconciliation.
* `is_one_to_many_target`: Boolean, true if the original target ID from Phase 1 is mapped by multiple distinct source IDs after reconciliation.
* `all_forward_mapped_target_ids`: Semicolon-separated list of all target IDs associated with a given source ID from the forward mapping perspective.
* `all_reverse_mapped_source_ids`: Semicolon-separated list of all source IDs associated with a given target ID from the reverse mapping perspective.
* And many other metadata columns.

---

## 2. `test_phase3_bidirectional.sh`

### 2.1. Overview

The `test_phase3_bidirectional.sh` script is a shell script designed to test the execution and output of the `phase3_bidirectional_reconciliation.py` script. It uses a predefined set of Phase 1 and Phase 2 input files and runs the Python script with specific column name configurations to ensure it operates as expected, particularly testing features like dynamic column naming and the generation of one-to-many related output columns.

**Key Actions:**

1.  Sets up paths for input files (hardcoded in the script) and a timestamped output directory.
2.  Calls `phase3_bidirectional_reconciliation.py` with specific command-line arguments, including paths to test data and explicit column name mappings.
3.  Checks the exit status of the Python script.
4.  If successful, it verifies:
    *   The creation of the output reconciliation file.
    *   The headers of the output file.
    *   The presence of specific columns related to one-to-many mappings (e.g., `all_forward_mapped_target_ids`, `all_reverse_mapped_source_ids`).
    *   It also attempts to count and display sample rows that exhibit one-to-many characteristics (by checking for semicolons in output fields, which typically denote multiple concatenated IDs in columns like `all_forward_mapped_target_ids`).

### 2.2. Role in Biomapper Project

This script serves as an automated test case for the `phase3_bidirectional_reconciliation.py` script. It helps ensure that modifications to the Python script do not break existing functionality and that the script correctly processes data according to its specifications, especially concerning the handling of different column naming schemes and the reporting of complex mapping scenarios.

### 2.3. Flowchart

```mermaid
graph TD
    A[Start: test_phase3_bidirectional.sh] --> B[Set Up Paths: Script Dir, Output Dir, Hardcoded Phase1/Phase2 Input Files];
    B --> C[Create Timestamped Output Directory];
    C --> D[Call phase3_bidirectional_reconciliation.py with predefined arguments (input files, output dir, specific column names)];
    D --> E{Python Script Exit Status?};
    E -- Success (0) --> F[Verification Steps];
    F --> G[Check if output file (phase3_reconciliation_results.tsv) exists];
    G -- Exists --> H[Display Output File Header];
    H --> I[Check for presence of 'all_forward_mapped_target_ids' column];
    I --> J[Check for presence of 'all_reverse_mapped_source_ids' column];
    J --> K[Count and display sample rows with multiple mappings (e.g., containing ';')];
    K --> Y[Report Test Success];
    G -- Does Not Exist --> X[Report Error: Output file not created];
    E -- Failure (non-0) --> W[Report Error: Reconciliation Failed];
    W --> Z[End Test];
    X --> Z;
    Y --> Z;
```

### 2.4. Updating for New Datasets

This script is primarily intended for testing with its **current, hardcoded input files**:
*   `PHASE1_FILE="$SCRIPT_DIR/../output/ukbb_to_arivale_path_fix_20250507_182543.tsv"`
*   `PHASE2_FILE="$SCRIPT_DIR/../output/ukbb_to_arivale_with_reverse_20250507_183627.tsv"`

**It is generally not intended to be directly adapted for new, arbitrary datasets by end-users.** For processing new datasets, you should use `phase3_bidirectional_reconciliation.py` directly as described in its own section.

However, if a developer needs to adapt this *test script* for new *test datasets*:

1.  **Modify Input File Paths:**
    *   Change the `PHASE1_FILE` and `PHASE2_FILE` variables within the script (lines 8-9) to point to your new test dataset files.
2.  **Adjust Column Name Arguments:**
    *   The script calls `phase3_bidirectional_reconciliation.py` with specific column name arguments (lines 25-30):
        ```bash
        --phase1_source_id_col "Assay" \
        --phase1_source_ontology_col "UniProt" \
        --phase1_mapped_id_col "ARIVALE_PROTEIN_ID" \
        --phase2_source_id_col "ARIVALE_PROTEIN_ID" \
        --phase2_source_ontology_col "UniProt" \
        --phase2_mapped_id_col "Assay"
        ```
    *   If your new test datasets use different column names for these roles, you **must** update these arguments in the shell script accordingly.
3.  **Update Verification Steps (Optional):**
    *   The script checks for specific columns like `all_forward_mapped_target_ids`. If your test scenario or Python script modifications change these expected output columns, the verification logic (lines 48-60) might need adjustment.

---

## 3. Interrelation between Scripts

*   `test_phase3_bidirectional.sh` **executes and tests** `phase3_bidirectional_reconciliation.py`.
*   `phase3_bidirectional_reconciliation.py` is the **core engine** that performs the actual data processing and reconciliation.
*   The shell script acts as a **driver or test harness** for the Python script, providing a specific set of inputs and checking for expected outputs to validate the Python script's behavior under controlled conditions.

For general data processing tasks with new datasets, users will interact directly with `phase3_bidirectional_reconciliation.py` by providing appropriate command-line arguments. The `test_phase3_bidirectional.sh` script is more of a developer/testing tool for ensuring the Python script's integrity.

