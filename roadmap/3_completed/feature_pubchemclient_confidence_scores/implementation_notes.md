# Implementation Notes: Enhance PubChemRAGMappingClient with Qdrant Similarity Scores

## 1. Key Objective

The primary goal is to make the raw Qdrant similarity score available to users of the `PubChemRAGMappingClient`. This provides a more granular and accurate measure of search result relevance than the current approximated confidence.

## 2. Qdrant Score Retrieval

*   **`QdrantClient.search()`:** The `qdrant_client.search()` method typically returns a list of `ScoredPoint` objects. Each `ScoredPoint` has a `score` attribute. Ensure your interaction with this method in `QdrantVectorStore` captures this.
    ```python
    # Example:
    # from qdrant_client import QdrantClient
    # from qdrant_client.http.models import PointStruct, Distance, VectorParams, ScoredPoint
    #
    # client = QdrantClient(host="localhost", port=6333) # Or however initialized
    # hits: List[ScoredPoint] = client.search(
    #     collection_name="your_collection",
    #     query_vector=[0.1, 0.2, ...],
    #     limit=5
    # )
    # for hit in hits:
    #     print(f"ID: {hit.id}, Score: {hit.score}, Payload: {hit.payload}")
    ```
*   **`QdrantVectorStore` Responsibility:** This class is the direct interface to Qdrant. It *must* be the one to retrieve the scores and pass them upwards. Avoid trying to infer scores in `PubChemRAGMappingClient` if `QdrantVectorStore` doesn't provide them.

## 3. Pydantic Model Modification

*   The change to `MappingResultItem` (or its equivalent) is straightforward: add `qdrant_similarity_score: Optional[float] = None`.
*   Ensure this model is correctly imported and used within `PubChemRAGMappingClient`.

## 4. `PubChemRAGMappingClient` Logic

*   The main change is to populate the `qdrant_similarity_score` field in the `MappingResultItem` instances it creates.
*   **Decision on Existing Confidence:** The `task_list.md` (Task 2.2) mentions deciding what to do with any pre-existing high-level confidence logic.
    *   **Simplest Approach for this Task:** Keep existing logic as-is and simply add the new `qdrant_similarity_score`. Users can then choose which score to use.
    *   **Slightly More Involved:** If the existing confidence is a simple transformation of, say, the number of hits, it might be easy to adjust or note its relation to the new scores.
    *   **Avoid:** Do not get bogged down in a major refactor of the old confidence logic if it's complex. The priority is exposing the *new* raw score.

## 5. Score Interpretation & Documentation

*   **Qdrant Score Meaning:** The meaning of a Qdrant score depends on the `distance` metric configured for the collection (e.g., Cosine, Euclid, Dot).
    *   For **Cosine similarity**, scores are typically between -1 and 1 (or 0 and 1 if vectors are normalized), where higher is better.
    *   For **Euclidean distance**, scores are non-negative, where lower is better (closer).
    *   For **Dot product**, the range can vary, and higher is generally better.
*   **Documentation:** It's crucial to document this. Add notes to the docstring of `PubChemRAGMappingClient.map_identifiers` and/or the `qdrant_similarity_score` field in the Pydantic model about how to interpret the score, or that its interpretation depends on the Qdrant collection's distance metric.

## 6. Testing

*   **Mocking is Key:** For unit/integration tests, mocking `qdrant_client.search` (for `QdrantVectorStore` tests) and `QdrantVectorStore.search` (for `PubChemRAGMappingClient` tests) will be essential.
*   Ensure your mocks return data structures that include a `score` attribute that your code expects.

## 7. Dependencies

*   This task primarily involves modifying existing Python code within the `biomapper` project.
*   No new external library dependencies are anticipated. Relies on `qdrant-client` and `pydantic`.

## 8. Adherence to Project Standards
*   Remember to follow the project's coding style (PEP 8), type hinting, and documentation conventions.
*   Refer to `/home/ubuntu/biomapper/docs/draft/iterative_mapping_strategy.md` and `/home/ubuntu/biomapper/roadmap/_status_updates/2025-05-08-mvp-refinement-and-dual-agent-plan.md` for broader project context if needed, though this task is fairly self-contained.
