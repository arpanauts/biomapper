# Task List: MVP - UKBB NMR to Arivale Chemistries Mapping

## Phase 1: Setup and Initial Data Handling (Python Script)

*   **Task 1.1:** Create the main script file: `/home/ubuntu/biomapper/scripts/mvp_ukbb_arivale_chemistries/map_ukbb_to_arivale_chemistries.py`.
    *   Create the directory `/home/ubuntu/biomapper/scripts/mvp_ukbb_arivale_chemistries/` if it doesn't exist.
*   **Task 1.2:** Implement basic script structure:
    *   Add imports (e.g., `pandas`, `csv`, `argparse`, `logging`).
    *   Set up basic logging.
    *   Define a `main()` function.
*   **Task 1.3:** Implement `load_data(filepath, relevant_cols, is_arivale_chemistries=False)` function:
    *   Load UKBB NMR metadata (`UKBB_NMR_Meta.tsv`), selecting `field_id` and `title`.
    *   Load Arivale Chemistries metadata (`chemistries_metadata.tsv`), selecting relevant columns (e.g., `TestId`, `TestDisplayName`, `TestName`, `Units`, `Loinccode`, `Pubchem`).
    *   Handle skipping initial comment lines (e.g., starting with `#`) for Arivale data.
    *   Return data (e.g., as Pandas DataFrames).
*   **Task 1.4:** **Crucial:** Verify Arivale Chemistries column names.
    *   Before proceeding, manually inspect `chemistries_metadata.tsv` to confirm the exact names for `TestDisplayName`, `TestName`, `TestId`, `Units`, `Loinccode`, and `Pubchem`. Update the script if they differ from assumptions. Log the actual names used.

## Phase 2: Core Mapping Logic

*   **Task 2.1:** Implement `normalize_name(text: str) -> str` function:
    *   Converts text to lowercase.
    *   Trims leading/trailing whitespace.
    *   (Optional: Add other simple normalizations if deemed necessary after initial review, but keep simple for MVP).
*   **Task 2.2:** Implement `perform_mapping(ukbb_data, arivale_chemistries_data)` function:
    *   Iterate through unique UKBB `title` entries.
    *   Normalize the UKBB `title`.
    *   Normalize the Arivale `TestDisplayName` and `TestName` for comparison.
    *   Attempt to match normalized UKBB `title` against normalized Arivale `TestDisplayName`.
    *   If no match, attempt against normalized Arivale `TestName`.
    *   Handle match outcomes:
        *   **Single Match:** Record mapping details.
        *   **Multiple Matches:** For MVP, log the occurrence and pick the first match. Record which Arivale field matched.
        *   **No Match:** Record as "No Match".
    *   Store results in a list of dictionaries.
    *   Return the list of results.

## Phase 3: Output and Finalization

*   **Task 3.1:** Convert mapping results to a Pandas DataFrame.
*   **Task 3.2:** Write the DataFrame to a TSV file:
    *   Filename: `ukbb_to_arivale_chemistries_mapping.tsv`
    *   Location: `/home/ubuntu/biomapper/output/` (Create directory if it doesn't exist).
    *   Ensure columns match the `spec.md`.
*   **Task 3.3:** Implement summary statistics reporting:
    *   Count and print the number of "Successfully Mapped to Arivale", "No Match", "Multiple Arivale Matches - First Taken", etc.
*   **Task 3.4:** Add command-line argument parsing (e.g., using `argparse`) for input file paths and output directory, with sensible defaults.

## Phase 4: Testing and Review

*   **Task 4.1:** Test the script with the actual UKBB and Arivale Chemistries data files.
*   **Task 4.2:** Verify the output TSV file format and content.
*   **Task 4.3:** Review the console output for summary statistics.
*   **Task 4.4:** Ensure code is well-commented and follows PEP 8.
