# Task: Enhance MetadataQueryService

**Source Prompt Reference:** This task is defined by the prompt: `/home/ubuntu/biomapper/roadmap/_active_prompts/2025-06-22-171745-prompt-enhance-metadata-query-service.md`

## 1. Task Objective
Enhance the existing `MetadataQueryService` at `/home/ubuntu/biomapper/biomapper/core/services/metadata_query_service.py` by moving the remaining metadata and database query methods from `MappingExecutor` into it. This centralizes all direct database query logic for metadata.

## 2. Prerequisites
- [x] Required files exist: `/home/ubuntu/biomapper/biomapper/core/mapping_executor.py` and `/home/ubuntu/biomapper/biomapper/core/services/metadata_query_service.py`.
- [x] Required permissions: Write access to `/home/ubuntu/biomapper/biomapper/core/services/`.

## 3. Task Decomposition
1.  **Open `metadata_query_service.py`:** Open the existing service file for editing.
2.  **Move `_get_endpoint_by_name`:** Move this method from `MappingExecutor` to `MetadataQueryService`. Rename it to `get_endpoint_by_name` (making it public).
3.  **Move `get_strategy`:** Move this method from `MappingExecutor` to `MetadataQueryService`.
4.  **Update `__init__`:** Ensure the `MetadataQueryService` is initialized with a `SessionManager` or an `async_session` factory to perform its queries.
5.  **Add necessary imports:** Add any missing model or SQLAlchemy imports.

## 4. Implementation Requirements
- **Input files:** `/home/ubuntu/biomapper/biomapper/core/mapping_executor.py`, `/home/ubuntu/biomapper/biomapper/core/services/metadata_query_service.py`
- **Expected output:** An updated `/home/ubuntu/biomapper/biomapper/core/services/metadata_query_service.py` file.
- **Code standards:** Follow existing project conventions.

## 5. Error Recovery Instructions
- **Method Signature:** The methods in `MetadataQueryService` should not have a `self` from `MappingExecutor`. They will rely on the `SessionManager` provided during their own initialization.

## 6. Success Criteria and Validation
Task is complete when:
- [ ] The `MetadataQueryService` class now contains the `get_endpoint_by_name` and `get_strategy` methods.
- [ ] The logic is identical to the original methods, adapted for the service's own dependencies.

## 7. Feedback Requirements
Create a detailed Markdown feedback file at:
`[PROJECT_ROOT]/roadmap/_active_prompts/feedback/YYYY-MM-DD-HHMMSS-feedback-enhance-metadata-query-service.md`
