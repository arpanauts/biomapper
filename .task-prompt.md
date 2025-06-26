# Task 1: Debug and Resolve Poetry Environment Failure

**Source Prompt Reference:** This is the highest priority task to unblock all `biomapper-api` development and testing.

## 1. Task Objective
Diagnose and definitively resolve the root cause of the Python/Poetry environment failure for the `biomapper-api` service. The primary symptom is that dependencies, such as `uvicorn` and `fastapi`, are not available within the virtual environment after installation commands are run, leading to a `ModuleNotFoundError` at runtime.

## 2. Service Architecture Context
- **Primary Service:** `biomapper-api`
- **API Endpoints Required:** None. The goal is to enable the server to start.
- **Service Dependencies:** The issue lies within the `biomapper-api`'s own Poetry environment.

## 3. Problem Context and History
The `biomapper-api` service cannot be started with `uvicorn` because of a `ModuleNotFoundError`. Multiple attempts to install the required dependencies using both Poetry and pip have failed to populate the virtual environment correctly.

**Summary of Failed Attempts:**
1.  **`poetry install`:** Runs without error but fails to install dependencies. `poetry run pip list` shows a nearly empty environment.
2.  **Recreating the Environment:** The virtual environment was successfully removed (`poetry env remove ...`) and recreated, but the issue persists on the fresh environment.
3.  **Direct Pip Install:** Using the virtual environment's `pip` executable directly (`/path/to/venv/bin/pip install ...`) also failed to make the packages available at runtime, even though the command itself reported success.

## 4. Task Decomposition
1.  **Deep Environment Analysis:** Conduct a thorough investigation of the Poetry configuration, environment variables, system path, and file permissions that could interfere with package installation.
2.  **Diagnose Installation Failure:** Determine precisely why installation commands are not working. This may involve using verbose flags (`-vvv`), checking Poetry's cache (`poetry cache clear --all .`), and analyzing system logs if necessary.
3.  **Establish a Reliable Installation:** Find and execute a robust method to install the dependencies listed in `biomapper-api/pyproject.toml` into the virtual environment.
4.  **Validate the Fix:** Confirm that the dependencies are correctly installed and visible within the environment.
5.  **Start the Server:** Successfully launch the `biomapper-api` service.

## 5. Implementation Requirements
- **Project Root:** `/home/trentleslie/github/biomapper/biomapper-api`
- **Key Commands for Investigation:**
  - `poetry env info -v`
  - `poetry config --list`
  - `poetry run which python`
  - `which poetry`
  - `ls -la /home/trentleslie/.cache/pypoetry/virtualenvs/`
  - `poetry install -vvv`

## 6. Success Criteria and Validation
- **Primary Criteria:** The command `poetry run python -m uvicorn app.main:app --host 0.0.0.0 --port 8000` successfully starts the API server.
- **Validation Steps:**
  - [ ] The command `poetry run pip list` shows `fastapi`, `uvicorn`, and other required packages are installed.
  - [ ] The API server logs show a successful startup sequence.
