# Prompt: Diagnose and Fix Uvicorn Server Startup Failure

**Objective:**

Your task is to diagnose and resolve a critical server startup failure that is preventing the `biomapper-api` service from running. The `uvicorn` server process is terminating unexpectedly with a `KeyboardInterrupt` during its initialization phase.

**Problem Description:**

When attempting to start the FastAPI application using `poetry run uvicorn app.main:app`, the process fails immediately. The command output shows a `KeyboardInterrupt` traceback originating from deep within Python's `typing` module, which is highly unusual and suggests a potential environment or dependency conflict.

**Full Traceback:**

```
^CTraceback (most recent call last):
  File "/root/.cache/pypoetry/virtualenvs/biomapper-OD08x7G7-py3.11/bin/uvicorn", line 5, in <module>
    from uvicorn.main import main
  File "/root/.cache/pypoetry/virtualenvs/biomapper-OD08x7G7-py3.11/lib/python3.11/site-packages/uvicorn/__init__.py", line 1, in <module>
    from uvicorn.config import Config
  File "/root/.cache/pypoetry/virtualenvs/biomapper-OD08x7G7-py3.11/lib/python3.11/site-packages/uvicorn/config.py", line 19, in <module>
    from uvicorn._types import ASGIApplication
  File "/root/.cache/pypoetry/virtualenvs/biomapper-OD08x7G7-py3.11/lib/python3.11/site-packages/uvicorn/_types.py", line 150, in <module>
    class _WebSocketReceiveEventBytes(TypedDict):
  File "/root/.pyenv/versions/3.11.13/lib/python3.11/typing.py", line 3005, in __new__
    own_annotations = {
                      ^
  File "/root/.pyenv/versions/3.11.13/lib/python3.11/typing.py", line 3006, in <dictcomp>
    n: _type_check(tp, msg, module=tp_dict.__module__)
       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/root/.pyenv/versions/3.11.13/lib/python3.11/typing.py", line 190, in _type_check
    if arg in (Any, LiteralString, NoReturn, Never, Self, TypeAlias):
       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/root/.pyenv/versions/3.11.13/lib/python3.11/typing.py", line 916, in __eq__
    def __eq__(self, other):

KeyboardInterrupt
```

**Context & Environment:**

*   **Project Root:** `/home/ubuntu/biomapper/`
*   **API Directory:** `/home/ubuntu/biomapper/biomapper-api/`
*   **Dependency Management:** The project uses `poetry`.
*   **Command to Run Server:** `poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000` (executed from the `biomapper-api` directory).

**Required Investigation and Debugging Steps:**

1.  **Inspect Dependency Tree:** The traceback strongly suggests a dependency issue. Run `poetry show --tree` within the `/home/ubuntu/biomapper/` directory to get a complete picture of the installed packages and their versions. Look for any outdated or conflicting packages related to `uvicorn`, `fastapi`, `starlette`, `pydantic`, and `anyio`.

2.  **Isolate the Environment:** Create a minimal test case to determine if the issue is with the environment or the application code. Create a new file named `minimal_test.py` in the `/home/ubuntu/biomapper/biomapper-api/app/` directory with the following content:

    ```python
    from fastapi import FastAPI

    app = FastAPI()

    @app.get("/")
    def read_root():
        return {"Hello": "World"}
    ```

    Then, try to run this minimal app from the `/home/ubuntu/biomapper/biomapper-api/` directory:

    ```bash
    poetry run uvicorn app.minimal_test:app --host 0.0.0.0 --port 8000
    ```

    If this command also fails, the problem is likely with the environment itself. If it succeeds, the issue lies within the `biomapper-api` application's imports or initialization logic.

3.  **Refresh Dependencies:** Based on the findings, attempt to fix the environment by reinstalling the dependencies. From the `/home/ubuntu/biomapper/` directory, run:

    ```bash
    poetry lock
    poetry install
    ```

    This will resolve the latest compatible versions based on `pyproject.toml` and perform a clean installation.

**Expected Outcome:**

The `uvicorn` server should start successfully without any errors, displaying output similar to this:

```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

**Verification:**

Once the server is running, you must verify the complete end-to-end pipeline. Run the following commands from the `/home/ubuntu/biomapper/` directory:

1.  Start the server in the background:
    ```bash
    cd /home/ubuntu/biomapper/biomapper-api/ && poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000 &
    ```
2.  Wait for the server to initialize:
    ```bash
    sleep 5
    ```
3.  Run the client script:
    ```bash
    cd /home/ubuntu/biomapper/ && poetry run python3 scripts/main_pipelines/run_full_ukbb_hpa_mapping.py
    ```

The final command should now produce the JSON output of the mapping results, confirming the fix.
