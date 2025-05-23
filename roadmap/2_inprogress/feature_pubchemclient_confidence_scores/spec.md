# Specification: PubChemRAGMappingClient - Qdrant Similarity Scores

## 1. Current Behavior

*   The `PubChemRAGMappingClient.map_identifiers()` method returns a `MappingOutput` object.
*   Confidence scores within `MappingOutput` (if present or implied) are currently approximated (e.g., based on the number of results from the RAG query, as noted in MVP feedback `2025-05-23-222703-feedback-implement-ukbb-arivale-metabolomics-mvp.md`).
*   The raw similarity scores from Qdrant search results are not directly exposed to the caller of `PubChemRAGMappingClient`.

## 2. Desired Behavior

*   The `PubChemRAGMappingClient.map_identifiers()` method should provide access to the Qdrant similarity score for each individual mapping result (i.e., for each PubChem CID returned for a query).
*   The `QdrantVectorStore.search()` method (or equivalent) should be confirmed to return these scores. Qdrant's `search` API typically includes a `score` field with each hit.
*   The `MappingOutput` structure, likely via its `MappingResultItem` or a similar nested model, should be updated to include a dedicated field for this similarity score (e.g., `qdrant_score: Optional[float]`).
*   The score should be a float, representing the similarity as calculated by Qdrant.

## 3. Affected Components

*   `biomapper.mapping.rag.pubchem_client.PubChemRAGMappingClient`:
    *   The `map_identifiers` method will need to be modified to process and include scores.
*   `biomapper.mapping.rag.vector_store.QdrantVectorStore`:
    *   The `search` method needs to ensure it retrieves and returns scores from Qdrant search results.
*   `biomapper.mapping.models.MappingOutput` (and its constituent Pydantic models like `MappingResultItem`):
    *   Will need a new field to hold the similarity score.

## 4. Success Criteria

*   `PubChemRAGMappingClient.map_identifiers()` returns mapping results that include a Qdrant similarity score for each item.
*   The scores accurately reflect those provided by Qdrant for the corresponding vector search.
*   The changes are accompanied by tests demonstrating the correct propagation of scores.
*   The interface remains clear and usable.
