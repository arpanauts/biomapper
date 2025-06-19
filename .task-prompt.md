# Task: Resolve MVP0 Pipeline Errors

## Context:
Tests for the MVP0 pipeline components, specifically `PipelineOrchestrator` and `QdrantSearch`, are failing with `AssertionError`, `AttributeError`, and `pydantic_core._pydantic_core.ValidationError`. These errors point to issues in the orchestration logic, data flow, Pydantic model validation for search results, and interaction with the Qdrant client.

## Objective:
Debug and fix the errors in `PipelineOrchestrator` and `QdrantSearch` to ensure the MVP0 pipeline components function correctly, data is validated, and interactions with services like Qdrant are robust.

## Affected Tests & Errors:

**`tests/mvp0_pipeline/test_pipeline_orchestrator.py`**
- `TestPipelineOrchestrator::test_run_single_mapping_no_qdrant_hits` - `AssertionError: assert None == []`
- `TestPipelineOrchestrator::test_run_pipeline_batch` - `assert 1 == 0`
- `TestPipelineOrchestrator::test_create_orchestrator_from_env` - `AttributeError: <module 'biomapper.mvp0_pipeline.pipeline_orchestrator' ...>`
- `TestPipelineIntegration::test_data_flow_between_components` - `AssertionError: assert <PipelineStat...NT_ERROR_LLM'> == <PipelineStat...SS: 'SUCCESS'>`

**`tests/mvp0_pipeline/test_qdrant_search.py`**
- `TestQdrantSearch::test_search_successful_with_scores` - `pydantic_core._pydantic_core.ValidationError: 1 validation error for MappingOutput`
- `TestQdrantSearch::test_search_with_top_k_limit` - `pydantic_core._pydantic_core.ValidationError: 1 validation error for MappingOutput`
- `TestQdrantSearch::test_search_empty_input` - `AssertionError: Expected 'map_identifiers' to not have been called. Called 1 times.`
- `TestQdrantSearch::test_search_no_results` - `pydantic_core._pydantic_core.ValidationError: 1 validation error for MappingOutput`
- `TestQdrantSearch::test_search_with_scores_mismatch` - `pydantic_core._pydantic_core.ValidationError: 1 validation error for MappingOutput`
- `TestQdrantSearch::test_search_invalid_pubchem_id` - `pydantic_core._pydantic_core.ValidationError: 1 validation error for MappingOutput`
- `TestQdrantSearch::test_search_with_default_client` - `AttributeError: <module 'biomapper.mvp0_pipeline.qdrant_search' ...>`

## Tasks:

1.  **`PipelineOrchestrator` (`test_pipeline_orchestrator.py`):**
    *   **AssertionErrors (`test_run_single_mapping_no_qdrant_hits`, `test_run_pipeline_batch`, `test_data_flow_between_components`):**
        *   Review the orchestrator's logic for running mappings, batch processing, and managing pipeline state/status. Ensure expected return values and state transitions are correct.
    *   **AttributeError (`test_create_orchestrator_from_env`):**
        *   Investigate how the orchestrator is created from environment variables. The error suggests a module-level attribute is missing or named incorrectly.

2.  **`QdrantSearch` (`test_qdrant_search.py`):**
    *   **Pydantic ValidationErrors (multiple tests):**
        *   Review the `MappingOutput` Pydantic model (or any other relevant models).
        *   Inspect the data being returned from Qdrant searches that's failing validation. Ensure the data structure matches the model or update the model if necessary.
    *   **AssertionError (`test_search_empty_input`):**
        *   Verify the logic for handling empty input lists. The `map_identifiers` method should likely not be called if there's no input.
    *   **AttributeError (`test_search_with_default_client`):**
        *   Check how the default Qdrant client is instantiated or accessed within `QdrantSearch`. The error indicates a missing attribute on the `qdrant_search` module itself.

## Expected Outcome:
All listed tests for the MVP0 pipeline components should pass, demonstrating correct orchestration, data validation, and Qdrant client interaction.
