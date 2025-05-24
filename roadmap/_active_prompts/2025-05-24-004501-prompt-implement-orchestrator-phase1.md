# Prompt: Implement Phase 1 of MVP0 Pipeline Orchestrator

**Date:** 2025-05-24
**Project:** Biomapper
**Feature:** MVP 0 - Pipeline Orchestrator (Phase 1: Core Setup & Configuration)
**Source Task List:** `/home/ubuntu/biomapper/roadmap/2_inprogress/mvp0_pipeline_orchestrator/task_list.md` (Focus on Phase 1 tasks: 1.1, 1.2, 1.3, 1.4)

## 1. Objective

Implement the initial setup and configuration components for the MVP0 Arivale BIOCHEMICAL_NAME RAG Mapping Pipeline Orchestrator. This involves creating the main orchestrator file, defining Pydantic models for configuration and results, and establishing a status taxonomy.

## 2. Background & Context

The Biomapper project aims to map biochemical names to standardized identifiers. The MVP0 pipeline uses a three-stage RAG approach:
1.  `qdrant_search.py`: Finds candidate CIDs.
2.  `pubchem_annotator.py`: Enriches CIDs with PubChem data.
3.  `llm_mapper.py`: Selects the best CID using an LLM.

These components are already implemented (see `/home/ubuntu/biomapper/biomapper/mvp0_pipeline/`). This task is to create the foundational Python modules for orchestrating these components.

Relevant project memories and context:
*   **MVP0 Component Design (MEMORY[7dfb2207-4698-49d9-bc5b-99ae2d8e991c]):** Details the inputs/outputs of the individual components.
*   **Previous Orchestrator Planning (Refer to Checkpoint 10 summary provided to Project Manager Cascade):** Outlined the need for centralized configuration (`PipelineConfig`), detailed result tracking (`PipelineMappingResult`), and a granular status taxonomy.

## 3. Tasks to Perform (Phase 1 from Task List)

Refer to Phase 1 of `/home/ubuntu/biomapper/roadmap/2_inprogress/mvp0_pipeline_orchestrator/task_list.md`.

**3.1. Task 1.1: Create Main Orchestrator File**
    *   Create an empty or minimally structured Python file: `/home/ubuntu/biomapper/biomapper/mvp0_pipeline/pipeline_orchestrator.py`.
    *   Add necessary imports (e.g., `typing`, `logging`).
    *   Include a placeholder for the main orchestrator function/class.

**3.2. Task 1.2: Define `PipelineConfig` Pydantic Model**
    *   Create a new Python file: `/home/ubuntu/biomapper/biomapper/mvp0_pipeline/pipeline_config.py`.
    *   In this file, define a Pydantic `BaseSettings` model named `PipelineConfig`.
    *   It should include fields for:
        *   Qdrant settings: `qdrant_url: str`, `qdrant_collection_name: str`, `qdrant_api_key: Optional[str] = None`.
        *   PubChem API settings: `pubchem_max_concurrent_requests: int = 5`.
        *   LLM settings: `llm_model_name: str = "claude-3-sonnet-20240229"`, `anthropic_api_key: str`.
    *   Ensure configuration values are loaded from environment variables (e.g., `ANTHROPIC_API_KEY` from `.env`). Provide sensible defaults where appropriate.
    *   Add necessary imports (e.g., `Optional` from `typing`, `BaseSettings` from `pydantic_settings`).

**3.3. Task 1.3: Define/Refine `PipelineMappingResult` Pydantic Model**
    *   This model will represent the final output of a single pipeline run for one biochemical name.
    *   You can define this in `/home/ubuntu/biomapper/biomapper/schemas/mvp0_schema.py` or create a new schema file like `/home/ubuntu/biomapper/biomapper/schemas/pipeline_schema.py` if it feels cleaner. If adding to `mvp0_schema.py`, ensure it's distinct from `FinalMappingOutput` if that model is not suitable.
    *   The `PipelineMappingResult` model should include at least:
        *   `input_biochemical_name: str`
        *   `status: str` (this will use the status taxonomy defined in Task 1.4)
        *   `selected_cid: Optional[int] = None`
        *   `confidence: Optional[str] = None` (e.g., "High", "Medium", "Low", or a numeric score if applicable later)
        *   `rationale: Optional[str] = None`
        *   `qdrant_results: Optional[List[QdrantSearchResultItem]] = None` (from `mvp0_schema.py`)
        *   `pubchem_annotations: Optional[Dict[int, PubChemAnnotation]] = None` (from `mvp0_schema.py`)
        *   `llm_choice: Optional[LLMChoice] = None` (from `llm_mapper.py`)
        *   `error_message: Optional[str] = None`
        *   `processing_details: Dict[str, Any] = {}` (for any other intermediate data or timings)

**3.4. Task 1.4: Define Detailed Status Taxonomy/Enum**
    *   Define an `Enum` (e.g., `PipelineStatus`) for the pipeline's operational status.
    *   Place this Enum in the same file as `PipelineMappingResult` (e.g., `/home/ubuntu/biomapper/biomapper/schemas/mvp0_schema.py` or your new pipeline schema file).
    *   Include at least the following statuses:
        *   `SUCCESS`
        *   `PARTIAL_SUCCESS` (e.g., Qdrant hits, but LLM couldn't map)
        *   `NO_QDRANT_HITS`
        *   `INSUFFICIENT_ANNOTATIONS` (e.g., Qdrant found CIDs, but none could be annotated by PubChem)
        *   `LLM_NO_MATCH` (LLM processed candidates but decided none were a good match)
        *   `COMPONENT_ERROR_QDRANT`
        *   `COMPONENT_ERROR_PUBCHEM`
        *   `COMPONENT_ERROR_LLM`
        *   `CONFIG_ERROR`
        *   `VALIDATION_ERROR`
        *   `UNKNOWN_ERROR`
    *   Ensure the `status` field in `PipelineMappingResult` uses this Enum or string representations of its values.

## 4. Deliverables

1.  New file: `/home/ubuntu/biomapper/biomapper/mvp0_pipeline/pipeline_orchestrator.py` (with basic structure).
2.  New file: `/home/ubuntu/biomapper/biomapper/mvp0_pipeline/pipeline_config.py` (containing the `PipelineConfig` model).
3.  Updated or new schema file (e.g., `/home/ubuntu/biomapper/biomapper/schemas/mvp0_schema.py` or `/home/ubuntu/biomapper/biomapper/schemas/pipeline_schema.py`) containing:
    *   The `PipelineMappingResult` Pydantic model.
    *   The `PipelineStatus` Enum.
4.  All Python code should be well-commented, follow PEP 8 guidelines, and include necessary type hints.
5.  Ensure all new models and enums are correctly imported and usable.

## 5. Important Considerations

*   **Environment Variables:** The `PipelineConfig` must load sensitive keys like `ANTHROPIC_API_KEY` from environment variables (typically via a `.env` file loaded by `python-dotenv`). Do not hardcode API keys.
*   **Modularity:** Keep Pydantic models in schema files and configuration in its own file to maintain separation of concerns.
*   **Existing Schemas:** Leverage existing schemas from `/home/ubuntu/biomapper/biomapper/schemas/mvp0_schema.py` (like `QdrantSearchResultItem`, `PubChemAnnotation`) where appropriate.
*   **Clarity:** The Pydantic models should be clearly defined and self-explanatory.

## 6. Verification

*   All specified files are created in the correct locations.
*   Pydantic models (`PipelineConfig`, `PipelineMappingResult`) are correctly defined and can be imported.
*   `PipelineConfig` correctly loads settings from environment variables (this can be tested by setting mock env vars).
*   The `PipelineStatus` Enum is defined and usable.
*   The code is free of syntax errors.

Please provide feedback upon completion, including paths to all created/modified files and a brief summary of how each task was addressed.
