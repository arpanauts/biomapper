# Task: Organize the `/home/ubuntu/biomapper/scripts` Directory

## Objective
The `/home/ubuntu/biomapper/scripts` directory contains a large number of Python scripts, shell scripts, and subdirectories, making it difficult to navigate and understand the purpose of each item. The goal is to reorganize this directory into a more logical and maintainable structure.

## Current State
The `scripts` directory currently has a flat structure with many individual files, along with some existing subdirectories. A listing of the current top-level contents has been provided (see context below if available, otherwise assume a mixed flat structure).

## Requested Reorganization Approach

Please reorganize the scripts and existing subdirectories into the following proposed structure. Use your best judgment for scripts not explicitly listed, based on their names and likely functionality. If a script's purpose is ambiguous from its name, you can leave it in a temporary `needs_categorization` subfolder or make a reasonable guess.

### Proposed New Directory Structure:

1.  **`main_pipelines/`**:
    *   Purpose: Primary, end-to-end mapping pipeline execution scripts.
    *   Move scripts like:
        *   `run_full_ukbb_hpa_mapping.py`
        *   `map_ukbb_to_arivale.py`
        *   `map_ukbb_to_hpa.py`
        *   `map_ukbb_to_qin.py`
        *   `map_ukbb_to_hpa_gene.py`
        *   `map_ukbb_to_qin_gene.py`
        *   `map_endpoints_flexible.py` (if it's a primary execution script)
        *   `phase3_bidirectional_reconciliation.py`
        *   `simple_ukbb_to_hpa_mapper.py` (consider if these "simple" mappers are distinct or older versions)
        *   `simple_ukbb_to_qin_mapper.py`
    *   Consider moving relevant MVP directories like `mvp_ukbb_arivale_chemistries/` and `mvp_ukbb_arivale_metabolomics/` here as sub-folders if they represent runnable pipelines.

2.  **`setup_and_configuration/`**:
    *   Purpose: Scripts for database setup, metadata population, resource configuration.
    *   Move scripts like:
        *   `populate_metamapper_db.py`
        *   `populate_composite_patterns.py`
        *   `update_entity_mapping_metadata.py`
        *   `fix_hpa_mapping_properties.py`
    *   Merge contents of the existing `db_management/` directory here if appropriate, or keep `db_management/` as a sub-folder if its contents are extensive and solely focused on DB admin tasks.

3.  **`data_preprocessing/`**:
    *   Purpose: Scripts for data preparation, filtering, transformation prior to mapping or DB loading.
    *   Move scripts like:
        *   `create_bio_relevant_cid_allowlist.py`
        *   `create_bio_relevant_cid_allowlist_chunked.py`
        *   `filter_pubchem_embeddings.py` (if primarily a preprocessing step for embeddings)
        *   `process_unichem_mappings.py`
        *   `enhanced_process_uniprot_gene_fallback.py`
        *   `extract_unmapped_for_uniprot.py`
    *   Merge contents of existing `data_processing/` and `preprocessing/` directories here.

4.  **`embeddings_and_rag/`**:
    *   Purpose: Scripts for creating, indexing, or querying embeddings, and RAG processes.
    *   Move scripts like:
        *   `index_filtered_embeddings_to_qdrant.py`
    *   Merge contents of existing `embeddings/` and `rag/` directories here. (Note: `test_qdrant_search.py` and `test_semantic_search.py` should go to `testing_and_validation/`)

5.  **`testing_and_validation/`**:
    *   Purpose: Test scripts, validation utilities, debugging tools, and test execution shell scripts.
    *   Move all `test_*.py` scripts here.
    *   Move all `debug_*.py` scripts here.
    *   Move scripts like `verify_arivale_client_init.py`, `stress_test_mapping_executor.py`.
    *   Move test-related shell scripts like `run_phase3_example.sh`, `test_one_to_many_in_real_world.sh`, `test_phase3_bidirectional.sh`, `test_phase3_with_real_data.sh`.
    *   Merge contents of existing `testing/`, `tests/`, `validation/`, `db_verification/`, and `debug/` directories here.

6.  **`analysis_and_reporting/`**:
    *   Purpose: Scripts for analyzing results, generating reports, or specific data checks post-processing.
    *   Move scripts like:
        *   `analyze_cid_overlap.py`
        *   `check_cid_ranges.py`
        *   `check_chunk_sizes.py`
    *   Merge contents of the existing `analysis/` directory here.
    *   Evaluate if `knowledge_graph/` contents belong here or if they are for KG construction (might be `data_preprocessing/` or its own category if substantial).

7.  **`utility_and_tools/`**:
    *   Purpose: General-purpose utilities, helper scripts, or tools.
    *   Move scripts like:
        *   `clear_uniprot_cache.py`
        *   `fix_mapping_script_flexible.py` (if it's a general utility for fixing/modifying other scripts or configurations)
    *   Merge contents of the existing `utils/` directory here.

8.  **`archived_or_experimental/`**:
    *   Purpose: Older versions, backups, or highly experimental scripts not in current active use.
    *   Move `*.py.backup` files here.
    *   Carefully evaluate scripts with "simple" in their names if more complex/current versions exist (e.g., `simple_ukbb_to_hpa_mapper.py` vs `run_full_ukbb_hpa_mapping.py`).
    *   If any `map_*.py` scripts are clearly superseded by `map_endpoints_flexible.py` or the main pipeline scripts, consider them for this category.

### Handling Other Existing Directories:

*   **`__pycache__/`**: This can be deleted or ignored (typically gitignored).
*   **`logs/`**: Can likely be deleted or ignored unless they contain critical historical logs that need to be preserved (if so, perhaps move to an `archived_logs/` within `archived_or_experimental/`).
*   **`test_output/`**: Can likely be deleted or ignored (typically gitignored).
*   **`mapping/`, `metamapping/`**:
    *   Examine their contents. If they contain runnable scripts, categorize them as above.
    *   If they contain Python modules or library code that is imported by scripts or other parts of the `biomapper` application, they likely **should not** be in the `scripts/` directory at all. They might belong in the main `biomapper/` package directory. Please flag these for review if they appear to be library code.
*   **`resources/`**:
    *   If these are data files (e.g., CSVs, TSVs, JSON data) used by the scripts, consider moving them to a project-level `data/resources/` directory outside of `scripts/` for better separation of code and data.
    *   If they are script-specific resources (e.g., templates, small config snippets only used by one script), they could be co-located within the new subdirectories alongside the scripts that use them.

### Deliverables:

1.  A list of `mv` commands (or equivalent file operation descriptions) to achieve the reorganization.
2.  For any files/directories where categorization is ambiguous, list them under a "Needs Manual Review" section with your reasoning.
3.  If any directories like `mapping/` or `metamapping/` appear to contain library code rather than runnable scripts, please highlight this as a separate point for further action (i.e., moving them out of `scripts/` entirely).

### Important Considerations:

*   **Path Updates**: Be aware that moving scripts might break relative import paths within the scripts themselves or in how they are called. This prompt focuses on the file organization; code updates to fix paths will be a subsequent step.
*   **Git History**: If this is a Git repository, these moves should ideally be done with `git mv` to preserve history, but for this task, providing the conceptual file moves is sufficient.
*   **Idempotency**: The reorganization should ideally result in the same structure if run multiple times (though this is a one-off task).

Please provide the reorganization plan.
