# Task: Implement PubChem Annotator Component for MVP0 Pipeline

**Objective:**
Implement the `fetch_pubchem_annotations` function within the file `/home/ubuntu/biomapper/biomapper/mvp0_pipeline/pubchem_annotator.py`. This component is responsible for fetching detailed chemical annotations from PubChem for a given list of PubChem Compound IDs (CIDs).

**Context:**
This component takes a list of CIDs (typically from the Qdrant Search component) and enriches them with information like IUPAC name, molecular formula, SMILES, InChIKey, description, and synonyms. This enriched data will be used by the LLM Mapper component to make a final mapping decision.

**Key Requirements & Implementation Details:**

1.  **File to Implement:**
    *   `/home/ubuntu/biomapper/biomapper/mvp0_pipeline/pubchem_annotator.py` (Use the existing stub file as a starting point).

2.  **Core Logic:**
    *   The main function to implement is `async def fetch_pubchem_annotations(cids: List[int]) -> Dict[int, PubChemAnnotation]:`.
    *   **Method for Fetching Data:**
        *   Use either the `pubchempy` library or direct asynchronous calls to the PubChem PUG REST API (e.g., using `httpx`). The `pubchempy` library is generally preferred if it supports asynchronous operations or can be wrapped appropriately. If direct API calls are made, ensure they are asynchronous.
    *   **Attributes to Fetch:**
        *   Fetch attributes as defined in the `PUBCHEM_ATTRIBUTES_TO_FETCH` list within the stub file (e.g., "Title", "IUPACName", "MolecularFormula", "CanonicalSMILES", "InChIKey", "Description", "Synonym"). Ensure this list remains configurable.
        *   The `PubChemAnnotation` Pydantic model in `/home/ubuntu/biomapper/biomapper/schemas/mvp0_schema.py` defines the structure for these attributes.
    *   **Batching and Concurrency:**
        *   Process CIDs in batches if supported by the chosen PubChem access method (PUG REST allows comma-separated CIDs for some lookups).
        *   Manage concurrency to respect PubChem API rate limits (typically 5 requests per second). Consider using `asyncio.Semaphore` to limit concurrent requests.
    *   **Error Handling for Individual CIDs:**
        *   If an annotation for a specific CID cannot be fetched (e.g., CID not found, API error for that CID), the function should handle this gracefully. It could either omit the CID from the results or include it with a `PubChemAnnotation` object indicating an error or missing data (e.g., all fields `None` or an explicit error field if added to the schema). Log the error.
    *   **Return Value:** The function should return a dictionary mapping each successfully annotated CID (int) to its `PubChemAnnotation` object.

3.  **Pydantic Schema:**
    *   Use `PubChemAnnotation` from `/home/ubuntu/biomapper/biomapper/schemas/mvp0_schema.py` to structure the fetched annotations.

4.  **Asynchronous Nature:**
    *   The function must be `async def` and use `await` for all PubChem API calls.

5.  **Rate Limiting:**
    *   Implement mechanisms (e.g., delays, semaphore) to adhere to PubChem's API rate limits.

6.  **Logging:**
    *   Add informative log messages (e.g., starting annotation for a batch of CIDs, number of CIDs successfully annotated, errors encountered for specific CIDs).

7.  **Example Usage (`if __name__ == "__main__":`)**:
    *   Include a section to demonstrate how to use `fetch_pubchem_annotations`.
    *   Provide a sample list of CIDs.
    *   Run the async function using `asyncio.run()` and print the results in a readable format.

**References:**

*   **Stub File:** `/home/ubuntu/biomapper/biomapper/mvp0_pipeline/pubchem_annotator.py`
*   **Pydantic Schemas:** `/home/ubuntu/biomapper/biomapper/schemas/mvp0_schema.py` (for `PubChemAnnotation`)
*   **Project Design Docs:** Refer to comments in the stub file and general MVP0 design principles.
*   **Overall MVP0 Pipeline Structure MEMORY:** MEMORY[7dfb2207-4698-49d9-bc5b-99ae2d8e991c]
*   **Starter Prompt (for PM guidance):** `/home/ubuntu/biomapper/roadmap/_active_prompts/_starter_prompt.md`

**Deliverables:**

1.  The fully implemented `/home/ubuntu/biomapper/biomapper/mvp0_pipeline/pubchem_annotator.py` file.
2.  (Recommended) Basic unit tests for `fetch_pubchem_annotations`, covering successful annotation, handling of non-existent CIDs, and rate limit considerations (can be mocked).

**Acceptance Criteria:**

*   The `fetch_pubchem_annotations` function correctly fetches specified attributes from PubChem for a list of CIDs.
*   It returns a dictionary mapping CIDs to `PubChemAnnotation` objects.
*   It handles errors for individual CIDs gracefully.
*   It respects PubChem API rate limits.
*   The code is asynchronous.
*   Logging is implemented.
*   The example usage in `if __name__ == "__main__":` runs and demonstrates functionality.

**Instruction for Feedback:**
Upon task completion, or if significant updates or blockers arise, create a corresponding feedback file in `/home/ubuntu/biomapper/roadmap/_active_prompts/feedback/YYYY-MM-DD-HHMMSS-feedback-pubchem-annotator-component.md`. The `YYYY-MM-DD-HHMMSS` timestamp in the filename should be in UTC and reflect when the feedback is generated. This feedback file should summarize actions taken, results, any issues encountered, and any questions for the Project Manager (Cascade).

**Source Prompt Reference:**
This task is defined by the prompt: `/home/ubuntu/biomapper/roadmap/_active_prompts/2025-05-24-001304-implement-pubchem-annotator-component.md`
