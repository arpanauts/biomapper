# Task List: MVP 0 - Arivale BIOCHEMICAL_NAME RAG Mapping Pipeline

## Phase 1: Setup and Initial Qdrant Search Component

*   [ ] **Task 1.1:** Create project directory structure for MVP 0 implementation (e.g., `biomapper/mvp0_pipeline/`).
*   [ ] **Task 1.2:** Define Pydantic models for data structures as outlined in `design.md` (e.g., `QdrantSearchResultItem`, `PubChemAnnotation`, `LLMCandidateInfo`, `FinalMappingOutput`). Place in `biomapper/schemas/mvp0_schema.py` or similar.
*   [ ] **Task 1.3:** Implement the Qdrant Search Component (`qdrant_search.py`):
    *   [ ] Function to accept `biochemical_name` and `top_k`.
    *   [ ] Instantiate and use `PubChemRAGMappingClient`.
    *   [ ] Correctly call `map_identifiers()` and `get_last_mapping_output()` to retrieve CIDs and scores (MEMORY[aeefe19c-5e8a-44ad-ab52-72293a84876a]).
    *   [ ] Return a list of `QdrantSearchResultItem`.
*   [ ] **Task 1.4:** Write unit tests for the Qdrant Search Component (mocking `PubChemRAGMappingClient`).

## Phase 2: PubChem Annotation Component

*   [ ] **Task 2.1:** Implement the PubChem Annotation Component (`pubchem_annotator.py`):
    *   [ ] Function to accept a list of PubChem CIDs.
    *   [ ] Use `PubChemPy` or direct PUG REST API calls (`httpx`/`requests`) to fetch attributes specified in `design.md`.
    *   [ ] Handle potential errors (e.g., CID not found, API rate limits, network issues).
    *   [ ] Populate and return a dictionary mapping CIDs to `PubChemAnnotation` Pydantic models.
*   [ ] **Task 2.2:** Write unit tests for the PubChem Annotation Component (mocking PubChem API responses).

## Phase 3: LLM Mapping Component

*   [ ] **Task 3.1:** Implement the LLM Mapping Component (`llm_mapper.py`):
    *   [ ] Function to accept `original_biochemical_name`, `enriched_candidate_data` (from PubChem Annotator), and `qdrant_scores`.
    *   [ ] Develop robust prompt construction logic as per `design.md`.
    *   [ ] Interface with Anthropic Claude API (using the Python SDK).
    *   [ ] Implement parsing logic for LLM response to extract selected CID, confidence, and rationale.
    *   [ ] Handle API errors and potential malformed responses.
    *   [ ] Return an `LLMOutput` (or similar Pydantic model) containing the mapping results.
*   [ ] **Task 3.2:** Write unit tests for the LLM Mapping Component (mocking Anthropic API responses and testing prompt construction/response parsing).

## Phase 4: Pipeline Orchestration and Testing

*   [ ] **Task 4.1:** Develop the main pipeline orchestrator script (`main_pipeline.py` or `run_mvp0.py`):
    *   [ ] Function to read Arivale `BIOCHEMICAL_NAME`s from the specified TSV file.
    *   [ ] Loop through names, calling each component in sequence.
    *   [ ] Aggregate and format the final `FinalMappingOutput` for each input name.
    *   [ ] Implement logging throughout the pipeline.
    *   [ ] Option to write results to a CSV/TSV file.
*   [ ] **Task 4.2:** Create a sample input file with diverse Arivale `BIOCHEMICAL_NAME`s for testing.
*   [ ] **Task 4.3:** Perform integration testing of the full pipeline with a small set of names (mocking external APIs initially, then with live APIs if feasible for a few calls).
*   [ ] **Task 4.4:** Document how to configure and run the pipeline (e.g., API keys, input file path).

## Phase 5: (Stretch Goal) SPOKE Integration Exploration

*   [ ] **Task 5.1:** Research SPOKE API endpoints relevant for biochemical entities.
*   [ ] **Task 5.2:** Develop a proof-of-concept function to query SPOKE for a given PubChem CID and retrieve relevant contextual information.
*   [ ] **Task 5.3:** Outline how this SPOKE data could be incorporated into the LLM prompt in the LLM Mapping Component.

## Phase 6: Review and Finalization

*   [ ] **Task 6.1:** Code review of all components and the orchestrator.
*   [ ] **Task 6.2:** Refine documentation.
*   [ ] **Task 6.3:** Test with a larger sample of Arivale data.
*   [ ] **Task 6.4:** Summarize findings, performance, and potential areas for improvement.
