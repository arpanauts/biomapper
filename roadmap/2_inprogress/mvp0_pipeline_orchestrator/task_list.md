# Task List: MVP 0 - Pipeline Orchestrator

## Phase 1: Core Orchestrator Setup & Configuration

*   [ ] **Task 1.1:** Create the main orchestrator file: `biomapper/mvp0_pipeline/pipeline_orchestrator.py`.
*   [ ] **Task 1.2:** Define `PipelineConfig` Pydantic model (e.g., in `biomapper/mvp0_pipeline/pipeline_config.py` or within the orchestrator file).
    *   [ ] Include settings for Qdrant (URL, collection name, API key if any).
    *   [ ] Include settings for PubChem API (e.g., request concurrency).
    *   [ ] Include settings for LLM (model name, API key like `ANTHROPIC_API_KEY`).
    *   [ ] Implement loading of config values from environment variables (using `python-dotenv` and Pydantic's `BaseSettings`).
*   [ ] **Task 1.3:** Define `PipelineMappingResult` Pydantic model (if not already sufficiently defined or needing refinement from `mvp0_schema.py`).
    *   [ ] Include fields for original input, final selected CID, confidence, rationale, intermediate results from each component, and a detailed status.
*   [ ] **Task 1.4:** Define the detailed status taxonomy/enum (e.g., `SUCCESS`, `PARTIAL_SUCCESS`, `NO_QDRANT_HITS`, `INSUFFICIENT_ANNOTATIONS`, `LLM_NO_MATCH`, `COMPONENT_ERROR`, `CONFIG_ERROR`).

## Phase 2: Orchestration Logic Implementation

*   [ ] **Task 2.1:** Implement the main orchestration function in `pipeline_orchestrator.py`.
    *   [ ] Takes a biochemical name (and potentially a list of names) as input.
    *   [ ] Initializes `PipelineConfig`.
    *   [ ] Calls `qdrant_search.search_qdrant_for_biochemical_name`.
    *   [ ] Handles `NO_QDRANT_HITS` scenario.
    *   [ ] Calls `pubchem_annotator.fetch_pubchem_annotations` with CIDs from Qdrant.
    *   [ ] Handles `INSUFFICIENT_ANNOTATIONS` scenario (e.g., if no CIDs could be annotated).
    *   [ ] Prepares `LLMCandidateInfo` for the `llm_mapper`.
    *   [ ] Calls `llm_mapper.select_best_cid_with_llm`.
    *   [ ] Handles `LLM_NO_MATCH` scenario.
    *   [ ] Populates and returns `PipelineMappingResult`.
*   [ ] **Task 2.2:** Implement robust error handling for each component call (try-except blocks).
    *   [ ] Catch specific exceptions from components.
    *   [ ] Map component errors to the defined status taxonomy.
    *   [ ] Log errors comprehensively.
*   [ ] **Task 2.3:** Integrate structured logging throughout the orchestrator (`logging` module).
    *   [ ] Log input, output, and key decisions/errors for each step.
    *   [ ] Log configuration used.

## Phase 3: Input/Output and Testing

*   [ ] **Task 3.1:** Implement functionality to read a list of biochemical names from an input source (e.g., a TSV/CSV file, a Python list).
*   [ ] **Task 3.2:** Implement functionality to write `PipelineMappingResult` objects to an output destination (e.g., a TSV/CSV file, JSON lines).
*   [ ] **Task 3.3:** Create example usage/main script for the orchestrator.
    *   [ ] Demonstrate running the pipeline for a single name and a small batch of names.
    *   [ ] Show how to load configuration and interpret results.
*   [ ] **Task 3.4:** Write unit tests for the orchestrator.
    *   [ ] Mock the three components (`qdrant_search`, `pubchem_annotator`, `llm_mapper`).
    *   [ ] Test different pipeline paths (success, various failure modes).
    *   [ ] Test configuration loading.
*   [ ] **Task 3.5:** Perform integration testing with the actual components (can be limited to a few test cases to avoid excessive API calls).

## Phase 4: Documentation and Refinement

*   [ ] **Task 4.1:** Document how to configure and run the `pipeline_orchestrator.py`.
    *   [ ] Required environment variables.
    *   [ ] Input/output formats.
*   [ ] **Task 4.2:** Review and refine logging messages for clarity and utility.
*   [ ] **Task 4.3:** (Optional) Consider adding basic metrics collection (e.g., processing time per name, success/error rates).
