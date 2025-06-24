# Task: Develop Python SDK for biomapper-api

**Source Prompt Reference:** Orchestrator-generated task to improve API usability.

## 1. Task Objective

To create a simple, installable Python client SDK for the `biomapper-api`. This will abstract away the details of HTTP requests and provide a clean, programmatic interface for other services or scripts to interact with the API.

## 2. Service Architecture Context

- **Primary Service:** This is a new, standalone package.
- **Files to Create:**
    - `/home/ubuntu/biomapper/biomapper_client/` (new directory)
    - `/home/ubuntu/biomapper/biomapper_client/pyproject.toml`
    - `/home/ubuntu/biomapper/biomapper_client/biomapper_client/` (new package directory)
    - `/home/ubuntu/biomapper/biomapper_client/biomapper_client/client.py`
    - `/home/ubuntu/biomapper/biomapper_client/README.md`

## 3. Task Decomposition

1.  **Set up Package Structure:** Create the directory and file structure outlined above.
2.  **Create `pyproject.toml`:** Define the package metadata (name, version, author) and its dependencies, which should include `httpx` and `pydantic`.
3.  **Implement `BiomapperClient` Class:**
    *   In `client.py`, create a class named `BiomapperClient`.
    *   The `__init__` method should accept an optional `base_url` (defaulting to `http://localhost:8000`) and initialize an `httpx.AsyncClient`.
    *   Implement an `async def execute_strategy(self, strategy_name: str, context: dict) -> dict:` method.
    *   This method should handle making the `POST` request to `/api/strategies/{strategy_name}/execute`.
    *   It should handle JSON serialization of the request body and deserialization of the response.
    *   It should raise an exception if the API returns a non-200 status code.
4.  **Write `README.md`:** Create a simple README file with installation instructions (`pip install .`) and a basic usage example showing how to instantiate the client and call `execute_strategy`.

## 4. Implementation Requirements

- The client must be fully asynchronous.
- The client should manage the lifecycle of the `httpx.AsyncClient` correctly (e.g., using `async with`).
- Provide clear error handling for network issues or API errors.

## 5. Success Criteria and Validation

- The `biomapper_client` directory and its contents are created.
- The package can be installed locally using `pip`.
- A separate script can import the `BiomapperClient` and successfully call the API (once the API is ready).

## 6. Feedback Requirements

Create a detailed Markdown feedback file at:
`[PROJECT_ROOT]/roadmap/_active_prompts/feedback/YYYY-MM-DD-HHMMSS-feedback-04-develop-python-sdk.md`

Include:
-   **Execution Status:** [COMPLETE_SUCCESS | PARTIAL_SUCCESS | FAILED]
-   **Links to Artifacts:** Links to the new files created.
-   **Summary of Changes:** A description of the client's features and a code snippet showing how to use it.
