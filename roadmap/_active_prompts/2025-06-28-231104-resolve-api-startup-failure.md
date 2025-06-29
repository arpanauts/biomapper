# Task: Resolve Critical API Startup Failure and Validate Pipeline

**Source Prompt Reference:** This task is defined by the prompt: `/home/ubuntu/biomapper/roadmap/_active_prompts/2025-06-28-231104-resolve-api-startup-failure.md`. It is based on the findings in `/home/ubuntu/biomapper/roadmap/_status_updates/2025-06-25-final-offboarding-summary.md`.

## 1. Task Objective

The primary objective is to diagnose and fix the `ModuleNotFoundError` that prevents the `biomapper-api` service from starting. The ultimate success criterion is the successful execution of the end-to-end data processing pipeline, which is currently blocked.

## 2. Service Architecture Context
- **Primary Service:** `biomapper-api`
- **API Endpoints Required:** 
    - `GET /api/health` (for verifying the service is up)
    - `POST /api/strategies/execute` (used by the validation script)
    - `GET /api/mappings/{mapping_id}` (used by the validation script)
- **Service Dependencies:** The `biomapper-api` service depends on the `biomapper` core library.
- **Configuration Files:** `pyproject.toml` is the primary file that will likely require modification.

## 3. Prerequisites
- [x] The project code is checked out at `/home/ubuntu/biomapper/`.
- [x] `poetry` is used for dependency management.
- [ ] **Problem:** `biomapper-api` service is **not** running due to the startup error.

## 4. Context from Previous Attempts
Running `poetry run uvicorn biomapper.api.main:app --reload` from the project root fails with `ModuleNotFoundError: No module named 'biomapper.api'`. This strongly suggests an issue with how the project's packages are defined in `pyproject.toml`, preventing Poetry from making the `biomapper.api` submodule available in the environment's path.

## 5. Task Decomposition
Break this task into the following verifiable subtasks:
1.  **[Investigation]:** Diagnose the root cause. Inspect `pyproject.toml`, specifically the `[tool.poetry.packages]` section. Verify the directory structure with `ls -R biomapper` to ensure `biomapper/api/__init__.py` exists.
2.  **[Implementation]:** Modify `pyproject.toml` to correctly configure the project's packages. The fix will likely involve explicitly including the `api` and `client` packages.
3.  **[Dependency Update]:** Run `poetry install` to apply the configuration changes to the virtual environment.
4.  **[Service Verification]:** Start the API service using `poetry run uvicorn biomapper.api.main:app --reload`. Confirm it runs without errors.
5.  **[Integration Testing]:** Execute the end-to-end pipeline script to validate the fix: `poetry run python scripts/main_pipelines/run_full_ukbb_hpa_mapping.py`.

## 6. Implementation Requirements
- **Configuration Updates:** The `[tool.poetry.packages]` section in `pyproject.toml` is likely incorrect. It should be updated to explicitly include all necessary packages.

  **Hypothesized Fix for `pyproject.toml`:**
  ```toml
  [tool.poetry]
  # ... other settings
  packages = [
      { include = "biomapper" },
      { include = "tests", format = "sdist" },
      { include = "scripts", format = "sdist" }
  ]
  ```
  The above is likely the problem. It should probably be changed to something that discovers the subpackages, or lists them explicitly.

- **Testing Requirements:**
  - **Unit Test:** N/A. This is a configuration and packaging issue.
  - **Integration Test:** The primary validation is running the `run_full_ukbb_hpa_mapping.py` script successfully.

## 7. Error Recovery Instructions
Service-specific error handling:
- **`ModuleNotFoundError` (persists):** If the error continues after your fix, double-check the paths in `pyproject.toml`. Ensure there are no typos and that the `__init__.py` files are in place. You may need to clean the poetry cache (`poetry cache clear --all pypi`) and reinstall.
- **`SERVICE_UNAVAILABLE`:** This is the initial state. Your goal is to resolve this. After the fix, if the service doesn't start, check the `uvicorn` logs for a different error.
- **`INTEGRATION_ERROR`:** If the pipeline script fails after the API is running, check the script's console output and the API logs for errors related to API calls, data processing, or strategy execution.

## 8. Success Criteria and Validation
Task is complete when:
- [ ] The command `poetry run uvicorn biomapper.api.main:app --reload` starts the server successfully.
- [ ] A `curl http://localhost:8000/api/health` returns a success status.
- [ ] The command `poetry run python scripts/main_pipelines/run_full_ukbb_hpa_mapping.py` runs to completion without errors.
- [ ] Service logs show no startup errors.

## 9. Deployment Considerations
- **Environment Update:** This change requires running `poetry install` to take effect in any environment where the code is deployed.
- **Configuration Reload:** The fix is at the packaging level; `uvicorn`'s `--reload` will not pick it up. A full stop/start of the server process is required after `poetry install`.

## 10. Feedback Requirements
Create a detailed Markdown feedback file at:
`[PROJECT_ROOT]/roadmap/_active_prompts/feedback/YYYY-MM-DD-HHMMSS-feedback-resolve-api-startup-failure.md`

Include service-specific feedback:
- **Root Cause Analysis:** A brief explanation of the exact issue in `pyproject.toml`.
- **Integration Test Results:** Confirmation of the successful pipeline run.
- **Final `pyproject.toml` snippet:** Show the corrected `[tool.poetry.packages]` section.
