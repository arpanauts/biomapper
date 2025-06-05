# Biomapper Configuration Files (`configs/`)

This directory contains YAML configuration files (e.g., `protein_config.yaml`, `metabolite_config.yaml`) that define the data sources, ontologies, and mapping strategies for different biological entity types within the Biomapper system. These configurations are crucial for populating the `metamapper.db` metadata database and guiding the `MappingExecutor` during the mapping processes.

## Structure of `*_config.yaml` Files

Each `*_config.yaml` file follows a structured format to provide a comprehensive definition of an entity type, its associated identifier types (ontologies), the data sources (endpoints) that contain these entities, and the methods (clients and paths) to map between different identifier types.

Below is a meta-level overview of the common components found in these YAML files:

1.  **`entity_type` (String)**:
    *   **Purpose**: A top-level string declaring the broad category of biological entities this configuration file pertains to (e.g., `"protein"`, `"metabolite"`).
    *   **Example**: `protein`

2.  **`version` (String)**:
    *   **Purpose**: A version string for the configuration file itself, allowing for tracking changes and compatibility.
    *   **Example**: `1.0.0`

3.  **`ontologies` (List of Objects)**:
    *   **Purpose**: Acts as a central registry of all recognized identifier types (ontology types) for the given `entity_type`. Other parts of the configuration refer to these.
    *   **Structure**: Each object defines an ontology type with:
        *   `id`: A unique string identifier (e.g., `HPA_OSP_PROTEIN_ID_ONTOLOGY`, `PROTEIN_UNIPROTKB_AC_ONTOLOGY`). This is used for internal references.
        *   `name`: A human-readable name (e.g., "HPA OSP Protein ID").
        *   `description`: A brief explanation.
    *   **Example Snippet**:
        ```yaml
        ontologies:
          - id: "PROTEIN_UNIPROTKB_AC_ONTOLOGY"
            name: "UniProtKB Accession"
            description: "UniProt Knowledgebase Accession Number (e.g., P12345)"
        ```

4.  **`databases` (Dictionary/Map of Objects)**:
    *   **Purpose**: This section is the heart of data source definition. It describes each dataset (endpoint): what it is, what IDs it contains, how to access its data, and associated mapping tools.
    *   **Structure**: Each key is a unique endpoint name (e.g., `hpa_osp`, `ukbb_protein`). The value is an object describing that endpoint, containing:
        *   `name` (String): Human-readable name.
        *   `description` (String): Brief description.
        *   `endpoint.type` (String): Often the primary ontology type this endpoint is natively keyed by.
        *   `endpoint.properties` (Object):
            *   `primary` (String): The `id` of the ontology type (from `properties.mappings` keys) considered the main/canonical identifier for this endpoint.
            *   `mappings` (Dictionary): Crucial for linking ontology types to actual data columns.
                *   *Keys*: Ontology type `id`s.
                *   *Values*: Objects detailing extraction for that ontology type from this endpoint's data file:
                    *   `column` (String): The actual column name in the raw data file (e.g., "gene", "UniProt").
                    *   `ontology_type` (String): The ontology type `id` this mapping refers to.
        *   `connection_details` (Object): How to access the raw data.
            *   `type` (String): Type of data source (e.g., `file.csv`, `file.tsv`).
            *   `path` (String): File path, supporting environment variables (e.g., `${DATA_DIR}/hpa_protein.csv`).
            *   Other parameters (e.g., `delimiter`).
        *   `mapping_clients` (Dictionary): Defines mapping clients (ID conversion tools) available/configured for this endpoint.
            *   *Keys*: Unique client names (scoped to this endpoint).
            *   *Values*: Objects defining the client:
                *   `type` (String): Python class of the client (e.g., `biomapper.mapping.clients.uniprot_client.UniProtMappingClient`).
                *   `input_ontology_type` (String): Expected input ontology type `id`.
                *   `output_ontology_type` (String): Produced output ontology type `id`.
                *   `config` (Object): Client-specific settings (API keys, lookup file paths, etc.).
    *   **Example Snippet (`hpa_osp` endpoint)**:
        ```yaml
        hpa_osp:
          name: "Human Protein Atlas OSP Data"
          # ... other fields ...
          endpoint:
            type: "HPA_OSP_PROTEIN_ID_ONTOLOGY"
            properties:
              primary: "HPA_OSP_PROTEIN_ID_ONTOLOGY"
              mappings:
                HPA_OSP_PROTEIN_ID_ONTOLOGY:
                  column: "gene"
                  ontology_type: "HPA_OSP_PROTEIN_ID_ONTOLOGY"
                PROTEIN_UNIPROTKB_AC_ONTOLOGY:
                  column: "uniprot"
                  ontology_type: "PROTEIN_UNIPROTKB_AC_ONTOLOGY"
          connection_details:
            type: "file.csv"
            path: "${DATA_DIR}/hpa_protein.csv"
          # ... mapping_clients if any ...
        ```

5.  **`ontology_preferences` (Dictionary/Map of Lists)**:
    *   **Purpose**: For an endpoint with multiple ID types, this specifies a preferred order of usage or conversion *within that endpoint's context*.
    *   **Structure**: Keys are endpoint names. Values are ordered lists of ontology type `id`s.
    *   **Example Snippet**:
        ```yaml
        ontology_preferences:
          hpa_osp:
            - "HPA_OSP_PROTEIN_ID_ONTOLOGY"
            - "PROTEIN_UNIPROTKB_AC_ONTOLOGY"
        ```

6.  **`endpoint_relationships` (Dictionary/Map of Objects)**:
    *   **Purpose**: Explicitly defines strategies for mapping between specific pairs of endpoints.
    *   **Structure**: Keys are descriptive relationship names (e.g., `HPA_OSP_PROTEIN_TO_UKBB_PROTEIN`). Values are objects with:
        *   `source_endpoint` (String): Source endpoint name.
        *   `target_endpoint` (String): Target endpoint name.
        *   `primary_shared_ontology` (String): An ontology type `id` considered the best "bridge" for mapping between these two.
        *   `source_conversion_preference` / `target_conversion_preference` (List of Strings): Ordered ontology type `id`s suggesting preferred conversion paths to/from the `primary_shared_ontology`.
    *   **Example Snippet**:
        ```yaml
        endpoint_relationships:
          HPA_OSP_PROTEIN_TO_UKBB_PROTEIN:
            source_endpoint: "hpa_osp"
            target_endpoint: "ukbb_protein"
            primary_shared_ontology: "PROTEIN_UNIPROTKB_AC_ONTOLOGY"
            # ... conversion_preferences ...
        ```

7.  **`mapping_paths` (List of Objects)**:
    *   **Purpose**: Provides pre-defined, potentially multi-step, "recipes" for converting one ontology type to another.
    *   **Structure**: Each object defines a path with:
        *   `name` (String): Unique path name.
        *   `source_type` (String): Starting ontology type `id`.
        *   `target_type` (String): Final desired ontology type `id`.
        *   `steps` (List of Objects): Ordered steps, each specifying:
            *   `resource` (String): Name of a `mapping_client` (defined under a `databases` entry) to execute this step.
    *   **Example Snippet**:
        ```yaml
        mapping_paths:
          - name: "HPA_GENE_TO_UNIPROT_VIA_BIOMART"
            source_type: "ENSEMBL_GENE_ID_ONTOLOGY" # Assuming this is defined
            target_type: "PROTEIN_UNIPROTKB_AC_ONTOLOGY"
            steps:
              - resource: "biomart_ensembl_to_uniprot_client" # Must be defined elsewhere
        ```

This structured configuration approach enables Biomapper to be highly flexible and adaptable to new data sources and mapping requirements.

8.  **`mapping_strategies` (Object, Optional)**:
    *   **Purpose**: Defines named, ordered pipelines of mapping operations for specific, complex mapping tasks. This allows for explicit control over multi-step mapping processes.
    *   **Details**: For a comprehensive explanation of how to define and use mapping strategies, please refer to [YAML-Defined Mapping Strategies in Biomapper](../roadmap/technical_notes/core_mapping_logic/yaml_defined_mapping_strategies.md).
    *   **Example Snippet**:
        ```yaml
        mapping_strategies:
          MY_COMPLEX_PROTEIN_STRATEGY:
            description: "A specific strategy for mapping X to Y with intermediate steps."
            steps:
              - step_id: "S1_INITIAL_CONVERSION"
                action:
                  type: "CONVERT_IDENTIFIERS_LOCAL"
                  # ... other parameters
              # ... more steps
        ```

## Strategy for Configuring "UniProt-Complete" Datasets (e.g., HPA, QIN, UKBB Proteins)

For datasets like HPA, QIN, and UKBB protein data, where UniProt Accession numbers (`PROTEIN_UNIPROTKB_AC_ONTOLOGY`) are comprehensively available and serve as a robust primary shared ontology (PSO), the configuration can be streamlined:

1.  **Focus on Essential Identifiers:**
    *   **Native Primary ID:** Each dataset's configuration in `databases.<endpoint_name>.endpoint.properties.primary` should reflect its true native primary identifier (e.g., Ensembl Gene ID for HPA OSP, Assay ID for UKBB).
    *   **UniProt AC:** The `databases.<endpoint_name>.endpoint.properties.mappings` must include an entry for `PROTEIN_UNIPROTKB_AC_ONTOLOGY`, mapping it to the correct column in the data file (e.g., "uniprot" or "UniProt").
    *   **Minimal Other Secondary IDs (Initially):** For the initial direct UniProt-bridged mapping, other secondary ontology types (e.g., RefSeq IDs) might not be strictly necessary to define in the `mappings` if they are not part of this primary strategy. They can be added later for more complex mapping scenarios.

2.  **Mapping Strategy:**
    *   **Direct UniProt Comparison:** The primary mapping strategy involves:
        1.  Converting the source entity's native ID to its UniProt AC (using the information within the source dataset's `mappings`).
        2.  Directly comparing this UniProt AC against the UniProt ACs available in the target dataset (again, using the target dataset's `mappings`).
        3.  If a match is found, retrieving the target entity's desired native ID.
    *   **UniProt API for Enhanced Recall (Secondary Step):** After the direct comparison, a `UniProtMappingClient` (defined in `mapping_clients`) can be employed:
        1.  To take UniProt ACs (especially those that didn't find an initial match).
        2.  To query the official UniProt API for any known historical, merged, or alternative UniProt ACs.
        3.  To use these "expanded" UniProt ACs for a subsequent round of comparison against the target dataset.

This layered approach simplifies initial configuration while allowing for sophisticated enhancements to mapping recall. The `MappingExecutor` can be guided to use UniProt AC as the PSO, and specific `mapping_paths` can be defined to leverage the `UniProtMappingClient` for the secondary step.
