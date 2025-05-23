# MVP: UKBB NMR to Arivale Metabolomics Mapping

## 1. Overview

This task focuses on mapping metabolic biomarker data from UKBB (specifically, `UKBB_NMR_Meta.tsv`) to Arivale metabolomics metadata (`metabolomics_metadata.tsv`). The primary goal is to link UKBB `title` entries (human-readable names of metabolites) to corresponding entries in the Arivale dataset by leveraging PubChem CIDs as the primary shared ontology.

The core mapping mechanism will be the `PubChemRAGMappingClient`, which will convert UKBB titles to PubChem CIDs. These CIDs will then be used to look up matching entries in the Arivale data.

This MVP includes a preliminary step to test the `PubChemRAGMappingClient`'s performance on known biochemical names from the Arivale dataset to validate its efficacy before full-scale mapping.

## 2. Goals

*   Successfully map UKBB NMR metabolite titles to Arivale metabolomics entries via PubChem CIDs.
*   Utilize the `PubChemRAGMappingClient` for converting names to PubChem CIDs.
*   Produce a TSV output file detailing the mapping results, including confidence scores and status.
*   Validate the `PubChemRAGMappingClient` on a subset of Arivale data.

## 3. Scope

*   **In Scope:**
    *   Loading and parsing `UKBB_NMR_Meta.tsv`.
    *   Loading and parsing `metabolomics_metadata.tsv`.
    *   Implementing a test script for `PubChemRAGMappingClient` using Arivale data.
    *   Implementing the main mapping script using `PubChemRAGMappingClient`.
    *   Generating a TSV output of mapping results.
    *   Basic statistics reporting on mapping success.
*   **Out of Scope (for this MVP):**
    *   Mapping to Arivale Chemistries data (covered in a separate MVP).
    *   Full implementation of the complex iterative mapping strategy beyond RAG-based PubChem ID derivation.
    *   UI/Dashboard for results.
    *   Database persistence of these specific mapping results (beyond the output file).
