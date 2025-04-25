# Contributing a New Mapping Resource to Biomapper

This document outlines the steps required to add a new mapping resource (e.g., a new API, database, or algorithm for translating between ontology types) to the Biomapper project.

## 1. Database Setup

*   **Add Resource Entry:** Add a new row to the `mapping_resources` table in the `metamapper.db` database.
    *   Assign a unique `id` (typically auto-assigned during population).
    *   Provide a descriptive `name` (e.g., 'UniProt_IDMapper', 'UniProt_NameSearch', 'MyNewResource'). This name is used by the executor to identify the resource logic.
    *   Specify the `resource_type` (e.g., 'api', 'db', 'local_file', 'algorithm').
    *   Add a brief `description`.
    *   **Important Note on APIs:** If a single external API provides multiple *distinct mapping functions* via different endpoints (e.g., one endpoint maps ID -> OtherID, another maps Name -> ID), each distinct function should generally be treated as a **separate `MappingResource`** entry. This ensures clarity in `MappingPath` definitions and simplifies the executor's dispatch logic.
    *   Note: General configuration *about* the resource itself goes here.
*   **Define Endpoint Configuration (If applicable):** If your resource acts as an *endpoint* (like SPOKE) or requires specific connection details (like a file path or API key), ensure there is a corresponding entry in the `endpoints` table.
    *   The `connection_info` column in the `endpoints` table stores critical connection parameters as a **JSON string**.
    *   **Example (`endpoints` table):**
        *   For a file-based resource: `connection_info = '{"file_path": "/path/to/data.csv", "delimiter": ","}'`
        *   For an API: `connection_info = '{"url": "https://api.example.com/v1", "api_key": "${EXAMPLE_API_KEY}"}'` (Note the use of environment variable placeholders if needed).
    *   **Verification:** During development, it's crucial to check the actual `connection_info` stored in `metamapper.db` (e.g., using `sqlite3 "SELECT name, connection_info FROM endpoints;"`).
*   **Add Ontology Types:** If the resource introduces or primarily works with ontology types not already present, add them to the relevant table (if we create a dedicated ontology type table, otherwise ensure consistent naming).

## 2. Client Implementation

*   **Create Client Module:** Create a new Python file in `biomapper/mapping/clients/`, named appropriately (e.g., `my_new_resource_client.py`).
*   **Implement Mapping Logic:**
    *   Define a primary function or class method that will perform the mapping. This function should accept standard arguments:
        *   `input_entity` (str): The identifier to map.
        *   `input_ontology` (str): The ontology type of the input entity.
        *   `target_ontology` (str): The desired ontology type for the output.
        *   (Optional) `session` (AsyncSession) if database access is needed within the client.
        *   **`config` (Dict[str, Any]):** If the resource requires connection details, the client's `__init__` method or primary mapping function should accept a configuration dictionary. This dictionary is **automatically parsed** from the `connection_info` JSON string stored in the corresponding `endpoints` table entry.
    *   **Using Configuration:** Inside the client, access parameters directly from the `config` dictionary (e.g., `api_url = config.get('url')`, `api_key = config.get('api_key')`). Handle potential environment variable placeholders (like `${VAR_NAME}`) if necessary, possibly using `os.path.expandvars`.
    *   **Document Configuration:** Clearly document the expected keys and structure of the `config` dictionary in the client's docstrings.
    *   Implement the interaction with the resource (API calls, database queries, file parsing, algorithm execution).
    *   Handle authentication, request limits, error conditions gracefully.
    *   Parse the response to extract the mapped entity/entities and a confidence score (float between 0.0 and 1.0).
*   **Return Value:** The client function must return a `Tuple[Optional[str], float]`, representing the best-mapped entity identifier and its confidence score. Return `(None, 0.0)` on failure.

## 3. Integration with Executor

*   **Update Dispatcher:** Modify the `RelationshipMappingExecutor._execute_mapping_step` method in `biomapper/mapping/relationships/executor.py`.
    *   Add a condition (e.g., `elif resource_id == YOUR_NEW_RESOURCE_ID:`) to the dispatcher logic. *(Note: Dispatching based on `resource_name` might be more robust against changes in population order in the future, but the current implementation often relies on the `resource_id` retrieved alongside the resource details)*.
    *   Inside the condition, import and call your new client function/method, passing the required arguments.
    *   Ensure the return value from your client is correctly handled.

## 4. Define Mapping Paths

*   **Add Path Entries:** Add new rows to the `mapping_paths` table in `metamapper.db`.
    *   Define paths that incorporate the new `resource_id` in their `steps` JSON field.
    *   Ensure the `source_ontology_type` and `target_ontology_type` accurately reflect the overall transformation achieved by the path.
    *   Link the path to the relevant `relationship_id`.
    *   Set `is_enabled` to `True`.
*   **Consider Path Evaluation:** Think about how this new path compares to existing ones. Does it offer a more direct route? Higher confidence? Should it be preferred for certain relationships? This might involve updating `OntologyPreference` entries if the resource provides a preferred intermediate type for certain endpoints.

## 5. Testing

*   **Unit Tests:** Create unit tests for your new client module in the `tests/` directory. Test:
    *   Successful mapping cases.
    *   Handling of invalid inputs.
    *   Error conditions (API errors, missing data).
    *   Correct parsing of responses.
*   **Integration Tests:** (Optional but recommended) Add integration tests that define a relationship and path using the new resource, then run `RelationshipMappingExecutor.map_entity` to ensure it works end-to-end.

## 6. Documentation

*   **Update Resource List:** Add the new resource to any user-facing documentation lists.
*   **Client Documentation:** Add docstrings to your client module and functions.
*   **(Optional) Update Main Docs:** If the resource significantly changes capabilities, update relevant sections of the main project documentation.
