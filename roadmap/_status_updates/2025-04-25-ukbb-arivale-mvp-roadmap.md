# Biomapper Status Update: Roadmap for UKBB -> Arivale MVP Mapping

**Overarching Goal:** The primary objective of this MVP phase is **not** just to create a one-off UKBB->Arivale mapping, but to **build and validate the core, configuration-driven mapping framework** (`MappingExecutor`, `metamapper.db`, `clients`, `cache`). The UKBB->Arivale protein use case serves as the essential driver and testbed for developing this reusable framework, which will then be extensible to metabolites (e.g., using UMLS) and other mapping scenarios.

## 1. Recent Accomplishments (In Recent Memory)

*   **Strategic Shift:** Agreed to pivot the MVP mapping direction from Arivale -> UKBB to **UKBB -> Arivale**. This better addresses the challenge of starting with unstructured text names in UKBB data.
*   **Resource Prioritization:** Decided to prioritize investigating and implementing clients for text-oriented mapping resources (UMLS, UniProt Name Search) *before* extensive database configuration.
*   **RAG Integration Strategy:** Incorporated the PubChem-based RAG approach as a planned fallback mechanism for when standard mapping resources are exhausted, noting the need for vector DB preparation and executor integration (using similarity cutoffs).
*   **Codebase Exploration:** Located the mapping clients directory at `/home/ubuntu/biomapper/biomapper/mapping/clients/`.
*   **Client Assessment:** Identified existing clients (UniChem, ChEBI, PubChem, KEGG, RefMet, UniProt ID-mapper) and confirmed the need to implement clients/functionality for UMLS and UniProt Name/Symbol search. Analyzed `uniprot_focused_mapper.py` and determined it handles ID-to-ID mapping but not the required Name-to-ID lookup.
*   **Initial Protein Mapping:** Implemented `UniProtNameClient` (handling composite genes) and basic endpoint configurations in `populate_metamapper_db.py`. Successfully ran a preliminary UKBB->Arivale protein mapping script (`map_ukbb_to_arivale.py`), demonstrating the two-step process (UKBB GeneName -> UniProtKB AC -> Arivale Name) and highlighting limitations (high UniProt->Arivale mismatch, simplistic/hardcoded executor logic).

## 2. Current Project State

*   **Overall:** The project has successfully executed a basic protein mapping, proving individual components (client, DB config) work in isolation. However, this revealed the need to significantly enhance the `MappingExecutor` to be truly configuration-driven and less hardcoded, fulfilling the core architectural goal.
*   **Component Status:**
    *   `db/models.py`: Core configuration models stable.
    *   `db/cache_models.py`: Schema defined for caching results and provenance.
    *   `mapping_cache.db`: Setup complete via Alembic.
    *   `scripts/populate_metamapper_db.py`: Updated with basic configurations for UKBB_Protein and Arivale_Protein endpoints, including property extraction for relevant identifiers (GeneName, UniProtKB AC, Arivale Name). **Sufficient for current protein framework focus.**
    *   `biomapper/core/mapping_executor.py`: **Requires significant refactoring.** Current implementation is too simplistic and hardcoded for the UniProt client. Needs enhancement to dynamically determine paths and call clients based on `metamapper.db` configuration.
    *   `mapping/clients/`: `UniProtNameClient` implemented and functional for GeneName->UniProtKB mapping (including composite handling). `UMLSClient` implementation is **deferred**. Existing clients may need adjustments later.
*   **Outstanding Issues:**
    *   **Highest Priority:** Refactor `MappingExecutor` to be configuration-driven.
    *   Implement basic provenance logging to `mapping_cache.db` within the executor.
    *   Need a defined strategy within the *enhanced* executor for selecting mapping paths (e.g., prioritize direct UniProt). Handling resource failures and complex fallback logic (UMLS, RAG, UniChem 404s) is **deferred** until the core dynamic execution framework is stable.
    *   `UMLSClient` implementation is **deferred**.
    *   PubChem RAG vector DB preparation is **deferred**.

## 3. Technical Context

*   **Architecture:** Reaffirmed the endpoint-relationship-resource model. Mapping direction is now UKBB -> Arivale.
*   **Mapping Strategy:** Prioritize structured mapping using new resources (UMLS, UniProt Name Search) followed by existing resources (UniChem etc.), with RAG as the final fallback.
*   **Technology/Patterns:** Continue using SQLAlchemy, SQLite, `asyncio`. New clients will interact with REST APIs (UMLS UTS, UniProt Search). RAG integration will involve vector similarity lookups (details TBD based on vector DB implementation).
*   **Database Management:** `metamapper.db` configuration stored in `models.py` and populated by `populate_metamapper_db.py`. `mapping_cache.db` runtime data schema defined in `cache_models.py` and managed by Alembic via the configuration in `biomapper/db/migrations`.
*   **Learnings:**
    *   `uniprot_focused_mapper.py` uses the ID mapping API, not suitable for Name -> ID search.
    *   Starting with unstructured text (UKBB `NAME`) necessitates prioritizing text-based resources like UMLS.
    *   Fallback logic in the executor is critical for robustness against external API limitations and incomplete mappings.

## 4. Next Steps (Revised Priorities)

**Focus: Build the Core Dynamic Mapping Framework using Protein Use Case**

1.  **Refactor `MappingExecutor` (Highest Priority): Detailed Plan**

    *   **Goal:** Transform the executor into a dynamic, configuration-driven engine using `metamapper.db`.
    *   **Phased Approach:**

        **Phase 1: Foundation & Pathfinding (with Integrated Testing)**

        1.  **Helper Functions for DB Queries:**
            *   **Goal:** Abstract database interactions.
            *   **Tasks:** Implement internal methods (`_get_endpoint_ontology`, `_find_mapping_paths`) focusing initially on explicit `MappingPaths`.
            *   **Testing:** Implement concurrent unit tests (mocking DB session) for query logic.

        2.  **Initial Path Selection Strategy:**
            *   **Goal:** Implement basic logic to choose a path.
            *   **Tasks:** Implement simple strategy (direct > shortest). Note future enhancements (confidence, weights).
            *   **Testing:** Unit test the selection logic.

        **Phase 2: Dynamic Execution Core (with Adapters, Error Handling & Testing)**

        3.  **Client Interaction Strategy (Adapter/Interface):**
            *   **Goal:** Define a flexible way to interact with diverse clients.
            *   **Tasks:** Analyze clients, design strategy (Protocol vs. Adapter), define standard `MappingResult`, consider batching.
            *   **Configuration:** Store client/adapter class, method, params in `MappingResource`.

        4.  **Dynamic Client Instantiation & Method Call:**
            *   **Goal:** Load and use the correct client/adapter.
            *   **Tasks:** Implement dynamic import/instantiation based on DB config. Call standardized method.
            *   **Testing:** Unit test dynamic loading and dispatch, mocking clients/adapters.

        5.  **Refactor `execute_mapping` Main Loop (with Basic Error Handling):**
            *   **Goal:** Orchestrate the dynamic mapping robustly.
            *   **Tasks:** Replace hardcoded logic, loop through path steps, instantiate client/adapter, wrap calls in `try...except`, log failures, implement basic failure logic (terminate path for ID), return results.
            *   **Testing:** Develop integration tests (mocked DB/clients), cover success/failure, consider TDD.

        **Phase 3: Caching, Integration & Final Testing**

        6.  **Implement Caching & Provenance Logging:**
            *   **Goal:** Persist results and execution details.
            *   **Tasks:** Integrate calls to write to `mapping_cache.db` (`MappingMetadata`, `EntityMapping`, `PathExecutionLog`, `EntityMappingProvenance`) for successes and failures.

        7.  **End-to-End Testing & Refinement:**
            *   **Goal:** Verify the fully refactored executor.
            *   **Tasks:** Use test script with actual protein config, verify path selection, execution, results, cache/provenance. Test edge cases.

2.  **Implement Basic Caching in Executor:**
    *   _(This step is now integrated into Step 6 of the detailed refactoring plan above)_.

3.  **Test Refactored Executor:**
    *   _(This step is now integrated into Steps 1, 2, 4, 5, and 7 of the detailed refactoring plan above)_.

**Deferred Steps (Post-Core Framework):**

*   Implement advanced fallback logic (UniProt->UMLS->UniChem->RAG, UniChem 404 handling) within the executor.
*   Implement `UMLSClient`.
*   Configure `metamapper.db` for metabolite endpoints and mapping paths.
*   Implement metabolite mapping use cases.
*   Integrate RAG component.
*   Generalize identifier handling (composites, outdated IDs) across clients/executor.
*   Implement logging/handling for failed mappings (e.g., to a separate table for retries).

## 5. Open Questions & Considerations

*   How should the executor dynamically determine the correct client *method* to call for a given mapping step? (Standard interface? Configurable method name?)
*   What is the best strategy for finding/selecting mapping paths in `metamapper.db` (especially multi-step paths)?
*   How should the initial provenance data (path taken, confidence) be represented and stored in the cache?
*   _(Deferred)_ What are the rate limits and authentication requirements for the UMLS UTS API?
*   _(Deferred)_ What is the specific interface/input/output for the RAG component?

### Future Considerations

*   **Generalize Identifier Handling:** The current approach handles composite (e.g., `GENE1_GENE2`) and potentially outdated identifiers within specific clients (`UniProtNameClient`). This pattern is common across entity types and resources. Future work should generalize this handling (e.g., via pre-processors, resolver resources, or middleware) to improve reusability and maintainability across Biomapper. (See Memory: 5e6be590-afbc-4008-9edd-106becd63356 for details).

---

## Status Summary (As of 2025-04-29)

*   **UKBB->Arivale Protein Mapping (Basic Script):** Completed.
*   **`UniProtNameClient`:** Implemented.
*   **`metamapper.db` Config (Protein):** Basic configuration added.
*   **`mapping_cache.db` Setup:** Completed.
*   **`MappingExecutor` Refactoring:** **Required - Highest Priority Next Step.**
*   **`UMLSClient` Implementation:** Deferred.
*   **Metabolite Mapping:** Deferred.
*   **Advanced Fallback Logic (Executor):** Deferred.
*   **RAG Integration:** Deferred.

- **Tasks:**
  - Implement clients for selected mapping resources.
    - `UniProtNameClient`: **Completed**
    - `UMLSClient`: **Deferred**
  - Configure `metamapper.db` (`scripts/populate_metamapper_db.py`):
    - Define Endpoints (UKBB, Arivale): **Basic definitions added.**
    - Define Mapping Resources (UniProt): **Basic definition added.**
    - Define Property Extraction (UKBB/Arivale Protein): **Added.**
    - Define Relationships & Ontology Preferences: Pending (Low priority until executor refactored)
    - Define Mapping Paths: Pending (Low priority until executor refactored)
  - Implement core mapping logic (`MappingExecutor`):
    - **Status:** **Needs Major Refactoring (Highest Priority)**
    - **Next Step:** Refactor executor for dynamic, config-driven path finding and client execution.
