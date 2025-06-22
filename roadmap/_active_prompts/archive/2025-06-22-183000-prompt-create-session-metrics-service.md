# Prompt: Create SessionMetricsService

**Objective:** Create a new `SessionMetricsService` to handle the creation, updating, and storage of mapping session logs and execution metrics. This service will extract and centralize logic currently located in private methods within `MappingExecutor`.

**Context:** As part of the ongoing modularization of the `biomapper` core, we are extracting distinct responsibilities from the `MappingExecutor` facade into specialized services. This effort simplifies the `MappingExecutor`, improves separation of concerns, and enhances maintainability.

**File to be Created:**

*   `/home/ubuntu/biomapper/biomapper/core/services/session_metrics_service.py`

**Task Decomposition:**

1.  **Create the Service File:**
    *   Create a new Python file at the path specified above.

2.  **Define the `SessionMetricsService` Class:**
    *   Inside the new file, define a class named `SessionMetricsService`.
    *   The class should have a `logger` instance initialized in its `__init__` method.

3.  **Implement Service Methods:**
    *   Migrate the logic from the following private methods in `/home/ubuntu/biomapper/biomapper/core/mapping_executor.py` into new public methods in `SessionMetricsService`.
    *   Each method in the new service should accept an `AsyncSession` object as its first parameter.

    *   **`_create_mapping_session_log` -> `create_mapping_session_log`**
        *   **Signature:** `async def create_mapping_session_log(self, session: AsyncSession, ...) -> MappingSession:`
        *   The method should accept the same parameters as the original, excluding `self`.
        *   It should create and return a `MappingSession` object.

    *   **`_update_mapping_session_log` -> `update_mapping_session_log`**
        *   **Signature:** `async def update_mapping_session_log(self, session: AsyncSession, ...):`
        *   The method should accept the same parameters as the original, excluding `self`.

    *   **`_save_metrics_to_database` -> `save_metrics_to_database`**
        *   **Signature:** `async def save_metrics_to_database(self, session: AsyncSession, ...):`
        *   The method should accept the same parameters as the original, excluding `self`.

4.  **Add Necessary Imports:**
    *   Ensure the new file includes all necessary imports, such as `logging`, `datetime`, `typing` (`Dict`, `Any`, `Optional`), `sqlalchemy.ext.asyncio.AsyncSession`, and the required database models (`MappingSession`, `ExecutionMetric`, `PathExecutionStatus`) from `biomapper.db.cache_models`.

**Success Criteria:**

*   The file `/home/ubuntu/biomapper/biomapper/core/services/session_metrics_service.py` is created.
*   The file contains a `SessionMetricsService` class with the three specified public methods.
*   The logic within these methods is identical to the logic in the corresponding private methods from `MappingExecutor`.
*   The code is well-formatted, includes necessary imports, and has no linting errors.
