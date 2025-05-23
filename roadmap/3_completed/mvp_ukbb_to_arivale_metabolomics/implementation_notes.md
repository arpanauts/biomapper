# Implementation Notes: MVP UKBB NMR to Arivale Metabolomics Mapping

## 1. `PubChemRAGMappingClient` Configuration
*   Ensure that the `PubChemRAGMappingClient` is correctly configured. This might involve environment variables for API keys, model endpoints, or vector database connection details. Refer to the client's own documentation or setup instructions.
*   The `map_identifiers` method is expected to take a list of strings (queries) and return a structured output (e.g., `MappingOutput` class instance) that contains the original query, mapped PubChem CID(s), and confidence scores.

## 2. Data Handling
*   **Arivale `metabolomics_metadata.tsv`:**
    *   This file is known to have comment lines at the beginning (starting with `#`). Ensure these are skipped during parsing.
    *   The `PUBCHEM` column in Arivale data might have missing values or potentially multiple CIDs (though less common for PubChem). The `load_arivale_data_for_lookup` function should decide how to handle these (e.g., log and skip entries with missing PubChem CIDs, or if multiple, decide on a strategy like taking the first or splitting if the RAG client can handle multiple target CIDs). For MVP, focusing on single, clean PubChem IDs is likely sufficient.
*   **UKBB `UKBB_NMR_Meta.tsv`:**
    *   The `title` column will be the primary input to the RAG client. Consider if any pre-processing of these titles (e.g., stripping extra whitespace) is beneficial before sending to the RAG client.
*   **Pandas:** Using Pandas DataFrames for loading and initial manipulation of TSV data can be convenient, especially for `UKBB_NMR_Meta.tsv`. For the Arivale lookup, a dictionary keyed by PubChem CID will likely offer better performance.

## 3. Confidence Threshold
*   The RAG client test (`test_rag_client_arivale.py`) should help inform a reasonable `confidence_threshold` for the main mapping script. This threshold determines whether a RAG mapping is considered reliable enough to proceed with an Arivale lookup.
*   Start with a relatively high threshold (e.g., 0.8 or 0.85) and adjust based on test results and initial mapping run quality.

## 4. Mapping Logic (`process_rag_output`)
*   When the RAG client returns multiple PubChem CIDs for a single UKBB title:
    *   For the MVP, the simplest approach is to pick the one with the highest confidence score.
    *   Log that multiple candidates were returned, perhaps including the other candidates and their scores in a separate log or a specific column in the output if deemed necessary for later analysis (though `spec.md` currently doesn't require this for the main output TSV).
*   The `mapping_status` column in the output is crucial for understanding the results. Ensure all scenarios (successful match, RAG success but no Arivale match, RAG fail, low confidence) are covered.

## 5. Performance
*   For the full UKBB dataset, iterating and calling the RAG client for each unique title might take time.
    *   Consider processing only unique UKBB titles to avoid redundant RAG calls.
    *   Batching calls to `map_identifiers` (if the client supports it efficiently) could be an optimization, but for MVP, individual calls per unique title are acceptable.

## 6. Python Environment
*   Ensure all necessary libraries (`pandas`, etc.) are part of the project's dependencies (e.g., in `pyproject.toml` if using Poetry).
*   The scripts should be runnable from the project's root directory or a designated `scripts` directory.

## 7. Output File
*   The output TSV (`ukbb_to_arivale_metabolomics_mapping.tsv`) should strictly follow the column order and naming specified in `spec.md`.
*   Ensure consistent quoting and escaping if necessary, though standard TSV writers usually handle this.
