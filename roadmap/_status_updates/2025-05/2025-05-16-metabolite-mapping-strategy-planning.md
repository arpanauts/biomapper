# Biomapper Status Update: Metabolite Mapping Strategy & Implementation Planning (May 16, 2025)

## 1. Recent Accomplishments (In Recent Memory)

* **Generalized Iterative Mapping Strategy:**
  * Updated `/home/ubuntu/biomapper/roadmap/technical_notes/core_mapping_logic/iterative_mapping_strategy.md` to support multiple entity types
  * Added metabolite-specific examples and ontology types alongside protein examples
  * Ensured consistent terminology for mapping validation statuses ("Validated" vs "Successful")

* **UKBB-Arivale Metabolite Mapping Plan:**
  * Developed comprehensive planning documentation in `/home/ubuntu/biomapper/roadmap/1_planning/ukbb_arivale_metabolite_mapping/`
  * Created entity-specific mapping scripts design with clear separation of concerns
  * Designed tiered fallback architecture with UniChem as primary and Name Resolver/UMLS/RAG as secondary approaches
  * Developed confidence scoring framework for reconciling results from multiple mapping sources

* **Validation Terminology Standardization:**
  * Established consistent validation status terminology across documentation
  * Identified instances of terminology misalignment in codebase (UnidirectionalSuccess vs. Successful)
  * Created implementation task to update terminology throughout the codebase

* **Documentation Improvements:**
  * Enhanced status update process to incorporate historical context while prioritizing recent progress
  * Updated `/home/ubuntu/biomapper/roadmap/_status_updates/_status_offboarding.md` instructions

## 2. Current Project State

* **Overall:** The project is transitioning from protein-focused mapping to a generalized entity mapping framework, with metabolites as the next entity type for implementation.

* **Component Status:**
  * **Iterative Mapping Strategy:** Fully generalized for multi-entity support in documentation, with implementation updates planned
  * **Phase 1/2/3 Pipeline:** Functional for proteins; requires entity-specific scripts for metabolites
  * **Fallback Mechanisms:** Designed but not yet implemented; identified clients to develop
  * **Confidence Scoring:** Design complete with detailed multi-factor approach; implementation pending

* **Key Statistics & Metrics:**
  * Current protein mapping success rate remains at 0.2-0.5%, highlighting the need for improved approaches
  * Initial metabolite mapping is expected to achieve ~30% with primary approach, 50%+ with fallbacks

* **Known Issues:**
  * The `is_one_to_many_target` flag bug in `phase3_bidirectional_reconciliation.py` remains to be fixed
  * Terminology inconsistencies between documentation ("Successful") and code ("UnidirectionalSuccess")
  * No existing client implementations for metabolite-specific fallback mechanisms

## 3. Technical Context

* **Entity-Agnostic Design Philosophy:**
  * Confirmed viability of applying the same iterative mapping strategy across entity types
  * Identified specific aspects requiring entity-specific handling (client interfaces, identifier formats)
  * Established approach of dedicated entity-specific scripts rather than conditional logic

* **Fallback Mechanism Design:**
  * Prioritized fallback approaches: UniChem > Translator Name Resolver > UMLS > RAG
  * Designed `FallbackOrchestrator` class to coordinate multiple approaches
  * Developed confidence scoring system to integrate results from various sources

* **Multi-Entity Architecture Decisions:**
  * Chose script-level separation of concerns over single multi-entity scripts
  * Committed to eventual migration of hard-coded configurations to `populate_metamapper.db.py`
  * Designed for common interfaces to standardize client behaviors across entity types

* **Validation Framework:**
  * Established terminology standard: "Validated" only for bidirectional exact matches
  * "Successful" for one-directional mappings (forward or reverse only)
  * "Conflict" and "Unmapped" statuses for problematic or failed mapping attempts

## 4. Next Steps

* **Priorities for Coming Week:**
  * **Phase 1: Core Infrastructure**
    * Fix `is_one_to_many_target` flag bug in `phase3_bidirectional_reconciliation.py`
    * Update validation terminology across codebase for consistency
    * Implement confidence scoring system
    * Enhance output format for tiered results
  
  * **Phase 2: Metabolite Client Development**
    * Implement `UniChemClient` for primary metabolite mapping
    * Implement `TranslatorNameResolverClient` for name resolution
    * Implement `UMLSClient` for concept mapping
    * Create unit tests for each client
  
  * **Phase 3: Script Development**
    * Create dedicated scripts for metabolite mapping:
      * `/home/ubuntu/biomapper/scripts/map_ukbb_metabolites_to_arivale_metabolites.py`
      * `/home/ubuntu/biomapper/scripts/map_ukbb_metabolites_to_arivale_clinlabs.py`

* **Longer-Term Tasks:**
  * Implement RAG-based approach with Qdrant/FastEmbed
  * Integrate fallback results with primary mapping pipeline
  * End-to-end testing with metabolite datasets
  * Performance optimization for large datasets

## 5. Open Questions & Considerations

* **Confidence Score Calibration:** How should we calibrate the multi-factor confidence scores for metabolites? Will the weights used for proteins be appropriate, or do we need entity-specific tuning?

* **Fallback Priority Refinement:** Should we dynamically adjust the priority of fallback mechanisms based on the entity type or specific identifier formats encountered?

* **Vector Database Population:** What's the optimal approach for populating the Qdrant/FastEmbed vector database for the RAG-based fallback? Should we use public metabolite databases, Arivale-specific data, or a combination?

* **Metabolite Metadata Analysis:** We need to analyze the actual structure and content of the metabolite data files to confirm our assumptions about available columns and identifier formats.

* **Output Representation:** How should we represent confidence levels and provenance in the output files? Are additional visualization tools needed to help interpret complex multi-source mapping results?

* **Canonical Selection Strategy:** When multiple valid mappings exist with similar confidence scores, what additional criteria should influence canonical mapping selection for metabolites?

This status update builds on the recent mapping strategy reorganization work while focusing on the specific UKBB-Arivale metabolite mapping planning and implementation approach.
