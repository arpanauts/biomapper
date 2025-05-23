# Feature: Improve UKBB NMR to Arivale Chemistries Mapping Success Rate

## 1. Overview

The initial MVP for mapping UKBB NMR metadata to Arivale Chemistries (`mvp_ukbb_to_arivale_chemistries`) yielded a low match rate of approximately 2.8% using simple direct name matching (lowercase and trimmed). This feature aims to investigate the reasons for this low success rate and implement more advanced mapping strategies to significantly improve it.

## 2. Goals

*   Analyze the unmatched UKBB NMR titles and Arivale Chemistries entries to identify patterns and reasons for mismatches.
*   Explore and implement more sophisticated string matching techniques (e.g., fuzzy matching, partial matching, token-based matching).
*   Investigate the utility of leveraging additional fields in the Arivale dataset (e.g., "Labcorp Name", "Quest Name", "Labcorp LOINC Name") for matching.
*   Potentially refine normalization techniques for both datasets.
*   Significantly increase the mapping success rate between UKBB NMR and Arivale Chemistries.
*   Update or create new scripts to implement the improved mapping logic.

## 3. Scope

*   **In Scope:**
    *   Data analysis of unmatched entries from the MVP.
    *   Research and selection of appropriate advanced string matching algorithms/libraries.
    *   Implementation of new or modified Python scripts incorporating these techniques.
    *   Testing of the improved mapping logic.
    *   Documentation of the new approach and its performance.
*   **Out of Scope (Potentially):**
    *   Fundamental changes to the RAG-based mapping approach (this feature focuses on direct/advanced string matching for *this specific* UKBB-Arivale Chemistries link).
    *   Large-scale manual curation (though some manual review might inform strategy).

## 4. Potential Approaches (to be investigated)

*   FuzzyWuzzy, python-Levenshtein, or similar libraries for fuzzy matching.
*   Tokenization and set matching (e.g., Jaccard similarity on name components).
*   Considering synonyms or common abbreviations if available or derivable.
*   Rule-based mapping for common patterns.
*   Using LOINC codes if a reliable mapping from UKBB terms to LOINC can be established first (could be a separate sub-task).
