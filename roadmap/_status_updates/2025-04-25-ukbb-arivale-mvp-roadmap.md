# Biomapper Status Update: Roadmap for UKBB -> Arivale MVP Mapping

## 1. Recent Accomplishments (In Recent Memory)

*   **Strategic Shift:** Agreed to pivot the MVP mapping direction from Arivale -> UKBB to **UKBB -> Arivale**. This better addresses the challenge of starting with unstructured text names in UKBB data.
*   **Resource Prioritization:** Decided to prioritize investigating and implementing clients for text-oriented mapping resources (UMLS, UniProt Name Search) *before* extensive database configuration.
*   **RAG Integration Strategy:** Incorporated the PubChem-based RAG approach as a planned fallback mechanism for when standard mapping resources are exhausted, noting the need for vector DB preparation and executor integration (using similarity cutoffs).
*   **Codebase Exploration:** Located the mapping clients directory at `/home/ubuntu/biomapper/biomapper/mapping/clients/`.
*   **Client Assessment:** Identified existing clients (UniChem, ChEBI, PubChem, KEGG, RefMet, UniProt ID-mapper) and confirmed the need to implement clients/functionality for UMLS and UniProt Name/Symbol search. Analyzed `uniprot_focused_mapper.py` and determined it handles ID-to-ID mapping but not the required Name-to-ID lookup.

## 2. Current Project State

*   **Overall:** The project is in the planning and resource development phase for the UKBB -> Arivale MVP. Core infrastructure (database models, basic executor logic) exists but requires enhancement for new resources and fallback logic.
*   **Component Status:**
    *   `db/models.py`: Contains configuration models for `metamapper.db` (managed by population script). Core structure stable. `EntityMapping` and `MappingMetadata` models moved to `cache_models.py`.
    *   `db/cache_models.py`: **Created.** Contains models for runtime cache data (`EntityMapping`, `MappingMetadata`, `EntityMappingProvenance`, `PathExecutionLog`, plus placeholders).
    *   `mapping_cache.db`: **Setup complete.** Schema created and managed by Alembic (initial migration `bf1c24ebbbec`).
    *   `scripts/populate_metamapper_db.py`: Requires significant updates (new endpoints, resources, relationships, paths, preferences) after resource clients are ready.
    *   `mapping/relationships/executor.py`: Requires significant updates to integrate new clients (UMLS, UniProt Name Search), implement fallback logic between resources, and integrate the RAG mechanism.
    *   `mapping/clients/`: Requires implementation of `UMLSClient` and `UniProtNameClient` (or similar). Existing clients (`UniChemClient`, etc.) are available but may need adjustments for error handling/robustness (re: UniChem 404s).
*   **Outstanding Issues:**
    *   Need implementation for UMLS and UniProt Name/Symbol search clients.
    *   Need a defined strategy within the executor for handling resource failures and executing fallback logic (including RAG).
    *   The previously identified UniChem `404 Not Found` issue for specific `PUBCHEM -> CHEBI` mappings still needs a robust handling strategy within the executor's fallback logic.
    *   The PubChem vector database for RAG requires filtering/preparation (acknowledged as a related but potentially separate task).

## 3. Technical Context

*   **Architecture:** Reaffirmed the endpoint-relationship-resource model. Mapping direction is now UKBB -> Arivale.
*   **Mapping Strategy:** Prioritize structured mapping using new resources (UMLS, UniProt Name Search) followed by existing resources (UniChem etc.), with RAG as the final fallback.
*   **Technology/Patterns:** Continue using SQLAlchemy, SQLite, `asyncio`. New clients will interact with REST APIs (UMLS UTS, UniProt Search). RAG integration will involve vector similarity lookups (details TBD based on vector DB implementation).
*   **Database Management:** `metamapper.db` configuration stored in `models.py` and populated by `populate_metamapper_db.py`. `mapping_cache.db` runtime data schema defined in `cache_models.py` and managed by Alembic via the configuration in `biomapper/db/migrations`.
*   **Learnings:**
    *   `uniprot_focused_mapper.py` uses the ID mapping API, not suitable for Name -> ID search.
    *   Starting with unstructured text (UKBB `NAME`) necessitates prioritizing text-based resources like UMLS.
    *   Fallback logic in the executor is critical for robustness against external API limitations and incomplete mappings.

## 4. Next Steps

*   **Phase 1: Resource Investigation & Client Implementation (Highest Priority)**
    1.  **Implement `UniProtNameClient` (or enhance existing):**
        *   **Goal:** Create functionality to query a UniProt API (likely search endpoint) to find UniProt IDs (`UNIPROT`) given protein/gene names (`NAME`).
        *   **Action:** Design and implement this client/functionality within `/home/ubuntu/biomapper/biomapper/mapping/clients/`. Consider if it should be a new file or added to `uniprot_focused_mapper.py`.
    2.  **Implement `UMLSClient`:**
        *   **Goal:** Enable mapping from text names (`NAME`) to UMLS CUIs (`UMLS_CUI`) and potentially from CUIs to other identifiers like `LOINC`.
        *   **Action:** Design and implement `clients/umls.py`. Requires obtaining UMLS Terminology Services (UTS) API credentials.
        *   *(Note: Basic structure created. Full authentication logic (TGT/ST handling) will be implemented later, specifically when defining mapping paths that require UMLS.)*
    3.  **Define RAG Integration:**
        *   **Goal:** Specify how the executor calls the RAG component and processes its results (cosine similarity cutoff).
        *   **Action:** Outline the required interface/functions for the RAG component and plan the executor modifications. (Vector DB prep is parallel).
*   **Phase 2: Database Configuration**
    4.  **Update `populate_metamapper_db.py`:**
        *   Add `MappingResource` entries for UniProt Name Search, UMLS, PubChemRAG.
        *   Ensure configuration models (`PropertyExtractionConfig`, etc.) are populated.
        *   Add `Endpoint` entries for `UKBB_Protein`, `Arivale_Protein`, `Arivale_Chemistry`.
        *   Define **reversed** `EndpointRelationship` entries (UKBB -> Arivale).
        *   Define `EndpointOntologyPreference` for target (Arivale) endpoints.
        *   Define `MappingPath` entries utilizing the new resources and specifying fallback order conceptually.
        *   Define `RelationshipMappingPath` entries linking relationships to specific mapping paths.
    5.  **Configure `mapping_cache.db` (Alembic):**
        *   **DONE.**
        *   **Details:** Created `cache_models.py` and moved `EntityMapping`/`MappingMetadata` there. Added `EntityMappingProvenance` and `PathExecutionLog`. Configured Alembic (`alembic.ini`, `biomapper/db/migrations/env.py`) to manage `mapping_cache.db` using `cache_models.py`. Cleaned conflicting migration files from `versions/` directory. Generated and applied initial migration `bf1c24ebbbec`.
*   **Phase 3: Executor Enhancement & Testing**
    6.  **Enhance `RelationshipMappingExecutor`:** Implement the client calls, fallback logic (UniProt->UMLS->UniChem->RAG etc.), UniChem 404 handling, and logging results to `mapping_cache.db` (including provenance).
    7.  **Testing:** Create/adapt test scripts for UKBB -> Arivale scenarios, verifying cache entries.

*   **Priorities:** Complete Phase 1 (Client implementation) before moving to Phase 2/3.
*   **Dependencies:** UMLS client requires UTS credentials. RAG integration depends on vector DB availability/interface. Executor logging (Phase 3, Step 6) dependency on `mapping_cache.db` setup (Phase 2, Step 5) is **resolved**.
*   **Challenges:** Robust error handling for external APIs, defining effective fallback logic, potential complexity in RAG integration, low success rate for pure `NAME` mapping.

## 5. Open Questions & Considerations

*   What specific UniProt API endpoint is best for Name/Symbol -> ID search? (Needs research).
*   What are the rate limits and authentication requirements for the UMLS UTS API?
*   How exactly should the executor manage the sequence of trying different `MappingPath`s for the same source/target ontology pair before falling back to RAG?
*   What is the specific interface/input/output for the RAG component?
*   How should partial successes (e.g., mapping found via UMLS but not UniChem) be handled or logged?
*   Should the `uniprot_focused_mapper.py` (ID-to-ID) be refactored or used alongside the new Name-to-ID functionality?
