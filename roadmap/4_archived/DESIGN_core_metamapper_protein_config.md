# Design Document: Core Metamapper Configuration for Protein Datasets

## 1. Architectural Considerations
The core architecture revolves around the `metamapper.db` SQLite database and its schema, defined by SQLAlchemy models in `biomapper.db.models`. The `/home/ubuntu/biomapper/scripts/populate_metamapper_db.py` script acts as the configuration agent, populating this database.

-   **Data Models Utilized:**
    -   `Ontology`: To define identifier systems (e.g., `UNIPROTKB_AC`).
    -   `Property`: To define specific properties linked to ontologies (e.g., "UniProtKB Accession Number").
    -   `Endpoint`: To represent each data source (UKBB TSV, HPA CSV, Qin CSV).
    -   `PropertyExtractionConfig`: To specify how to parse identifiers from the raw data files (column names, data types).
    -   `EndpointPropertyConfig`: To link extracted properties to endpoints and define their roles (e.g., primary identifier).
    -   `MappingResource`: To define the lookup capabilities, primarily using `GenericFileLookupClient`. The `config_template` (a JSON string) is critical here, storing file paths, delimiters, and column mappings for the client.
    -   `OntologyCoverage`: To declare the input and output ontology types for each `MappingResource` (e.g., `UNIPROTKB_AC` to `UNIPROTKB_AC` for identity lookups).
-   **System Interactions:**
    -   The `populate_metamapper_db.py` script directly interacts with `metamapper.db` via SQLAlchemy.
    -   The `MappingExecutor` (future use) will read from `metamapper.db` to understand how to process and map data.
    -   The `GenericFileLookupClient` is invoked by the `MappingExecutor` based on `MappingResource` configurations.

## 2. Component Interactions
-   **`populate_metamapper_db.py`:**
    1.  Initializes the database schema (potentially deleting an existing DB).
    2.  Sequentially creates entries in `Ontology`, `Property`, `Endpoint`, `PropertyExtractionConfig`, `MappingResource`, `EndpointPropertyConfig`, and `OntologyCoverage` tables.
    3.  For `MappingResource`, it uses `json.dumps()` to create the `config_template` string.
-   **`GenericFileLookupClient` (as configured by `MappingResource`):**
    1.  Instantiated by `MappingExecutor` with parameters from `config_template`.
    2.  Reads the specified data file (e.g., `/home/ubuntu/biomapper/data/isb_osp/hpa_osps.csv`).
    3.  Performs lookups based on a provided key (e.g., a UniProt AC) in the specified "key column" and returns data from the specified "value column".

## 3. Visual Sketches / Mockups
Not applicable for this backend configuration feature. The "design" is represented by the database schema and the structure of the Python objects used in `populate_metamapper_db.py`.

A conceptual representation of a `MappingResource` configuration for HPA:
-   **Resource Name:** `hpa_protein_lookup`
-   **Client:** `GenericFileLookupClient`
-   **`config_template` (conceptual, actual is a JSON string):**
    ```json
    {
        "file_path": "/home/ubuntu/biomapper/data/isb_osp/hpa_osps.csv",
        "delimiter": ",",
        "key_column": "uniprot", // Column in hpa_osps.csv containing UniProt ACs
        "value_column": "uniprot" // Column to return (for identity lookup)
    }
    ```
-   **`OntologyCoverage`:**
    -   Input: `UNIPROTKB_AC`
    -   Output: `UNIPROTKB_AC`
