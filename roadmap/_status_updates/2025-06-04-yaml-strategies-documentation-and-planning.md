# Status Update: YAML-Defined Mapping Strategies - Documentation and Planning

## 1. Recent Accomplishments (In Recent Memory)

- **Clarified and Documented YAML-Defined Mapping Strategies:**
    - Created a new detailed technical note: `/home/ubuntu/biomapper/roadmap/technical_notes/core_mapping_logic/yaml_defined_mapping_strategies.md`. This document defines explicit, ordered mapping pipelines using YAML, where each step has an `action.type` and parameters, corresponding to Python handler modules. It clarifies the relationship between YAML-defined strategies, the default iterative strategy, and bidirectional reconciliation.
    - Updated related documentation (`/home/ubuntu/biomapper/configs/README.md`, `/home/ubuntu/biomapper/roadmap/technical_notes/core_mapping_logic/iterative_mapping_strategy_protein.md`, `/home/ubuntu/biomapper/roadmap/technical_notes/core_mapping_logic/iterative_mapping_strategy.md`, `/home/ubuntu/biomapper/roadmap/technical_notes/phase3_reconciliation/bidirectional_validation_with_secondary_identifiers.md`, `/home/ubuntu/biomapper/roadmap/technical_notes/core_mapping_logic/live_document.md`) to ensure consistency and cross-referencing of the new YAML-defined strategy approach.
- **Created Guide for UKBB/HPA/QIN Protein Mapping Configuration:**
    - Developed a new guide document: `/home/ubuntu/biomapper/roadmap/guides/configuring_ukbb_hpa_qin_mapping.md`. This guide provides specific instructions on configuring `protein_config.yaml` and defining `mapping_strategies` for these "UniProt-complete" datasets, emphasizing mandatory UniProt API resolution.
- **Foundational Work (Context from previous status updates & memory):**
    - Successfully aligned `/home/ubuntu/biomapper/configs/protein_config.yaml` with the iterative mapping strategy and validated its parsing and population into `metamapper.db` via `/home/ubuntu/biomapper/scripts/populate_metamapper_db.py` (as per `/home/ubuntu/biomapper/roadmap/_status_updates/2025-06-03-protein-config-alignment.md`).
    - Pivoted project strategy to focus on YAML-based configuration per entity type, with `/home/ubuntu/biomapper/scripts/populate_metamapper_db.py` as the central parser (as per `/home/ubuntu/biomapper/roadmap/_status_updates/2025-06-02-extensibility-review-and-strategy-pivot.md`).
    - Resolved critical performance issues in `MappingExecutor` via client caching (as per `/home/ubuntu/biomapper/roadmap/_status_updates/2025-05-30-session-recap-and-roadmap-update.md`).

## 2. Current Project State

- **Overall:** Biomapper is advancing towards a highly configurable mapping system. The foundational YAML-based configuration for individual resources (clients, paths) is in place and validated for proteins. The project is now defining a higher-level YAML-based *strategy* execution layer that leverages these configurations.
- **Mapping Strategy Definition:**
    - The conceptual framework for YAML-defined mapping strategies is well-documented.
    - A specific guide for applying these strategies to UKBB, HPA, and QIN protein datasets has been created.
- **Configuration Management (`protein_config.yaml`, `populate_metamapper_db.py`):**
    - `/home/ubuntu/biomapper/configs/protein_config.yaml` is the current source of truth for protein data source definitions, clients, and basic mapping paths.
    - `/home/ubuntu/biomapper/scripts/populate_metamapper_db.py` is functional for parsing these entity-specific YAMLs and needs to be updated to parse the new `mapping_strategies` section.
- **`MappingExecutor`:**
    - Currently supports iterative mapping based on `metamapper.db` configurations.
    - Needs enhancement to parse and execute the new YAML-defined `mapping_strategies`.
- **Documentation:** Key architectural documents for mapping strategies and specific dataset configurations are now up-to-date or newly created.
- **Outstanding Critical Issues/Blockers:**
    - Implementation of the `MappingExecutor`'s capability to understand and run YAML-defined strategies.
    - Development of the Python handler modules for the defined `action.type`s (e.g., `CONVERT_IDENTIFIERS_LOCAL`, `EXECUTE_MAPPING_PATH`).

## 3. Technical Context

- **Architectural Decision (Mapping Strategies):** Explicit, multi-step mapping strategies will be defined in YAML within the entity configuration files (e.g., `protein_config.yaml` under a `mapping_strategies` key). Each step specifies an `action.type` and parameters.
- **Architectural Decision (Action Handlers):** `action.type` strings in YAML strategies will map to dedicated Python handler modules/functions that `MappingExecutor` will dispatch to. This promotes modularity and extensibility for strategy steps.
- **Relationship to Iterative Mapping:** YAML-defined strategies provide an explicit alternative to the default iterative mapping for unidirectional mapping. Both can feed into a separate bidirectional reconciliation phase.
- **Key Data Structures:**
    - YAML schema for `mapping_strategies` (list of steps, each with `step_id`, `description`, `action.type`, and action-specific parameters).
    - (Anticipated) Python classes/interfaces for action handlers.
- **Core Components to Leverage/Extend:**
    - `MappingExecutor`: Needs to be extended to load strategy definitions and execute their steps sequentially, managing data flow between steps.
    - Existing client infrastructure (e.g., `UniProtHistoricalResolverClient`) will be invoked by specific `action.type` handlers (e.g., via `EXECUTE_MAPPING_PATH`).

## 4. Next Steps

- **Implement `MappingExecutor` Enhancements for YAML Strategies:**
    - Add logic to `MappingExecutor` to load and parse `mapping_strategies` from the configuration (likely from `metamapper.db` after `populate_metamapper_db.py` is updated to handle this new YAML section).
    - Implement the dispatch mechanism to route `action.type`s to their respective Python handlers.
    - Define how data (e.g., lists of identifiers) is passed and transformed between strategy steps.
- **Develop Initial Python Action Handler Modules:**
    - Implement handlers for core `action.type`s identified, such as:
        - `CONVERT_IDENTIFIERS_LOCAL` (leveraging existing endpoint property data).
        - `EXECUTE_MAPPING_PATH` (invoking pre-defined mapping paths from `metamapper.db`).
        - `FILTER_IDENTIFIERS_BY_TARGET_PRESENCE` (checking identifier existence in a target endpoint).
- **Augment `protein_config.yaml` with a Test Strategy:**
    - Add a concrete `mapping_strategy` (e.g., HPA to UKBB as outlined in `/home/ubuntu/biomapper/roadmap/guides/configuring_ukbb_hpa_qin_mapping.md`) to `/home/ubuntu/biomapper/configs/protein_config.yaml`.
    - Update `/home/ubuntu/biomapper/scripts/populate_metamapper_db.py` to parse and store this `mapping_strategies` section in `metamapper.db`.
- **Develop Integration Tests for YAML Strategies:**
    - Create tests that execute a full YAML-defined strategy via `MappingExecutor` and verify the output.
- **Address Low Mapping Success Rate (MEMORY[140ad7b0-e133-4771-a738-07e4b4926be6]):** Once the strategy execution framework is in place, apply it to investigate and improve the low mapping success rates, particularly for UKBB data, by ensuring robust UniProt resolution and correct handling of gene names/IDs.

## 5. Open Questions & Considerations

- **Data Flow and State Management within Strategies:** How will intermediate results, provenance, and potential errors be managed as data flows through the steps of a YAML-defined strategy?
- **Parameterization of `action.type` Handlers:** Finalize the exact parameters each action handler will require from the YAML and how they are passed.
- **Error Handling and Reporting for Strategies:** How should errors within a strategy step be handled? Should they halt the entire strategy or allow for fallback paths? How are errors reported to the user?
- **Schema Validation for `mapping_strategies` YAML:** Implement validation for the `mapping_strategies` section within `populate_metamapper_db.py` or as Pydantic models.
- **Reusability and Composition of Strategies:** Can strategies call other strategies, or can common sequences of steps be abstracted into reusable components? (Future consideration).
- **Impact on Bidirectional Reconciliation:** How will the outputs of YAML-defined strategies be formatted to seamlessly feed into the existing bidirectional reconciliation process?
