# Task: Update protein_config.yaml with New File Paths and Add HPA/QIN OSP Data

## 1. Context
The `/home/ubuntu/biomapper/configs/protein_config.yaml` file needs to be updated to reflect new consolidated locations for various protein ontology data files. Additionally, new data sources for HPA OSP and QIN OSP need to be integrated.

The `file_path` entries in `protein_config.yaml` use a `${DATA_DIR}` placeholder. This placeholder is resolved by the `populate_metamapper_db.py` script, and `settings.data_dir` (from `biomapper.config`) currently points to `/home/ubuntu/biomapper/data`.

The new data files are located under the absolute path `/procedure/data/local_data/MAPPING_ONTOLOGIES/`. You will need to construct the `file_path` values in the YAML such that `${DATA_DIR}/<relative_path_segment>` correctly points to these new absolute locations.
The relative path from `/home/ubuntu/biomapper/data` to `/procedure/data/local_data/MAPPING_ONTOLOGIES/` is `../../../../procedure/data/local_data/MAPPING_ONTOLOGIES/`.
For example, if a new file is at `/procedure/data/local_data/MAPPING_ONTOLOGIES/example_source/data.csv`, the corresponding `file_path` in the YAML should be `"${DATA_DIR}/../../../../procedure/data/local_data/MAPPING_ONTOLOGIES/example_source/data.csv"`.

**Target File:** `/home/ubuntu/biomapper/configs/protein_config.yaml`

## 2. Instructions

### 2.1. Update File Paths for Existing Data Sources
For each of the following data sources, update all relevant `file_path` entries in their `endpoint.connection_details` and any associated `mapping_clients[*].config`:

*   **UKBB_PROTEIN**:
    *   New main file location: `/procedure/data/local_data/MAPPING_ONTOLOGIES/ukbb/UKBB_Protein_Meta.tsv`
*   **ARIVALE_PROTEIN**:
    *   New file location: `/procedure/data/local_data/MAPPING_ONTOLOGIES/arivale/proteomics_metadata.tsv`
*   **SPOKE_PROTEIN** (currently item #4 in the YAML):
    *   New file location: `/procedure/data/local_data/MAPPING_ONTOLOGIES/spoke_ontologies/spoke_proteins.csv`
    *   Note: The file extension changes from `.tsv` to `.csv`. Adjust delimiter and potentially column names.
*   **KG2_PROTEIN** (currently item #5 in the YAML):
    *   New file location: `/procedure/data/local_data/MAPPING_ONTOLOGIES/kg2c_ontologies/kg2c_proteins.csv`
    *   Note: The file extension changes from `.tsv` to `.csv`. Adjust delimiter and potentially column names.

**Important Note on Columns and Delimiters:**
When updating `file_path`, critically review the `key_column`, `value_column` in `mapping_clients` and the `delimiter` in `connection_details` (for endpoints) and `mapping_clients`.
*   If a file changes from `.tsv` to `.csv`, the delimiter should likely change from `"\t"` to `","`.
*   Column names in the new files might be different. If the new column names are not specified, make plausible assumptions (e.g., common names like `uniprot_ac`, `gene_name`, `protein_id`, `assay_id`, `node_id`, `entity_id`). Clearly document any assumptions made in your feedback file.

### 2.2. Integrate HPA OSP and QIN OSP Data Sources
Add configurations for two new protein data sources. These should be added as new numbered items under the `databases:` key (e.g., they will become items #6 and #7, following KG2_PROTEIN).

**A. HPA OSP Protein Data:**
*   File location: `/procedure/data/local_data/MAPPING_ONTOLOGIES/isb_osp/hpa_osps.csv`

    1.  **Add Ontology Definition:**
        *   In the top-level `ontologies:` section, add a definition for `HPA_OSP_PROTEIN_ID_ONTOLOGY`. Include a `name`, `description` (e.g., "HPA Olink Sample Panel Protein Identifier"), and an optional `identifier_prefix` (e.g., "HPAOSP_").
    2.  **Add Database Configuration:**
        *   `endpoint`:
            *   `name: "HPA_OSP_PROTEIN"`
            *   `type: "file_csv"`
            *   `connection_details`:
                *   `file_path`: (Construct as described above)
                *   `delimiter: ","`
        *   `properties`:
            *   `primary: "HPA_OSP_PROTEIN_ID_ONTOLOGY"`
            *   `mappings`:
                *   Map `HPA_OSP_PROTEIN_ID_ONTOLOGY` to a plausible column name (e.g., `hpa_assay_id`).
                *   Map `PROTEIN_UNIPROTKB_AC_ONTOLOGY` to a plausible column name (e.g., `uniprot_ac`).
        *   `mapping_clients`:
            *   Define two clients using `biomapper.mapping.clients.generic_file_client.GenericFileLookupClient`:
                1.  `hpa_osp_to_uniprot_lookup`:
                    *   `input_ontology_type: "HPA_OSP_PROTEIN_ID_ONTOLOGY"`
                    *   `output_ontology_type: "PROTEIN_UNIPROTKB_AC_ONTOLOGY"`
                    *   `config`: `file_path` (as above), `key_column` (e.g., `hpa_assay_id`), `value_column` (e.g., `uniprot_ac`), `delimiter: ","`.
                2.  `uniprot_to_hpa_osp_lookup`:
                    *   `input_ontology_type: "PROTEIN_UNIPROTKB_AC_ONTOLOGY"`
                    *   `output_ontology_type: "HPA_OSP_PROTEIN_ID_ONTOLOGY"`
                    *   `config`: `file_path` (as above), `key_column` (e.g., `uniprot_ac`), `value_column` (e.g., `hpa_assay_id`), `delimiter: ","`.

**B. QIN OSP Protein Data:**
*   File location: `/procedure/data/local_data/MAPPING_ONTOLOGIES/isb_osp/qin_osps.csv`

    1.  **Add Ontology Definition:**
        *   In the top-level `ontologies:` section, add a definition for `QIN_OSP_PROTEIN_ID_ONTOLOGY`. Include a `name`, `description` (e.g., "QIN Olink Sample Panel Protein Identifier"), and an optional `identifier_prefix` (e.g., "QINOSP_").
    2.  **Add Database Configuration:**
        *   Follow the same structure as for `HPA_OSP_PROTEIN`, adapting names and assumed column names:
            *   `endpoint.name: "QIN_OSP_PROTEIN"`
            *   `properties.primary: "QIN_OSP_PROTEIN_ID_ONTOLOGY"`
            *   Assumed property columns: e.g., `qin_assay_id`, `uniprot_ac`.
            *   Mapping clients: `qin_osp_to_uniprot_lookup` and `uniprot_to_qin_osp_lookup`, with appropriate configurations.

### 2.3. General Instructions
*   Ensure the final `/home/ubuntu/biomapper/configs/protein_config.yaml` is well-formed and maintains structural consistency.
*   Pay attention to indentation and YAML syntax.
*   The "Function Health" section has already been removed by the user. SPOKE is #4, KG2 is #5. HPA will be #6, QIN will be #7.

## 3. Deliverables
1.  **Updated Configuration File:** The complete content of the modified `/home/ubuntu/biomapper/configs/protein_config.yaml`.
2.  **Feedback File:** Create a Markdown feedback file named `YYYY-MM-DD-HHMMSS-feedback-update-protein-config-paths.md` (use the current UTC timestamp of when you complete the task) in the `/home/ubuntu/biomapper/roadmap/_active_prompts/feedback/` directory. In this file, document:
    *   A summary of changes made.
    *   Any assumptions made about column names, delimiters, or file structures for the new or updated data sources.
    *   Any challenges encountered or potential issues identified.
    *   Confirmation of the tasks completed.
