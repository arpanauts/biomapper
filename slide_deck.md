# Project Biomapper: Bridging Biological Data Silos

---

## The Challenge: The Problem of Disparate Biological Identifiers

*   Biological data is vast, diverse, and stored across numerous disconnected databases (e.g., UKBB, HPA, UniProt, Ensembl).
*   Each database often uses its own unique identifiers for the same biological entities (genes, proteins, metabolites).
*   This fragmentation makes data integration, cross-study analysis, and comprehensive biological understanding extremely difficult and error-prone.
*   **Impact:** Hinders research, slows down discovery, and limits the potential of valuable datasets.

---

## Our Solution: Project Biomapper

A centralized, intelligent framework designed to:
*   **Map** identifiers accurately between different biological databases.
*   **Resolve** ambiguities and historical changes in identifiers.
*   **Provide** a consistent, reliable view of biological entities across datasets.

---

## Core Objective

To enable seamless data integration and advanced analytics by providing a robust, scalable, and maintainable solution for mapping biological identifiers across disparate data sources, starting with proteins and metabolites for key projects like UKBB, HPA, and QIN.

---

## Key Complexities & Our Approach (High-Level)

| Complexity                                  | Biomapper's Approach                                        |
| :------------------------------------------ | :---------------------------------------------------------- |
| **Diverse Data Sources & Formats**          | Standardized data ingestion; adaptable client architecture  |
| **Evolving Biological Knowledge**           | Handling of historical IDs; updatable mapping logic         |
| **Ensuring Accuracy & Provenance**          | Confidence scoring; detailed logging of mapping paths       |
| **Scalability & Extensibility**             | Modular design; asynchronous processing; configurable via DSL |

---

## Biomapper's Strategic Pillars

1.  **Centralized Metadata Hub (`metamapper.db`):**
    *   Stores configurations for data sources (Endpoints), ontologies, `MappingResource`s, detailed `MappingPath` definitions (the specific routes for transformation), and `MappingStrategy` definitions (loaded from YAML).
    *   Acts as the single source of truth for how mappings are structured and performed.

2.  **Declarative Mapping Strategies (YAML DSL):**
    *   Complex `MappingStrategy`s are defined in human-readable YAML files.
    *   Each strategy consists of a sequence of steps. Each step specifies an `ActionType` (e.g., convert, filter, fetch, or execute a pre-defined `MappingPath`) and its required parameters.
    *   This allows domain experts to orchestrate mapping workflows without deep coding knowledge for the strategy itself.
    *   Provides flexibility and rapid adaptation to new mapping needs by combining various `ActionType`s and `MappingPath`s.

3.  **Modular & Extensible Architecture:**
    *   Plugin-based system for data clients and action handlers.
    *   Easy to add support for new databases or custom mapping logic.

4.  **Robust Caching & Performance (`mapping_cache.db`):**
    *   Caches previously resolved mappings to accelerate repeated queries.
    *   Optimized for high-throughput operations.

---

## Current Status & Key Milestones Achieved

*   Core database schema (`metamapper.db`, `mapping_cache.db`) established.
*   Initial `MappingExecutor` capable of basic path execution developed.
*   YAML-based Domain Specific Language (DSL) for defining mapping strategies implemented and tested.
    *   Successfully populated `metamapper.db` from `protein_config.yaml`.
    *   Integration test for UKBB-to-HPA protein mapping via YAML strategy is operational.
*   Placeholder action handlers for YAML strategies created; ready for full logic implementation.
*   Refinement of asynchronous resource management in `MappingExecutor`.

---

## Next Steps & Future Vision

*   **Immediate Focus:**
    *   Complete implementation of core action handlers for YAML strategies (identifier conversion, path execution, filtering).
    *   Rigorous testing and validation of the UKBB-to-HPA protein mapping pipeline with real data.
    *   Address and improve current low mapping success rates by refining logic and data handling.
*   **Medium Term:**
    *   Expand to other entity types (e.g., metabolites) and datasets (e.g., QIN).
    *   Develop CLI tools for dynamic metadata retrieval and pipeline configuration.
    *   Enhance `MappingExecutor` with advanced features (iterative mapping, secondary ID lookups).
*   **Long Term Vision:**
    *   Biomapper as a foundational service for enterprise-wide biological data integration.
    *   Support for automated discovery of optimal mapping paths.
    *   Community contributions for new clients and mapping strategies.

---

## Impact & Value Proposition

*   **Accelerated Research:** Enables researchers to ask more complex questions across integrated datasets.
*   **Improved Data Quality & Reliability:** Provides consistent and traceable mappings.
*   **Enhanced Collaboration:** Facilitates data sharing and reuse.
*   **Reduced Manual Effort:** Automates a complex and time-consuming data integration task.
*   **Unlocks New Insights:** By connecting previously siloed information, Biomapper can reveal novel biological relationships.

---

## Q&A / Thank You

**Project Biomapper: Connecting Data, Driving Discovery.**
