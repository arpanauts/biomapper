# Feature Specification: Core Metamapper Configuration for Protein Datasets

## 1. Functional Scope
This feature will ensure that the `metamapper.db` is correctly populated with all necessary metadata to describe and enable mapping for the UKBB, HPA, and Qin protein datasets. This includes:
-   Defining `Ontology` entries for key identifiers like `UNIPROTKB_AC`.
-   Defining `Property` entries for these identifiers.
-   Establishing `Endpoint` entries for each of the three protein datasets.
-   Creating `PropertyExtractionConfig` to detail how to pull UniProt ACs (and potentially other data) from the source TSV/CSV files. This involves specifying column names and data types.
-   Setting up `EndpointPropertyConfig` to link the extracted properties to their respective endpoints and designate primary identifiers.
-   Configuring `MappingResource` entries for each dataset, utilizing the `GenericFileLookupClient`. This requires accurate `config_template` JSON strings detailing file paths, delimiters, and the columns to be used for lookup keys and values.
-   Defining `OntologyCoverage` to specify that these mapping resources can perform identity lookups for `UNIPROTKB_AC` (i.e., map a `UNIPROTKB_AC` to itself within the context of that file).
-   The `populate_metamapper_db.py` script will be the primary mechanism for implementing these configurations and will serve as a validation of the setup.

## 2. Technical Scope
-   **Database:** SQLite (`metamapper.db`).
-   **Schema:** Adherence to the existing SQLAlchemy models defined in `biomapper.db.models`.
-   **Configuration Script:** All configurations will be implemented within `/home/ubuntu/biomapper/scripts/populate_metamapper_db.py`.
-   **Data Files:**
    -   `/home/ubuntu/biomapper/data/UKBB_Protein_Meta_full.tsv`
    -   `/home/ubuntu/biomapper/data/isb_osp/hpa_osps.csv`
    -   `/home/ubuntu/biomapper/data/isb_osp/qin_osps.csv`
-   **Client:** `biomapper.mapping.clients.generic_file_client.GenericFileLookupClient` is the primary client for these resources.
-   **JSON Handling:** `json.dumps()` must be used for `config_template` in `MappingResource` to ensure valid JSON strings.
-   **Idempotency:** The `populate_metamapper_db.py` script should ideally be idempotent, or at least handle existing database states gracefully (e.g., by deleting and recreating, as it currently does).

## 3. UI Treatments / Layout Options
Not applicable for this feature, as it is backend configuration. The "UI" is effectively the structure of `metamapper.db` and the successful execution of `populate_metamapper_db.py`.
