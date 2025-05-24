# Task: Implement LLM Mapper Component for MVP0 Pipeline

**Objective:**
Implement the `select_best_cid_with_llm` function within the file `/home/ubuntu/biomapper/biomapper/mvp0_pipeline/llm_mapper.py`. This component uses a Large Language Model (LLM) to select the most appropriate PubChem Compound ID (CID) from a list of candidates, based on the original biochemical name and enriched annotations.

**Context:**
This is the final decision-making step in the MVP0 Arivale BIOCHEMICAL_NAME RAG Mapping Pipeline. It takes the original query name, a list of candidate CIDs (each with its Qdrant score and detailed PubChem annotations), and uses an LLM (Anthropic Claude) to determine the best match, its confidence, and the rationale.

**Key Requirements & Implementation Details:**

1.  **File to Implement:**
    *   `/home/ubuntu/biomapper/biomapper/mvp0_pipeline/llm_mapper.py` (Use the existing stub file as a starting point).

2.  **Pydantic Models:**
    *   **Input:** The function will receive `candidates_info: List[LLMCandidateInfo]`. `LLMCandidateInfo` is defined in `/home/ubuntu/biomapper/biomapper/schemas/mvp0_schema.py`.
    *   **Output:** The function should return an `LLMChoice` object. This Pydantic model needs to be **defined within `llm_mapper.py` itself** as per MEMORY[7dfb2207-4698-49d9-bc5b-99ae2d8e991c]. It should include at least:
        *   `selected_cid: Optional[int]`
        *   `llm_confidence: Optional[float]` (e.g., a score from 0.0 to 1.0 if the LLM can provide it, or a categorical confidence)
        *   `llm_rationale: Optional[str]`
        *   `error_message: Optional[str]` (for cases where the LLM call fails or cannot make a selection)

3.  **Core Logic:**
    *   The main function to implement is `async def select_best_cid_with_llm(original_biochemical_name: str, candidates_info: List[LLMCandidateInfo], anthropic_api_key: Optional[str] = None) -> LLMChoice:`.
    *   **LLM Integration (Anthropic Claude):**
        *   Use the official Anthropic Python SDK.
        *   Manage the Anthropic API key securely. It should be passable as an argument `anthropic_api_key` or loaded from an environment variable (e.g., `ANTHROPIC_API_KEY`). Prioritize the argument if provided.
    *   **Prompt Engineering:**
        *   Construct a clear and effective prompt for the LLM.
        *   The prompt must include:
            *   The `original_biochemical_name`.
            *   Details for each candidate CID from `candidates_info`. This includes the `cid`, `qdrant_score`, and relevant fields from `PubChemAnnotation` (e.g., title, synonyms, IUPAC name, description). Format this information clearly.
        *   The prompt should instruct the LLM to:
            *   Select the best matching CID.
            *   Provide a confidence score or category for its choice.
            *   Provide a brief rationale for its selection.
            *   If no candidate is a good match, it should indicate this.
    *   **Parsing LLM Response:**
        *   Carefully parse the LLM's response to extract the selected CID, confidence, and rationale.
        *   Handle cases where the LLM's output might not be perfectly structured. Consider asking the LLM to respond in a specific format (e.g., JSON) if feasible.
    *   **Return Value:** Populate and return an `LLMChoice` object. If the LLM fails or cannot make a selection, `selected_cid` might be `None`, and `error_message` should be populated.

4.  **Asynchronous Nature:**
    *   The function should be `async def` if the Anthropic client library supports asynchronous operations. Check the library's documentation. If not, it can be a synchronous function, but the overall pipeline orchestrator will need to manage its execution (e.g., via `asyncio.to_thread`). Assume async for now if the library supports it.

5.  **Configuration:**
    *   Document how the Anthropic API key is managed.

6.  **Logging:**
    *   Log key information, such as the prompt sent to the LLM (or a summary), the raw LLM response (or a summary), and the parsed `LLMChoice`. Log any errors during API calls or response parsing.

7.  **Example Usage (`if __name__ == "__main__":`)**:
    *   Include a section to demonstrate `select_best_cid_with_llm`.
    *   Create sample `original_biochemical_name` and `candidates_info` (with mock `QdrantSearchResultItem` and `PubChemAnnotation` data).
    *   Provide a placeholder for the Anthropic API key (instruct user to set it as an environment variable for testing).
    *   Run the function (using `asyncio.run()` if async) and print the `LLMChoice` result.

**References:**

*   **Stub File:** `/home/ubuntu/biomapper/biomapper/mvp0_pipeline/llm_mapper.py`
*   **Pydantic Schemas:**
    *   `/home/ubuntu/biomapper/biomapper/schemas/mvp0_schema.py` (for `LLMCandidateInfo`)
    *   `LLMChoice` (to be defined in `llm_mapper.py`)
*   **Project Design Docs:** Refer to comments in the stub file and general MVP0 design principles.
*   **Overall MVP0 Pipeline Structure MEMORY:** MEMORY[7dfb2207-4698-49d9-bc5b-99ae2d8e991c]
*   **Starter Prompt (for PM guidance):** `/home/ubuntu/biomapper/roadmap/_active_prompts/_starter_prompt.md`

**Deliverables:**

1.  The fully implemented `/home/ubuntu/biomapper/biomapper/mvp0_pipeline/llm_mapper.py` file, including the definition of the `LLMChoice` Pydantic model.
2.  (Recommended) Basic unit tests for `select_best_cid_with_llm`, focusing on prompt construction, LLM response parsing, and error handling (LLM interaction can be mocked).

**Acceptance Criteria:**

*   The `LLMChoice` Pydantic model is correctly defined in `llm_mapper.py`.
*   The `select_best_cid_with_llm` function correctly constructs a prompt for the Anthropic LLM.
*   It successfully calls the LLM API and parses its response.
*   It returns a populated `LLMChoice` object, including selected CID, confidence, and rationale.
*   API key management is handled securely.
*   Logging is implemented.
*   The example usage in `if __name__ == "__main__":` runs and demonstrates functionality (may require a valid API key for full execution).

**Instruction for Feedback:**
Upon task completion, or if significant updates or blockers arise, create a corresponding feedback file in `/home/ubuntu/biomapper/roadmap/_active_prompts/feedback/YYYY-MM-DD-HHMMSS-feedback-llm-mapper-component.md`. The `YYYY-MM-DD-HHMMSS` timestamp in the filename should be in UTC and reflect when the feedback is generated. This feedback file should summarize actions taken, results, any issues encountered, and any questions for the Project Manager (Cascade).

**Source Prompt Reference:**
This task is defined by the prompt: `/home/ubuntu/biomapper/roadmap/_active_prompts/2025-05-24-001305-implement-llm-mapper-component.md`
