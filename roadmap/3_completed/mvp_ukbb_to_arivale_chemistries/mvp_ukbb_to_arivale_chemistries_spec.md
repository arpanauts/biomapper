# Specification: UKBB NMR to Arivale Chemistries Mapping

## 1. Input Data

### 1.1. UKBB NMR Metadata
*   **File:** `/procedure/data/local_data/HPP_PHENOAI_METADATA/UKBB_NMR_Meta.tsv`
*   **Format:** Tab-Separated Values (TSV)
*   **Relevant Columns:**
    *   `field_id`: Unique identifier for the UKBB entry.
    *   `title`: Human-readable name of the metabolite/biomarker (primary input for matching).

### 1.2. Arivale Chemistries Metadata
*   **File:** `/procedure/data/local_data/ARIVALE_SNAPSHOTS/chemistries_metadata.tsv`
*   **Format:** Tab-Separated Values (TSV)
*   **Preprocessing:** Skip initial comment lines (typically starting with `#`).
*   **Relevant Columns for Matching (primary candidates - verify exact names from file):**
    *   `TestDisplayName`
    *   `TestName`
*   **Other Relevant Columns (for output/context - verify exact names from file):**
    *   `TestId`
    *   `Units`
    *   `Loinccode`
    *   `Pubchem` (Note: PubChem ID is less likely to be a primary key for chemistries but useful if present)

## 2. Core Logic & Components

### 2.1. Main Mapping Process
1.  **Load Data:**
    *   Load UKBB `title` and `field_id` (e.g., into a Pandas DataFrame or list of dicts).
    *   Load Arivale chemistries data (e.g., into a Pandas DataFrame or list of dicts).
2.  **Name Normalization:**
    *   Implement a `normalize_name(text)` function:
        *   Converts text to lowercase.
        *   Trims leading/trailing whitespace.
        *   (Consider other simple normalizations if obviously beneficial, e.g., removing specific common punctuation, but keep it simple for MVP).
3.  **Iterate and Match:**
    *   For each unique `title` in the UKBB data:
        *   `normalized_ukbb_title = normalize_name(ukbb_title)`
        *   Search for matches in the Arivale chemistries data:
            *   Attempt to match `normalized_ukbb_title` against `normalize_name(arivale_entry['TestDisplayName'])`.
            *   If no match, attempt to match `normalized_ukbb_title` against `normalize_name(arivale_entry['TestName'])`.
        *   **Decision Logic:**
            *   If a match is found:
                *   Record as "Successfully Mapped to Arivale".
                *   Store relevant Arivale data and which field matched (e.g., `TestDisplayName` or `TestName`).
                *   If multiple Arivale entries match a single UKBB title (e.g., after normalization), for MVP, either take the first match or log that multiple matches occurred and pick one.
            *   If no match is found:
                *   Record as "No Match".
4.  **Store Results:** Accumulate mapping results.

## 3. Output File

*   **Format:** Tab-Separated Values (TSV)
*   **Name:** `ukbb_to_arivale_chemistries_mapping.tsv`
*   **Location:** `/home/ubuntu/biomapper/output/` (Create directory if it doesn't exist)
*   **Columns:**
    *   `ukbb_field_id`
    *   `ukbb_title`
    *   `ukbb_normalized_title` (optional, for debugging)
    *   `mapping_status` (e.g., "Successfully Mapped to Arivale", "No Match", "Multiple Arivale Matches - First Taken")
    *   `arivale_test_id` (if successfully mapped)
    *   `arivale_test_display_name` (if successfully mapped)
    *   `arivale_test_name` (if successfully mapped)
    *   `arivale_matched_field` (e.g., "TestDisplayName", "TestName")
    *   `arivale_units` (if successfully mapped)
    *   `arivale_loinccode` (if successfully mapped and available)
    *   `arivale_pubchem` (if successfully mapped and available)

## 4. Success Criteria

*   The mapping script processes all unique UKBB titles.
*   The output TSV is generated in the specified format and location.
*   Mapping statistics (counts for each `mapping_status`) are reported.
*   The approach provides a baseline for UKBB-Arivale chemistries mapping.
