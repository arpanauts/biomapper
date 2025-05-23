# Design: Improve UKBB NMR to Arivale Chemistries Mapping

## 1. Initial Data Analysis & Strategy Selection

*   **Analyze Mismatches:**
    *   Load the output from the MVP (`ukbb_to_arivale_chemistries_mapping.tsv`).
    *   Systematically review a sample of unmatched UKBB `title` entries and compare them against the Arivale `Display Name`, `Name`, and other potentially relevant text fields.
    *   Categorize common reasons for mismatches (e.g., word order, abbreviations, synonyms, extra/missing words, punctuation, pluralization).
*   **Research Matching Techniques:**
    *   Based on mismatch analysis, evaluate suitable Python libraries/algorithms:
        *   **Fuzzy Matching:** `FuzzyWuzzy` (uses Levenshtein Distance), `python-Levenshtein`. Good for typos, minor variations.
        *   **Token-based Matching:**
            *   Split names into tokens (words).
            *   Calculate similarity based on common tokens (e.g., Jaccard index on sets of tokens, TF-IDF cosine similarity on token vectors).
        *   **Phonetic Matching:** Soundex, Metaphone (less likely for metabolite names but possible).
        *   **N-gram Matching:** Comparing sequences of characters.
*   **Select Primary Strategy (and potential fallbacks):** Choose one or a combination of techniques that seem most promising.

## 2. Proposed Script Structure (`improve_arivale_chem_mapping.py`)

*   **Configuration:**
    *   Command-line arguments for input files, output file, similarity thresholds, strategy selection (if multiple are implemented).
*   **Data Loading:**
    *   Functions to load UKBB and Arivale data (reuse/adapt from MVP).
    *   Ensure correct Arivale column names are used.
*   **Preprocessing/Normalization:**
    *   Standard normalization (lowercase, trim).
    *   Advanced normalization based on analysis (e.g., removing common suffixes/prefixes, standardizing units if embedded in names, handling punctuation).
*   **Core Matching Logic:**
    *   Implement the chosen advanced matching algorithm(s).
    *   Iterate through UKBB titles. For each, search for matches in Arivale data.
    *   Consider a multi-pass approach:
        1.  Attempt exact match (after normalization).
        2.  If no exact match, attempt chosen advanced matching technique(s) against `Display Name`.
        3.  If still no match, potentially try against `Name`, then `Labcorp Name`, `Quest Name`.
    *   Store results, including the UKBB title, best Arivale match, match score/confidence, and the Arivale field that produced the match.
*   **Output Generation:**
    *   TSV file with detailed mapping results.
    *   Console summary statistics (total processed, matched count, match rate, breakdown by match type/score if applicable).
*   **Logging:** Comprehensive logging of the process.

## 3. Key Components & Technologies

*   **Python 3**
*   **Pandas (Highly Recommended):** For data manipulation and analysis.
*   **Selected Matching Library (e.g., `FuzzyWuzzy`, `rapidfuzz`, `nltk` for tokenization):** Add to `pyproject.toml` if new.
*   Standard libraries: `csv`, `argparse`, `logging`.

## 4. Data Structures

*   Pandas DataFrames for holding UKBB and Arivale data.
*   Dictionaries or lists of Pydantic models for storing mapping results before writing to TSV.

## 5. Testing Strategy

*   Create a small, representative subset of UKBB and Arivale data for testing. Include:
    *   Known matches that the MVP missed but the new strategy should find.
    *   Known non-matches.
    *   Edge cases identified during analysis.
*   Unit tests for normalization functions and core matching algorithm components.
*   Integration tests for the overall script flow with the test dataset.
*   Compare output against expected results for the test dataset.

## 6. Iteration & Refinement

*   The first implementation might not be perfect. Be prepared to:
    *   Analyze results from the improved script.
    *   Adjust thresholds or parameters.
    *   Potentially tweak normalization or the matching algorithm.
    *   The goal is significant improvement, not necessarily 100% automation if the data is very noisy.
