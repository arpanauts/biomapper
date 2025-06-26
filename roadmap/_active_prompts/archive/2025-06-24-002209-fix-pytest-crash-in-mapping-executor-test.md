# Task: Fix Pytest Crash in `test_cache_results_db_error_during_commit`

**Source Prompt Reference:** This task is defined by the prompt: `/home/trentleslie/github/biomapper/roadmap/_active_prompts/2025-06-24-002209-fix-pytest-crash-in-mapping-executor-test.md`

## 1. Task Objective
The primary objective is to fix a crash that occurs when running the `pytest` test suite. The crash has been isolated to the test function `test_cache_results_db_error_during_commit` located in `/home/trentleslie/github/biomapper/tests/core/test_mapping_executor.py`. The fix involves correcting how a SQLAlchemy `OperationalError` is instantiated and improving the robustness of an asynchronous session mock.

## 2. Prerequisites
- [X] Required files exist: `/home/trentleslie/github/biomapper/tests/core/test_mapping_executor.py`
- [X] Required permissions: Write access to the file mentioned above.
- [X] Required dependencies: A fully installed Python environment via `poetry install`.
- [X] Environment state: The `pytest` suite currently crashes before completing.

## 3. Context from Previous Attempts (if applicable)
- **Previous attempt timestamp:** 2025-06-23T17:21:00-07:00
- **Issues encountered:** The initial fix was applied directly by the orchestrator agent, which violates the "Prompt-First" mandate. This prompt corrects that workflow by delegating the task.
- **Partial successes:** The root cause was correctly identified and a valid fix was prepared.
- **Recommended modifications:** The following change should be applied to `/home/trentleslie/github/biomapper/tests/core/test_mapping_executor.py`.

## 4. Task Decomposition
1. **Locate Target File:** Open `/home/trentleslie/github/biomapper/tests/core/test_mapping_executor.py`.
2. **Apply the Fix:** Find the `test_cache_results_db_error_during_commit` function and replace the session mocking logic with the corrected version.
3. **Validate the Fix:** Run the test suite using `poetry run pytest` from the project root (`/home/trentleslie/github/biomapper`).

## 5. Implementation Requirements
- **Input files/data:** `/home/trentleslie/github/biomapper/tests/core/test_mapping_executor.py`
- **Expected outputs:** The `pytest` command should complete successfully without any crashes.
- **Code standards:** The change must be compliant with `mypy --strict` and `ruff`.
- **Implementation Details:**

Replace this block of code:
```python
    # Create a mock cache sessionmaker
    mock_cache_sessionmaker = MagicMock()
    mock_cache_session = AsyncMock()
    
    # Configure the session operations
    mock_cache_session.add_all = MagicMock()  # add_all succeeds
    mock_cache_session.commit = AsyncMock(side_effect=OperationalError("Commit failed", {}, None))
    mock_cache_session.rollback = AsyncMock()
    
    # Configure the sessionmaker to return our mock session
    mock_cache_sessionmaker.return_value.__aenter__ = AsyncMock(return_value=mock_cache_session)
    mock_cache_sessionmaker.return_value.__aexit__ = AsyncMock(return_value=False)
```

With this corrected block:
```python
    # Create a mock cache sessionmaker and session
    mock_cache_sessionmaker = MagicMock()
    mock_cache_session = AsyncMock()

    # Configure the session operations
    mock_cache_session.add_all = MagicMock()
    # Correctly instantiate OperationalError with None for params, which is safer.
    mock_cache_session.commit = AsyncMock(
        side_effect=OperationalError("Commit failed", None, None)
    )
    mock_cache_session.rollback = AsyncMock()

    # Configure the sessionmaker to return a robust mock async context manager
    mock_session_context = AsyncMock()
    mock_session_context.__aenter__.return_value = mock_cache_session
    mock_session_context.__aexit__.return_value = False  # Ensure exceptions propagate
    mock_cache_sessionmaker.return_value = mock_session_context
```

## 6. Error Recovery Instructions
- **Logic/Implementation Errors:** If the test suite still crashes or if the `test_cache_results_db_error_during_commit` test fails for a new reason, capture the full `pytest` output and the new error message in your feedback file. Classify the error as `FAILED_WITH_RECOVERY_OPTIONS`.

## 7. Success Criteria and Validation
Task is complete when:
- [ ] The code modification has been applied to `/home/trentleslie/github/biomapper/tests/core/test_mapping_executor.py`.
- [ ] The command `poetry run pytest` runs to completion from the `/home/trentleslie/github/biomapper` directory without crashing.
- [ ] The test `test_cache_results_db_error_during_commit` still passes and correctly asserts that a `CacheStorageError` is raised.

## 8. Feedback Requirements
Create a detailed Markdown feedback file at:
`/home/trentleslie/github/biomapper/roadmap/_active_prompts/feedback/YYYY-MM-DD-HHMMSS-feedback-fix-pytest-crash.md`

**Mandatory Feedback Sections:**
- **Execution Status:** [COMPLETE_SUCCESS | FAILED_WITH_RECOVERY_OPTIONS]
- **Completed Subtasks:** [Checklist of what was accomplished]
- **Issues Encountered:** [Detailed error descriptions if any]
- **Next Action Recommendation:** [e.g., "The fix is applied and validated. Ready for the next task."]
- **Confidence Assessment:** [High]
- **Environment Changes:** [The file `tests/core/test_mapping_executor.py` was modified.]
- **Lessons Learned:** [Confirm that incorrect exception instantiation was the cause of the crash.]
