# Task: Debug Pytest Collection Hang in Biomapper Project

## 1. Task Objective
Diagnose and resolve the persistent issue where `pytest` hangs indefinitely during the test collection phase in the Biomapper project. The goal is to enable `pytest` to successfully collect and subsequently run all relevant tests.

## 2. Background & Context
The Biomapper project's test suite is currently unrunnable because `pytest` (v7.4.4, Python 3.11.12, Poetry managed environment on Linux) consistently stops at the "collecting ..." stage without providing further output or errors. This issue prevents automated testing and validation of recent code changes, including import path fixes and modularization efforts.

**Summary of Previous Debugging (Memory ID: `f463f0ec-34e2-4d85-b584-543010e8ccc9`):**
-   Verified `pytest.ini` and `pyproject.toml` for restrictive discovery patterns; minor adjustments (removing `-q` flag) had no effect.
-   Attempts to collect from specific subdirectories (`tests/cli`, `tests/core`) also resulted in a hang.
-   Examination and temporary modification of `tests/conftest.py` (related to `sys.modules` patching for `PydanticEncoder`) did not resolve the hang.
-   `tests/__init__.py` is minimal. No root `conftest.py` found.
-   Disabling the `pytest-cov` plugin did not solve the issue. The command `poetry run pytest -vv -p no:cov -p no:asyncio -p no:anyio` was attempted but canceled by the user before its result was observed, so the effect of disabling `asyncio` and `anyio` is unknown.

**Current Active Pytest Plugins (if `cov`, `asyncio`, `anyio` are disabled):**
-   `requests-mock-1.12.1`
-   `pytest-mock-3.14.0`

## 3. Detailed Steps & Requirements

1.  **Continue Plugin Isolation:**
    *   **Step 3.1.1:** Execute the command `poetry run pytest -vv -p no:cov -p no:asyncio -p no:anyio` (Cwd: `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/`). Observe if collection proceeds. This command was previously canceled.
    *   **Step 3.1.2:** If the hang persists, systematically disable the remaining plugins (`requests-mock`, `mock`) one by one, and then all together, to identify if any plugin is causing the hang.
        *   Example: `poetry run pytest -vv -p no:cov -p no:asyncio -p no:anyio -p no:requests-mock`
        *   Example: `poetry run pytest -vv -p no:cov -p no:asyncio -p no:anyio -p no:mock`
        *   Example: `poetry run pytest -vv -p no:cov -p no:asyncio -p no:anyio -p no:requests-mock -p no:mock`
    *   Document which plugin (if any) allows collection to proceed.

2.  **Python Debugger (`pdb`) Investigation (If plugins are not the cause):**
    *   **Step 3.2.1:** Launch `pytest` using the Python debugger:
        ```bash
        python -m pdb $(poetry run which pytest) -vv
        ```
        (Ensure Cwd is `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/`)
    *   **Step 3.2.2:** Step through the initial `pytest` loading and collection process. Try to identify the specific function call or module import where `pytest` hangs. This may involve setting breakpoints in `pytest`'s internal code or in project files like `conftest.py`.
    *   Focus on the code paths related to plugin loading and test file discovery.

3.  **Minimal `pytest` Invocation (If `pdb` is inconclusive or too complex):**
    *   **Step 3.3.1:** Temporarily simplify `pyproject.toml` by removing all `addopts` from `[tool.pytest.ini_options]`.
    *   **Step 3.3.2:** Run `poetry run pytest -vv`. If it still hangs, the issue is likely not with `addopts`. Revert `pyproject.toml`.

4.  **Individual Test File Analysis (Advanced, if other methods fail):**
    *   **Step 3.4.1:** Create a temporary, minimal test file (e.g., `tests/temp_test.py`) with a single passing test and no project-specific imports. Attempt to run `pytest` targeting only this file: `poetry run pytest -vv tests/temp_test.py`.
    *   **Step 3.4.2:** If the minimal test runs, incrementally add imports from the project or copy content from existing test files into this temporary file to pinpoint a specific import or code block that triggers the hang.

## 4. Success Criteria & Validation
-   `pytest` successfully completes the collection phase and lists the discovered tests.
-   Ideally, `pytest` should then proceed to run the tests (though fixing test *failures* is out of scope for this specific prompt; the focus is on unblocking collection).
-   The root cause of the collection hang is identified.

## 5. Implementation Requirements
-   **Input files/data:** The Biomapper project codebase at `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/`.
-   **Expected outputs:** Console output from `pytest` indicating successful collection, or detailed error messages if the hang is resolved into a concrete error. A clear diagnosis of the problem.
-   **Code standards:** No code changes are expected from this prompt, only diagnostic commands and analysis. If a simple configuration change is identified as the fix, it can be proposed.

## 6. Error Recovery Instructions
-   If a command leads to a new, specific error message (other than the hang), document this error fully.
-   If `pdb` becomes too difficult to navigate, fall back to other methods like plugin disabling or individual file analysis.
-   If a specific file or import is suspected, note this down even if the exact line cannot be pinpointed.

## 7. Feedback Format
Please provide the following in your feedback:
-   **Commands Executed:** List all commands run.
-   **Observed Outcomes:** For each command, describe the output and whether the hang persisted or changed.
-   **Analysis & Diagnosis:** Your detailed analysis of the findings.
-   **Root Cause Identified (if any):** The specific reason for the `pytest` collection hang.
-   **Suggested Next Steps:** Based on your findings, what should be tried next if the issue isn't fully resolved.
-   **Confidence Assessment:** Your confidence in the diagnosis.
-   **Environment Changes:** Note any temporary modifications made (e.g., to config files).
