# Biomapper Database Configuration

This document outlines the structure and purpose of the two primary SQLite databases used by the Biomapper project.

## 1. `metamapper.db` (Configuration Database)

*   **Purpose:** Stores the core, relatively static configuration of mapping resources, endpoints, and potential pathways.
*   **Management:** Populated and managed primarily by the `scripts/populate_metamapper_db.py` script.
*   **Models:** Defined in `biomapper/db/models.py`.
*   **Alembic:** Currently *not* managed by the main Alembic configuration (`biomapper/db/migrations/`). Schema changes would require manual updates to the population script or a separate, dedicated Alembic setup.

**Tables:**
+    -   `Endpoints`: Defines data sources/targets (e.g., UKBB_Protein, Arivale_Chemistry).
+    -   `MappingResources`: Defines tools/databases used for mapping (e.g., UniChem, UMLS, PubChemRAG).
+    -   `MappingPaths`: Defines reusable, multi-step mapping sequences between ontology types (e.g., `CHEBI` -> `PUBCHEM` -> `INCHIKEY`).
+    -   `EndpointRelationships`: Defines specific connections between two Endpoints that require mapping (e.g., `UKBB_Protein` -> `SPOKE_Protein`).
+    -   `OntologyPreferences`: Defines preferred target ontology types for specific `EndpointRelationships`.
+    -   `PropertyExtractionConfig`: Configuration for extracting specific properties/attributes from `MappingResources`.
+    -   `EndpointPropertyConfig`: Configuration for extracting specific properties/attributes directly from `Endpoints`.
+    -   `OntologyCoverage`: Documents which `MappingResources` can handle transitions between specific ontology types.
+    -   `RelationshipMappingPath`: Links an `EndpointRelationship` to a specific `MappingPath` for a given source/target ontology pair. This represents a concrete, configured way to attempt a mapping for that relationship.
+    -   `EntityTypeConfig`: Defines configuration parameters (e.g., TTL, confidence threshold) specific to pairs of source/target entity types.
+    -   `CacheStats`: Stores aggregated statistics about the usage and performance of the mapping cache.
+    -   `TransitiveJobLog`: Logs the execution details and outcomes of background jobs responsible for building transitive relationships.

## 2. `mapping_cache.db` (Runtime/Cache Database)

*   **Purpose:** Stores dynamic data generated during mapping operations, including results, provenance, and logs. This data can potentially be cleared or expire without affecting core configuration.
*   **Management:** Schema is managed by **Alembic** using the configuration defined in `alembic.ini` and the migration scripts located in `biomapper/db/migrations/`.
*   **Models:** Defined in `biomapper/db/cache_models.py`.

**Tables:**
    -   `EntityMapping`: Stores the actual mapping results discovered between specific source and target entities (e.g., mapping `UKBB_Protein_X` to `SPOKE_Protein_Y`). Includes source/target IDs and types, confidence, source, etc.
    -   `MappingMetadata`: Key-value store for additional metadata associated with a specific `EntityMapping`.
    -   `EntityMappingProvenance`: Logs how a specific `EntityMapping` was generated. Critically, it links `EntityMapping.id` back to the `RelationshipMappingPath.id` (from `metamapper.db`) that was used to create it. Also includes timestamp and potentially executor version.
    -   `PathExecutionLog`: Records details about the execution attempt of a specific `RelationshipMappingPath` for a source entity. Includes start/end times, status (success, failure), and potential error messages. (Note: There might be overlap with `EntityMappingProvenance`; structure may be refined).
    -   `MappingPathHistory` (Placeholder): Intended for tracking historical performance/usage statistics for specific `MappingPath`s.
    -   `PerformanceMetric` (Placeholder): Intended for storing aggregated performance metrics for `MappingResource`s or `MappingPath`s.

## 3. Key Changes & Decisions (as of 2025-04-27)

*   **Separation:** The configuration (`metamapper.db`) and runtime cache (`mapping_cache.db`) are distinct databases with separate model definitions (`models.py` vs `cache_models.py`) and management strategies (script vs. Alembic).
*   **Provenance Link:** `RelationshipMappingPath` remains in `metamapper.db` as it's part of the *configuration*. The link between a *runtime result* (`EntityMapping` in `mapping_cache.db`) and the *configuration used* is established via the `EntityMappingProvenance` table in `mapping_cache.db`, which stores the relevant `RelationshipMappingPath.id`.
*   **Model Migration:** `EntityMapping` and `MappingMetadata` were moved from `models.py` to `cache_models.py` to be managed by Alembic as part of `mapping_cache.db`.
*   **Alembic Dedication:** The Alembic setup in `biomapper/db/migrations/` is now solely responsible for `mapping_cache.db`.