# Prompt: Implement Phase 2 of MVP0 Pipeline Orchestrator

**Date:** 2025-05-24
**Project:** Biomapper
**Feature:** MVP 0 - Pipeline Orchestrator (Phase 2: Core Logic & Integration)
**Source Task List:** `/home/ubuntu/biomapper/roadmap/2_inprogress/mvp0_pipeline_orchestrator/task_list.md` (Focus on Phase 2 tasks)
**Phase 1 Feedback & Decisions:** `/home/ubuntu/biomapper/roadmap/_active_prompts/feedback/2025-05-24-030435-feedback-llm-mapper-component.md` (and subsequent discussion with Project Manager)

## 1. Objective

Implement the core processing logic for the `PipelineOrchestrator`. This includes initializing and integrating the three pipeline components (`qdrant_search`, `pubchem_annotator`, `llm_mapper`), defining the execution flow for single and batch biochemical name mapping, and implementing initial error handling and result aggregation.

## 2. Background & Context

Phase 1 established the foundational Pydantic models (`PipelineConfig`, `PipelineMappingResult`, `PipelineStatus`, `BatchMappingResult`) and the basic structure for `PipelineOrchestrator`. The individual pipeline components (`qdrant_search.py`, `pubchem_annotator.py`, `llm_mapper.py`) are already implemented in `/home/ubuntu/biomapper/biomapper/mvp0_pipeline/`.

This phase focuses on bringing these pieces together into a functional pipeline.

## 3. Key Decisions from Phase 1 Review (Incorporate these)

*   **Batch Processing:** Implement sequential processing for lists of biochemical names for now. (Concurrent processing is a future enhancement).
*   **Error Handling:** Implement a "fail fast" strategy for component errors. If a component fails for a specific biochemical name, log the error, set an appropriate status in its `PipelineMappingResult`, and proceed to the next name. Do not implement retries for component failures at this stage.
*   **Logging:** Implement high-level status update logging (e.g., start/end of processing for a name, success/failure of major steps). Detailed intermediate result logging is a future enhancement.
*   **Configuration Validation:** In the `PipelineOrchestrator`'s `__init__` method, perform essential configuration validation:
    *   Check for the presence of required API keys (e.g., `ANTHROPIC_API_KEY` from `PipelineConfig`).
    *   Attempt a basic reachability check for Qdrant (e.g., can the host/port specified in `PipelineConfig` be connected to? Many Qdrant clients have a health/ping check).
    *   If validation fails, raise a configuration error to prevent the orchestrator from starting in a broken state.

## 4. Tasks to Perform (Phase 2 from Task List)

**4.1. Task 2.1: Initialize Pipeline Components in Orchestrator**
    *   In `/home/ubuntu/biomapper/biomapper/mvp0_pipeline/pipeline_orchestrator.py`, within the `PipelineOrchestrator` class:
        *   Modify the `__init__` method to accept a `PipelineConfig` object.
        *   Store the `PipelineConfig`.
        *   Perform the configuration validation as decided above.
        *   Initialize instances of the clients/wrappers for:
            *   `qdrant_search.py` (e.g., `QdrantSearcher`)
            *   `pubchem_annotator.py` (e.g., `PubChemAnnotator`)
            *   `llm_mapper.py` (e.g., `LLMMapper`)
        *   These components should be configured using settings from the `PipelineConfig` (e.g., API keys, Qdrant URL/collection).

**4.2. Task 2.2: Implement `run_single_mapping` Method**
    *   Define the logic for `PipelineOrchestrator.run_single_mapping(self, biochemical_name: str) -> PipelineMappingResult`.
    *   This method should:
        1.  Take a single `biochemical_name` string as input.
        2.  Create an initial `PipelineMappingResult` object with the input name and a default status.
        3.  **Stage 1: Qdrant Search:**
            *   Call the Qdrant search component to get candidate CIDs.
            *   Handle potential errors from this component (fail fast: log, update `PipelineMappingResult.status` and `error_message`, return result).
            *   If no hits, update status (e.g., `PipelineStatus.NO_QDRANT_HITS`) and return.
            *   Store Qdrant results in `PipelineMappingResult.qdrant_results`.
        4.  **Stage 2: PubChem Annotation:**
            *   Call the PubChem annotator component with the CIDs from Stage 1.
            *   Handle potential errors (fail fast).
            *   If no annotations or insufficient annotations, update status (e.g., `PipelineStatus.INSUFFICIENT_ANNOTATIONS`) and return.
            *   Store annotations in `PipelineMappingResult.pubchem_annotations`.
        5.  **Stage 3: LLM Mapping:**
            *   Prepare input for the LLM mapper (original name, Qdrant results, PubChem annotations).
            *   Call the LLM mapper component.
            *   Handle potential errors (fail fast).
            *   If LLM determines no match, update status (e.g., `PipelineStatus.LLM_NO_MATCH`).
            *   Store LLM choice (selected CID, confidence, rationale) in `PipelineMappingResult.llm_choice` and update top-level fields like `selected_cid`, `confidence`, `rationale`.
        6.  Set final `PipelineMappingResult.status` to `PipelineStatus.SUCCESS` if all stages completed and a mapping was found, or `PipelineStatus.PARTIAL_SUCCESS` if some stages completed but no final mapping.
        7.  Return the populated `PipelineMappingResult`.
    *   Implement high-level logging throughout this process.

**4.3. Task 2.3: Implement `run_pipeline` Method (Batch Processing - Sequential)**
    *   Define the logic for `PipelineOrchestrator.run_pipeline(self, biochemical_names: List[str]) -> BatchMappingResult`.
    *   This method should:
        1.  Take a list of `biochemical_name` strings.
        2.  Initialize an empty list to store individual `PipelineMappingResult` objects.
        3.  Iterate through the `biochemical_names` **sequentially**:
            *   For each name, call `self.run_single_mapping(biochemical_name)`.
            *   Append the returned `PipelineMappingResult` to the list.
        4.  Populate and return a `BatchMappingResult` object containing all the individual results and any summary statistics (e.g., number processed, number successful).

**4.4. Task 2.4: Basic Error Handling and Status Updates**
    *   Ensure that errors from components are caught within `run_single_mapping`.
    *   Update the `PipelineMappingResult.status` and `PipelineMappingResult.error_message` fields appropriately based on component failures or specific outcomes (e.g., no Qdrant hits). Use the `PipelineStatus` enum.
    *   The "fail fast" approach means if `qdrant_search` fails for a name, the orchestrator doesn't proceed to `pubchem_annotator` or `llm_mapper` for that *specific name*.

## 5. Deliverables

1.  Updated `/home/ubuntu/biomapper/biomapper/mvp0_pipeline/pipeline_orchestrator.py` with:
    *   Completed `__init__` method including component initialization and configuration validation.
    *   Implemented `run_single_mapping` method with the three-stage pipeline logic.
    *   Implemented `run_pipeline` method for sequential batch processing.
    *   Incorporated error handling and status updates using `PipelineMappingResult` and `PipelineStatus`.
    *   High-level logging.
2.  Ensure all new logic is type-hinted and follows PEP 8.
3.  (If necessary) Minor adjustments to component interfaces or schema models if integration reveals a need, but aim to use existing structures. Document any such changes.

## 6. Important Considerations

*   **Component Interfaces:** Assume the existing interfaces for `qdrant_search.py`, `pubchem_annotator.py`, and `llm_mapper.py` are stable. Refer to their definitions and `MEMORY[7dfb2207-4698-49d9-bc5b-99ae2d8e991c]` for their expected inputs/outputs.
*   **Configuration:** The orchestrator must be fully configurable via the `PipelineConfig` object.
*   **Idempotency & State:** The orchestrator itself should be stateless; all state related to a mapping operation should be contained within the `PipelineMappingResult` for that operation.

## 7. Verification

*   The `PipelineOrchestrator` can be instantiated with a valid `PipelineConfig`.
*   Initialization fails gracefully if essential configuration (e.g., API keys) is missing or basic service connectivity (Qdrant) cannot be established.
*   `run_single_mapping` correctly executes the three stages for a successful case.
*   `run_single_mapping` correctly handles and reports errors from each stage (e.g., Qdrant error, no PubChem annotations, LLM no match) using the `PipelineStatus` enum.
*   `run_pipeline` processes a list of names sequentially and returns a `BatchMappingResult` containing individual `PipelineMappingResult` objects.
*   Logs provide high-level visibility into the pipeline's execution.

Please provide feedback upon completion, including a summary of how each task was addressed, any challenges, and paths to modified files.
