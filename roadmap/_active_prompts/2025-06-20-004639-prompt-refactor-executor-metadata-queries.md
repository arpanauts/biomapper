# Task: Consolidate Metadata Queries into `MetadataQueryService`

## 1. Task Objective
To refactor the `MappingExecutor` by moving all direct database query methods for retrieving metadata (like endpoints, properties, and ontologies) into the existing `MetadataQueryService`. This centralizes all metadata lookups into a single, dedicated service.

## 2. Context and Background
The `MappingExecutor` currently contains several helper methods for querying the metamapper database, such as `_get_endpoint`, `_get_endpoint_properties`, and `_get_ontology_type`. A `MetadataQueryService` already exists (`biomapper/core/services/metadata_query_service.py`) but may not be fully utilized. This task is to ensure all such query logic is consolidated within that service.

## 3. Key Memories and Documents
- **Source File:** `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/biomapper/core/mapping_executor.py`
- **Target Service:** `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/biomapper/core/services/metadata_query_service.py`
- **Starter Prompt:** `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/roadmap/_active_prompts/_starter_prompt.md`

## 4. Success Criteria
- The helper methods `_get_endpoint`, `_get_endpoint_properties`, `_get_ontology_type`, and any other similar metadata query methods are removed from `MappingExecutor`.
- The equivalent functionality is implemented and exposed by `MetadataQueryService`.
- The `MappingExecutor` and any other components that need this metadata are updated to call the `MetadataQueryService` instead of having the logic inline.
- The `MappingExecutor` class becomes smaller and less coupled to the database schema.
- All tests continue to pass.

## 5. Implementation Requirements
- **Input files/data:** `mapping_executor.py`, `metadata_query_service.py`
- **Expected outputs:** Modified versions of the input files.
- **Code standards:** Ensure the `MetadataQueryService` is properly injected into the `MappingExecutor` and other consumers. All methods should be asynchronous.

## 6. Error Recovery Instructions
- If you encounter `AttributeError` where the executor tries to call a removed method, ensure you have replaced the call with a call to the `MetadataQueryService`.
- If tests fail, verify that the queries in `MetadataQueryService` are correct and return data in the same format as the original methods.

## 7. Feedback and Reporting
- **File Path:** `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/roadmap/_active_prompts/feedback/YYYY-MM-DD-HHMMSS-feedback-refactor-executor-metadata-queries.md`
- **Content:**
    - **Completed Subtasks:** List the methods that were moved from the executor to the service.
    - **Issues Encountered:** Document any queries that were difficult to migrate.
    - **Next Action Recommendation:** Confirm that metadata querying is now centralized.
    - **Confidence Assessment:** High. This is a straightforward refactoring of query logic.
