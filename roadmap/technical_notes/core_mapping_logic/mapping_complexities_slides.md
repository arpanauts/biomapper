# Biomapper: Navigating Mapping Complexities

---

## Slide 1: Title Slide

*   **Title:** Biomapper: Navigating Mapping Complexities
*   **Subtitle:** Understanding Challenges & Solutions in Biological Entity Identifier Mapping

---

## Slide 2: Introduction - The Challenge of Mapping

*   **Goal:** Accurately link diverse biological identifiers across datasets.
*   **Why it's hard:**
    *   Identifiers change (merge, split, deprecate).
    *   Datasets have unique formats and quality issues.
    *   Different entity types have different identifier landscapes.
*   **Biomapper's Aim:** Provide a robust, configurable, and extensible framework to tackle these.

---

## Slide 3: Key Complexity Areas & Biomapper Solutions

*   UniProt ID Changes (Demergers, Composite IDs)
    *   *Solution: Historical resolution, specialized client logic.*
*   Dataset-Specific Nuances
    *   *Solution: YAML configs, modular clients, provenance.*
*   Entity-Type Specific Challenges
    *   *Solution: Vertical/Horizontal extensibility, tailored configs & actions.*
*   YAML-Defined Strategy Development
    *   *Solution: `MappingExecutor`, clear action contracts, parameterization.*
*   One-to-Many Mappings & Reconciliation
    *   *Solution: Provenance, reconciliation logic (`is_one_to_many_target` flag), (future) configurable rules.*
*   Iterative Mapping Approach Issues
    *   *Solution: Path prioritization, (future) cycle detection, detailed provenance.*

---

## Slide 4: UniProt ID Complexities & Solutions

*   **Demergers (e.g., P0CG05 -> P0DOY2 + P0DOY3):**
    *   Challenge: Ensuring correct mapping to existing demerged entities.
    *   **Biomapper Solution:** `UniProtHistoricalResolverClient` for up-to-date relationships; logic to select/flag relevant demerged targets.
*   **Composite IDs (Arivale - e.g., "P29460,P29459"):**
    *   Challenge: Splitting and mapping individual components.
    *   **Biomapper Solution:** Modifying Arivale clients to parse composite strings; configurable strategies for handling multiple resulting IDs (e.g., map all, map first).

---

## Slide 5: Dataset-Specific Parameters & Solutions

*   **Challenges:** Unique identifier systems, data formats, "UniProt-Completeness" variations, data quality, update cadences.
*   **Biomapper Solutions:**
    *   **Flexible Configuration (DSL):** `*_config.yaml` files, especially `mapping_strategies`, act as a Domain-Specific Language (DSL) to define native IDs, ontologies, data characteristics, and multi-step mapping pipelines declaratively.
    *   **Specialized Clients:** Custom client implementations (e.g., `ArivaleMetadataLookupClient`, file parsers) handle specific data sources/formats, callable via the DSL.
    *   **Historical Resolution:** Mandatory for "UniProt-complete" datasets (e.g., via `UniProtHistoricalResolverClient`), integrated as actions within the DSL.
    *   **Provenance:** Tracking data versions used in mappings, with strategy steps defined in the DSL providing context.
    *   *(Awareness of upstream data quality informs DSL-defined strategies and potential for custom pre-processing actions).*

---

## Slide 6: Entity-Type Specific Complexities & Solutions

*   **Challenges:** Proteins (lifecycle, history), Metabolites (fragmented IDs, chemistry), Genes (nomenclatures), Clinical (terminologies).
*   **Biomapper Solutions (Extensibility via DSL):**
    *   **Vertical (Deeper features per entity):**
        *   Developing sophisticated `action.type`s (new DSL vocabulary) for YAML strategies.
        *   Specialized clients, callable as actions within the DSL.
        *   Deeper integration with resources, exposed as DSL actions.
    *   **Horizontal (Adding new entity types):**
        *   New `*_config.yaml` files define the DSL scope for that entity.
        *   New ontology definitions and client implementations become part of the DSL's toolkit for that entity.
        *   New `action.type`s (DSL commands) tailored to the entity's specific mapping challenges.

---

## Slide 7: Developing Action Types (DSL Components) for YAML Strategies

*   Modular `action.type` handlers are the building blocks (verbs) of our YAML-based DSL.
*   **Challenges & Biomapper Solutions in DSL Component Development:**
    *   **Granularity (DSL Command Scope):** Reusable (e.g., `CONVERT_IDENTIFIERS_LOCAL`).
        *   *Solution: Design principles for balanced action scope, creating meaningful DSL commands.*
    *   **Interface Definition (DSL Command Syntax):** Clear contract for inputs/outputs.
        *   *Solution: Standardized parameter passing (DSL arguments) and return structures.*
    *   **State Management:** `MappingExecutor` (DSL interpreter) manages data flow.
        *   *Solution: Action handlers (DSL command implementations) are largely stateless.*
    *   **Parameterization (DSL Command Flexibility):** Configurable via YAML.
        *   *Solution: Actions accept parameters from YAML, making DSL commands adaptable.*
    *   **Error Handling:** Robustness within each action.
        *   *Solution: Defined error logging/exception handling for DSL command execution.*
    *   **Testing & Discovery:** Unit-testable; `MappingExecutor` dispatches to handlers.
        *   *Solution: Unit tests for each DSL command; registration in the DSL interpreter (`MappingExecutor`).*

---

## Slide 8: One-to-Many Mappings & Unidirectional Solutions

*   **Challenge:** A single source ID maps to multiple target IDs (due to biology, aggregation, ambiguity).
*   **Impact on Unidirectional YAML Strategies:**
    *   Handling multiple results from an action step.
    *   Ensuring clear provenance for each sub-mapping.
*   **Biomapper Solutions (Unidirectional):**
    *   **Data Flow:** YAML strategies and `action.type`s designed to receive and pass lists of identifiers, naturally handling growth in ID sets from 1-to-many steps.
    *   **Provenance:** Detailed logging at each step of the YAML strategy, tracing which input ID led to which set of output IDs.

---

## Slide 9: Bidirectional Reconciliation with 1-to-Many & Solutions

*   **Challenges:**
    *   **Symmetry Breaking:** If A -> B1, B2 and B1 -> A, but B2 -> A, C. Which is canonical?
    *   **Defining "True" Match:** Complex when one or both sides are 1-to-many.
    *   **Canonical Representative Selection:** Often need a single "best" match.
*   **Biomapper Solutions:**
    *   **Core Logic:** `phase3_bidirectional_reconciliation.py` implements the fundamental comparison.
    *   **Flagging:** `is_one_to_many_target` flag (and similar for source) informs reconciliation logic about the nature of the mappings being compared.
    *   **(Future) Configurable Rules:** Plans for scoring mechanisms or rule-sets (e.g., prefer direct matches, evidence-based scoring) to select canonical representatives when ambiguity exists.

---

## Slide 10: Complexities in Generalized Iterative Mapping & Solutions

*   The default iterative approach is powerful but has inherent challenges.
*   **Challenges & Biomapper Solutions:**
    *   **Path Explosion:** Too many routes without pruning.
        *   *Solution: `priority` in `mapping_paths` config to guide path selection; (Future) more advanced pruning.*
    *   **Cycle Detection:** A -> B -> C -> A needs handling.
        *   *Solution: (Future/Implicit) Iteration depth limits or explicit cycle detection in `MappingExecutor`.*
    *   **Optimal Path Selection:** "Best" path hard to determine globally.
        *   *Solution: Relies on `priority` settings; (Future) path scoring based on reliability/evidence.*
    *   **Provenance Tracking:** Complex for deep iterations.
        *   *Solution: `MappingResult.mapping_path_details` captures the sequence of client calls and intermediate IDs.*
    *   **Error Propagation & Scalability:**
        *   *Solution: Client-level caching; careful error handling in clients to prevent cascading failures.*

---

## Slide 11: Summary - Biomapper's Comprehensive Approach

*   Mapping is inherently complex, but Biomapper tackles these challenges systematically.
*   **Key Strategies:**
    *   **Domain-Specific Language (DSL):** YAML configurations (`*_config.yaml`, `mapping_strategies.yaml`) provide a high-level, declarative DSL for defining mapping pipelines, abstracting Python complexity.
    *   **Modular Architecture:** Extensible clients and `action.type`s (DSL components) for diverse needs.
    *   **Explicit Strategies via DSL:** YAML-defined mapping strategies allow clear, multi-step process definition using the DSL.
    *   **Robust Reconciliation:** Logic to handle one-to-many mappings, informed by DSL-defined strategy outputs.
    *   **Refined Iteration:** Path prioritization (configurable in DSL) and detailed provenance for iterative mapping.
    *   **Continuous Improvement:** Ongoing development to enhance DSL capabilities and address new complexities.

---

## Slide 12: Q&A / Discussion

