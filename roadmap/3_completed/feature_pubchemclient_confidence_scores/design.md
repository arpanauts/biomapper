# Design: PubChemRAGMappingClient - Qdrant Similarity Scores

## 1. Proposed Changes

### 1.1. `biomapper.mapping.rag.vector_store.QdrantVectorStore`
*   **`search` method:**
    *   Verify that the current implementation of `qdrant_client.search(...)` retrieves hit scores. Qdrant's `ScoredPoint` object (typically returned by search) includes a `score` attribute.
    *   Ensure the `search` method of `QdrantVectorStore` returns these scores along with other point data (e.g., payload, id). This might involve modifying the return type or structure of this method if it currently discards scores.
    *   Example (conceptual):
        ```python
        # In QdrantVectorStore.search
        # hits = self.qdrant_client.search(...)
        # results = []
        # for hit in hits:
        #     results.append({
        #         "id": hit.id,
        #         "payload": hit.payload,
        #         "score": hit.score  # Ensure this is captured
        #     })
        # return results
        ```

### 1.2. `biomapper.mapping.models` (Pydantic Models)
*   **`MappingResultItem` (or equivalent model representing a single mapped item):**
    *   Add a new optional field: `qdrant_similarity_score: Optional[float] = None`
    *   This will store the raw similarity score from Qdrant.

### 1.3. `biomapper.mapping.rag.pubchem_client.PubChemRAGMappingClient`
*   **`map_identifiers` method:**
    *   When calling `self.vector_store.search()`, ensure it receives the scores.
    *   When processing the search results and constructing `MappingResultItem` objects (or similar), populate the new `qdrant_similarity_score` field with the score obtained from the vector store.
    *   The logic for determining `mapping_status` or overall `confidence` (if still calculated separately) might remain, but the raw score will now also be available.

## 2. Data Flow for Scores

1.  `QdrantVectorStore.search()` executes a query against Qdrant.
2.  Qdrant returns `ScoredPoint` objects, each containing a `score`.
3.  `QdrantVectorStore.search()` extracts and returns these scores along with other relevant data for each hit.
4.  `PubChemRAGMappingClient.map_identifiers()` receives these hits (including scores).
5.  For each hit, it creates a `MappingResultItem` (or similar) and populates its `qdrant_similarity_score` field.
6.  The final `MappingOutput` object contains these items with their scores.

## 3. Testing Strategy

*   **Unit Test for `QdrantVectorStore.search`:**
    *   Mock the `qdrant_client.search` call to return sample `ScoredPoint` objects with known scores.
    *   Verify that `QdrantVectorStore.search` correctly extracts and returns these scores.
*   **Integration Test for `PubChemRAGMappingClient.map_identifiers`:**
    *   Mock `QdrantVectorStore.search` to return results with known scores.
    *   Call `map_identifiers` and verify that the resulting `MappingOutput` contains `MappingResultItem` objects with the correct `qdrant_similarity_score` values.
*   Consider a small end-to-end test if feasible, involving a tiny, local Qdrant instance with a few test vectors, to ensure scores are passed through correctly from Qdrant itself.

## 4. Considerations

*   **Score Interpretation:** Qdrant scores can vary based on the distance metric used (e.g., Cosine similarity, Dot product). The client using these scores should be aware of how to interpret them (e.g., higher is better for Cosine similarity). This might be worth a note in the docstring of the modified `map_identifiers` or the `qdrant_similarity_score` field.
*   **Existing Confidence Logic:** Decide if any existing high-level "confidence" calculation in `PubChemRAGMappingClient` should be deprecated, modified to use the new raw scores, or kept alongside it. For this task, the primary goal is just to *expose* the raw Qdrant score.
