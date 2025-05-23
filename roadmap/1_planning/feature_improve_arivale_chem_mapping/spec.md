# Specification: Improve UKBB NMR to Arivale Chemistries Mapping

## 1. Current State & Problem

*   The existing script `map_ukbb_to_arivale_chemistries.py` (from MVP) uses simple direct name matching (lowercase, trim whitespace) on UKBB `title` against Arivale `Display Name` and `Name`.
*   This resulted in a ~2.8% match rate (7 out of 251 UKBB entries).
*   Feedback from the MVP implementation (`2025-05-23-232700-feedback-implement-ukbb-arivale-chemistries-mvp.md`) highlighted this low rate and suggested further investigation.

## 2. Desired State

*   A significantly higher mapping success rate between UKBB NMR titles and Arivale Chemistries entries.
*   A robust, well-documented, and tested Python script that implements more advanced matching techniques.
*   Clear reporting on the performance of the new mapping strategy, including match rates and confidence/quality metrics if applicable.

## 3. Data Sources

*   **UKBB NMR Metadata:** `/procedure/data/local_data/HPP_PHENOAI_METADATA/UKBB_NMR_Meta.tsv` (Column: `title`)
*   **Arivale Chemistries Metadata:** `/procedure/data/local_data/ARIVALE_SNAPSHOTS/chemistries_metadata.tsv` (Relevant columns for matching: `Display Name`, `Name`, and potentially `Labcorp Name`, `Quest Name`, `Labcorp LOINC Name`).
    *   *Note: Ensure the `spec.md` for the original MVP is updated first to reflect correct Arivale column names as per `docfix_arivale_chem_spec_cols` task.*

## 4. Functional Requirements

*   The system must be able to load and preprocess data from both UKBB and Arivale sources.
*   Implement one or more advanced string matching techniques beyond simple exact matching.
*   Allow configuration of matching parameters (e.g., similarity thresholds for fuzzy matching).
*   Produce an output mapping file similar in structure to the MVP, but with potentially more matches and possibly additional columns indicating match type or confidence.
*   Provide summary statistics on mapping performance.

## 5. Non-Functional Requirements

*   **Performance:** The script should be reasonably performant for the given dataset sizes.
*   **Maintainability:** Code should be well-structured, commented, and easy to understand.
*   **Extensibility:** Design should allow for potential future additions of other matching strategies.

## 6. Success Criteria

*   A demonstrable and significant increase in the match rate compared to the MVP's 2.8%. (Target to be defined after initial analysis, e.g., >20% or >50%).
*   The implemented solution is robust and handles data variations gracefully.
*   The approach and its effectiveness are clearly documented.
