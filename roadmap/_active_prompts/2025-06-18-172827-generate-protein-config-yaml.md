# Task: Populate protein_config.yaml for Biomapper

**Source Prompt Reference:** This task is defined by the prompt: /home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/roadmap/_active_prompts/2025-06-18-172827-generate-protein-config-yaml.md

## 1. Task Objective
Generate the initial, comprehensive content for `configs/protein_config.yaml`. This file will define data sources, clients, and mapping paths for protein data from six sources: Arivale, UKBB, HPP, Function Health, SPOKE, and KG2. The configuration must adhere to the schema and examples provided in the project documentation.

## 2. Prerequisites
- [ ] Required files exist:
    - `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/roadmap/_active_prompts/feedback/2025-06-02-224317-focused-strategy-review.md` (Reference document for schema and examples)
- [ ] Required permissions: Write access to `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/configs/`.
- [ ] Required dependencies: `PyYAML` should be available in the environment.
- [ ] Environment state: The `${DATA_DIR}` environment variable should be conceptually understood and used as a placeholder in file paths.

## 3. Context from Previous Attempts (if applicable)
- N/A. This is the first attempt to create this configuration file.

## 4. Task Decomposition
Break this task into the following verifiable subtasks:
1. **Define Ontologies:** Create the `ontologies` section, defining all necessary protein ontology types (e.g., `PROTEIN_UNIPROTKB_AC_ONTOLOGY`, `ARIVALE_PROTEIN_ID_ONTOLOGY`, `UKBB_PROTEIN_ASSAY_ID_ONTOLOGY`).
2. **Configure Arivale Database:** Create the `databases` entry for Arivale, including its endpoint, properties, and file-based lookup clients.
3. **Configure UKBB Database:** Create the `databases` entry for UKBB, including its endpoint, properties, and file-based lookup clients.
4. **Configure HPP Database:** Create the `databases` entry for the Human Phenome Project (HPP), making reasonable assumptions for file paths and column names.
5. **Configure Function Health Database:** Create the `databases` entry for Function Health, making reasonable assumptions.
6. **Configure SPOKE Database:** Create the `databases` entry for SPOKE (from a hypothetical flat file), making reasonable assumptions.
7. **Configure KG2 Database:** Create the `databases` entry for KG2 (from a hypothetical flat file), making reasonable assumptions.
8. **Define Mapping Paths:** Create the `mapping_paths` section, defining at least two key mapping paths (e.g., Arivale -> UniProt -> UKBB and UKBB -> UniProt -> SPOKE).
9. **Create Feedback File:** Generate the corresponding feedback markdown file documenting assumptions and suggestions.

## 5. Implementation Requirements
- **Input files/data:**
    - `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/roadmap/_active_prompts/feedback/2025-06-02-224317-focused-strategy-review.md` (For schema guidance).
- **Expected outputs:**
    - A new, well-formed YAML file at `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/configs/protein_config.yaml`.
    - A new feedback file at `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/roadmap/_active_prompts/feedback/YYYY-MM-DD-HHMMSS-feedback-generate-protein-config-yaml.md`.
- **Code standards:**
    - The output YAML must be valid and adhere to the project's schema.
    - Use `${DATA_DIR}` for file paths.
- **Validation requirements:**
    - The generated YAML should be parsable.
    - The structure should match the guidelines in the reference document.

## 6. Error Recovery Instructions
If you encounter errors during execution:
- **Permission/Tool Errors:** If you cannot write the file, report a `FAILED_NEEDS_ESCALATION` error.
- **Configuration Errors:** If the schema from the reference document is unclear, make a reasonable assumption, document it clearly in the feedback file, and proceed.
- **Logic/Implementation Errors:** N/A for a file generation task.

## 7. Success Criteria and Validation
Task is complete when:
- [ ] The file `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/configs/protein_config.yaml` is created and contains configurations for all 6 specified data sources.
- [ ] The YAML structure correctly includes `entity_type`, `version`, `ontologies`, `databases`, and `mapping_paths`.
- [ ] The feedback file is created at the specified path, documenting all assumptions made.

## 8. Feedback Requirements
Create a detailed Markdown feedback file at:
`/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/roadmap/_active_prompts/feedback/YYYY-MM-DD-HHMMSS-feedback-generate-protein-config-yaml.md`

**Mandatory Feedback Sections:**
- **Execution Status:** [COMPLETE_SUCCESS | PARTIAL_SUCCESS | FAILED_WITH_RECOVERY_OPTIONS | FAILED_NEEDS_ESCALATION]
- **Completed Subtasks:** [checklist of what was accomplished]
- **Issues Encountered:** [Document any ambiguities in the schema or requirements.]
- **Assumptions Made:** [List all assumptions made about file paths, column names, identifiers, etc., for HPP, Function Health, SPOKE, and KG2.]
- **Next Action Recommendation:** [e.g., "Proceed with populating metamapper.db using the new configuration."]
- **Confidence Assessment:** [e.g., "High confidence in YAML structure. Assumptions for new data sources are clearly documented."]
- **Environment Changes:** [e.g., "Created file: /home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/configs/protein_config.yaml"]
- **Lessons Learned:** [e.g., "Schema is flexible enough to accommodate hypothetical data sources."]
