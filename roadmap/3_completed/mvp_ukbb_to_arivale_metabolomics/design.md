# Design: UKBB NMR to Arivale Metabolomics Mapping

## 1. High-Level Script Structure (Python)

The solution will likely consist of two main Python scripts:

1.  `test_rag_client_arivale.py`: For validating the `PubChemRAGMappingClient` on Arivale data.
2.  `map_ukbb_to_arivale_metabolomics.py`: For the main end-to-end mapping.

Shared utility functions (e.g., for TSV loading) might be in a `utils.py` or similar.

## 2. Key Components and Functions

### 2.1. `test_rag_client_arivale.py`
*   `load_arivale_samples(filepath, sample_size=20)`:
    *   Reads `metabolomics_metadata.tsv`.
    *   Skips comments.
    *   Selects a diverse sample of `BIOCHEMICAL_NAME` and their `PUBCHEM` IDs.
    *   Returns a list of tuples/dicts: `(biochemical_name, ground_truth_pubchem_id)`.
*   `main_test_loop(arivale_samples, rag_client_instance)`:
    *   Iterates through samples.
    *   Calls `rag_client_instance.map_identifiers([sample.biochemical_name])`.
    *   Compares results with `sample.ground_truth_pubchem_id`.
    *   Prints/logs detailed results for each sample.
    *   Calculates overall accuracy for the test set.

### 2.2. `map_ukbb_to_arivale_metabolomics.py`
*   `load_ukbb_data(filepath)`:
    *   Reads `UKBB_NMR_Meta.tsv`.
    *   Returns a list of dicts: `[{'field_id': ..., 'title': ...}, ...]`.
*   `load_arivale_data_for_lookup(filepath)`:
    *   Reads `metabolomics_metadata.tsv`.
    *   Skips comments.
    *   Creates and returns a dictionary: `{arivale_pubchem_id: {arivale_row_data}, ...}`.
        *   Handles cases where `PUBCHEM` might be missing or duplicated in Arivale file.
*   `perform_mapping(ukbb_data, arivale_lookup, rag_client_instance)`:
    *   Initializes an empty list `mapping_results`.
    *   Iterates through each `item` in `ukbb_data`.
        *   `ukbb_title = item['title']`
        *   `rag_output = rag_client_instance.map_identifiers([ukbb_title])`
        *   `derived_cid, confidence, status = process_rag_output(rag_output, arivale_lookup)`
        *   If `status == "Successfully Mapped to Arivale"`:
            *   `arivale_data = arivale_lookup[derived_cid]`
            *   Append full result to `mapping_results`.
        *   Else:
            *   Append partial result (UKBB info, RAG info, status) to `mapping_results`.
    *   Return `mapping_results`.
*   `process_rag_output(rag_output, arivale_lookup, confidence_threshold=0.8)`:
    *   Analyzes the output from `rag_client.map_identifiers()`.
    *   Determines the best PubChem CID candidate and its confidence.
    *   Checks if the candidate CID exists in `arivale_lookup`.
    *   Returns `(derived_cid, confidence, mapping_status_string)`.
*   `write_results_to_tsv(mapping_results, output_filepath)`:
    *   Writes the `mapping_results` to a TSV file with headers as specified in `spec.md`.
*   `main()`:
    *   Parses command-line arguments (input file paths, output file path).
    *   Instantiates `PubChemRAGMappingClient`.
    *   Calls data loading functions.
    *   Calls `perform_mapping`.
    *   Calls `write_results_to_tsv`.
    *   Prints summary statistics.

## 3. Data Structures
*   **UKBB Data:** List of dictionaries: `[{'field_id': str, 'title': str}, ...]`
*   **Arivale Lookup:** Dictionary: `{pubchem_id_str: {'CHEMICAL_ID': str, 'BIOCHEMICAL_NAME': str, ...other_arivale_cols}, ...}`
*   **Mapping Results:** List of dictionaries, where each dictionary corresponds to a row in the output TSV.

## 4. `PubChemRAGMappingClient` Interaction
*   **Assumption:** The client has a method like `map_identifiers(queries: List[str], **kwargs) -> MappingOutput`.
*   `MappingOutput` (or its equivalent) should provide:
    *   A list of mapped terms, each with:
        *   Original query term.
        *   Derived PubChem CID(s).
        *   Confidence score(s).
        *   Potentially other metadata like source of match if RAG provides it.
*   Configuration of the client (API keys, model names, vector store details) is assumed to be handled externally or during instantiation.

## 5. Error Handling & Logging
*   Log file I/O errors.
*   Log errors during RAG client calls.
*   Log cases where PubChem IDs from RAG are not found in Arivale.
*   Provide counts for different mapping statuses.
