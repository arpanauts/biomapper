# MVP 0: Arivale BIOCHEMICAL_NAME RAG Mapping Pipeline

## 1. Overview

This "MVP 0" establishes a foundational, multi-step RAG (Retrieval Augmented Generation) pipeline to accurately map the free-text `BIOCHEMICAL_NAME` column from the Arivale metabolomics dataset to PubChem Compound IDs (CIDs). This capability is crucial for robustly identifying entities in the Arivale dataset, which is a prerequisite for more effective cross-dataset mapping (e.g., to UKBB in MVP 1) and serves as an advanced alternative where direct matching (as in MVP 2) yields low success.

The pipeline consists of three core stages:
1.  **Qdrant Search:** Utilize the `PubChemRAGMappingClient` to search a Qdrant-filtered PubChem database using the Arivale `BIOCHEMICAL_NAME` to retrieve candidate PubChem CIDs and their similarity scores.
2.  **PubChem Annotation:** Enrich the candidate CIDs with detailed, semantically valuable information directly from PubChem (e.g., synonyms, descriptions, classifications).
3.  **LLM-based Mapping:** Employ an LLM (e.g., Anthropic Claude) to analyze the original `BIOCHEMICAL_NAME` alongside the annotated PubChem data for candidate CIDs, to determine the most accurate mapping and provide a rationale.

A stretch goal includes incorporating knowledge from the SPOKE graph to further enhance the LLM's context.

## 2. Goals

*   Implement a robust script or set of modules for each of the three core pipeline stages.
*   Utilize the enhanced `PubChemRAGMappingClient` (with Qdrant similarity score retrieval - MEMORY[aeefe19c-5e8a-44ad-ab52-72293a84876a]) for the initial retrieval step.
*   Develop a PubChem annotation component to gather rich metadata for candidate CIDs.
*   Develop an LLM interaction component for intelligent mapping determination.
*   Produce high-quality, confident PubChem CID mappings for entries in the Arivale `BIOCHEMICAL_NAME` column.
*   Lay the groundwork for a hybrid RAG approach by considering SPOKE integration.
*   Align with the project's `iterative_mapping_strategy.md` (MEMORY[3aad9ae4-b2a1-4b3f-9943-75a87cab704c]).

## 3. Scope

*   **In Scope:**
    *   Input: `BIOCHEMICAL_NAME` column from Arivale metabolomics data.
    *   Technologies: `PubChemRAGMappingClient`, Qdrant, PubChem API, Anthropic Claude API.
    *   Output: PubChem CID, mapping confidence/rationale, supporting evidence.
    *   Development of Python scripts/modules for each pipeline stage.
*   **Out of Scope (for initial MVP 0 delivery):**
    *   Full SPOKE integration (this is a stretch goal for exploration within MVP 0).
    *   Direct mapping from Arivale `BIOCHEMICAL_NAME` to UKBB entities (this MVP focuses on robustly identifying the Arivale entity first).
    *   UI development.

## 4. Relation to Other MVPs

*   **Supports MVP 1 (UKBB NMR to Arivale Metabolomics):** By providing a more accurate way to identify PubChem CIDs for Arivale metabolomics entries (especially those identified by `BIOCHEMICAL_NAME`), MVP 0 can improve the quality of the Arivale side of the mapping, leading to better overall UKBB-Arivale links.
*   **Alternative for MVP 2 (UKBB NMR to Arivale Chemistries):** The principles and pipeline developed in MVP 0 could be adapted to improve mapping for Arivale Chemistries, where direct name matching had low success.
