# Feature Idea: Populate Mapping Strategies from YAML into metamapper.db

## Core Concept / Problem
The `metamapper.db` needs to store not only entity and resource definitions (now populated from YAML) but also the `MappingStrategy` and `MappingStep` definitions that dictate how `MappingExecutor` should perform mapping operations. Currently, `populate_metamapper_db.py` handles entity configs but does not yet parse or populate the `mapping_strategies` section from YAML files (e.g., `protein_config.yaml`) into the corresponding database tables.

## Intended Goal / Benefit
- Enable `MappingExecutor` to execute complex, multi-step mapping strategies defined entirely in YAML.
- Complete the YAML-driven configuration pipeline, making YAML files the comprehensive source of truth for all `metamapper.db` content.
- Allow for easy definition, modification, and versioning of mapping strategies without direct database manipulation or Python code changes for strategy logic.

## Initial Thoughts / Requirements / Context
- **Source YAML Section:** The `mapping_strategies` section within entity configuration YAML files (e.g., `/home/ubuntu/biomapper/configs/protein_config.yaml`).
- **Target Database Tables:** `MappingStrategy` and `MappingStep` in `metamapper.db`.
- **Script to Update:** `/home/ubuntu/biomapper/scripts/populate_metamapper_db.py`.
- **Functionality Needed in Script:**
    - Extend YAML parsing to correctly interpret the `mapping_strategies` list and its nested `steps`.
    - Add new modular functions (similar to those for entities/resources) to populate `MappingStrategy` and `MappingStep` tables.
    - Ensure foreign key relationships (e.g., linking steps to strategies, linking steps to `MappingResource` instances) are correctly established.
    - Update the `ConfigurationValidator` to include checks for the `mapping_strategies` section, such as:
        - Ensuring referenced `resource` names in steps exist as defined `MappingResource`s.
        - Validating `input_type` and `output_type` for steps against defined ontologies.
- This is a critical next step after the successful refactoring of `populate_metamapper_db.py` for entity configurations.
