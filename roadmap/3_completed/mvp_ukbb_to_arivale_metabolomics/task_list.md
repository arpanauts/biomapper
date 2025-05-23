# Task List: MVP UKBB NMR to Arivale Metabolomics Mapping

This task list is derived from `spec.md` and `design.md`.

## Phase 1: Setup and Initial RAG Client Testing

*   [ ] **1.1 Environment Setup:**
    *   [ ] Ensure `PubChemRAGMappingClient` is installed and configurable.
    *   [ ] Confirm access to input files:
        *   `/procedure/data/local_data/HPP_PHENOAI_METADATA/UKBB_NMR_Meta.tsv`
        *   `/procedure/data/local_data/ARIVALE_SNAPSHOTS/metabolomics_metadata.tsv`
*   [ ] **1.2 Create `test_rag_client_arivale.py` script:**
    *   [ ] Implement `load_arivale_samples(filepath, sample_size=20)`:
        *   [ ] Read `metabolomics_metadata.tsv`.
        *   [ ] Handle comment lines (e.g., skip lines starting with '#').
        *   [ ] Select a diverse sample of `BIOCHEMICAL_NAME` and their `PUBCHEM` IDs.
        *   [ ] Return a list of tuples/dicts: `(biochemical_name, ground_truth_pubchem_id)`.
    *   [ ] Implement `main_test_loop(arivale_samples, rag_client_instance)`:
        *   [ ] Instantiate `PubChemRAGMappingClient`.
        *   [ ] Iterate through samples.
        *   [ ] Call `rag_client_instance.map_identifiers([sample.biochemical_name])`.
        *   [ ] Compare RAG-derived PubChem CID(s) with `sample.ground_truth_pubchem_id`.
        *   [ ] Log/print detailed results: input name, ground truth CID, RAG CID(s), confidence, match status.
        *   [ ] Calculate and print overall accuracy for the test set.
*   [ ] **1.3 Execute `test_rag_client_arivale.py`:**
    *   [ ] Run the script.
    *   [ ] Analyze results to validate `PubChemRAGMappingClient` performance. Note any systematic issues.
    *   [ ] Determine a preliminary confidence threshold for "good" RAG matches based on test results.

## Phase 2: Main Mapping Script Implementation

*   [ ] **2.1 Create `map_ukbb_to_arivale_metabolomics.py` script:**
    *   [ ] Add necessary imports (e.g., `pandas`, `csv`, `PubChemRAGMappingClient`).
*   [ ] **2.2 Implement Data Loading Functions:**
    *   [ ] Implement `load_ukbb_data(filepath)`:
        *   [ ] Read `UKBB_NMR_Meta.tsv`.
        *   [ ] Extract `field_id` and `title`.
        *   [ ] Return a list of dicts or Pandas DataFrame.
    *   [ ] Implement `load_arivale_data_for_lookup(filepath)`:
        *   [ ] Read `metabolomics_metadata.tsv`.
        *   [ ] Handle comment lines.
        *   [ ] Create and return a dictionary mapping Arivale `PUBCHEM` ID to relevant Arivale row data (e.g., `{'pubchem_id': {'CHEMICAL_ID': ..., 'BIOCHEMICAL_NAME': ..., 'KEGG': ..., 'HMDB': ...}}`).
        *   [ ] Address potential missing or multiple PubChem IDs per Arivale entry (e.g., log warnings, decide on a strategy like taking the first).
*   [ ] **2.3 Implement Core Mapping Logic:**
    *   [ ] Implement `process_rag_output(rag_output, arivale_lookup, confidence_threshold)`:
        *   [ ] Analyze output from `rag_client.map_identifiers()`.
        *   [ ] Select the best PubChem CID candidate (e.g., highest confidence).
        *   [ ] Check if the candidate CID exists in `arivale_lookup`.
        *   [ ] Return `(derived_cid, confidence, mapping_status_string)`.
            *   Mapping statuses: "Successfully Mapped to Arivale", "Mapped to PubChem - Not in Arivale", "RAG Mapping Failed", "Multiple RAG Candidates - Chose Best", "RAG Confidence Below Threshold".
    *   [ ] Implement `perform_mapping(ukbb_data, arivale_lookup, rag_client_instance, confidence_threshold)`:
        *   [ ] Initialize an empty list `mapping_results`.
        *   [ ] Iterate through unique UKBB `title`s.
        *   [ ] Call `rag_client_instance.map_identifiers([ukbb_title])`.
        *   [ ] Call `process_rag_output` to get `derived_cid`, `confidence`, and `status`.
        *   [ ] If successfully mapped to Arivale, retrieve Arivale details.
        *   [ ] Construct a result dictionary with all specified output columns (from `spec.md`).
        *   [ ] Append to `mapping_results`.
        *   [ ] Return `mapping_results`.
*   [ ] **2.4 Implement Output and Main Execution:**
    *   [ ] Implement `write_results_to_tsv(mapping_results, output_filepath)`:
        *   [ ] Write `mapping_results` to a TSV file with headers as per `spec.md`.
    *   [ ] Implement `main()` function:
        *   [ ] Add argument parsing for input file paths and output file path.
        *   [ ] Instantiate `PubChemRAGMappingClient`.
        *   [ ] Call data loading functions.
        *   [ ] Call `perform_mapping`.
        *   [ ] Call `write_results_to_tsv`.
        *   [ ] Print summary statistics (e.g., count of each `mapping_status`).
*   [ ] **2.5 Initial Run and Debugging:**
    *   [ ] Run `map_ukbb_to_arivale_metabolomics.py` with a small subset of UKBB data if possible, or full data.
    *   [ ] Debug any issues.
    *   [ ] Verify output format and content.

## Phase 3: Review and Finalization

*   [ ] **3.1 Code Review (Self or Peer):**
    *   [ ] Check for clarity, efficiency, and adherence to `spec.md` and `design.md`.
    *   [ ] Ensure proper error handling and logging.
*   [ ] **3.2 Documentation:**
    *   [ ] Add/update comments in the code.
    *   [ ] Briefly document how to run the scripts and interpret outputs in a `README.md` within the script's directory (if creating a new subdirectory for scripts) or update the feature's main `README.md`.
*   [ ] **3.3 Final Test Run:**
    *   [ ] Perform a final run with the complete `UKBB_NMR_Meta.tsv`.
    *   [ ] Collect final mapping statistics.
