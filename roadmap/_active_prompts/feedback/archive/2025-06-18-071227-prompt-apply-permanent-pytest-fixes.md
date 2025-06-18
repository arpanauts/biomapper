# Task: Apply Permanent Fixes to Resolve Pytest Collection Issues

## 1. Task Objective
Implement permanent solutions for issues identified during the `pytest` collection hang debugging. This involves addressing problematic test file behavior, resolving a missing module, and cleaning up temporary workarounds to ensure a stable and reliable test environment.

## 2. Background & Context
Previous debugging efforts (summarized in feedback file `2025-06-18-070736-feedback-debug-pytest-collection-hang.md` and Memory ID `3362f46d-01b4-4384-9636-527643b27c96`) identified key problems:

1.  **`examples/tutorials/test_gemini.py`:** This file causes `pytest` to hang when collected due to an HTTP request (`requests.post(None)`) made at import time. The `norecursedirs` setting in `pyproject.toml` was not consistently preventing its collection.
2.  **Missing Module `biomapper.embedder.storage.vector_store.py`:** This module is missing, leading to import errors.
3.  **Temporary Fixes:** To work around the missing module, the following files were modified by a previous agent:
    *   `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/biomapper/embedder/storage/__init__.py`
    *   `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/biomapper/embedder/__init__.py`
    (Changes involved commenting out imports and setting `FAISSVectorStore = None`).

The goal is to apply robust, permanent fixes for these issues.

## 3. Detailed Steps & Requirements

### 3.1. Address `examples/tutorials/test_gemini.py` Behavior

1.  **Analyze `test_gemini.py`:**
    *   View the contents of `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/examples/tutorials/test_gemini.py`.
    *   Identify the import-time HTTP request.

2.  **Implement a Solution (Choose one and document reasoning):**
    *   **Option A (Preferred if `test_gemini.py` is a valid example that might be run, but not as a pytest test):** Modify `test_gemini.py` so that the HTTP request is not made at import time. For example, move the request logic into a function or a conditional block (e.g., `if __name__ == "__main__":`).
    *   **Option B (If `test_gemini.py` should NEVER be collected by pytest):** Ensure `pytest` ignores the `examples` directory.
        *   Verify the `norecursedirs` setting in `pyproject.toml` (`[tool.pytest.ini_options]`). It should include `examples`.
        *   If `norecursedirs` is correctly set but ineffective when `pytest` is run from the root, create a new file `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/examples/.pytest.ini` with the content:
            ```ini
            [pytest]
            collect_ignore = ["*.py"]
            ```
        *   Test if `pytest` (run from project root) no longer attempts to collect from `examples/tutorials/test_gemini.py`.

### 3.2. Resolve Missing `biomapper.embedder.storage.vector_store.py`

1.  **Investigation:**
    *   Determine if `biomapper.embedder.storage.vector_store.py` was accidentally deleted or if it has become obsolete. (Since direct git history access might be limited, focus on project structure and existing references).
    *   Search the codebase for any other references to `vector_store` or `FAISSVectorStore` from this specific module path to understand its intended role.

2.  **Implement a Solution (Choose one and document reasoning):**
    *   **Option A (If deemed necessary and content is known/recoverable):** Restore or recreate `biomapper.embedder.storage.vector_store.py`. If exact content is unknown, create a minimal placeholder file with the necessary class/function definitions (e.g., a `FAISSVectorStore` class skeleton) and clear comments indicating it's a placeholder.
    *   **Option B (If deemed obsolete):** Prepare to remove all references.

### 3.3. Clean Up Temporary Fixes in `__init__.py` Files

1.  **View current state:**
    *   `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/biomapper/embedder/storage/__init__.py`
    *   `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/biomapper/embedder/__init__.py`

2.  **Apply Permanent Changes:**
    *   **If `vector_store.py` (and `FAISSVectorStore`) is restored/recreated (Step 3.2, Option A):**
        *   Update both `__init__.py` files to correctly import `FAISSVectorStore` (or other relevant components) from `biomapper.embedder.storage.vector_store`.
        *   Remove the temporary `FAISSVectorStore = None` lines and any commented-out old imports.
    *   **If `vector_store.py` is deemed obsolete (Step 3.2, Option B):**
        *   Remove the temporary `FAISSVectorStore = None` lines from both `__init__.py` files.
        *   Ensure any remaining commented-out imports related to the obsolete module are also removed.
        *   Verify that no other code in the project still relies on these specific imports from the `__init__` files.

## 4. Success Criteria & Validation
-   Running `poetry run pytest tests/` from the project root collects all tests successfully without errors related to `test_gemini.py` or `vector_store.py`.
-   Running `poetry run pytest` from the project root either:
    *   Does not attempt to collect tests from the `examples` directory, OR
    *   If it does collect (e.g., `test_gemini.py` was modified to be safe), it does not hang or error due to `test_gemini.py`'s previous import-time issues.
-   The status of `biomapper.embedder.storage.vector_store.py` is definitively resolved (restored, placeholder created, or confirmed obsolete and references removed).
-   The temporary fixes in `biomapper/embedder/storage/__init__.py` and `biomapper/embedder/__init__.py` are removed and replaced with correct, permanent import logic or clean removal.
-   The codebase is in a state where `pytest` collection is stable and predictable.

## 5. Implementation Requirements
-   **Files to potentially analyze/modify:**
    *   `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/examples/tutorials/test_gemini.py`
    *   `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/pyproject.toml`
    *   `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/examples/.pytest.ini` (potentially create)
    *   `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/biomapper/embedder/storage/vector_store.py` (potentially create/restore)
    *   `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/biomapper/embedder/storage/__init__.py`
    *   `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/biomapper/embedder/__init__.py`
-   Use appropriate tools for file viewing and editing.
-   All changes should be documented in the feedback.

## 6. Error Recovery Instructions
-   If modifying `test_gemini.py` introduces new issues, revert to ensuring it's ignored by `pytest`.
-   If the role of `vector_store.py` cannot be confidently determined, err on the side of creating a clear placeholder and documenting the uncertainty, rather than deleting potentially crucial (though currently missing) logic.
-   If changes lead to widespread import errors, isolate the problematic change and reconsider the approach.

## 7. Feedback Format
-   **Summary of Changes:** Briefly describe the actions taken for each sub-task.
-   **Decisions Made:** Document choices made (e.g., how `test_gemini.py` was handled, whether `vector_store.py` was deemed obsolete or restored).
-   **Files Created/Modified:** List all files touched with a brief note on the change.
-   **Pytest Collection Status:** Confirm the outcome of running `pytest tests/` and `pytest` (from root).
-   **Unresolved Issues/Questions:** Any remaining uncertainties or new issues encountered.
-   **Confidence Assessment:** Your confidence in the implemented permanent fixes.
