# Implementation Notes: MVP - UKBB NMR to Arivale Chemistries Mapping

## 1. Core Objective
The primary goal is to map UKBB NMR `title` entries to Arivale Chemistries entries based on **direct name matching**. This is a simpler approach than the RAG-based mapping used for metabolomics and serves as a baseline for chemistries.

## 2. Data File Paths
*   **UKBB NMR Metadata:** `/procedure/data/local_data/HPP_PHENOAI_METADATA/UKBB_NMR_Meta.tsv`
*   **Arivale Chemistries Metadata:** `/procedure/data/local_data/ARIVALE_SNAPSHOTS/chemistries_metadata.tsv`
*   **Output Mapping File:** `/home/ubuntu/biomapper/output/ukbb_to_arivale_chemistries_mapping.tsv`
    *   The `/home/ubuntu/biomapper/output/` directory should be created by the script if it does not exist.

## 3. Critical: Arivale Chemistries Column Names
*   The `spec.md` and `design.md` list assumed column names for Arivale Chemistries data (e.g., `TestDisplayName`, `TestName`, `TestId`, `Units`, `Loinccode`, `Pubchem`).
*   **It is crucial to verify these column names by inspecting the actual `chemistries_metadata.tsv` file before or during early implementation.** The script must use the correct column names found in the file. Log which names are being used.

## 4. Name Matching Strategy
*   **Normalization:**
    *   Implement a `normalize_name(text)` function.
    *   At a minimum, this function should convert text to **lowercase** and **trim leading/trailing whitespace**.
    *   Consider if any other very simple, safe normalizations are beneficial (e.g., removing specific punctuation like hyphens or parentheses if they consistently cause mismatches), but avoid complex regex or fuzzy logic for this MVP.
*   **Matching Order:**
    1.  Attempt to match the normalized UKBB `title` against the normalized Arivale `TestDisplayName`.
    2.  If no match, attempt to match against the normalized Arivale `TestName`.
*   **Case Sensitivity:** Matching should be case-insensitive (handled by normalization).

## 5. Handling Multiple Matches
*   If a single normalized UKBB `title` matches multiple entries in the Arivale Chemistries data (either via `TestDisplayName` or `TestName`):
    *   For this MVP, the script should:
        1.  Log that multiple matches were found for the given UKBB title.
        2.  Select the **first** match encountered.
        3.  Populate the output row with details from this first match.
        4.  Use a `mapping_status` like "Multiple Arivale Matches - First Taken".

## 6. Output File (`ukbb_to_arivale_chemistries_mapping.tsv`)
*   Ensure the columns in the output TSV strictly follow the order and names specified in `spec.md`:
    *   `ukbb_field_id`
    *   `ukbb_title`
    *   `ukbb_normalized_title` (optional, useful for debugging the matching logic)
    *   `mapping_status` (e.g., "Successfully Mapped to Arivale", "No Match", "Multiple Arivale Matches - First Taken")
    *   `arivale_test_id`
    *   `arivale_test_display_name`
    *   `arivale_test_name`
    *   `arivale_matched_field` (Indicate which Arivale field led to the match, e.g., "TestDisplayName" or "TestName")
    *   `arivale_units`
    *   `arivale_loinccode`
    *   `arivale_pubchem`
*   Fields from Arivale should be blank if `mapping_status` is "No Match".

## 7. Libraries
*   **Pandas** is highly recommended for data loading and manipulation.
*   `csv` module can be used if Pandas is not preferred, but Pandas will simplify operations.
*   `argparse` for command-line arguments.
*   `logging` for basic logging.

## 8. Script Location
*   The main script should be: `/home/ubuntu/biomapper/scripts/mvp_ukbb_arivale_chemistries/map_ukbb_to_arivale_chemistries.py`
*   Create the `mvp_ukbb_arivale_chemistries` subdirectory under `scripts` if it doesn't exist.

Good luck with the implementation!
