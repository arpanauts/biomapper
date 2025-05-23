# MVP: UKBB NMR to Arivale Chemistries Mapping

## 1. Overview

This task focuses on mapping metabolic biomarker data from UKBB (specifically, `UKBB_NMR_Meta.tsv`) to Arivale chemistries metadata (`chemistries_metadata.tsv`). The primary goal is to link UKBB `title` entries (human-readable names of biomarkers) to corresponding entries in the Arivale Chemistries dataset.

The initial mapping approach will focus on direct name matching between the UKBB `title` and relevant name fields in the Arivale Chemistries data (e.g., `TestDisplayName`, `TestName`). This MVP aims to establish a baseline mapping for chemistries.

## 2. Goals

*   Successfully map UKBB NMR biomarker titles to Arivale Chemistries entries via direct name matching.
*   Produce a TSV output file detailing the mapping results.
*   Identify potential challenges and areas for improvement in chemistry mapping (e.g., name variations, need for more sophisticated matching).

## 3. Scope

*   **In Scope:**
    *   Loading and parsing `UKBB_NMR_Meta.tsv`.
    *   Loading and parsing `chemistries_metadata.tsv`.
    *   Implementing a script for direct name matching (with basic normalization).
    *   Generating a TSV output of mapping results.
    *   Basic statistics reporting on mapping success.
*   **Out of Scope (for this MVP):**
    *   RAG-based mapping for chemistries (may be considered later).
    *   Mapping to Arivale Metabolomics data (covered in a separate MVP).
    *   Complex fuzzy matching algorithms (beyond basic normalization like case-insensitivity and whitespace trimming).
    *   UI/Dashboard for results.
    *   Database persistence of these specific mapping results (beyond the output file).
