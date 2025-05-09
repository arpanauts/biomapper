# Contributing a New Mapping Resource to Biomapper

This guide provides a comprehensive walkthrough for adding a new mapping resource to the Biomapper framework. A mapping resource represents an external tool, API, database, or algorithm that can be used to translate identifiers between specific ontology types (e.g., using the UniProt ID Mapping API to convert UniProt ACs to Gene Names).

**Audience:** Developers (human or LLM) familiar with Python, SQLAlchemy, basic bioinformatics identifier concepts, and potentially interacting with external APIs or data files, but possibly new to the Biomapper internals.

**Goal:** To implement a new `MappingClient` and configure a corresponding `MappingResource` in Biomapper, making a new translation capability available for use in `MappingPaths`.

## Prerequisites

Before adding a mapping resource, ensure you understand these core Biomapper concepts:

1.  **Endpoints:** Represent data sources or targets (e.g., "UKBB_Protein", "Arivale_Proteomics", "UniProtKB"). Defined in the `Endpoints` table in `metamapper.db`. Associated with connection details (like file paths) and property configurations.
2.  **Ontology Types:** Standardized strings representing the *type* of identifier being mapped (e.g., `UNIPROTKB_AC`, `ENSEMBL_GENE`, `ARIVALE_PROTEIN_ID`, `ENSEMBL_PROTEIN`). Used for matching compatible resources and paths.
3.  **Mapping Clients:** Python classes (typically inheriting from `BaseMappingClient`) that implement the actual logic to perform a mapping lookup (e.g., querying an API, looking up in a file). Found in `biomapper/mapping/clients/` or `biomapper/clients/`. **This is what you will likely implement.**
4.  **Mapping Resources:** Define *how* a specific `MappingClient` is used to map between two specific `Ontology Types`. They link a client implementation to the input/output types it handles and any necessary configuration. Defined in the `MappingResources` table in `metamapper.db`. **This is what you will configure.**
5.  **Mapping Paths:** Define a sequence of one or more `MappingPathSteps`, where each step uses a `MappingResource` to transform identifiers from one type towards the final target type. Defined in the `MappingPaths` table in `metamapper.db`. *(Adding a resource enables its use in these paths)*.
6.  **`metamapper.db`:** The SQLite database (located at `biomapper/data/metamapper.db` by default) storing all the configuration for endpoints, resources, paths, etc.
7.  **`populate_metamapper_db.py`:** The script used to programmatically define and populate `metamapper.db` with all the necessary configuration objects. **This is the primary configuration file you will modify.**
8.  **`MappingExecutor`:** The core Biomapper component that reads `metamapper.db` to find and execute relevant `MappingPaths` based on the requested source and target endpoints. It dynamically uses the configured clients and resources.

## Step-by-Step Guide

### Step 1: Define Input and Output Ontology Types for the Resource

Identify the *specific* standardized ontology types that your new resource will translate between.

*   **Example:** A new UniProt client function might map `UNIPROTKB_AC` (input) to `GENE_NAME` (output).

### Step 2: Implement the Mapping Client

Create the Python class responsible for the mapping logic.

1.  **Create Client Module:**
    *   Create a new Python file in an appropriate location, usually `biomapper/clients/` (e.g., `biomapper/clients/my_new_resource_client.py`).
2.  **Define Client Class:**
    *   Create a class, often inheriting from `biomapper.mapping.base_client.BaseMappingClient` for consistency, although not strictly required if it provides the necessary methods.
    *   Implement an `__init__` method if the client needs initialization (e.g., to set up API sessions or load data).
3.  **Implement Core Mapping Method(s):**
    *   The primary method should typically handle batch processing for efficiency.
    *   **Recommended Signature:**
        ```python
        from typing import List, Dict, Optional, Any
        import asyncio # If performing async operations

        class MyNewResourceClient:
            # ... __init__ if needed ...

            async def map_identifiers(
                self,
                identifiers: List[str],
                input_ontology: str,
                target_ontology: str,
                config: Optional[Dict[str, Any]] = None
            ) -> Dict[str, Optional[List[str]]]:
                """Maps a list of input identifiers to target ontology types.

                Args:
                    identifiers: List of identifiers to map.
                    input_ontology: The ontology type of the input identifiers.
                    target_ontology: The desired ontology type for the output.
                    config: Optional configuration dictionary passed from the
                            MappingResource config_template.

                Returns:
                    A dictionary mapping each input identifier to a list of
                    found target identifiers, or None if no mapping was found
                    for that input.
                """
                results = {}
                # --- Implementation Logic --- 
                # 1. Use 'config' if provided (e.g., API keys, file paths)
                #    Handle environment variable expansion if needed (e.g., os.path.expandvars)
                # 2. Iterate through identifiers (or perform batch API call/query).
                # 3. Handle API interactions, file parsing, DB queries, etc.
                # 4. Handle errors, rate limits, authentication.
                # 5. For each input identifier, populate 'results' dictionary:
                #    results[input_id] = [output_id1, output_id2] or None
                # --- End Logic ---
                return results
        ```
    *   **Configuration (`config` dict):** If your client needs parameters like API keys, URLs, or file paths that might vary depending on *how* the resource is used, accept the `config` dictionary. This dictionary will be populated from the `config_template` JSON defined in the `MappingResource` (Step 3).
    *   **Return Value:** The method should return a dictionary where keys are the *input* identifiers and values are lists of corresponding *output* identifiers found. If no mapping is found for an input ID, its value should be `None`.
    *   **Error Handling:** Implement robust error handling (e.g., network errors, parsing errors, API limits) and log warnings or errors appropriately. Decide if specific errors should result in `None` for an identifier or raise an exception.
    *   **Bidirectionality (Optional):** If the resource can naturally map in the reverse direction, you might implement a `reverse_map_identifiers` method following a similar pattern.

### Step 3: Define Mapping Resource in `populate_metamapper_db.py`

Now, configure how Biomapper should use your new client.

*   **Add `MappingResource` Entry:** In `scripts/populate_metamapper_db.py`, add a `MappingResource` object to the `resources` dictionary or list.
    *   **Key Fields:**
        *   `name`: A unique, descriptive name (e.g., `UniProtAC_to_GeneName`). This might be used internally.
        *   `description`: A brief explanation.
        *   `resource_type`: Categorize the resource (e.g., `api`, `db`, `local_file`, `algorithm`).
        *   `client_class_path`: The **full Python path** to your client class (e.g., `biomapper.clients.my_new_resource_client.MyNewResourceClient`).
        *   `input_ontology_term`: The *specific* ontology type this resource expects as input (e.g., `UNIPROTKB_AC`). Must match Step 1.
        *   `output_ontology_term`: The *specific* ontology type this resource produces (e.g., `GENE_NAME`). Must match Step 1.
        *   `config_template` (Optional): A **JSON string** containing default configuration parameters to be passed to your client's `map_identifiers` method (as the `config` dict). Use this for parameters specific to *this usage* of the client (e.g., specific API endpoints, query flags).
            *   Example: `'{"api_endpoint": "/map_ac_to_gene", "include_synonyms": false}'`
            *   **Avoid storing secrets here.** Use environment variables handled within the client itself for API keys etc.
*   **Example:**
    ```python
    # In populate_metamapper_db.py
    resources = {
        # ... other resources ...
        "uniprot_ac_to_genename": MappingResource(
            name="UniProtAC_to_GeneName",
            description="Maps UniProtKB AC to Gene Name using UniProt API",
            resource_type="api",
            client_class_path="biomapper.clients.uniprot.UniProtClient", # Assuming a generic UniProtClient
            input_ontology_term="UNIPROTKB_AC",
            output_ontology_term="GENE_NAME",
            # Example config_template if the client method needs guidance
            config_template='{"target_db": "Gene_Name"}' 
        ),
    }
    ```

### Step 4: Define Ontology Coverage in `populate_metamapper_db.py`

Explicitly declare the transformation your resource provides.

*   **Add `OntologyCoverage` Entry:** Add an `OntologyCoverage` object to the `ontology_coverage_configs` list.
    *   **Key Fields:**
        *   `resource_id`: References the `.id` of the `MappingResource` (defined in Step 3). Use `resources["resource_name"].id`.
        *   `source_type`: The source ontology type handled (e.g., `UNIPROTKB_AC`).
        *   `target_type`: The target ontology type produced (e.g., `GENE_NAME`).
        *   `support_level`: Describes how the mapping is done (e.g., `api_lookup`, `client_lookup`, `file_lookup`).
*   **Example:**
    ```python
    # In populate_metamapper_db.py
    ontology_coverage_configs = [
        # ... other coverage entries ...
        OntologyCoverage(
            resource_id=resources["uniprot_ac_to_genename"].id,
            source_type="UNIPROTKB_AC",
            target_type="GENE_NAME",
            support_level="api_lookup",
        ),
    ]
    ```

### Step 5 (Optional): Define Endpoint Configuration

This step is usually **not required** for pure mapping resources like an API client. It's needed if your resource *itself* represents a primary data source or target (like a specific database instance or a dataset file) that needs connection details.

*   If needed, add/update an `Endpoint` entry in the `endpoints` dictionary/list in `populate_metamapper_db.py`.
*   Define `connection_info` as a JSON string containing necessary parameters (URLs, file paths, credentials - **use environment variables for secrets**).
*   Reference: See `CONTRIBUTING_NEW_MAPPING_PATH.md` for `Endpoint` details.

### Step 6: Update `populate_metamapper_db.py`

Ensure all the definitions (`MappingResource`, `OntologyCoverage`, optional `Endpoint`) are correctly placed within the `populate_database` function in `scripts/populate_metamapper_db.py`.

### Step 7: Run `populate_metamapper_db.py`

Execute the script to regenerate `metamapper.db`:

```bash
cd /path/to/biomapper
python scripts/populate_metamapper_db.py
```

Check for errors.

### Step 8: Testing

1.  **Unit Tests:**
    *   Create unit tests for your new client class in the `tests/` directory (e.g., `tests/clients/test_my_new_resource_client.py`).
    *   Use `unittest.mock` to patch external dependencies (like API calls, file reads).
    *   Test successful mapping, handling of multiple inputs, empty inputs, expected failures (e.g., ID not found), error conditions, and config parsing.
2.  **Integration Test (Recommended):**
    *   To test the resource end-to-end within Biomapper, you typically need to:
        *   Define a `MappingPath` in `populate_metamapper_db.py` that *uses* your new `MappingResource` (see `CONTRIBUTING_NEW_MAPPING_PATH.md`).
        *   Regenerate `metamapper.db`.
        *   Run a script that calls the `MappingExecutor` for a source/target that requires this path.
        *   Verify logs and output to confirm your resource was called correctly and produced the expected results as part of the path execution.

## Considerations

*   **Client Reusability:** Can your client be made more generic? Could it handle multiple types of mappings based on the `input_ontology`, `target_ontology`, or `config` parameters passed from different `MappingResource` definitions?
*   **Configuration Management:** Sensitive information (API keys, passwords) should **never** be stored directly in `metamapper.db` (`config_template`). Handle these using environment variables or a secure configuration mechanism loaded *within* the client code.
*   **Error Handling:** How should your client report failures? Returning `None` in the result dictionary for an ID indicates a mapping wasn't found. Raising exceptions might be appropriate for critical errors (e.g., invalid config, API outage) that should halt the process.
*   **Bidirectional Support:** Consider implementing `reverse_map_identifiers` in your client to support bidirectional validation. When the `validate_bidirectional` parameter is set in `execute_mapping`, the executor will check if target IDs map back to their source IDs, which requires paths in both directions. If your resource is naturally bidirectional, explicitly supporting this can improve validation results.
*   **Performance & Rate Limits:** Be mindful of external API rate limits. Implement appropriate delays or batching in your client. Consider caching strategies if querying the same identifiers repeatedly.
*   **Resource vs. Endpoint:** Remember, a `MappingResource` is primarily a *translator* between ontology types. An `Endpoint` is a *source* or *target* dataset. Sometimes a service can act as both (e.g., querying UniProt for data *about* an ID vs. using its API to *map* IDs), requiring both `Endpoint` and `MappingResource` configurations.

By following these steps, you can integrate new mapping capabilities into Biomapper, leveraging external tools and data sources to enhance its identifier translation power.
