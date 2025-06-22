# Prompt: Refactor MappingExecutor to Use SessionMetricsService

**Objective:** Refactor the `MappingExecutor` to delegate all session and metrics logging responsibilities to the `SessionMetricsService`. This change will complete the extraction of logging logic, further simplifying the `MappingExecutor` and improving modularity.

**Context:** This task is the second part of a two-step refactoring process. The first step was creating the `SessionMetricsService`. This step integrates that new service into the application.

**Files to be Modified:**

1.  `/home/ubuntu/biomapper/biomapper/core/engine_components/initialization_service.py`
2.  `/home/ubuntu/biomapper/biomapper/core/mapping_executor.py`

**Task Decomposition:**

1.  **Update `InitializationService`:**
    *   Open `/home/ubuntu/biomapper/biomapper/core/engine_components/initialization_service.py`.
    *   Add the following import:
        ```python
        from biomapper.core.services.session_metrics_service import SessionMetricsService
        ```
    *   In the `initialize_components` method, instantiate the service:
        ```python
        components['session_metrics_service'] = SessionMetricsService()
        ```

2.  **Refactor `MappingExecutor`:**
    *   Open `/home/ubuntu/biomapper/biomapper/core/mapping_executor.py`.
    *   **Remove Private Methods:** Delete the following methods from the `MappingExecutor` class:
        *   `_create_mapping_session_log`
        *   `_update_mapping_session_log`
        *   `_save_metrics_to_database`
    *   **Update `execute_mapping` Method:**
        *   Find the calls to the old private methods within the `execute_mapping` method.
        *   Replace them with calls to the new `session_metrics_service`.
        *   For example, a call like `session_log = await self._create_mapping_session_log(...)` should become `session_log = await self.session_metrics_service.create_mapping_session_log(session, ...)`.
        *   Ensure you pass the `session` object to the new service methods.

**Success Criteria:**

*   `InitializationService` correctly instantiates and provides `SessionMetricsService`.
*   `MappingExecutor` no longer contains the private logging methods (`_create_mapping_session_log`, `_update_mapping_session_log`, `_save_metrics_to_database`).
*   `MappingExecutor` successfully uses `self.session_metrics_service` to handle all session and metrics logging.
*   The application is fully functional and all tests pass after the changes.
