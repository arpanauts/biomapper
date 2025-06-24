# Task: Refactor Configuration with Pydantic-Settings

**Source Prompt Reference:** Orchestrator-generated task to improve configuration management.

## 1. Task Objective

To refactor the API's configuration management to use the `pydantic-settings` library. This will replace the manual environment variable loading (`load_dotenv`, `os.getenv`) with a more robust, declarative, and type-safe approach.

## 2. Service Architecture Context

- **Primary Service:** `biomapper-api`
- **Files to Modify:**
    - `/home/ubuntu/biomapper/biomapper-api/app/core/config.py`
    - `/home/ubuntu/biomapper/biomapper-api/pyproject.toml` (to add the new dependency)

## 3. Task Decomposition

1.  **Add Dependency:** Add `pydantic-settings` to the `dependencies` section of the `pyproject.toml` file.
2.  **Refactor `Settings` Class:**
    *   In `config.py`, change the `Settings` class to inherit from `pydantic_settings.BaseSettings` instead of `pydantic.BaseModel`.
    *   Remove the manual `load_dotenv()` call.
    *   Remove the manual `os.getenv()` calls for individual settings. `pydantic-settings` handles this automatically by matching field names to environment variable names (case-insensitively).
    *   Add a `model_config` inner class to specify the `.env` file path and other settings:
        ```python
        from pydantic_settings import BaseSettings, SettingsConfigDict

        class Settings(BaseSettings):
            PROJECT_NAME: str = "Biomapper API"
            # ... other fields

            model_config = SettingsConfigDict(env_file=".env", env_file_encoding='utf-8')
        ```
3.  **Verify Functionality:** Ensure that all settings, including the `Path` objects and the dynamic `MAX_UPLOAD_SIZE`, are still configured correctly.

## 4. Implementation Requirements

- The refactored `Settings` class should be cleaner and no longer contain manual environment variable loading logic.
- The application must behave identically to before the refactor.
- Ensure the `STRATEGIES_DIR` setting added previously is preserved.

## 5. Success Criteria and Validation

- The two specified files are modified correctly.
- The API starts up without any configuration-related errors.
- The settings are still correctly loaded from environment variables or the `.env` file.

## 6. Feedback Requirements

Create a detailed Markdown feedback file at:
`[PROJECT_ROOT]/roadmap/_active_prompts/feedback/YYYY-MM-DD-HHMMSS-feedback-08-advanced-configuration.md`

Include:
-   **Execution Status:** [COMPLETE_SUCCESS | PARTIAL_SUCCESS | FAILED]
-   **Links to Artifacts:** Links to the modified files.
-   **Summary of Changes:** A brief before-and-after comparison of the `Settings` class to highlight the improvements.
