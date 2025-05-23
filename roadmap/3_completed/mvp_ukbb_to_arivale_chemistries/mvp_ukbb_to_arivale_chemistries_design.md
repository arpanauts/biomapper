# Design: UKBB NMR to Arivale Chemistries Mapping

## 1. High-Level Script Structure (Python)

The solution will primarily consist of a single Python script:

*   `map_ukbb_to_arivale_chemistries.py`

This script will handle data loading, normalization, matching, and output generation.

## 2. Key Components and Functions within `map_ukbb_to_arivale_chemistries.py`

*   `load_data(filepath, is_ukbb=True)`:
    *   Generic function to load TSV data, potentially into Pandas DataFrames.
    *   Handles skipping comment lines for Arivale data.
    *   Returns relevant columns.
*   `normalize_name(text: str) -> str`:
    *   Converts text to lowercase.
    *   Trims leading/trailing whitespace.
    *   Returns the normalized string.
*   `perform_mapping(ukbb_df, arivale_df)`:
    *   `ukbb_df`: DataFrame with UKBB `field_id` and `title`.
    *   `arivale_df`: DataFrame with Arivale chemistries data.
    *   Initializes an empty list `mapping_results`.
    *   Pre-normalize relevant Arivale name columns for efficient lookup if possible, or normalize on-the-fly.
    *   Iterate through unique UKBB titles:
        *   `normalized_title = normalize_name(ukbb_row['title'])`
        *   Search for `normalized_title` in normalized Arivale `TestDisplayName` and `TestName` columns.
        *   If a match is found:
            *   Collect all matching Arivale rows.
            *   If one match, record details.
            *   If multiple matches, decide on a strategy (e.g., take first, list all CIDs if IDs are the target, or flag as "Multiple Matches"). For MVP, taking the first and noting is acceptable.
            *   Append result to `mapping_results`.
        *   If no match, append a "No Match" result.
    *   Return a DataFrame from `mapping_results`.
*   `main()`:
    *   Argument parsing for input file paths (UKBB, Arivale Chemistries) and output file path.
    *   Call `load_data` for both inputs.
    *   Call `perform_mapping`.
    *   Write the resulting DataFrame to TSV (e.g., `ukbb_to_arivale_chemistries_mapping.tsv` in `/home/ubuntu/biomapper/output/`).
    *   Print summary statistics (counts of mapping statuses).

## 3. Data Structures
*   **Pandas DataFrames** are recommended for handling the TSV data, allowing for easier column selection and vectorized normalization if desired.
*   The final `mapping_results` can be a list of dictionaries, converted to a DataFrame before writing to TSV.

## 4. Column Name Verification
*   **Crucial Step:** Before full implementation, the exact column names in `chemistries_metadata.tsv` (e.g., `TestDisplayName`, `TestName`, `TestId`, `Units`, `Loinccode`, `Pubchem`) **must be verified** by inspecting the file. The design assumes these names but they might differ. The script should use the correct names.

## 5. Error Handling and Logging
*   Use basic `try-except` blocks for file I/O.
*   Log warnings if expected columns are missing in input files.
*   Report counts of records processed, matches found, and no-matches.
