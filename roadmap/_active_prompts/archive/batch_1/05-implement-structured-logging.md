# Task: Implement Structured Logging

**Source Prompt Reference:** Orchestrator-generated task to improve service observability.

## 1. Task Objective

To replace the default FastAPI/Uvicorn logging with a structured, JSON-based logging format. This will make logs easier to parse, search, and analyze, which is critical for a production service.

## 2. Service Architecture Context

- **Primary Service:** `biomapper-api`
- **Files to Create:** `/home/ubuntu/biomapper/biomapper-api/app/core/logging_config.py`
- **Files to Modify:** `/home/ubuntu/biomapper/biomapper-api/app/main.py`
- **Dependencies:** This task may require adding a new dependency like `structlog`.

## 3. Task Decomposition

1.  **Add Dependency:** If using a library like `structlog`, add it to the project's `pyproject.toml`.
2.  **Create Logging Configuration:**
    *   In the new `logging_config.py` file, create a dictionary that defines the logging configuration for Python's built-in `logging` module.
    *   Configure it to use a JSON formatter. The log records should include a timestamp, log level, message, and other relevant context.
    *   Ensure Uvicorn's access logs are also captured and formatted as JSON.
3.  **Apply Configuration:**
    *   In `main.py`, import `logging.config`.
    *   Call `logging.config.dictConfig()` with your configuration dictionary before the `FastAPI` app is instantiated.
4.  **Test Logging:**
    *   Add a simple log message to the `startup_event` in `main.py` (e.g., `logging.getLogger(__name__).info("API starting up...")`).
    *   Run the server and verify that the console output is in the new JSON format.

## 4. Implementation Requirements

- All logs produced by the application should be in a consistent JSON format.
- The configuration should be easy to modify (e.g., to change the log level from `INFO` to `DEBUG`).
- The solution should be compatible with Uvicorn's logging system.

## 5. Success Criteria and Validation

- The new and modified files are created correctly.
- When the API server is run, all console output is formatted as JSON strings.

## 6. Feedback Requirements

Create a detailed Markdown feedback file at:
`[PROJECT_ROOT]/roadmap/_active_prompts/feedback/YYYY-MM-DD-HHMMSS-feedback-05-implement-structured-logging.md`

Include:
-   **Execution Status:** [COMPLETE_SUCCESS | PARTIAL_SUCCESS | FAILED]
-   **Links to Artifacts:** Links to the new/modified files.
-   **Example Log Output:** A few lines of the new JSON log output to demonstrate the result.
