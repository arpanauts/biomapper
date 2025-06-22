# Prompt: Remove Legacy Handlers from MappingExecutor

**Objective:** Remove the legacy handler methods from `MappingExecutor` to eliminate unnecessary delegation and simplify the facade.

**Context:** The `MappingExecutor` currently contains several private methods that act as simple pass-through delegates to the `MappingHandlerService`. These methods were maintained for backward compatibility but are no longer necessary. Removing them will make the `MappingExecutor` leaner and more focused.

**Files to be Modified:**

*   `/home/ubuntu/biomapper/biomapper/core/mapping_executor.py`

**Task Decomposition:**

1.  **Identify and Delete Legacy Handlers:**
    *   Open `/home/ubuntu/biomapper/biomapper/core/mapping_executor.py`.
    *   Locate and delete the following methods from the `MappingExecutor` class:
        *   `_handle_convert_identifiers_local`
        *   `_handle_execute_mapping_path`
        *   `_handle_filter_identifiers_by_target_presence`

2.  **Update Internal Call Sites (If Any):**
    *   Search within `MappingExecutor` for any calls to the deleted methods.
    *   If any calls are found, update them to call the corresponding method on `self.mapping_handler_service` directly.

**Success Criteria:**

*   The specified legacy handler methods are removed from `MappingExecutor`.
*   The `MappingExecutor` no longer contains any references to these deleted methods.
*   The application remains fully functional, and all relevant calls are correctly delegated to `MappingHandlerService`.
*   All tests pass after the refactoring.
