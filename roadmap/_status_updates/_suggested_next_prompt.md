## Context Brief:

We have successfully aligned the `/home/ubuntu/biomapper/configs/protein_config.yaml` file with the iterative mapping strategy. This involved adding new ontologies, refining property mappings, configuring secondary conversion clients, implementing ontology preferences, and updating mapping paths. The `/home/ubuntu/biomapper/scripts/populate_metamapper_db.py` script successfully parsed this updated configuration and populated the `metamapper.db`, validating the structural and referential integrity of our protein setup.

## Initial Steps:

1.  Please begin by reviewing the overall project context and goals outlined in `/home/ubuntu/biomapper/CLAUDE.md`.
2.  Familiarize yourself with the current state of the protein configuration by briefly reviewing `/home/ubuntu/biomapper/configs/protein_config.yaml`.

## Work Priorities:

1.  **Test Protein Mapping Execution:**
    *   The primary goal is to test the `MappingExecutor` using the newly configured protein data.
    *   Focus on executing mappings between different protein sources defined in `/home/ubuntu/biomapper/configs/protein_config.yaml` (e.g., Arivale to UKBB, UKBB to HPP).
    *   Pay close attention to whether the `MappingExecutor` correctly utilizes the `ontology_preferences` and the newly added secondary conversion clients (e.g., `ensembl_protein_to_uniprot`, `uniprot_name_search`).
2.  **Detail Function Health Configuration:**
    *   Revisit the Function Health section within `/home/ubuntu/biomapper/configs/protein_config.yaml`.
    *   Define more detailed property mappings.
    *   Determine if any specific placeholder conversion clients are needed for Function Health secondary identifiers and implement them if necessary (this was deferred item D).
3.  **Initiate Metabolite Configuration:**
    *   Begin planning for the next entity type by creating `/home/ubuntu/biomapper/configs/metabolite_config.yaml`.
    *   Start by defining the basic structure: `entity_type`, `version`, and an initial list of `ontologies` relevant to metabolites.

## References:

-   `/home/ubuntu/biomapper/configs/protein_config.yaml` (Current protein configuration)
-   `/home/ubuntu/biomapper/scripts/populate_metamapper_db.py` (For understanding how config is loaded)
-   `/home/ubuntu/biomapper/biomapper/core/mapping_executor.py` (The mapping engine to be tested)
-   `/home/ubuntu/biomapper/roadmap/technical_notes/core_mapping_logic/iterative_mapping_strategy.md` (For context on expected mapping behavior)

## Workflow Integration (Claude Assistance):

-   **Test Case Design:** Consider asking Claude to help design specific test cases for protein mapping. For example: "Given the `protein_config.yaml` and `iterative_mapping_strategy.md`, propose 3 distinct test scenarios to validate the `MappingExecutor`'s handling of primary mappings, secondary identifier conversions using `ontology_preferences`, and multi-step paths. Specify input IDs, expected intermediate steps, and final outcomes."
-   **Metabolite Configuration Draft:** You can ask Claude to help draft the initial structure or specific sections of `/home/ubuntu/biomapper/configs/metabolite_config.yaml` once you have gathered preliminary information about metabolite data sources and identifiers. For example: "Based on common metabolite databases (e.g., HMDB, KEGG) and typical identifiers (e.g., HMDB ID, KEGG ID, ChEBI ID, PubChem CID, SMILES, InChIKey), draft an `ontologies` section and a basic `databases` entry for HMDB for a `metabolite_config.yaml` file."