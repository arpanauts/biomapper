# Feature: Enhance PubChemRAGMappingClient with Qdrant Similarity Scores

## 1. Overview

The `PubChemRAGMappingClient` currently approximates confidence scores for its mapping results (e.g., based on the number of hits). This task aims to enhance the client to return the actual similarity scores provided by the underlying Qdrant vector search. This will provide a more accurate and reliable measure of confidence for each mapping.

## 2. Goals

*   Modify `PubChemRAGMappingClient` to retrieve and expose Qdrant similarity scores.
*   Update the `MappingOutput` data structure (or its components) to include these similarity scores.
*   Ensure the scores are correctly passed through from `QdrantVectorStore` to the client's output.
*   Provide a clear way for users of the client to access these scores.

## 3. Scope

*   **In Scope:**
    *   Modifications to `biomapper.mapping.rag.pubchem_client.PubChemRAGMappingClient`.
    *   Potential modifications to `biomapper.mapping.rag.vector_store.QdrantVectorStore` if it doesn't already return scores.
    *   Updates to relevant data structures (likely Pydantic models like `MappingResultItem` within `MappingOutput`).
    *   Unit tests or integration tests to verify the correct retrieval and exposure of scores.
*   **Out of Scope (for this specific task):**
    *   Refactoring existing scripts (like the UKBB-Arivale MVP scripts) to *use* these new scores. That would be a follow-up task.
    *   Developing new complex algorithms based on these scores (beyond simple thresholding).
