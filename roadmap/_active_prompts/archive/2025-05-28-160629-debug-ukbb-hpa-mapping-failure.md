## Claude Code Prompt: Debug UKBB to HPA Protein Mapping Failure

**Source Prompt Reference:** Cascade conversation leading to Step 347 (USER_REQUEST at 2025-05-28T16:06:29Z).

**Task Definition:**
Investigate and identify the root cause for the continued failure (0 successful mappings out of 10 records) of the UKBB Protein to HPA Protein mapping, even after correcting configurations in `populate_metamapper_db.py`.

**Context:**
- The goal is to map UniProtKB ACs from a UKBB input file to UniProtKB ACs in an HPA data file.
- The mapping script `scripts/map_ukbb_to_hpa.py` is used, which leverages the `MappingExecutor`.
- The `metamapper.db` is populated by `scripts/populate_metamapper_db.py`.
- Recent corrections were made to `populate_metamapper_db.py` to ensure:
    - `HPA_Protein` endpoint has correct `connection_details` pointing to `/home/ubuntu/biomapper/data/isb_osp/hpa_osps.csv`.
    - `PropertyExtractionConfig` for HPA's UniProtKB AC correctly uses `resources["hpa_protein_lookup"].id` and expects a 'uniprot' column.
    - `hpa_protein_lookup` `MappingResource` correctly points to the HPA CSV and its 'uniprot' column for identity lookup.
    - `UKBB_Protein` endpoint and its UniProtKB AC extraction are correctly configured.
    - The `MappingPath` `UKBB_Protein_to_HPA_Protein_UniProt_Identity` seems correct.

**Input Files & Key Configurations:**
1.  **UKBB Source Data (first 10 rows used by script):** `/procedure/data/local_data/HPP_PHENOAI_METADATA/UKBB_Protein_Meta.tsv`
    - UniProtKB ACs are in a column named `UniProt`.
2.  **HPA Target Data:** `/home/ubuntu/biomapper/data/isb_osp/hpa_osps.csv`
    - UniProtKB ACs are in a column named `uniprot` (header: `gene,uniprot,organ`).
3.  **Mapping Script:** `/home/ubuntu/biomapper/scripts/map_ukbb_to_hpa.py`
    - Command used: `poetry run python scripts/map_ukbb_to_hpa.py --source_endpoint UKBB_Protein --target_endpoint HPA_Protein --input_id_column_name UniProt --input_primary_key_column_name UniProt --output_mapped_id_column_name HPA_UniProtKB_AC --source_ontology_name UNIPROTKB_AC --target_ontology_name UNIPROTKB_AC --summary /procedure/data/local_data/HPP_PHENOAI_METADATA/UKBB_Protein_Meta.tsv /home/ubuntu/biomapper/data/output/ukbb_to_hpa_mapping_results.tsv`
4.  **Metamapper DB Population Script:** `/home/ubuntu/biomapper/scripts/populate_metamapper_db.py`
5.  **Output TSV:** `/home/ubuntu/biomapper/data/output/ukbb_to_hpa_mapping_results.tsv`
6.  **Output Summary:** `/home/ubuntu/biomapper/data/output/ukbb_to_hpa_mapping_results_summary_report.txt` (shows 0/10 mapped).

**Investigation Steps for Claude Code Instance:**

1.  **Data Validation (Crucial):**
    a.  Extract the first 10 UniProtKB ACs from `/procedure/data/local_data/HPP_PHENOAI_METADATA/UKBB_Protein_Meta.tsv` (as read by the script).
    b.  For each of these 10 UniProtKB ACs, manually check if they exist in the `uniprot` column of `/home/ubuntu/biomapper/data/isb_osp/hpa_osps.csv`.
        - Pay close attention to potential discrepancies: case sensitivity (though UniProt ACs are usually consistent), leading/trailing whitespace, or any special characters.
    c.  Report the findings of this manual check: which IDs were found, which were not, and any observed discrepancies.

2.  **Enhanced Logging (If data validation doesn't reveal a simple non-overlap):**
    a.  Modify `scripts/map_ukbb_to_hpa.py` (or relevant parts of `MappingExecutor` / `GenericFileLookupClient` if necessary, though modifying the script is preferred for localized debugging) to add detailed logging output during the lookup process for the HPA target.
    b.  Logs should include:
        - The exact source UniProtKB AC being looked up.
        - Confirmation that the `hpa_protein_lookup` resource is being used.
        - The key being used for lookup in the HPA CSV (should be the source UniProtKB AC).
        - Whether a match is found by the `GenericFileLookupClient` in the HPA CSV.
        - Any errors or exceptions encountered during the lookup for a specific ID.
    c.  Re-run the population script and the mapping script with enhanced logging.

3.  **Analysis of Logs and Findings:**
    a.  Analyze the detailed logs to pinpoint where the mapping process fails for these 10 records.
    b.  If the issue is data-related (e.g., subtle formatting), clearly state it.
    c.  If the issue points to a potential bug in the code (e.g., `GenericFileLookupClient` not handling data correctly, `MappingExecutor` path resolution issue), provide a hypothesis.

**Expected Output from Claude Code Instance:**

- A Markdown feedback file in `/home/ubuntu/biomapper/roadmap/_active_prompts/feedback/` named `YYYY-MM-DD-HHMMSS-feedback-debug-ukbb-hpa-mapping-failure.md`.
- The feedback file should contain:
    - Results of the data validation (which of the 10 UKBB UniProt IDs are present in the HPA CSV).
    - If enhanced logging was implemented, the modified code snippet(s) and the relevant log outputs.
    - A clear explanation of the root cause of the mapping failure for these 10 records.
    - If a code change is required to fix a bug (beyond simple data cleaning), provide the suggested code modification.

**Constraints:**
- Prioritize data validation first, as it's the most likely culprit.
- If modifying code for logging, ensure changes are localized and easily reversible if needed.
- All paths are absolute.
- The environment uses Poetry (`pyproject.toml` in `/home/ubuntu/biomapper/`).

This detailed investigation should help us understand why the seemingly correct configurations are still leading to zero successful mappings.
