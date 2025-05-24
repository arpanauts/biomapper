# Design: MVP 0 - Arivale BIOCHEMICAL_NAME RAG Mapping Pipeline

## 1. High-Level Architecture

The pipeline processes each Arivale `BIOCHEMICAL_NAME` through three sequential stages:

`BIOCHEMICAL_NAME` -> [1. Qdrant Search] -> `List[CandidateCID, QdrantScore]` -> [2. PubChem Annotation] -> `List[EnrichedCandidateCID]` -> [3. LLM Mapping] -> `FinalMappingResult`

## 2. Component Design

### 2.1. Qdrant Search Component
*   **Input:** `biochemical_name: str`, `top_k: int`
*   **Core Logic:**
    *   Instantiate `PubChemRAGMappingClient`.
    *   Call `await client.map_identifiers([biochemical_name])`.
    *   Call `client.get_last_mapping_output()` to retrieve `MappingOutput` object (contains `MappingResultItem` list with `qdrant_similarity_score` - MEMORY[aeefe19c-5e8a-44ad-ab52-72293a84876a]).
    *   Extract top_k CIDs and their scores.
*   **Output:** `List[Tuple[int, float]]` (list of (PubChem CID, Qdrant Score) tuples).
*   **Technologies:** Python, `PubChemRAGMappingClient`.

### 2.2. PubChem Annotation Component
*   **Input:** `List[int]` (list of PubChem CIDs).
*   **Core Logic:**
    *   For each CID, query the PubChem PUG REST API (or use PubChemPy library).
    *   Fetch a predefined set of attributes: e.g., CanonicalSMILES, CanonicalizedCompound (Parent CID), IUPACName, MolecularFormula, InChIKey, Title (Preferred Term), Description (if available), synonym list.
    *   Handle cases where some attributes might be missing for a CID.
*   **Output:** `Dict[int, Dict[str, Any]]` (dictionary mapping CID to its fetched annotations).
*   **Technologies:** Python, `httpx` or `requests` for API calls (or `PubChemPy`).

### 2.3. LLM Mapping Component
*   **Input:**
    *   `original_biochemical_name: str`
    *   `enriched_candidate_data: Dict[int, Dict[str, Any]]` (output from PubChem Annotation Component)
    *   `qdrant_scores: Dict[int, float]` (mapping CID to its Qdrant score from Qdrant Search Component)
*   **Core Logic:**
    *   **Prompt Construction:**
        *   System Prompt: Define the LLM's role (expert biochemist/cheminformatician, task is to map a given name to the best PubChem CID from a list of candidates).
        *   User Prompt:
            *   Include the `original_biochemical_name`.
            *   For each candidate CID: provide its Qdrant score and its fetched PubChem annotations in a structured way.
            *   Ask the LLM to:
                1.  Identify the best matching PubChem CID.
                2.  Provide a confidence level (e.g., High/Medium/Low).
                3.  Explain its reasoning.
                4.  If no good match, indicate that.
    *   **API Call:** Send the prompt to the Anthropic Claude API.
    *   **Response Parsing:** Extract the selected CID, confidence, and rationale from the LLM's response. This might involve expecting a specific format (e.g., JSON) or robust parsing of text.
*   **Output:** `Dict[str, Any]` (containing `mapped_pubchem_cid`, `llm_confidence`, `llm_rationale`, etc.)
*   **Technologies:** Python, Anthropic Python SDK.

## 3. Data Structures (Pydantic Models)

*   `QdrantSearchResultItem(BaseModel)`: `cid: int`, `score: float`
*   `PubChemAnnotation(BaseModel)`: Fields for each fetched attribute (e.g., `iupac_name: Optional[str]`, `synonyms: List[str]`).
*   `LLMCandidateInfo(BaseModel)`: `cid: int`, `qdrant_score: float`, `annotations: PubChemAnnotation`
*   `FinalMappingOutput(BaseModel)`: `original_biochemical_name: str`, `mapped_pubchem_cid: Optional[int]`, `qdrant_score_of_selected: Optional[float]`, `llm_confidence: Optional[str]`, `llm_rationale: Optional[str]`, `candidates_considered: List[LLMCandidateInfo]`

## 4. Workflow Orchestration

A main script/orchestrator will manage the flow:
1.  Read Arivale `BIOCHEMICAL_NAME`s (e.g., from the TSV).
2.  For each name:
    a.  Call Qdrant Search Component.
    b.  Call PubChem Annotation Component with results from (a).
    c.  Call LLM Mapping Component with original name and results from (a) and (b).
    d.  Store/output `FinalMappingOutput`.

## 5. Error Handling

*   Retry mechanisms for API calls (PubChem, Anthropic).
*   Logging of errors and intermediate steps.
*   Default/fallback values if annotations or LLM responses are problematic.

## 6. Testing Strategy

*   **Unit Tests:** For each component, mocking external API calls.
    *   Test Qdrant client interaction and score extraction.
    *   Test PubChem data fetching and parsing.
    *   Test LLM prompt construction and response parsing.
*   **Integration Tests:** Test the end-to-end pipeline with a small, curated set of `BIOCHEMICAL_NAME`s and mocked API responses for all external services.

## 7. Stretch Goal: SPOKE Integration

*   After the PubChem Annotation stage, for each candidate CID, query SPOKE API.
*   Fetch relevant information, e.g., connections to diseases, genes, pathways.
*   Incorporate this SPOKE-derived information into the prompt for the LLM Mapping Component to provide even richer context.
