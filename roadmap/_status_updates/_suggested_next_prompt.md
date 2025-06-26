# Suggested Next Work Session Prompt

## Context Brief
The project is critically blocked. While the core `biomapper` library is stable with a fully passing test suite, the `biomapper-api` server fails to start with a `ModuleNotFoundError: No module named 'biomapper.api'`. This prevents any end-to-end testing and blocks all further progress on the service-oriented architecture and UI development.

## Initial Steps
1.  **Review `CLAUDE.md`:** Start by reviewing `/home/trentleslie/github/biomapper/CLAUDE.md` for overall project context and goals.
2.  **Review Offboarding Summary:** Read the latest status update for a complete overview of our last session and the current critical issue: `/home/trentleslie/github/biomapper/roadmap/_status_updates/2025-06-25-final-offboarding-summary.md`.

## Work Priorities

### Priority 1: Fix the API Server Startup
- **This is the only priority.** Nothing else can proceed until the API server runs.
- **Action:** Investigate and resolve the `ModuleNotFoundError: No module named 'biomapper.api'`.
- **Suggested Investigation Steps:**
    1.  Inspect the project structure: `ls -R /home/trentleslie/github/biomapper/biomapper`. Does an `api` directory with an `__init__.py` file exist inside it?
    2.  Review `pyproject.toml` to see how packages and modules are defined. Is the `biomapper` package configured correctly to include submodules?
    3.  Try running `poetry install` again to ensure the environment is set up correctly in editable mode.
    4.  Once a fix is attempted, try running the server again: `poetry run uvicorn biomapper.api.main:app --host 0.0.0.0 --port 8000`.

### Priority 2: Validate the Fix
- Once the server starts successfully, run the client script to confirm end-to-end functionality:
  - `python /home/trentleslie/github/biomapper/scripts/main_pipelines/run_full_ukbb_hpa_mapping.py`

## References
- **Offboarding Summary:** `/home/trentleslie/github/biomapper/roadmap/_status_updates/2025-06-25-final-offboarding-summary.md`
- **Main API File:** `/home/trentleslie/github/biomapper/biomapper/api/main.py` (Assumed location, needs verification)
- **Project Configuration:** `/home/trentleslie/github/biomapper/pyproject.toml`