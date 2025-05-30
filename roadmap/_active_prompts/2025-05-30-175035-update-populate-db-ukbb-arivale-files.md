# Prompt for Claude Code Instance: Update populate_metamapper_db.py for UKBB/Arivale File Resources

**Source Prompt:** This task is defined by the prompt: `/home/ubuntu/biomapper/roadmap/_active_prompts/2025-05-30-175035-update-populate-db-ukbb-arivale-files.md`

## 1. Task Overview

This task requires you to enhance the `/home/ubuntu/biomapper/scripts/populate_metamapper_db.py` script to include `MappingResource` definitions for file-based lookups using UKBB and Arivale protein metadata files. This is based on the blueprint outlined in project memory MEMORY[c3f81352-4385-4f0e-b00f-c46577cbec43] and aligns with the goal of improving extensibility (Checkpoint Summary).

Your goal is to add configurations for `GenericFileLookupClient` to enable mappings like UKBB Assay ID <-> UniProt and Arivale UniProt <-> Arivale Name, using the specified local files.

## 2. Project Context & Guidelines

*   Familiarize yourself with the Biomapper project structure by reviewing `/home/ubuntu/biomapper/CLAUDE.md`.
*   The script to be modified is: `/home/ubuntu/biomapper/scripts/populate_metamapper_db.py`.
*   The `GenericFileLookupClient` is located at `biomapper.mapping.clients.generic_file_client.GenericFileLookupClient`.
*   Refer to MEMORY[c3f81352-4385-4f0e-b00f-c46577cbec43] for the detailed plan, including file paths, column names, and ontology terms.
*   Ensure consistency with existing patterns in `populate_metamapper_db.py` for defining resources and ontology coverage.
*   All Python package management for this project should be done using Poetry.
*   Relevant file paths from memory:
    *   UKBB Protein Meta: `/procedure/data/local_data/HPP_PHENOAI_METADATA/UKBB_Protein_Meta.tsv` (Headers: Assay, UniProt, Panel)
    *   Arivale Proteomics Meta: `/procedure/data/local_data/ARIVALE_SNAPSHOTS/proteomics_metadata.tsv` (Headers: name, panel, uniprot, gene_name, etc.)
    *   Note: MEMORY[87598b65-0bf2-40c3-be97-ad15baf90c5f] mentions a copy of UKBB data at `/home/ubuntu/biomapper/data/UKBB_Protein_Meta_full.tsv`. For consistency with the blueprint in MEMORY[c3f81352-4385-4f0e-b00f-c46577cbec43], use the `/procedure/` paths for now, but be aware of this alternative.

## 3. Detailed Steps & Requirements

1.  **Review Blueprint:** Thoroughly understand the requirements from MEMORY[c3f81352-4385-4f0e-b00f-c46577cbec43].

2.  **Define New Ontologies (if necessary, as per memory):**
    *   The memory suggests `UKBB_ASSAY_ID_ONTOLOGY`. Ensure this (and any other new ontology types) are defined or referenced correctly in `populate_metamapper_db.py`. Remember to use uppercase for ontology terms. If these ontology terms are already defined, ensure your new resources use the existing definitions.

3.  **Define New `MappingResource` entries in `populate_data` function (or equivalent section):**
    *   **`ukbb_assay_to_uniprot`**:
        *   `name`: e.g., "UKBB Assay ID to UniProt (File)"
        *   `client_class_path`: `biomapper.mapping.clients.generic_file_client.GenericFileLookupClient`
        *   `config_template`: `{'file_path': '/procedure/data/local_data/HPP_PHENOAI_METADATA/UKBB_Protein_Meta.tsv', 'key_column': 'Assay', 'value_column': 'UniProt', 'delimiter': '\t'}`
        *   `input_ontology_term`: `UKBB_ASSAY_ID` (or the appropriate term if already defined differently)
        *   `output_ontology_term`: `UNIPROTKB_AC`
    *   **`uniprot_to_ukbb_assay`**:
        *   `name`: e.g., "UniProt to UKBB Assay ID (File)"
        *   `client_class_path`: `biomapper.mapping.clients.generic_file_client.GenericFileLookupClient`
        *   `config_template`: `{'file_path': '/procedure/data/local_data/HPP_PHENOAI_METADATA/UKBB_Protein_Meta.tsv', 'key_column': 'UniProt', 'value_column': 'Assay', 'delimiter': '\t'}`
        *   `input_ontology_term`: `UNIPROTKB_AC`
        *   `output_ontology_term`: `UKBB_ASSAY_ID`
    *   **Arivale File Resources:**
        *   The memory mentions `arivale_lookup`, `arivale_reverse_lookup`, `arivale_genename_lookup` might exist. Verify this.
        *   If they exist and use `GenericFileLookupClient` for `/procedure/data/local_data/ARIVALE_SNAPSHOTS/proteomics_metadata.tsv`, ensure their `config_template` points to this file and uses correct `key_column` and `value_column` (e.g., 'uniprot' and 'name' for UniProt -> Arivale ID; 'name' and 'uniprot' for reverse; 'name' and 'gene_name' for Arivale ID -> Gene Name).
        *   If they don't exist or use a different client/file, add new `MappingResource` entries as needed for these Arivale mappings using `GenericFileLookupClient` and the specified TSV file. For example:
            *   `arivale_uniprot_to_name (File)`: input `UNIPROTKB_AC`, output `ARIVALE_PROTEIN_ID` (using 'uniprot' as key, 'name' as value from `proteomics_metadata.tsv`).
            *   `arivale_name_to_uniprot (File)`: input `ARIVALE_PROTEIN_ID`, output `UNIPROTKB_AC` (using 'name' as key, 'uniprot' as value from `proteomics_metadata.tsv`).

4.  **Add `OntologyCoverage` entries:** For each new `MappingResource`, add corresponding `OntologyCoverage` entries to declare the supported mapping types (e.g., `UKBB_ASSAY_ID` -> `UNIPROTKB_AC`).

5.  **Testing (Conceptual):**
    *   After modification, running `python /home/ubuntu/biomapper/scripts/populate_metamapper_db.py --drop-all --no-prompt` (or similar, depending on script arguments) should successfully populate the database with these new resources without errors.
    *   Conceptually, these resources should then be discoverable by the `MappingExecutor`.

## 5. Deliverables

Create a single Markdown feedback file named `YYYY-MM-DD-HHMMSS-feedback-update-populate-db-ukbb-arivale-files.md` (use UTC timestamp of task completion) in the `/home/ubuntu/biomapper/roadmap/_active_prompts/feedback/` directory. This file must include:

1.  **Summary of Actions:** Briefly describe the changes made to the script.
2.  **Code Changes:** A `diff` of the changes made to `/home/ubuntu/biomapper/scripts/populate_metamapper_db.py`.
3.  **Confirmation:** State whether the script runs without errors after your changes (e.g., by running `python /home/ubuntu/biomapper/scripts/populate_metamapper_db.py --drop-all --no-prompt`).
4.  **List of New/Updated Resources:** Briefly list the names of the `MappingResource` entries you added or updated.
5.  **Any Challenges Encountered or Open Questions.**

## 6. Tool Permissions
You will need `Edit` permissions for `/home/ubuntu/biomapper/scripts/populate_metamapper_db.py`.
