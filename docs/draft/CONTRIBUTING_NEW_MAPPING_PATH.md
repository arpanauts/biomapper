# Contributing a New Mapping Path to Biomapper

This guide provides a comprehensive walkthrough for adding a new mapping path to the Biomapper framework. Mapping paths define how Biomapper can transform identifiers from a source entity type to a target entity type, potentially through multiple steps using different mapping clients or resources.

**Audience:** Developers (human or LLM) familiar with Python, SQLAlchemy, and basic bioinformatics identifier concepts, but potentially new to the Biomapper internals.

**Goal:** To configure Biomapper to support a new transformation between two types of biological identifiers (e.g., mapping Arivale Protein IDs to UniProtKB Accessions).

## Prerequisites

Before adding a mapping path, ensure you understand these core Biomapper concepts:

1.  **Endpoints:** Represent data sources or targets (e.g., "UKBB_Protein", "Arivale_Proteomics", "UniProtKB"). Defined in the `Endpoints` table in `metamapper.db`. Associated with connection details (like file paths) and property configurations.
2.  **Ontology Types:** Standardized strings representing the *type* of identifier being mapped (e.g., `UNIPROTKB_AC`, `ENSEMBL_GENE`, `ARIVALE_PROTEIN_ID`, `ENSEMBL_PROTEIN`). Used for matching compatible resources and paths.
3.  **Mapping Clients:** Python classes (typically inheriting from `BaseMappingClient`) that implement the actual logic to perform a mapping lookup (e.g., querying an API, looking up in a file). Found in `biomapper/mapping/clients/` or `biomapper/clients/`.
4.  **Mapping Resources:** Define *how* a specific `MappingClient` is used to map between two specific `Ontology Types`. They link a client implementation to the input/output types it handles and any necessary configuration. Defined in the `MappingResources` table in `metamapper.db`.
5.  **Mapping Paths:** Define a sequence of one or more `MappingPathSteps`, where each step uses a `MappingResource` to transform identifiers from one type towards the final target type. Defined in the `MappingPaths` table in `metamapper.db`.
6.  **`metamapper.db`:** The SQLite database (located at `biomapper/data/metamapper.db` by default) storing all the configuration for endpoints, resources, paths, etc.
7.  **`populate_metamapper_db.py`:** The script used to programmatically define and populate `metamapper.db` with all the necessary configuration objects. **This is the primary file you will modify.**
8.  **`MappingExecutor`:** The core Biomapper component that reads `metamapper.db` to find and execute relevant `MappingPaths` based on the requested source and target endpoints.

## Step-by-Step Guide

### Step 1: Define Source and Target Ontology Types

Identify the standardized string representations for the source identifier type and the target identifier type you want to map between. These should ideally align with existing conventions in Biomapper or common bioinformatics standards.

*   **Example:** For mapping Arivale Protein IDs (which are Ensembl Protein IDs) to UniProtKB Accessions, the types are:
    *   Source: `ENSEMBL_PROTEIN`
    *   Target: `UNIPROTKB_AC`

### Step 2: Identify or Implement the Mapping Client

Determine the Python class responsible for performing the actual mapping transformation.

*   **Option A: Reuse Existing Client:** If a client already exists that can perform the required mapping (perhaps with different configuration), identify its class path (e.g., `biomapper.clients.uniprot.UniProtNameClient`).
*   **Option B: Implement New Client:** If no suitable client exists, you (or a collaborating agent like Claude) need to:
    1.  Create a new Python class, typically inheriting from `biomapper.mapping.base_client.BaseMappingClient`.
    2.  Implement the `map_identifiers` method (and potentially `reverse_map_identifiers` if bidirectional mapping is needed for this specific client). This method should contain the logic to perform the lookup (e.g., call an external API, read a file).
    3.  Place the new client file in an appropriate location (e.g., `biomapper/clients/your_client_module.py`).
    4.  Note the full Python class path (e.g., `biomapper.clients.your_client_module.YourNewClient`).

*   **Example:** For `ENSEMBL_PROTEIN` -> `UNIPROTKB_AC`, a new client `UniProtEnsemblProteinMappingClient` was required to interact with the UniProt ID Mapping API. Its path is `biomapper.mapping.clients.uniprot_ensembl_protein_mapping_client.UniProtEnsemblProteinMappingClient`.

### Step 3: Define Endpoints (If Necessary)

If your mapping involves data sources or targets not already represented in `metamapper.db`, you need to define them in the `endpoints` dictionary within `populate_metamapper_db.py`. This involves specifying a name, description, connection details (e.g., file path), and the default ontology type.

*   **Example:** Endpoints like `UKBB_Protein`, `Arivale_Proteomics`, and `UniProtKB` likely already exist. If mapping to a *new* database, you'd add it here.

```python
# In populate_metamapper_db.py
endpoints = {
    "YourNewEndpoint": Endpoint(
        name="YourNewEndpoint",
        description="Description of your new data source/target.",
        default_ontology_type="YOUR_ONTOLOGY_TYPE",
        connection_details=json.dumps({"path": "/path/to/your/data.tsv"}),
        # ... other fields ...
    ),
    # ... other endpoints ...
}
```

### Step 4: Define the Mapping Resource

In `populate_metamapper_db.py`, define a `MappingResource` in the `resources` dictionary. This links your chosen `MappingClient` (from Step 2) to the specific input and output `Ontology Types` (from Step 1) it handles for this task, along with any default configuration.

*   **Key Fields:**
    *   `name`: A unique, descriptive name for this resource usage (e.g., `UniProtEnsemblProteinMapping`).
    *   `description`: Explains what this resource does.
    *   `client_class_path`: The full Python path to the client class (Step 2).
    *   `input_ontology_term`: The source ontology type (Step 1).
    *   `output_ontology_term`: The target ontology type (Step 1).
    *   `config_template` (Optional): A JSON string containing default configuration for the client *when used by this resource*.

*   **Example:**

```python
# In populate_metamapper_db.py
resources = {
    # ... other resources ...
    "uniprot_ensembl_protein_mapping": MappingResource(
        name="UniProtEnsemblProteinMapping",
        description="Maps Ensembl Protein IDs (ENSP...) to UniProtKB accessions using UniProt's ID Mapping API.",
        client_class_path="biomapper.mapping.clients.uniprot_ensembl_protein_mapping_client.UniProtEnsemblProteinMappingClient",
        input_ontology_term="ENSEMBL_PROTEIN",
        output_ontology_term="UNIPROTKB_AC",
        # config_template can be added if the client needs specific defaults here
    ),
}
```

### Step 5: Define the Mapping Path (and Steps)

Define the overall `MappingPath` in the `paths` list within `populate_metamapper_db.py`. A path defines the start (`source_type`) and end (`target_type`) ontology types for the overall transformation. It consists of one or more `MappingPathStep`s, each using a `MappingResource` defined in Step 4.

*   **Key Fields (`MappingPath`):**
    *   `name`: A unique, descriptive name (e.g., `Arivale_Protein_to_UniProtKB`).
    *   `source_type`: The starting ontology type for the *entire path*.
    *   `target_type`: The final target ontology type for the *entire path*.
    *   `priority`: Integer indicating preference (lower numbers tried first).
    *   `description`: Explains the path's purpose.
    *   `steps`: A list of `MappingPathStep` objects.

*   **Key Fields (`MappingPathStep`):**
    *   `mapping_resource_id`: References the `.id` of the `MappingResource` (defined in Step 4) used for this step. Use `resources["resource_name"].id`.
    *   `step_order`: Integer sequence (1, 2, ...).
    *   `description`: Explains what this specific step achieves.

*   **Example (Single Step Path):**

```python
# In populate_metamapper_db.py
paths = [
    # ... other paths ...
    MappingPath(
        name="Arivale_Protein_to_UniProtKB",
        source_type="ARIVALE_PROTEIN_ID", # Starts with the ID type from Arivale endpoint
        target_type="UNIPROTKB_AC",      # Aims to get UniProtKB AC
        priority=1,
        description="Maps Arivale Protein IDs (Ensembl) to UniProtKB accessions using UniProt's ID Mapping API.",
        steps=[
            MappingPathStep(
                # Assumes Arivale Protein ID is equivalent to ENSEMBL_PROTEIN for this client
                mapping_resource_id=resources["uniprot_ensembl_protein_mapping"].id,
                step_order=1,
                description="Map ENSEMBL_PROTEIN -> UNIPROTKB_AC via UniProt ID Mapping API",
            )
            # Add more steps here for multi-hop paths
        ],
    ),
]
```
*Note: The `source_type` of the `MappingPath` might differ from the `input_ontology_term` of the first step's `MappingResource` if the initial data requires interpretation (e.g., `ARIVALE_PROTEIN_ID` needs to be treated as `ENSEMBL_PROTEIN` for the client).* 

### Step 6: Define Ontology Coverage

Add an `OntologyCoverage` entry in `populate_metamapper_db.py`. This explicitly declares that the `MappingResource` you defined covers the transformation between the specified source and target ontology types. It helps the `MappingExecutor` quickly find relevant resources.

*   **Key Fields:**
    *   `resource_id`: References the `.id` of the `MappingResource` (Step 4). Use `resources["resource_name"].id`.
    *   `source_type`: The source ontology type handled by the resource.
    *   `target_type`: The target ontology type produced by the resource.
    *   `support_level`: Describes how the mapping is done (e.g., `api_lookup`, `client_lookup`, `file_lookup`).

*   **Example:**

```python
# In populate_metamapper_db.py
ontology_coverage_configs = [
    # ... other coverage entries ...
    OntologyCoverage(
        resource_id=resources["uniprot_ensembl_protein_mapping"].id,
        source_type="ENSEMBL_PROTEIN",
        target_type="UNIPROTKB_AC",
        support_level="api_lookup", # As it uses the UniProt API
    ),
]
```

### Step 7: Update `populate_metamapper_db.py`

Ensure all the definitions (Endpoints, Resources, Paths, Coverage) you created or modified in the previous steps are correctly placed within the `populate_database` function in `scripts/populate_metamapper_db.py`. Make sure resource names and IDs are referenced correctly between the different configuration sections.

### Step 8: Run `populate_metamapper_db.py`

Execute the script from the project root directory to regenerate `metamapper.db` with your new configuration.

```bash
cd /path/to/biomapper
python scripts/populate_metamapper_db.py
```

Watch for any errors during execution.

### Step 9: Testing the New Path

1.  **Unit Tests:** If you implemented a new client, add unit tests for it.
2.  **Integration Test:** Modify or create a script similar to `scripts/map_ukbb_to_arivale.py` to specifically test your new mapping path.
    *   Set the `SOURCE_ENDPOINT_NAME` and `TARGET_ENDPOINT_NAME` appropriately.
    *   Ensure the `MappingExecutor` is called.
    *   Examine the logs and output file to verify that the `MappingExecutor` selected and executed your new path correctly and produced the expected results.
    *   Pay attention to logs indicating which paths were considered and chosen.

## Considerations

*   **Directionality:** The `MappingPath` definition doesn't explicitly include a direction. The `MappingExecutor` determines usability based on matching the requested source/target endpoints to the path's `source_type` and `target_type` (considering forward and reverse possibilities if enabled). Clients *can* implement `reverse_map_identifiers` if they support bidirectional lookups.
*   **Priority:** Use the `priority` field on `MappingPath` to influence which path is chosen if multiple paths could satisfy a mapping request. Lower numbers have higher priority.
*   **Configuration:** Decide whether client configuration (like API keys, specific database identifiers like `"ENSEMBL_PRO"`) should be hardcoded in the client, passed via `config_template` in the `MappingResource`, or handled via environment variables/external config files loaded by the client itself. For simple, fixed parameters specific to a resource's usage (like `from_db`/`to_db`), embedding them in the client or `config_template` can be reasonable. Sensitive keys should **never** be in the database.
*   **Bidirectional Validation:** When implementing paths, consider how they will be used in the bidirectional validation process. For reliable validation, both forward (S→T) and reverse (T→S) paths should exist. The `validate_bidirectional` parameter in `execute_mapping` enables validation that checks if target IDs map back to their source IDs, providing a three-tiered status: "Validated" (bidirectional success), "UnidirectionalSuccess" (forward only), or "Failed".
*   **Ontology Alignment:** Carefully ensure the `Ontology Types` used in `MappingPath` (`source_type`, `target_type`) align correctly with the `input_ontology_term` and `output_ontology_term` of the `MappingResource`(s) used in its steps.

By following these steps, you can systematically add new mapping capabilities to the Biomapper framework, making it more versatile and powerful.
