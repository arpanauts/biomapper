# Biomapper Status Update: Roadmap for UKBB -> Arivale MVP Mapping

**Overarching Goal:** The primary objective of this MVP phase is **not** just to create a one-off UKBB->Arivale mapping, but to **build and validate the core, configuration-driven mapping framework** (`MappingExecutor`, `metamapper.db`, `clients`, `cache`). The UKBB->Arivale protein use case serves as the essential driver and testbed for developing this reusable framework, which will then be extensible to metabolites (e.g., using UMLS) and other mapping scenarios.

## 1. Recent Accomplishments (In Recent Memory)

*   **Strategic Shift:** Agreed to pivot the MVP mapping direction from Arivale -> UKBB to **UKBB -> Arivale**. This better addresses the challenge of starting with unstructured text names in UKBB data.
*   **Resource Prioritization:** Decided to prioritize investigating and implementing clients for text-oriented mapping resources (UMLS, UniProt Name Search) *before* extensive database configuration.
*   **RAG Integration Strategy:** Incorporated the PubChem-based RAG approach as a planned fallback mechanism for when standard mapping resources are exhausted, noting the need for vector DB preparation and executor integration (using similarity cutoffs).
*   **Codebase Exploration:** Located the mapping clients directory at `/home/ubuntu/biomapper/biomapper/mapping/clients/`.
*   **Client Assessment:** Identified existing clients (UniChem, ChEBI, PubChem, KEGG, RefMet, UniProt ID-mapper) and confirmed the need to implement clients/functionality for UMLS and UniProt Name/Symbol search. Analyzed `uniprot_focused_mapper.py` and determined it handles ID-to-ID mapping but not the required Name-to-ID lookup.
*   **Initial Protein Mapping:** Implemented `UniProtNameClient` (handling composite genes) and basic endpoint configurations in `populate_metamapper_db.py`. Successfully ran a preliminary UKBB->Arivale protein mapping script (`map_ukbb_to_arivale.py`), demonstrating the two-step process (UKBB GeneName -> UniProtKB AC -> Arivale Name) and highlighting limitations (high UniProt->Arivale mismatch, simplistic/hardcoded executor logic).
*   **MappingExecutor Basic Refactoring:** Completed initial refactoring of the MappingExecutor to support dynamic path selection and client instantiation from `metamapper.db` configuration. Successfully implemented and executed the UKBB-to-Arivale mapping using UniProt accession numbers, with proper caching and logging.
*   **Bidirectional Mapping & Provenance:** Implemented bidirectional path finding (`ReversiblePath`, updated `_find_mapping_paths`). Enhanced `EntityMapping` model with metadata: `confidence_score`, `hop_count`, `mapping_direction`, `mapping_path_details`. Implemented confidence scoring (`_calculate_confidence_score`).
*   **Cache Functionality & Consistency:** Fixed `MappingExecutor` initialization to reliably create cache schema (`mapping_cache.db`). Resolved cache inconsistency: `MappingExecutor` now consistently returns `Dict[str, Optional[List[str]]]`.
*   **Client Development & Fixes:** `ArivaleMetadataLookupClient` fixed to handle composite UniProt *keys* (e.g., "P1,P2") present in the Arivale source data by creating a component lookup map during initialization.

## 2. Current Project State

*   **Overall:** The project has successfully executed a basic protein mapping, demonstrating that the core framework components can work together. The `MappingExecutor` now provides a configuration-driven foundation, but requires further enhancement to support more complex mapping scenarios.
*   **Component Status:**
    *   `db/models.py`: Core configuration models stable.
    *   `db/cache_models.py`: Schema defined for caching results and provenance.
    *   `mapping_cache.db`: Setup complete via Alembic.
    *   `scripts/populate_metamapper_db.py`: Updated with basic configurations for UKBB_Protein and Arivale_Protein endpoints, including property extraction for relevant identifiers (GeneName, UniProtKB AC, Arivale Name). **Sufficient for current protein framework focus.**
    *   `biomapper/core/mapping_executor.py`: **Partially refactored.** Now supports dynamic path finding, client instantiation, and basic caching, but needs further enhancement for more complex mapping strategies.
    *   `mapping/clients/`: `UniProtNameClient` implemented and functional for GeneName->UniProtKB mapping (including composite handling). `UMLSClient` implementation is **deferred**. Existing clients may need adjustments later.
*   **Outstanding Issues:**
    *   **Highest Priority:** Enhance `MappingExecutor` to support bidirectional and multi-strategy mapping approaches.
    *   Integrate confidence scoring and mapping metadata to improve provenance tracking.
    *   Address the remaining NULL constraint issue in the path logging system.
    *   Move `PathLogMappingAssociation` to `cache_models.py` for better code organization.
    *   Implement more comprehensive error handling and reporting for mapping failures.
    *   Enhance the schema to support mapping with multiple ontological resources, fallback strategies, and handling of outdated/merged identifiers.
    *   `UMLSClient` implementation remains **deferred**.
    *   PubChem RAG vector DB preparation remains **deferred**.

## 3. Technical Context

*   **Architecture:** Reaffirmed the endpoint-relationship-resource model. Mapping direction is now UKBB -> Arivale.
*   **Mapping Strategy:** Prioritize structured mapping using new resources (UMLS, UniProt Name Search) followed by existing resources (UniChem etc.), with RAG as the final fallback.
*   **Technology/Patterns:** Continue using SQLAlchemy, SQLite, `asyncio`. New clients will interact with REST APIs (UMLS UTS, UniProt Search). RAG integration will involve vector similarity lookups (details TBD based on vector DB implementation).
*   **Database Management:** `metamapper.db` configuration stored in `models.py` and populated by `populate_metamapper_db.py`. `mapping_cache.db` runtime data schema defined in `cache_models.py` and managed by Alembic via the configuration in `biomapper/db/migrations`.
*   **Learnings:**
    *   `uniprot_focused_mapper.py` uses the ID mapping API, not suitable for Name -> ID search.
    *   Starting with unstructured text (UKBB `NAME`) necessitates prioritizing text-based resources like UMLS.
    *   Fallback logic in the executor is critical for robustness against external API limitations and incomplete mappings.
    *   Direct UniProt AC mapping works well but leaves many unmatched entities, demonstrating the need for a more comprehensive approach.

## 4. Next Steps (Revised Priorities)

**Focus: Enhance the Core Mapping Framework to Support Comprehensive Bidirectional Mapping**

1. **Enhance `MappingExecutor` for Comprehensive Mapping (Highest Priority): Detailed Plan**

   *   **Goal:** Transform the executor to support bidirectional, multi-strategy ontological mapping.
   *   **Phased Approach:**

      **Phase 1: Bidirectional Mapping Support**

      1. **Implement Bidirectional Path Finding:**
         *   **Goal:** Support finding and executing paths in both directions.
         *   **Tasks:** Extend path finding to consider both directions, implement a "reverse" mechanism to try mapping target->source when source->target fails.
         *   **Testing:** Test with test datasets ensuring bidirectional paths are correctly identified and executed.

      2. **Enhance Metadata Tracking:**
         *   **Goal:** Add metadata to track confidence, path direction, and number of hops.
         *   **Tasks:** Extend entity mapping and provenance models to store confidence scores and path details.
         *   **Testing:** Verify metadata is correctly stored for direct vs. indirect mappings.

      **Phase 2: Multi-Strategy Mapping**

      3. **Implement Alternative Path Strategy:**
         *   **Goal:** Support trying multiple paths for unmapped entities.
         *   **Tasks:** Add logic to attempt alternative paths for unmapped identifiers, prioritizing by confidence.
         *   **Testing:** Test with entities that require indirect mapping paths.

      4. **Add ID Normalization Support:**
         *   **Goal:** Handle outdated, merged, or variant identifiers.
         *   **Tasks:** Add preprocessing step to check for outdated/merged IDs, extend client interfaces to support variant checks.
         *   **Testing:** Test with known outdated UniProt IDs.

      **Phase 3: Enhanced Reporting and Integration**

      5. **Implement Comprehensive Reporting:**
         *   **Goal:** Generate detailed mapping reports with statistics and diagnostics.
         *   **Tasks:** Extend result format to include mapping metadata, success/failure rates, path details.
         *   **Testing:** Generate and verify reports for test datasets.

      6. **Integrate with Outer Join Strategy:**
         *   **Goal:** Create a combined dataset showing what matches and what's unique to each endpoint.
         *   **Tasks:** Implement outer join-like result format showing matched pairs and unique entries.
         *   **Testing:** Verify with test datasets covering different overlap scenarios.

2. **Immediate Technical Improvements:**

   *   **Fix `NULL` constraint in `PathExecutionLog`:** Ensure `source_entity_type` is properly passed to avoid constraint violations.
   *   **Move `PathLogMappingAssociation` to `cache_models.py`:** Improve code organization and maintainability.
   *   **Implement confidence scoring system:** Add a confidence score calculation based on path directness, number of steps, and client reliability.
   *   **Refine error reporting and handling:** Improve how mapping failures are logged and handled.

3. **Enhance Database Schema:**

   *   **Extend `EntityMapping` with metadata fields:** Add fields for confidence score, mapping method, and path details.
   *   **Add support for mapping attempts logging:** Track all attempts to map an entity, not just successful ones.
   *   **Create schema for alternative identifier mapping:** Support storing outdated/merged ID relationships.

**Deferred Steps (Post-Enhanced Framework):**

*   Implement `UMLSClient` for text-based entity mapping.
*   Configure `metamapper.db` for metabolite endpoints and mapping paths.
*   Implement metabolite mapping use cases.
*   Integrate RAG component as a final fallback strategy.
*   Implement more advanced client adapters to standardize interaction.

## 5. Open Questions & Considerations

*   How should we define and calculate confidence scores for different mapping paths?
*   What is the optimal strategy for determining when to try reversed mapping (target → source) vs. continuing with alternative source → target paths?
*   How can we best represent and store the provenance of multi-step mappings in a way that's both efficient and queryable?
*   How should we handle conflicts when multiple mapping paths produce different results for the same entity?
*   What level of automation vs. manual review should be supported for mappings with low confidence scores?
*   _(Deferred)_ What are the rate limits and authentication requirements for the UMLS UTS API?
*   _(Deferred)_ What is the specific interface/input/output for the RAG component?

### Future Considerations

*   **Generalize Identifier Handling:** The current approach handles composite (e.g., `GENE1_GENE2`) and potentially outdated identifiers within specific clients (`UniProtNameClient`). This pattern is common across entity types and resources. Future work should generalize this handling (e.g., via pre-processors, resolver resources, or middleware) to improve reusability and maintainability across Biomapper.

*   **Intermediary Ontology Mapping Layer:** Develop a systematic approach to document and track all attempted mappings between ontological identifiers, with confidence scores and detailed provenance. This layer would sit between the top-level metamapping (e.g., UKBB->Arivale) and the base-level entity mapping, providing a rich, queryable record of mapping attempts and outcomes.

*   **Unified Mapping Strategy:** Implement a system where direct mappings (highest confidence) are attempted first, followed by progressively more indirect or approximate methods, with clear documentation of the mapping path, number of hops, and confidence scores. This provides both deterministic success metrics and rich diagnostic information.

---

## Status Summary (As of 2025-04-30)

*   **UKBB->Arivale Basic Protein Mapping:** **Completed**
*   **`UniProtNameClient`:** **Implemented**
*   **`MappingExecutor` Basic Refactoring:** **Completed**
*   **Bidirectional Mapping Support:** **Completed**
*   **Enhanced Metadata Tracking:** **Completed**
*   **Multiple Path Strategy:** Pending
*   **ID Normalization Support:** Pending
*   **Comprehensive Reporting:** Pending
*   **`UMLSClient` Implementation:** **Deferred**
*   **Metabolite Mapping:** **Deferred**
*   **RAG Integration:** **Deferred**

- **Tasks:**
  - Fix immediate technical issues:
    - **NULL constraint in PathExecutionLog**: **Completed**
    - **Move PathLogMappingAssociation to cache_models.py**: Pending
    - **Implement confidence scoring system**: **Completed**
  - Enhance database schema:
    - **Extend EntityMapping with metadata fields**: **Completed**
    - **Add mapping attempts tracking**: **Completed**
    - **Create schema for alternative IDs**: Pending
  - Implement core bidirectional mapping:
    - **Bidirectional path finding**: **Completed**
    - **Alternative path strategy**: Pending
    - **Comprehensive reporting**: **Completed**
