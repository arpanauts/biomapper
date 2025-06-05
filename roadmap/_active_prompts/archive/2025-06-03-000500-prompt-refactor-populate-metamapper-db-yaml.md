```markdown
# Task: Refactor populate_metamapper_db.py for YAML Configuration

## Context:
Biomapper is transitioning to a YAML-based configuration system. The script `/home/ubuntu/biomapper/scripts/populate_metamapper_db.py` needs a significant refactoring to read entity configurations from multiple YAML files (e.g., `configs/protein_config.yaml`, `configs/metabolite_config.yaml`) and use this information to populate the `metamapper.db` SQLite database.

This refactoring aims to make the database population process more modular, extensible, and easier to manage as new entity types and data sources are added.

Refer to the proposed refactoring strategy and YAML structure details in the "Critical Review: Focused Biomapper Strategy & Protein Mapping Plan" document: `/home/ubuntu/biomapper/roadmap/_active_prompts/feedback/2025-06-02-224317-focused-strategy-review.md` (specifically Section 3.3 "Single Database with YAML Configuration" and Section 4, Phase 3, Step 6 "Modular Population Script").

## Instructions:
1.  **YAML Parsing Logic:**
    *   Implement functionality to discover and parse all `*_config.yaml` files located in a `configs/` directory (relative to the project root: `/home/ubuntu/biomapper/configs/`).
    *   Use a robust YAML parsing library (e.g., `PyYAML`).

2.  **Modular Population Functions:**
    *   Restructure the database population logic into modular asynchronous functions.
    *   Create a main coordinating function, e.g., `populate_from_configs(session: AsyncSession)`.
    *   This function should iterate through parsed YAML configurations and call entity-specific or generic population functions, for example: `populate_entity_type(session: AsyncSession, entity_name: str, config_data: dict)`.
    *   `populate_entity_type` should, in turn, call more granular functions based on the YAML structure:
        *   `populate_ontologies(session: AsyncSession, ontologies_data: list, entity_name: str)`
        *   `populate_endpoints_and_properties(session: AsyncSession, databases_data: dict, entity_name: str)` (This will handle `Endpoint`, `EndpointPropertyConfig`, and `PropertyExtractionConfig` models)
        *   `populate_mapping_resources(session: AsyncSession, databases_data: dict, entity_name: str)` (This will handle `MappingResource` models, using client definitions from the YAML)
        *   `populate_mapping_paths(session: AsyncSession, paths_data: list, entity_name: str)` (This will handle `MappingPath` and `MappingPathStep` models)
    *   Ensure these functions correctly map YAML data to the existing SQLAlchemy models in `biomapper/db/models.py`.

3.  **Configuration Validator:**
    *   Design and implement a `ConfigurationValidator` class or module.
    *   This validator should be called after parsing each YAML file and before attempting database population with its content.
    *   Validation checks should include:
        *   Presence of required fields in the YAML structure (e.g., `entity_type`, `version`, `ontologies`, `databases`).
        *   Existence of file paths specified in client configurations (e.g., in `connection_details` or `config` blocks for file-based clients), after resolving environment variables.
        *   Consistency of internal references:
            *   Ontology types used in `properties`, `mapping_clients` (as `input_ontology_type`, `output_ontology_type`), and `mapping_paths` (as `source_type`, `target_type`) must be defined in the `ontologies` section of the same YAML file.
            *   Resources referenced in `mapping_paths` (in `steps.resource`) must be defined as a client name under `mapping_clients` within one of the `databases` sections.
        *   Client configurations should contain necessary fields based on their type (e.g., a file lookup client needs `file_path`, `key_column`, `value_column`).

4.  **Environment Variable Resolution:**
    *   Implement robust resolution for environment variables like `${DATA_DIR}` within file path strings found in the YAML configurations. This should occur before file existence checks and before storing paths in the database. The `settings.data_dir` from `biomapper.config` can be the source for `DATA_DIR`.

5.  **Main Orchestration Update:**
    *   Update the `main` asynchronous function in `populate_metamapper_db.py`.
    *   It should initialize the database and `DatabaseManager` as before.
    *   Then, it should call the new `populate_from_configs` function to drive the population process using the YAML files.
    *   Ensure error handling and logging are appropriate. If a YAML file fails validation, its contents should not be populated, and an error should be logged.

6.  **Backward Compatibility & Cleanup:**
    *   Remove the old, hardcoded data population logic from `populate_data(session: AsyncSession)`. This function might be repurposed or removed if `populate_from_configs` entirely replaces it. The goal is for `metamapper.db` to be solely populated based on the `configs/*.yaml` files.

7.  **Output:**
    *   Provide the fully modified `/home/ubuntu/biomapper/scripts/populate_metamapper_db.py` script.

8.  **Feedback File:**
    *   Create a Markdown feedback file named `YYYY-MM-DD-HHMMSS-feedback-refactor-populate-metamapper-db-yaml.md` (use the current UTC timestamp) in the `/home/ubuntu/biomapper/roadmap/_active_prompts/feedback/` directory.
    *   In this feedback file, document:
        *   Key design decisions made during the refactoring (e.g., structure of validator, error handling strategy).
        *   Any parts of the existing script that were challenging to adapt or remove.
        *   Any assumptions made about the YAML schema details not explicitly covered.
        *   A brief confirmation of the tasks completed and the script's readiness for testing with a `protein_config.yaml`.
```
