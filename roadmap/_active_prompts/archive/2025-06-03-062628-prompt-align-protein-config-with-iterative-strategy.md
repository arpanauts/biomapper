# Task: Align protein_config.yaml with Iterative Mapping Strategy

## Context:
Biomapper employs an `iterative_mapping_strategy.md` (located at `/home/ubuntu/biomapper/roadmap/technical_notes/core_mapping_logic/iterative_mapping_strategy.md`) for its `MappingExecutor`. This strategy aims to maximize mapping success by systematically using primary shared ontologies and converting secondary ontologies.

We have been developing `/home/ubuntu/biomapper/configs/protein_config.yaml` to define ontologies, data sources (endpoints), their properties (available identifier types), mapping clients (atomic lookup capabilities), and explicit mapping paths for protein entities from 6 sources (Arivale, UKBB, HPP, Function Health, SPOKE, KG2).

The goal of this task is to critically review `protein_config.yaml` in light of the `iterative_mapping_strategy.md` and ensure full alignment, identifying any gaps or necessary modifications.

## Source Documents for Review:
1.  **Iterative Mapping Strategy:** `/home/ubuntu/biomapper/roadmap/technical_notes/core_mapping_logic/iterative_mapping_strategy.md`
2.  **Protein Configuration:** `/home/ubuntu/biomapper/configs/protein_config.yaml` (current version)

## Instructions:

1.  **Understand the Iterative Strategy:** Thoroughly review `iterative_mapping_strategy.md` to understand its core concepts:
    *   Role of Primary Shared Ontology.
    *   Direct Primary Mapping (Step 2).
    *   Identification of Unmapped Entities & Secondary Types (Step 3).
    *   Prioritized Iteration for Secondary -> Primary Conversion (Step 4), including the role of `OntologyPreference` for source endpoints.
    *   Re-attempting Primary Mapping with derived IDs (Step 5).
    *   The nature of "atomic mapping paths" versus potentially more complex, named `mapping_paths` in the YAML.

2.  **Analyze `protein_config.yaml`:** Examine the current `protein_config.yaml` focusing on:
    *   Defined `ontologies`.
    *   `databases` section:
        *   `endpoint` definitions.
        *   `properties` subsections (primary and mappings for secondary ontology types, and their extraction details like `column`).
        *   `mapping_clients` (these are the primary candidates for "atomic mapping paths").
    *   `mapping_paths` section (explicitly defined multi-step paths).
    *   `additional_resources` (for clients not tied to a single database).

3.  **Assess Alignment and Identify Gaps:**
    *   **Support for Direct Primary Mapping:** Does `protein_config.yaml` adequately define primary ontology types for each of the 6 protein databases to support Step 2 of the strategy?
    *   **Support for Secondary Types:** For each of the 6 protein databases, does the `properties.mappings` section comprehensively list all relevant secondary identifier types that could be used for conversion to a primary shared type (e.g., UniProtKB AC)?
    *   **Atomic Paths for Conversion:** Are there sufficient `mapping_clients` defined (using `GenericFileLookupClient` or specialized clients) that can act as "atomic mapping paths" to convert these secondary types to the likely primary shared ontology (UniProtKB AC)? Consider all 6 databases.
        *   Example conversions needed: `GENE_NAME` -> `UNIPROTKB_AC`, `ENSEMBL_PROTEIN_ID` -> `UNIPROTKB_AC`, `SPOKE_PROTEIN_ID` -> `UNIPROTKB_AC`, `KG2_PROTEIN_ID` -> `UNIPROTKB_AC`, `FUNCTION_HEALTH_PROTEIN_ID` -> `UNIPROTKB_AC`.
    *   **OntologyPreference:** The strategy document mentions `OntologyPreference` for source endpoints to guide the order of secondary type conversion. Is this concept currently addressed in `protein_config.yaml` or is it expected to be a separate configuration? If not present, how should it be incorporated or referenced?
    *   **Role of Named `mapping_paths`:** Clarify how the `mapping_paths` section in `protein_config.yaml` interacts with the `MappingExecutor`'s iterative logic. Does the executor:
        *   Primarily use these named, potentially multi-step paths?
        *   Or, does it dynamically discover and chain "atomic" client capabilities (from `mapping_clients`) based on input/output ontology types to implement the iterative steps, with the named paths serving as fallbacks or higher-level routes?
        *   Or a combination?

4.  **Propose Modifications/Additions:**
    *   Based on the gap analysis, suggest specific, concrete additions or modifications to `protein_config.yaml`. This might include:
        *   Adding new ontology types if missing.
        *   Expanding the `properties.mappings` for certain databases to include more secondary identifiers.
        *   Defining new `mapping_clients` (atomic paths) for necessary Secondary -> Primary conversions, especially for SPOKE, KG2, and Function Health. Specify their configurations (e.g., placeholder file paths, key/value columns).
        *   Clarifying or suggesting how `OntologyPreference` should be handled.
    *   Consider if the current `GenericFileLookupClient` is sufficient for all anticipated "atomic" lookups, or if new specialized client types might be more appropriate for certain conversions (e.g., if a conversion requires more complex logic than a simple file lookup).

5.  **Consider All 6 Protein Sources:** Ensure the analysis and proposals cover all 6 target databases: Arivale, UKBB, HPP, Function Health, SPOKE, and KG2.

## Expected Output:

A Markdown feedback file named `YYYY-MM-DD-HHMMSS-feedback-align-protein-config-iterative-strategy.md` (use current UTC timestamp) in `/home/ubuntu/biomapper/roadmap/_active_prompts/feedback/` containing:
1.  A summary of how `protein_config.yaml` currently supports the iterative mapping strategy.
2.  A detailed list of identified gaps or areas needing clarification, cross-referencing specific parts of the strategy document and the YAML file.
3.  A clear explanation of the presumed or recommended interaction between the YAML's `mapping_paths` and the `MappingExecutor`'s dynamic pathfinding/iterative logic.
4.  Concrete proposals for additions/modifications to `protein_config.yaml` (or related configurations) to fully support the strategy for all 6 protein sources. Include example YAML snippets for new clients or property mappings where appropriate.
5.  Discussion on the `OntologyPreference` mechanism and how it should be integrated.
