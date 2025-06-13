# Biomapper Configuration Files (`configs/`)

This directory contains YAML configuration files that define the data sources, ontologies, and mapping strategies for different biological entity types within the Biomapper system. These configurations are crucial for populating the `metamapper.db` metadata database and guiding the `MappingExecutor` during the mapping processes.

## Configuration Structure

The configuration system is divided into two types of files:

### 1. Entity Configuration Files (e.g., `protein_config.yaml`, `metabolite_config.yaml`)
These files define:
- **Ontologies**: Identifier types for the entity
- **Databases**: Data sources and their endpoints
- **Mapping Paths**: Direct conversion sequences between ontologies
- **Additional Resources**: External API clients and services

### 2. Mapping Strategies Configuration (`mapping_strategies_config.yaml`)
This centralized file contains:
- **Generic Strategies**: Reusable across all entity types
- **Entity-Specific Strategies**: Complex pipelines for specific entities
- **Composition Rules**: How strategies can be combined
- **Selection Hints**: Guidance on when to use each strategy

## Structure of Entity Configuration Files

Each entity configuration file follows a structured format to provide a comprehensive definition of an entity type, its associated identifier types (ontologies), the data sources (endpoints) that contain these entities, and the methods (clients and paths) to map between different identifier types.

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

**Note**: Mapping strategies have been moved to a separate configuration file (`mapping_strategies_config.yaml`) for better organization and reusability across entity types. Entity configuration files should no longer contain a `mapping_strategies` section.

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

## Action Types Reference

For information about the action types available in mapping strategies, see:
- `/home/ubuntu/biomapper/docs/ACTION_TYPES_REFERENCE.md`

Action types are the building blocks of mapping strategies, each corresponding to a method in the MappingExecutor. Understanding these action types is essential for creating new mapping strategies.

## Mapping Strategies Configuration

Mapping strategies are now centralized in `mapping_strategies_config.yaml`. This file contains:

### Generic Strategies
Reusable strategies that work across entity types:
- **DIRECT_SHARED_ONTOLOGY_MATCH**: Simple matching when endpoints share an ontology
- **BRIDGE_VIA_COMMON_ID**: Use a common identifier as bridge between endpoints
- **RESOLVE_AND_MATCH**: Handle deprecated/historical identifiers before matching

### Entity-Specific Strategies
Complex pipelines tailored to specific entity types:
- **protein.UKBB_TO_HPA_PROTEIN_PIPELINE**: Maps UKBB assay IDs to HPA gene names
- **protein.HANDLE_COMPOSITE_UNIPROT**: Processes composite UniProt IDs
- **metabolite.PUBCHEM_TO_HMDB_VIA_INCHIKEY**: Maps using chemical structure keys

### Using the Separated Configuration

1. **Loading Order**: The `populate_metamapper_db.py` script processes entity configs first, then mapping strategies
2. **Config Type Detection**: Files with `config_type: "mapping_strategies"` are handled differently
3. **Backward Compatibility**: The system warns if strategies are found in entity configs but continues to work

## Migration Guide

If you have existing entity configs with mapping strategies:

1. **Move strategies** to `mapping_strategies_config.yaml` under appropriate sections
2. **Update references** if any scripts directly reference strategy names
3. **Test thoroughly** to ensure strategies still work correctly
4. **Remove old sections** from entity configs once migration is verified

## Approaching New Mappings: A Systematic Workflow

When faced with a new mapping requirement, follow this systematic discovery-to-implementation workflow:

### Phase 1: Discovery - Examine the Actual Data

Before creating any configuration, thoroughly understand your data:

```bash
# Examine source data structure
head -20 /path/to/source_data.csv
# Note: Column names, identifier formats, sample values

# Examine target data structure  
head -20 /path/to/target_data.csv
# Note: What identifiers are available, data quality

# Check for missing values, duplicates, formatting issues
```

### Phase 2: Strategy Design - Plan the Mapping Approach

Based on your discovery, answer these key questions:

1. **What identifiers does the source have?**
   - Primary identifiers (e.g., proprietary assay IDs)
   - Secondary identifiers (e.g., UniProt, Gene names)
   - Are identifiers composite or simple?

2. **What identifiers does the target expect?**
   - What is the target's primary identifier?
   - What secondary identifiers are available for matching?

3. **Is there a direct path or do we need bridges?**
   - Do source and target share any identifier types?
   - If not, what intermediate identifier can connect them?
   - For proteins: UniProt often serves as a universal bridge

4. **Are there deprecated/obsolete IDs to resolve?**
   - Do identifiers need historical resolution (e.g., old UniProt IDs)?
   - Are there versioning issues to handle?

5. **Should we filter by target presence?**
   - Is it valuable to reduce the dataset early?
   - Will filtering improve performance without losing mappings?

6. **Are there composite/complex identifiers?**
   - Do any IDs contain multiple values (e.g., "Q14213_Q8NEV9")?
   - Do IDs need parsing or transformation?

### Phase 3: Configuration - Fill the Gaps

Based on your strategy design, update the configuration files:

#### In Entity Configuration (e.g., `protein_config.yaml`):

1. **Define new ontologies** if needed:
   ```yaml
   ontologies:
     - id: "NEW_ID_TYPE_ONTOLOGY"
       name: "Human Readable Name"
       description: "What this identifier represents"
   ```

2. **Add endpoint definitions** for new data sources:
   ```yaml
   databases:
     new_dataset:
       name: "New Dataset Name"
       endpoint:
         type: "PRIMARY_ONTOLOGY_TYPE"
         properties:
           primary: "PRIMARY_ONTOLOGY_TYPE"
           mappings:
             PRIMARY_ONTOLOGY_TYPE:
               column: "id_column_name"
               ontology_type: "PRIMARY_ONTOLOGY_TYPE"
             SECONDARY_ONTOLOGY_TYPE:
               column: "secondary_id_column"
               ontology_type: "SECONDARY_ONTOLOGY_TYPE"
       connection_details:
         type: "file.csv"  # or file.tsv
         path: "${DATA_DIR}/path/to/file.csv"
   ```

3. **Create mapping clients** if external resolution is needed:
   ```yaml
   mapping_clients:
     new_resolver_client:
       type: "biomapper.mapping.clients.NewResolverClient"
       input_ontology_type: "INPUT_TYPE"
       output_ontology_type: "OUTPUT_TYPE"
       config:
         api_endpoint: "https://api.example.com"
   ```

#### In Strategies Configuration (`mapping_strategies_config.yaml`):

Design your mapping strategy step by step:

```yaml
entity_strategies:
  protein:  # or metabolite, gene, etc.
    NEW_MAPPING_PIPELINE:
      description: "Maps X to Y via Z"
      default_source_ontology_type: "SOURCE_PRIMARY_ONTOLOGY"
      default_target_ontology_type: "TARGET_PRIMARY_ONTOLOGY"
      steps:
        - step_id: "S1_INITIAL_CONVERSION"
          description: "Convert source IDs to bridge format"
          action:
            type: "CONVERT_IDENTIFIERS_LOCAL"
            endpoint_context: "SOURCE"
            output_ontology_type: "BRIDGE_ONTOLOGY_TYPE"
        
        - step_id: "S2_RESOLVE_IF_NEEDED"
          description: "Resolve deprecated IDs"
          action:
            type: "EXECUTE_MAPPING_PATH"
            path_name: "RESOLVER_PATH_NAME"
        
        - step_id: "S3_FILTER_BY_TARGET"
          description: "Keep only IDs present in target"
          action:
            type: "FILTER_IDENTIFIERS_BY_TARGET_PRESENCE"
            endpoint_context: "TARGET"
            ontology_type_to_match: "BRIDGE_ONTOLOGY_TYPE"
        
        - step_id: "S4_FINAL_CONVERSION"
          description: "Convert to target's native IDs"
          action:
            type: "CONVERT_IDENTIFIERS_LOCAL"
            endpoint_context: "TARGET"
            input_ontology_type: "BRIDGE_ONTOLOGY_TYPE"
            output_ontology_type: "TARGET_PRIMARY_ONTOLOGY"
```

### Phase 4: Implementation - Load and Test

1. **Validate configuration**:
   ```bash
   python scripts/setup_and_configuration/validate_config_separation.py
   ```

2. **Load into database**:
   ```bash
   python scripts/setup_and_configuration/populate_metamapper_db.py --drop-all
   ```

3. **Test with small sample**:
   - Use the notebook to test on a subset
   - Verify each step produces expected results
   - Check for data quality issues

4. **Run full pipeline**:
   - Create a script following the pattern in `run_full_ukbb_hpa_mapping.py`
   - Monitor performance and results

### Example: UKBB to HPA Protein Mapping

This real example illustrates the workflow:

**Discovery**:
- UKBB has proprietary assay IDs + UniProt column
- HPA uses gene names + UniProt column
- Both have UniProt → can use as bridge

**Strategy Design**:
- Path: UKBB ID → UniProt → Resolved UniProt → Filter by HPA → HPA Gene
- Need UniProt resolution for obsolete IDs
- Filter improves performance

**Configuration**:
- Added UKBB_PROTEIN_ASSAY_ID_ONTOLOGY to ontologies
- Created UKBB_PROTEIN and HPA_OSP_PROTEIN endpoints
- Designed 4-step UKBB_TO_HPA_PROTEIN_PIPELINE strategy

**Result**: Successfully maps 487 of 2,923 proteins (after filtering)

### Best Practices

1. **Always examine real data first** - Don't assume column names or formats
2. **Start simple** - Test direct matching before adding complexity
3. **Use existing bridges** - UniProt for proteins, InChIKey for metabolites
4. **Filter strategically** - Balance performance with mapping coverage
5. **Document your reasoning** - Explain why each step is necessary
6. **Test incrementally** - Verify each step before adding the next

### Common Pitfalls to Avoid

- **Assuming identifier formats** - Always check actual data
- **Over-engineering** - Start with the simplest strategy that works
- **Ignoring data quality** - Handle missing values and formatting issues
- **Skipping validation** - Test thoroughly before full runs
- **Hardcoding paths** - Use configuration-driven approach
