```markdown
# Task: Populate protein_config.yaml for Biomapper

## Context:
Biomapper is implementing a YAML-based configuration system to define data sources, clients, and mapping paths for different biological entity types. Your task is to generate the initial content for `configs/protein_config.yaml`.

This configuration will drive how protein-related metadata is loaded into `metamapper.db` and subsequently used by the `MappingExecutor`.

Refer to the proposed YAML structure and protein configuration examples in the "Critical Review: Focused Biomapper Strategy & Protein Mapping Plan" document: `/home/ubuntu/biomapper/roadmap/_active_prompts/feedback/2025-06-02-224317-focused-strategy-review.md` (specifically Section 3.2 "Protein Configuration Example" and related schema discussions in Section 3).

You need to define configurations for protein data from 6 sources:
1.  Arivale
2.  UKBB
3.  Human Phenome Project (HPP)
4.  Function Health
5.  SPOKE (assume a flat file export for protein data)
6.  KG2 (assume a flat file export for protein data)

## Instructions:
1.  **Gather/Define Information:** For each of the 6 databases, determine or make realistic assumptions for the following details. Prioritize using existing knowledge from the Biomapper project where available (e.g., Arivale and UKBB paths from previous configurations).
    *   **File Paths:** Use the `${DATA_DIR}` environment variable placeholder (e.g., `${DATA_DIR}/arivale_data/proteomics_metadata.tsv`). If actual file names are unknown, use plausible placeholders.
    *   **Primary Protein Identifiers:** Identify the main protein ID type used in each dataset (e.g., `ARIVALE_PROTEIN_ID`, `UNIPROTKB_AC`, `ENSEMBL_PROTEIN_ID`).
    *   **Column Names:** Specify the column names in the source files that correspond to these primary IDs and any important secondary/cross-reference identifiers (e.g., UniProt ACs, Gene Names, Ensembl IDs, Entrez Gene IDs).
    *   **Client Configurations:** Assume file-based lookups for all sources initially. Configure clients similar to `ArivaleMetadataLookupClient` or a generic file lookup client. The client configuration should include `file_path`, `key_column`, `value_column`, and `delimiter`.

2.  **Structure the YAML:** Adhere to the schema proposed in the reference document. The `protein_config.yaml` should include the following top-level keys:
    *   `entity_type: "protein"`
    *   `version: "1.0"`
    *   `ontologies:` Define all relevant protein ontology types (e.g., `PROTEIN_UNIPROTKB_AC_ONTOLOGY`, `PROTEIN_GENE_NAME_ONTOLOGY`, `ARIVALE_PROTEIN_ID_ONTOLOGY`, `UKBB_PROTEIN_ASSAY_ID_ONTOLOGY`). Include a `name`, `description`, and optional `identifier_prefix`.
    *   `databases:` For each of the 6 sources:
        *   `endpoint:` Define `name` (e.g., `ARIVALE_PROTEIN`), `type` (e.g., `file_tsv`), and `connection_details` (like `file_path`, `delimiter`).
        *   `properties:` Define the `primary` identifier ontology type and a `mappings` dictionary detailing how various ontology types are extracted from columns in the source file.
        *   `mapping_clients:` Define client instances (e.g., `arivale_protein_to_uniprot_lookup`). Specify `client_class_path` (e.g., `biomapper.mapping.clients.generic_file_client.GenericFileLookupClient` or `biomapper.mapping.clients.arivale_protein_client.ArivaleMetadataLookupClient`), `input_ontology_type`, `output_ontology_type`, and the `config` block with client-specific parameters like `file_path`, `key_column`, `value_column`.
    *   `mapping_paths:` Define a few key protein-to-protein mapping paths. For example:
        *   Arivale Protein ID -> UniProtKB AC -> UKBB Protein (via UniProtKB AC)
        *   UKBB Protein Assay ID -> UniProtKB AC -> SPOKE Protein (via UniProtKB AC)
        Each path should have a `name`, `source_type`, `target_type`, `priority`, and a list of `steps`, where each step specifies a `resource` (client name from `mapping_clients`) and `order`.

3.  **Output:**
    *   Provide the complete content for the `configs/protein_config.yaml` file.
    *   Ensure the YAML is well-formed and adheres to the structural guidelines from the reference document.

4.  **Feedback File:**
    *   Create a Markdown feedback file named `YYYY-MM-DD-HHMMSS-feedback-generate-protein-config-yaml.md` (use the current UTC timestamp) in the `/home/ubuntu/biomapper/roadmap/_active_prompts/feedback/` directory.
    *   In this feedback file, document:
        *   Any assumptions made about file paths, column names, or identifier types for the 6 databases.
        *   Any challenges encountered in interpreting the schema or applying it.
        *   Suggestions for schema improvements if any become apparent.
        *   A brief confirmation of the tasks completed.
```
