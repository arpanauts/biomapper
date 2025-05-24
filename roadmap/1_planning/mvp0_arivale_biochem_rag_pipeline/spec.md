# Specification: MVP 0 - Arivale BIOCHEMICAL_NAME RAG Mapping Pipeline

## 1. Problem Statement

Mapping free-text biochemical names (like those in the Arivale `BIOCHEMICAL_NAME` column) to standardized identifiers (PubChem CIDs) is challenging due to variations in nomenclature, synonyms, and lack of direct database keys. Simple string matching or basic RAG often lacks the necessary context and disambiguation capabilities, leading to low accuracy or confidence. This MVP aims to create a more sophisticated pipeline to address this.

## 2. Desired State

A robust, automated pipeline that takes an Arivale `BIOCHEMICAL_NAME` as input and outputs:
*   The most likely PubChem CID.
*   A confidence score for the mapping.
*   Supporting evidence or rationale derived from the LLM's analysis.
*   The pipeline should be modular and well-documented.

## 3. Data Sources & APIs

*   **Input Data:** Arivale metabolomics metadata file (`/procedure/data/local_data/ARIVALE_SNAPSHOTS/metabolomics_metadata.tsv`), specifically the `BIOCHEMICAL_NAME` column.
*   **Vector Database:** Qdrant instance containing a filtered PubChem dataset, accessible via `PubChemRAGMappingClient`.
*   **PubChem API:** For fetching detailed annotations for PubChem CIDs (e.g., PUG REST, PubChemPy).
*   **LLM API:** Anthropic Claude API for intelligent mapping determination.
*   **(Stretch Goal) SPOKE API:** For retrieving knowledge graph context.

## 4. Functional Requirements

*   **Input:** A single Arivale `BIOCHEMICAL_NAME` string or a list of such strings.
*   **Output (for each input name):**
    *   `original_biochemical_name: str`
    *   `mapped_pubchem_cid: Optional[int]`
    *   `qdrant_score: Optional[float]` (from initial Qdrant search for the chosen CID)
    *   `llm_confidence: Optional[str]` (e.g., "High", "Medium", "Low", or a numeric score if provided by LLM)
    *   `llm_rationale: Optional[str]`
    *   `candidate_pubchem_cids_details: Optional[List[Dict]]` (details of top candidates considered by LLM)
*   **Pipeline Stages:**
    1.  **Qdrant Search:**
        *   Accepts `BIOCHEMICAL_NAME`.
        *   Uses `PubChemRAGMappingClient.map_identifiers()` and `get_last_mapping_output()` (MEMORY[aeefe19c-5e8a-44ad-ab52-72293a84876a]) to get top_k PubChem CIDs and their Qdrant scores.
    2.  **PubChem Annotation:**
        *   Accepts a list of PubChem CIDs.
        *   Fetches predefined attributes for each CID (e.g., canonical name, synonyms, molecular formula, IUPAC name, InChIKey, description).
    3.  **LLM Mapping:**
        *   Accepts original `BIOCHEMICAL_NAME` and annotated data for candidate CIDs.
        *   Constructs a detailed prompt for the LLM.
        *   Parses the LLM's response to extract the chosen CID, confidence, and rationale.
*   **Configuration:**
    *   `top_k` for Qdrant search.
    *   List of PubChem attributes to fetch.
    *   LLM model name, prompt template(s).
*   **Logging:** Comprehensive logging for each stage.

## 5. Non-Functional Requirements

*   **Modularity:** Each pipeline stage should be a distinct, testable component.
*   **Error Handling:** Graceful handling of API errors, network issues, missing data.
*   **Testability:** Components should be unit-testable, potentially with mocks for external APIs.

## 6. Success Criteria

*   Successful end-to-end execution of the 3-stage pipeline for a sample of Arivale `BIOCHEMICAL_NAME`s.
*   Generation of structured output as defined.
*   Qualitative assessment by a human expert indicates high accuracy for a diverse test set of names.
*   Clear documentation of the pipeline, its components, and how to run it.
