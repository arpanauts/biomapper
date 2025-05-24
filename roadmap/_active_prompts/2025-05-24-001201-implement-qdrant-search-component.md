# Task: Implement Qdrant Search Component for MVP0 Pipeline

**Objective:**
Implement the `search_qdrant_for_biochemical_name` function within the file `/home/ubuntu/biomapper/biomapper/mvp0_pipeline/qdrant_search.py`. This component is the first step in the MVP0 Arivale BIOCHEMICAL_NAME RAG Mapping Pipeline, responsible for querying a Qdrant vector store to find potential PubChem Compound IDs (CIDs) matching a given biochemical name.

**Context:**
This component leverages the existing `PubChemRAGMappingClient` to interact with Qdrant and retrieve candidate CIDs along with their similarity scores. The results will be used by downstream components in the MVP0 pipeline.

**Key Requirements & Implementation Details:**

1.  **File to Implement:**
    *   `/home/ubuntu/biomapper/biomapper/mvp0_pipeline/qdrant_search.py` (Use the existing stub file as a starting point).

2.  **Core Logic:**
    *   The main function to implement is `async def search_qdrant_for_biochemical_name(biochemical_name: str, top_k: int, qdrant_url: Optional[str] = None, qdrant_api_key: Optional[str] = None, qdrant_collection_name: Optional[str] = None) -> List[QdrantSearchResultItem]:`.
    *   **Instantiate `PubChemRAGMappingClient`**:
        *   Import from `biomapper.mapping.clients.pubchem_rag_client import PubChemRAGMappingClient`.
        *   The client requires configuration: Qdrant URL, API key, and collection name.
        *   Allow these to be passed as arguments to the function. Consider using default values from a configuration file (e.g., `biomapper.config.settings`) or environment variables if available and appropriate for the project's standards. If no central config is established for this, prioritize function arguments.
    *   **Perform Search**:
        *   Use `await client.map_identifiers(ids_to_map=[biochemical_name], top_k=top_k)`. Note that `map_identifiers` takes a list, so pass `[biochemical_name]`.
    *   **Retrieve Results with Scores**:
        *   Use `mapping_output = await client.get_last_mapping_output()`.
        *   Extract candidate CIDs and their similarity scores. Based on MEMORY[aeefe19c-5e8a-44ad-ab52-72293a84876a], the scores are available in `mapping_output.qdrant_points`. Each point in this list has a `score` attribute and a `payload` (dictionary) which contains the `cid`.
    *   **Format Output**:
        *   Transform the retrieved CIDs and scores into a list of `QdrantSearchResultItem` Pydantic models.
        *   Import `QdrantSearchResultItem` from `/home/ubuntu/biomapper/biomapper/schemas/mvp0_schema.py`.
        *   Each `QdrantSearchResultItem` should have `cid: int` and `qdrant_score: float`.
    *   **Return Value**: The function should return `List[QdrantSearchResultItem]`.

3.  **Error Handling:**
    *   Implement basic error handling (e.g., for client initialization issues, network errors during Qdrant communication, or if no results are found).
    *   Log errors appropriately using the `logging` module.

4.  **Asynchronous Nature:**
    *   The function must be `async def` and use `await` for calls to the `PubChemRAGMappingClient`.

5.  **Configuration:**
    *   Clearly document how the `PubChemRAGMappingClient` is configured (Qdrant URL, API key, collection name). Prioritize explicit parameters to the function for clarity in this component.

6.  **Logging:**
    *   Add informative log messages (e.g., when starting a search, number of results found, errors encountered).

7.  **Example Usage (`if __name__ == "__main__":`)**:
    *   Include a section to demonstrate how to use `search_qdrant_for_biochemical_name`.
    *   This should set up necessary parameters (e.g., a test biochemical name, `top_k`, Qdrant connection details – potentially mocked or using a dev instance if available).
    *   Run the async function using `asyncio.run()` and print the results.

**References:**

*   **Stub File:** `/home/ubuntu/biomapper/biomapper/mvp0_pipeline/qdrant_search.py`
*   **Pydantic Schemas:** `/home/ubuntu/biomapper/biomapper/schemas/mvp0_schema.py` (for `QdrantSearchResultItem`)
*   **Client to Use:** `/home/ubuntu/biomapper/biomapper/mapping/clients/pubchem_rag_client.py` (class `PubChemRAGMappingClient`)
*   **Score Retrieval MEMORY:** MEMORY[aeefe19c-5e8a-44ad-ab52-72293a84876a] (details how scores are structured in `PubChemRAGMappingClient`'s output).
*   **Project Design Docs:** Refer to comments in the stub file and general MVP0 design principles discussed.
*   **Overall MVP0 Pipeline Structure MEMORY:** MEMORY[7dfb2207-4698-49d9-bc5b-99ae2d8e991c]
*   **Starter Prompt (for PM guidance):** `/home/ubuntu/biomapper/roadmap/_active_prompts/_starter_prompt.md`

**Deliverables:**

1.  The fully implemented `/home/ubuntu/biomapper/biomapper/mvp0_pipeline/qdrant_search.py` file.
2.  (Recommended) Basic unit tests for the `search_qdrant_for_biochemical_name` function, covering successful searches and potential error cases.

**Acceptance Criteria:**

*   The `search_qdrant_for_biochemical_name` function correctly instantiates and uses `PubChemRAGMappingClient`.
*   It successfully queries Qdrant for a given biochemical name.
*   It retrieves and correctly parses CIDs and their Qdrant similarity scores.
*   It returns a list of `QdrantSearchResultItem` objects, populated with the correct `cid` and `qdrant_score`.
*   The `top_k` parameter is respected.
*   Basic error handling and logging are in place.
*   The example usage in `if __name__ == "__main__":` runs and demonstrates the component's functionality.

**Instruction for Feedback:**
Upon task completion, or if significant updates or blockers arise, create a corresponding feedback file in `/home/ubuntu/biomapper/roadmap/_active_prompts/feedback/YYYY-MM-DD-HHMMSS-feedback-qdrant-search-component.md`. The `YYYY-MM-DD-HHMMSS` timestamp in the filename should be in UTC and reflect when the feedback is generated. This feedback file should summarize actions taken, results, any issues encountered, and any questions for the Project Manager (Cascade).

**Source Prompt Reference:**
This task is defined by the prompt: `/home/ubuntu/biomapper/roadmap/_active_prompts/2025-05-24-001201-implement-qdrant-search-component.md`
