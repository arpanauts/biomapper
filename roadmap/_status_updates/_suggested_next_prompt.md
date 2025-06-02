## Context Brief
Biomapper has pivoted to a focused strategy: achieving functional mappings for 6 specific entity types across 6 databases, starting with proteins. This involves a new YAML-based configuration system where entity-specific YAML files will define data sources, clients, and paths, to be parsed by an enhanced `populate_metamapper_db.py` into a single `metamapper.db`. This decision followed an extensive extensibility review.

## Initial Steps
1.  Review the overall project context and goals in `/home/ubuntu/biomapper/CLAUDE.md`.
2.  Thoroughly review the new focused strategy and protein mapping plan detailed in the AI feedback: `/home/ubuntu/biomapper/roadmap/_active_prompts/feedback/2025-06-02-224317-focused-strategy-review.md`.
3.  Review the latest full status update, which captures this strategic shift: `/home/ubuntu/biomapper/roadmap/_status_updates/2025-06-02-extensibility-review-and-strategy-pivot.md`.

## Work Priorities
1.  **Implement YAML-based Configuration System (Proteins First):**
    *   **Define YAML Schema:** Finalize the structure for `protein_config.yaml` (and other entity types) based on Claude's feedback (Section 3.2 of the strategy review).
    *   **Refactor `populate_metamapper_db.py`:**
        *   Implement discovery and parsing of `configs/*.yaml` files.
        *   Develop the translation logic from YAML to SQLAlchemy models.
        *   Integrate a `ConfigurationValidator` to check YAML data integrity (file paths, references).
    *   **Create Initial Protein Config:** Populate `configs/protein_config.yaml` for Arivale and UKBB protein data as the first test case.
    *   **Environment Variables:** Ensure `${DATA_DIR}` (or similar) in YAML file paths is correctly resolved.
2.  **Develop/Verify Protein Mapping Clients & Paths:**
    *   Configure and test existing/new file lookup clients (e.g., `ArivaleMetadataLookupClient`, `GenericProteinFileLookupClient`) using the new YAML system.
    *   Define initial mapping paths for protein-to-protein mappings in the YAML.
3.  **Test End-to-End Protein Mapping:**
    *   Once `populate_metamapper_db.py` processes the protein YAML, execute test mappings (e.g., Arivale Protein to UKBB Protein) using `MappingExecutor`.

## References
-   Key Feedback Document: `/home/ubuntu/biomapper/roadmap/_active_prompts/feedback/2025-06-02-224317-focused-strategy-review.md`
-   Script to be refactored: `/home/ubuntu/biomapper/scripts/populate_metamapper_db.py`
-   Core mapping engine: `/home/ubuntu/biomapper/biomapper/core/mapping_executor.py`
-   Previous extensibility discussions: `/home/ubuntu/biomapper/docs/technical/2025-06-02-193000-mapping-workflow-analysis.md`

## Workflow Integration
Given the plan for parallel Claude instances:
-   **Task Allocation Suggestion:** One Claude instance could focus on drafting the detailed `protein_config.yaml` content (data gathering for all 6 protein sources, structuring it per the schema). Another could focus on the Python code for refactoring `populate_metamapper_db.py` (YAML parsing, validation, DB population logic).
-   **Claude Prompt for YAML Content Generation (Example for one instance):**
    ```markdown
    # Task: Populate protein_config.yaml for Biomapper

    ## Context:
    Biomapper is implementing a YAML-based configuration system. Your task is to generate the content for `configs/protein_config.yaml`.
    Refer to the proposed YAML structure in `/home/ubuntu/biomapper/roadmap/_active_prompts/feedback/2025-06-02-224317-focused-strategy-review.md` (Section 3.2, Protein Configuration example).
    You need to define configurations for protein data from 6 sources: Arivale, UKBB, Human Phenome Project, Function Health, SPOKE (flat file), KG2 (flat file).

    ## Instructions:
    1.  **Gather Information:** For each of the 6 databases, determine/assume realistic details for:
        *   File paths (use `${DATA_DIR}/<path_to_file>`).
        *   Primary protein identifiers used in each dataset.
        *   Column names for these primary IDs and any secondary/cross-reference IDs (e.g., UniProt ACs, Gene Names, Ensembl IDs).
        *   Relevant `MappingResource` (client) configurations (assume file-based lookups for now, similar to `ArivaleMetadataLookupClient`).
    2.  **Structure the YAML:** Follow the schema: `entity_type`, `version`, `ontologies` (primary, secondary), `databases` (with `endpoint`, `properties`, `mapping_clients` for each of the 6 sources), `mapping_paths` (define a few key protein-to-protein paths, e.g., Arivale_Protein -> UniProt -> UKBB_Protein).
    3.  **Output:** Provide the complete content for `protein_config.yaml`.
    ```
-   **Claude Prompt for `populate_metamapper_db.py` Refactoring (Example for another instance):**
    ```markdown
    # Task: Refactor populate_metamapper_db.py for YAML Configuration

    ## Context:
    Biomapper is moving to a YAML-based configuration system. `/home/ubuntu/biomapper/scripts/populate_metamapper_db.py` needs to be refactored to read entity configurations from YAML files (e.g., `configs/protein_config.yaml`, `configs/metabolite_config.yaml`) and populate the `metamapper.db`.
    Refer to the proposed refactoring strategy in `/home/ubuntu/biomapper/roadmap/_active_prompts/feedback/2025-06-02-224317-focused-strategy-review.md` (Section 3.3, Single Database with YAML, and Section 4, Phase 3, Step 6).

    ## Instructions:
    1.  **YAML Parsing:** Implement logic to find and parse all `*.yaml` files in a `configs/` directory.
    2.  **Modular Population:** Create functions like `populate_entity_type(session, entity_config_dict)` which then call sub-functions `populate_ontologies`, `populate_endpoints`, `populate_mapping_resources`, `populate_mapping_paths` based on the parsed YAML dictionary.
    3.  **Validation:** Design and implement a `ConfigurationValidator` class/module. This should:
        *   Validate required fields in the YAML.
        *   Check that specified file paths (e.g., in client configs) exist (after resolving environment variables like `${DATA_DIR}`).
        *   Validate consistency of internal references (e.g., ontology types used in mappings exist in the `ontologies` section).
    4.  **Environment Variable Resolution:** Implement resolution for `${DATA_DIR}` in file paths found in YAML.
    5.  **Main Orchestration:** Update the `main` function in `populate_metamapper_db.py` to use this new YAML-driven workflow.
    6.  **Output:** Provide the modified `populate_metamapper_db.py` script.
    ```