# Task List: Enhance PubChemRAGMappingClient with Qdrant Similarity Scores

## Phase 1: Prerequisite Checks & Model Updates

*   [ ] **Task 1.1: Verify `QdrantVectorStore.search()` Score Retrieval**
    *   Examine `biomapper.mapping.rag.vector_store.QdrantVectorStore`.
    *   Confirm that the `search()` method (or its equivalent interacting with `qdrant_client`) currently retrieves or can easily be modified to retrieve the `score` attribute from Qdrant's `ScoredPoint` objects.
    *   If necessary, modify it to ensure scores are returned as part of its result.
*   [ ] **Task 1.2: Update Pydantic Models for Score Storage**
    *   Locate the Pydantic model used for individual mapping results (likely `MappingResultItem` or similar within `biomapper.mapping.models`).
    *   Add a new optional field: `qdrant_similarity_score: Optional[float] = None`.

## Phase 2: Client Logic Modification

*   [ ] **Task 2.1: Modify `PubChemRAGMappingClient.map_identifiers()`**
    *   Update the method to receive scores from `self.vector_store.search()`.
    *   When constructing `MappingResultItem` (or equivalent) objects, populate the new `qdrant_similarity_score` field with the score obtained from the vector store for each hit.
*   [ ] **Task 2.2: Review Existing Confidence Logic (Decision Point)**
    *   Analyze any existing high-level "confidence" calculation within `PubChemRAGMappingClient`.
    *   Decide if it should be:
        *   Kept as is (alongside the new raw score).
        *   Modified to utilize the new raw Qdrant score.
        *   Deprecated if the raw score is deemed sufficient.
    *   Document this decision and implement any minor related changes if straightforward. (Major refactoring of confidence logic is out of scope for *this* task if complex).

## Phase 3: Testing

*   [ ] **Task 3.1: Unit Test for `QdrantVectorStore.search()` Score Handling**
    *   Create/update unit tests for `QdrantVectorStore`.
    *   Mock the `qdrant_client.search` call to return sample `ScoredPoint` objects with known scores.
    *   Verify that `QdrantVectorStore.search()` correctly extracts and returns these scores.
*   [ ] **Task 3.2: Integration Test for `PubChemRAGMappingClient.map_identifiers()`**
    *   Create/update integration tests for `PubChemRAGMappingClient`.
    *   Mock `QdrantVectorStore.search` to return results with known scores.
    *   Call `map_identifiers` and verify that the resulting `MappingOutput` contains items with the correct `qdrant_similarity_score` values.
*   [ ] **Task 3.3 (Optional but Recommended): Small End-to-End Test**
    *   If feasible, set up a minimal test with a local Qdrant instance, a few vectors, and perform a query via the client to ensure scores propagate end-to-end.

## Phase 4: Documentation & Finalization

*   [ ] **Task 4.1: Update Docstrings**
    *   Update docstrings for modified methods/classes (especially `PubChemRAGMappingClient.map_identifiers` and the Pydantic model field) to explain the new score field and its interpretation (e.g., higher is better for cosine similarity).
*   [ ] **Task 4.2: Code Review & Refinement**
    *   Ensure code adheres to PEP 8 and project standards.
    *   Perform a self-review or prepare for a peer review.
*   [ ] **Task 4.3: Prepare Feedback File**
    *   Summarize work done, decisions made (especially for Task 2.2), and any challenges encountered.
