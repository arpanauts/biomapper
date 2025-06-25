# Meta-Prompt: Diagnose and Fix Silent API Server Startup Failure

## 1. Objective

The primary objective is to diagnose and resolve a persistent and critical issue where the `biomapper-api` FastAPI server fails to start silently. When launched via `poetry run uvicorn`, the process exits immediately with a success code (0) and provides no error messages or logs, making it impossible to debug directly. The successful resolution of this issue will allow the API server to run, stay active, and serve requests from the `biomapper-client`.

## 2. Context & Background

We are in the final stages of a major refactor to a service-oriented architecture (SOA). The goal is to run a full data analysis pipeline (`UKBB_HPA_PROTEIN_OVERLAP_ANALYSIS`) by having a client script (`scripts/main_pipelines/run_full_ukbb_hpa_mapping.py`) call the `biomapper-api` service. The API then loads a YAML-defined strategy and executes it.

We have encountered and solved several major blockers to get to this point:

1.  **Poetry Environment Corruption:** We resolved a complex issue where the `biomapper-client` package was not being installed correctly. The root cause was a `virtualenvs.in-project = true` setting in Poetry's configuration. This has been fixed by setting it to `false`, deleting the local `.venv`, and reinstalling all dependencies into a stable, cached virtual environment. **The Python environment is now considered stable and correct.**

2.  **Module Import Errors:** We fixed a `ModuleNotFoundError` for `biomapper_api` by adding the `--app-dir` flag to the `uvicorn` command, ensuring Python's import path was correct.

3.  **Redundant `__main__` Block:** We removed an `if __name__ == "__main__":` block from `biomapper-api/app/main.py` that was preventing `uvicorn` from starting the server when importing the `app` object.

Despite these fixes, the server still fails to launch.

**Current Command to run the server (from project root `/home/ubuntu/biomapper/`):**
```bash
poetry run uvicorn --app-dir biomapper-api/ app.main:app --host 0.0.0.0 --port 8000
```

## 3. Current Hypothesis

The silent crash strongly suggests the error is occurring very early in the application's startup sequence, likely during the initial module imports and object instantiations, before the `uvicorn` logger is fully configured.

- The FastAPI application is configured to initialize a `MapperService` instance on startup (via an `@app.on_event("startup")` decorator in `app/main.py`).
- The `MapperService.__init__` method in `app/services/mapper_service.py` is responsible for loading and parsing all YAML strategy files from the `STRATEGIES_DIR` (`/home/ubuntu/biomapper/configs`).
- **My primary hypothesis is that there is a syntax error, a validation error (against the Pydantic models), or a logical inconsistency in one of the YAML files being loaded from the `configs` directory. This error is being raised during the `MapperService` instantiation, but the exception is being swallowed somewhere, causing the entire process to terminate without a traceback.**

## 4. Investigation & Action Plan

Your task is to prove or disprove the hypothesis and fix the underlying issue. The approach should be to make the silent error visible.

1.  **Instrument the Code to Expose the Error:**
    *   **Modify `app/main.py`:** Wrap the `MapperService` instantiation inside the `startup_event` function in a `try...except Exception as e:` block. Add extensive logging within the `except` block to print the exception type and message to the console. This is the most likely place to catch the error.
    *   **Modify `app/services/mapper_service.py`:** Add detailed logging or `print` statements to the `MapperService.__init__` and its helper method `_load_strategies_from_dir`. Log the name of *each file* just before it is opened and parsed. This will identify the exact file that triggers the crash.

2.  **Isolate the Problematic Component:**
    *   If the logging reveals the problematic file, inspect it for obvious syntax errors or discrepancies with the strategy Pydantic models (e.g., `Strategy`, `StrategyStep` in the core `biomapper` library).
    *   If the error is still not clear, use a process of elimination. Temporarily modify `MapperService.__init__` to *not* load any strategies. Confirm that the server can start successfully without them. If it can, reintroduce the strategies one by one until the server fails to start again, definitively identifying the problematic file.

3.  **Implement the Fix:**
    *   Once the root cause is identified (e.g., a malformed YAML file, a bug in the Pydantic model validation), apply the necessary correction.

## 5. Verification

The task is complete when:

1.  Running `poetry run uvicorn --app-dir biomapper-api/ app.main:app --host 0.0.0.0 --port 8000` from the project root successfully starts the server.
2.  The server logs show messages like `INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)` and `INFO:     Application startup complete.`
3.  The server process **remains running** and does not exit silently.
4.  As a final confirmation, running the client script (`poetry run python scripts/main_pipelines/run_full_ukbb_hpa_mapping.py`) connects to the running server and successfully executes the pipeline, printing the final results dictionary to the console.
