# Mapping Executor Architecture

## 1. Overview

The `MappingExecutor` is the central component of the Biomapper system responsible for orchestrating the process of mapping identifiers between different biological ontologies or databases. It leverages a configuration-driven approach, reading mapping paths and resource details from the `metamapper.db` database and executing the necessary steps using pluggable client modules.

The primary goal is to provide a flexible and extensible framework for defining and executing complex, multi-step mapping workflows.

## 2. Core Components

### 2.1. `MappingExecutor` (`biomapper.core.mapping_executor.py`)

- **Role:** The main orchestrator.
- **Functionality:**
    - Initializes connections to `metamapper.db` (configuration) and `mapping_cache.db` (results).
    - Receives mapping requests specifying source/target endpoints and properties.
    - Queries `metamapper.db` to find the most suitable `MappingPath` based on the request and path priorities.
    - Iterates through the steps defined in the selected `MappingPath`.
    - Instantiates the appropriate mapping client for each step using the `client_class_path` defined in the `MappingResource`.
    - Invokes the `map_identifiers` method on the client instance, passing necessary configuration from the `MappingResource`'s `config_template`.
    - Collects results from each step, potentially using the output of one step as the input for the next.
    - Handles errors during path finding or step execution.
    - Caches the final mapping results and logs the execution details (path taken, status, timestamps) in `mapping_cache.db`.

### 2.2. Mapping Clients (e.g., `biomapper.mapping.clients.*`)

- **Role:** Implement the actual logic for interacting with external APIs or local data sources to perform a specific mapping task (e.g., Gene Name -> UniProt AC, UniProt AC -> Arivale ID lookup).
- **Design:** Clients are designed as adapters. They must implement:
    - An `__init__(self, config: Optional[Dict[str, Any]] = None)` method that accepts configuration (often unused if config is passed to `map_identifiers`).
    - An `async def map_identifiers(self, identifiers: List[str], config: Optional[Dict[str, Any]] = None) -> Dict[str, List[str]]` method. This method takes a list of input identifiers and the specific configuration for that mapping step (from the `MappingResource.config_template`). It returns a dictionary mapping input identifiers to a *list* of corresponding output identifiers.
- **Instantiation:** The `MappingExecutor` dynamically imports and instantiates the client class specified in the `MappingResource.client_class_path`.

### 2.3. `metamapper.db` (Configuration Database)

- **Role:** Stores the static configuration defining how mappings *can* be performed.
- **Key Tables (defined in `biomapper.db.models`):**
    - `Endpoint`: Represents data sources or contexts (e.g., `UKBB_Protein`, `Arivale_Protein`).
    - `MappingResource`: Defines tools/APIs/lookups available for mapping (e.g., `UniProt_NameSearch`, `Arivale_Metadata_Lookup`). Includes the client class path and configuration template.
    - `MappingPath`: Defines a specific sequence of steps (using `MappingResource`s) to get from a source ontology type to a target ontology type (e.g., `UKBB_GeneName_to_Arivale_Protein`). Includes source/target types and priority.
    - `MappingPathStep`: Defines a single step within a `MappingPath`, linking to a `MappingResource`.
    - `PropertyExtractionConfig`: Defines how to extract specific properties (identified by an `ontology_type`) from an `Endpoint`.
    - `EndpointPropertyConfig`: Links `Endpoint`s to `PropertyExtractionConfig`s, defining the available properties for each endpoint (e.g., `UKBB_Protein` has `PrimaryIdentifier` which is `GENE_NAME`).
- **Population:** Typically populated by the `scripts/populate_metamapper_db.py` script.
- **Further Details:** See `data/README_db_config.md` for more detailed schema information.

### 2.4. `mapping_cache.db` (Results Database)

- **Role:** Stores the results of mapping executions and associated logs.
- **Key Tables (defined in `biomapper.db.cache_models`):**
    - `EntityMapping`: Stores the successful mappings between individual source and target identifiers for a given path execution.
    - `PathExecutionLog`: Records details about each run of the `MappingExecutor`, including the path taken, input identifiers, status (success/failure), and timestamps.
- **Purpose:** Avoids redundant computation/API calls for previously mapped identifiers and provides provenance.
- **Further Details:** See `data/README_db_config.md` for more detailed schema information.

## 3. Configuration (`scripts/populate_metamapper_db.py`)

Configuration is primarily managed by defining instances of the SQLAlchemy models mentioned above in the `populate_metamapper_db.py` script.

- **Endpoints:** Define your data sources/contexts.
- **Properties:** Define properties using `PropertyExtractionConfig` (specifying `ontology_type`) and link them to Endpoints via `EndpointPropertyConfig`.
- **Mapping Resources:** Define the tools/clients available. Crucially, specify the `client_class_path` and any necessary `config_template` (as a JSON string) that will be passed to the client's `map_identifiers` method.
- **Mapping Paths:** Define the allowed routes between ontology types by creating `MappingPath` instances, specifying `source_type`, `target_type`, `priority`, and a list of `MappingPathStep`s that link to the required `MappingResource`s in the correct order.

**Important:** Ontology terms (`source_type`, `target_type`, `input_ontology_term`, `output_ontology_term`, `ontology_type`) MUST use consistent casing (currently uppercase, e.g., `GENE_NAME`) as database lookups are case-sensitive.

## 4. Execution Flow

1.  **Request:** `MappingExecutor.execute_mapping` is called with `source_endpoint_name`, `target_endpoint_name`, `input_identifiers`, `source_property_name`, and `target_property_name`.
2.  **Property Lookup:** The executor queries `metamapper.db` to find the `ontology_type` corresponding to the source and target properties for the given endpoints.
3.  **Path Finding:** It queries `metamapper.db` for `MappingPath`s that match the determined source and target `ontology_type`s, ordering them by `priority`.
4.  **Path Selection:** The highest priority valid path is selected.
5.  **Step Execution Loop:**
    a. For each `MappingPathStep` in the selected path:
    b. Identify the required `MappingResource`.
    c. Instantiate the client specified by `resource.client_class_path`.
    d. Call `client.map_identifiers`, passing the input identifiers for this step (initially the request's `input_identifiers`, subsequently the output of the previous step) and the parsed `resource.config_template`.
    e. Collect the results.
6.  **Result Aggregation:** Map the final output identifiers back to the original input identifiers.
7.  **Caching:** Store the successful `(original_input_id, final_output_id)` pairs in the `EntityMapping` table and log the overall execution in `PathExecutionLog`.
8.  **Return:** Return a dictionary containing the status and the aggregated results.

## 5. Extensibility

Adding new mapping capabilities involves:

1.  **Create a New Client:**
    - Implement a new Python class in `biomapper.mapping.clients`.
    - Ensure it has the required `__init__` and `async def map_identifiers` methods.
    - The `map_identifiers` method should handle the specific API interaction or data lookup required.
2.  **Define a New `MappingResource`:**
    - In `scripts/populate_metamapper_db.py`, add a new entry to the `resources` dictionary.
    - Specify a unique name, description, the `client_class_path` pointing to your new client, `input_ontology_term`, `output_ontology_term`, and any necessary `config_template`.
3.  **Define a New `MappingPath` (Optional):**
    - If the new resource enables a completely new path between ontology types, define a new `MappingPath` in `scripts/populate_metamapper_db.py`.
    - Add `MappingPathStep`s, including one that references your new `MappingResource`.
    - **OR:** If the new resource provides an alternative step within an *existing* conceptual path, you might create a new `MappingPath` with a different priority that utilizes the new resource.
4.  **Update Endpoints/Properties (If Necessary):**
    - If the new mapping involves new data sources or identifier types, define new `Endpoint`s and/or `PropertyExtractionConfig`s / `EndpointPropertyConfig`s.
5.  **Regenerate `metamapper.db`:** Run `poetry run python scripts/populate_metamapper_db.py`.
