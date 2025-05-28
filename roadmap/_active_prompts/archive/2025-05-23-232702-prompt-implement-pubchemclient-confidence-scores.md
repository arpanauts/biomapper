# Prompt for Claude Code Instance: Implement PubChemRAGMappingClient Qdrant Similarity Score Enhancement

**Date:** 2025-05-23
**Time (UTC):** 23:27:02
**Feature:** Enhance PubChemRAGMappingClient with Qdrant Similarity Scores
**Roadmap Location:** `/home/ubuntu/biomapper/roadmap/2_inprogress/feature_pubchemclient_confidence_scores/`

## 1. Objective

Your task is to implement the enhancement for the `PubChemRAGMappingClient` to retrieve and expose actual Qdrant similarity scores for its mapping results. This involves modifying existing Python code, updating data models, and adding relevant tests.

## 2. Core Task: Implement Feature as per Documentation

You must implement the feature based on the detailed specifications and design outlined in the following documents located in the feature's roadmap directory (`/home/ubuntu/biomapper/roadmap/2_inprogress/feature_pubchemclient_confidence_scores/`):

*   **`README.md`**: Provides an overview, goals, and scope.
*   **`spec.md`**: Details the current and desired behavior, affected components, and success criteria.
*   **`design.md`**: Outlines the proposed changes to `QdrantVectorStore`, Pydantic models, and `PubChemRAGMappingClient`, along with data flow and testing strategy.
*   **`task_list.md`**: Contains a detailed breakdown of tasks to be completed. Please follow this list.
*   **`implementation_notes.md`**: Provides specific guidance on Qdrant score retrieval, model modifications, handling existing confidence logic, score interpretation, and testing.

## 3. Key Files to Modify (and their locations):

*   `biomapper.mapping.rag.pubchem_client.PubChemRAGMappingClient` (likely in `/home/ubuntu/biomapper/biomapper/mapping/rag/pubchem_client.py`)
*   `biomapper.mapping.rag.vector_store.QdrantVectorStore` (likely in `/home/ubuntu/biomapper/biomapper/mapping/rag/vector_store.py`) - verify if modification is needed to pass scores.
*   Relevant Pydantic models for mapping output, likely in `/home/ubuntu/biomapper/biomapper/mapping/models.py` (e.g., `MappingResultItem`).
*   Associated test files for the above modules.

## 4. Deliverables

1.  **Modified Python Code:**
    *   Updated `PubChemRAGMappingClient` to process and expose Qdrant similarity scores.
    *   Updated `QdrantVectorStore` (if necessary) to ensure it retrieves and returns scores.
    *   Updated Pydantic data models (e.g., `MappingResultItem`) to include a field for `qdrant_similarity_score`.
2.  **Tests:**
    *   New or updated unit tests for `QdrantVectorStore` to verify score handling.
    *   New or updated integration tests for `PubChemRAGMappingClient` to verify correct propagation and availability of scores in the output.
3.  **Updated Docstrings:**
    *   Ensure all modified classes and methods have updated docstrings, clearly explaining the new score field and its interpretation (e.g., how it relates to the Qdrant distance metric).
4.  **Adherence to `task_list.md`:** Systematically go through the `task_list.md` and ensure all items are addressed.

## 5. Project Standards & Environment

*   **Python 3:** All code must be Python 3 compatible.
*   **PEP 8 & Type Hinting:** Adhere to PEP 8 style guidelines and use type hinting.
*   **Dependencies:** No new external dependencies are anticipated for this task. The project uses Poetry for dependency management (`pyproject.toml`).
*   **Logging:** Implement or update logging as appropriate for diagnostics.
*   **Error Handling:** Ensure robust error handling.
*   **Broader Context:** While this task is specific, be mindful of the project's overall goals outlined in `/home/ubuntu/biomapper/docs/draft/iterative_mapping_strategy.md` and `/home/ubuntu/biomapper/roadmap/_status_updates/2025-05-08-mvp-refinement-and-dual-agent-plan.md`.

## 6. Feedback File

Upon completion of all tasks, create a feedback file detailing the work done, any assumptions made, challenges encountered, and confirmation of deliverables.
*   **Feedback File Location:** `/home/ubuntu/biomapper/roadmap/_active_prompts/feedback/`
*   **Feedback File Name:** `YYYY-MM-DD-HHMMSS-feedback-implement-pubchemclient-confidence-scores.md` (use the timestamp of when you complete the work).

This prompt, along with the detailed documents in the feature directory, should provide all necessary information to implement the Qdrant similarity score enhancement for the `PubChemRAGMappingClient`.
