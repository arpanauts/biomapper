# Implementation Notes: MVP 0 - Arivale BIOCHEMICAL_NAME RAG Mapping Pipeline

## 1. General Approach

*   **Modularity:** Emphasize creating distinct, reusable Python modules for each of the three main pipeline stages (Qdrant Search, PubChem Annotation, LLM Mapping) and for Pydantic models.
*   **Configuration:** Store configurable parameters (e.g., `top_k` for Qdrant, PubChem attributes to fetch, LLM model name, API keys) in a separate configuration file (e.g., `config.yaml` or `.env` file) or pass them as arguments to the main script. Avoid hardcoding.
*   **Asynchronous Operations:** Consider using `asyncio` for API calls (PubChem, LLM) if processing a batch of names, to improve performance. The `PubChemRAGMappingClient` already supports async operations.
*   **Logging:** Implement comprehensive logging using Python's `logging` module. Log key inputs, outputs, errors, and timings for each stage.

## 2. Qdrant Search Component

*   Ensure the `PubChemRAGMappingClient` is correctly configured with the Qdrant URL and any necessary API keys.
*   Leverage the `MappingOutput` and `MappingResultItem` Pydantic models from `biomapper.schemas.rag_schema` (as per MEMORY[aeefe19c-5e8a-44ad-ab52-72293a84876a]) to access Qdrant scores.
*   The component should gracefully handle cases where `PubChemRAGMappingClient` returns no matches.

## 3. PubChem Annotation Component

*   **API Choice:** `PubChemPy` is a convenient Python wrapper. If more control or specific PUG REST features are needed, direct `httpx` calls can be used.
*   **Rate Limiting:** Be mindful of PubChem API rate limits (no more than 5 requests per second). Implement retries with exponential backoff if using direct API calls. `PubChemPy` might handle some of this internally.
*   **Attribute Selection:** The list of attributes to fetch (e.g., CanonicalSMILES, IUPACName, Synonyms, Description) should be configurable. Some attributes might not be available for all CIDs.
*   **Data Structure:** The output should clearly link each CID to its fetched annotations. A dictionary `Dict[int, PubChemAnnotation]` is suitable.

## 4. LLM Mapping Component

*   **Anthropic API Key:** Securely manage the Anthropic API key (e.g., via environment variables).
*   **Prompt Engineering:** This is critical.
    *   The system prompt should clearly define the LLM's role and the desired output format.
    *   The user prompt must clearly present the original `BIOCHEMICAL_NAME` and the structured information for each candidate CID (including its Qdrant score and PubChem annotations).
    *   Consider asking the LLM to output its choice in a structured format (e.g., JSON within its text response) to simplify parsing. Example:
        ```json
        {
          "selected_cid": 12345,
          "confidence": "High",
          "rationale": "The synonyms and IUPAC name for CID 12345 closely match the input biochemical name 'X'. The Qdrant score is also high."
        }
        ```
*   **LLM Model:** Start with a capable model (e.g., Claude 3 Sonnet or Opus, depending on budget and performance needs).
*   **Response Parsing:** Implement robust parsing for the LLM's output. If requesting JSON, use a JSON parser with error handling.
*   **Confidence Score:** The LLM's confidence can be qualitative ("High", "Medium", "Low") or a self-assessed numeric score if the model supports it. The rationale is key.

## 5. Input Data Handling

*   The Arivale metabolomics metadata is in `/procedure/data/local_data/ARIVALE_SNAPSHOTS/metabolomics_metadata.tsv`.
*   The pipeline should be able to process the `BIOCHEMICAL_NAME` column.
*   Consider how to handle missing or ambiguous `BIOCHEMICAL_NAME` entries.

## 6. Output

*   The final output for each input name should be a `FinalMappingOutput` Pydantic model.
*   Provide an option to write these structured results to a machine-readable format like CSV, TSV, or JSON Lines.

## 7. Testing

*   **Mocking:** Use `unittest.mock` extensively for external API calls (Qdrant client, PubChem, Anthropic). This allows for deterministic tests and avoids actual API costs/rate limits during development.
*   **Sample Data:** Curate a diverse set of test `BIOCHEMICAL_NAME`s, including:
    *   Simple, unambiguous names.
    *   Names with common synonyms.
    *   More complex or less common names.
    *   Names that might not have a clear PubChem match.
*   **Manual Verification:** For a small set of results, manually verify the LLM's choices and rationale to gauge accuracy.

## 8. Dependencies

*   `pydantic`
*   `anthropic` (Anthropic Python SDK)
*   `pubchempy` (optional, if used)
*   `httpx` or `requests` (if direct API calls)
*   `biomapper` (for `PubChemRAGMappingClient` and its schemas)
*   `python-dotenv` (for managing environment variables like API keys)
*   `PyYAML` (if using YAML for configuration)

Ensure these are added to `pyproject.toml` if not already present.
