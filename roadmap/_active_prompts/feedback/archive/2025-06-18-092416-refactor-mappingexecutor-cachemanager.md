# Task: Refactor Cache Management from MappingExecutor to CacheManager

## 1. Task Objective
Refactor the cache management responsibilities from the `MappingExecutor` class (`biomapper/core/mapping_executor.py`) into a new, dedicated `CacheManager` class. This new class will reside in `biomapper/core/engine_components/cache_manager.py`. The goal is to improve modularity, reduce the complexity of `MappingExecutor`, and make cache-related logic more maintainable.

## 2. Background Context
The `MappingExecutor` class has grown significantly and handles multiple responsibilities. As part of an ongoing effort to improve its structure, we are extracting cohesive sets of functionalities into separate components within the `biomapper/core/engine_components/` directory. Cache management (interacting with `mapping_cache.db` for storing and retrieving mapping results and logs) has been identified as a distinct responsibility suitable for such extraction.

Key methods in `MappingExecutor` currently handling cache logic include:
- `_check_cache`
- `_cache_results`
- `_create_mapping_log`
- `_get_path_details_from_log`

## 3. Detailed Plan/Steps

1.  **Create `CacheManager` File and Class:**
    *   Create a new Python file: `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/biomapper/core/engine_components/cache_manager.py`.
    *   Inside this file, define a new class named `CacheManager`.
    *   The `CacheManager` will likely need access to an `AsyncSession` for the cache database and the `MappingExecutor`'s logger. Its `__init__` method should accept these (e.g., `__init__(self, cache_sessionmaker: sessionmaker, logger: logging.Logger)`).

2.  **Migrate Cache-Related Methods from `MappingExecutor` to `CacheManager`:**
    *   **`_check_cache`:**
        *   Move the logic of `MappingExecutor._check_cache` to a new method in `CacheManager`, e.g., `async check_cache(self, input_identifiers: List[str], source_ontology: str, target_ontology: str, mapping_path_id: Optional[int] = None, expiry_time: Optional[datetime] = None) -> Tuple[Dict[str, List[Dict[str, Any]]], List[str]]`.
        *   Adapt the method to use the `CacheManager`'s session and logger.
    *   **`_cache_results`:**
        *   Move the logic of `MappingExecutor._cache_results` to a new method in `CacheManager`, e.g., `async store_mapping_results(self, results_to_cache: Dict[str, Dict[str, Any]], path: Union[MappingPath, "ReversiblePath"], source_ontology: str, target_ontology: str, mapping_session_id: Optional[int] = None)`.
        *   This method is substantial; ensure all its internal logic, including confidence score calculation and provenance creation, is correctly transferred.
    *   **`_create_mapping_log`:**
        *   Move the logic of `MappingExecutor._create_mapping_log` to a new method in `CacheManager`, e.g., `async create_path_execution_log(self, path_id: int, status: PathExecutionStatus, representative_source_id: str, source_entity_type: str) -> MappingPathExecutionLog`.
    *   **`_get_path_details_from_log`:**
        *   Move the logic of `MappingExecutor._get_path_details_from_log` to a new method in `CacheManager`, e.g., `async get_path_details_from_log(self, path_log_id: int) -> Dict[str, Any]`.

3.  **Update `MappingExecutor` to Use `CacheManager`:**
    *   In `MappingExecutor.__init__` (or its `create` factory method), instantiate `CacheManager`, passing the cache session maker (e.g., `self._cache_sessionmaker`) and `self.logger`.
        ```python
        # Example in MappingExecutor.__init__ or create
        from .engine_components.cache_manager import CacheManager
        self.cache_manager = CacheManager(cache_sessionmaker=self._cache_sessionmaker, logger=self.logger)
        ```
    *   Replace the original calls to `self._check_cache`, `self._cache_results`, `self._create_mapping_log`, and `self._get_path_details_from_log` with calls to the corresponding methods on `self.cache_manager` (e.g., `await self.cache_manager.check_cache(...)`).
    *   Remove the original private methods (`_check_cache`, etc.) from `MappingExecutor` after successfully delegating their functionality.

4.  **Handle Imports and Dependencies:**
    *   Ensure `cache_manager.py` has all necessary imports (e.g., `AsyncSession`, `sessionmaker`, `datetime`, SQLAlchemy models from `biomapper.db.cache_models`, `biomapper.db.models`, `PathExecutionStatus`, etc.).
    *   Update imports in `mapping_executor.py` as needed.
    *   Pay close attention to type hints and ensure they are correct in both files.
    *   All asynchronous methods must use `async def` and `await` appropriately.

5.  **Update `__init__.py`:**
    *   If `biomapper/core/engine_components/__init__.py` exists, ensure `CacheManager` is appropriately exposed if desired (though direct import is also fine).

## 4. Acceptance Criteria

*   The `CacheManager` class is created in `biomapper/core/engine_components/cache_manager.py` and contains the refactored cache management methods.
*   `MappingExecutor` successfully instantiates and uses `CacheManager` for all cache-related operations.
*   The original cache-related private methods are removed from `MappingExecutor`.
*   The overall functionality of mapping execution, including cache checks and storage, remains unchanged and operates correctly.
*   The codebase remains type-hinted and passes any linting/static analysis checks if they are part of the project setup.
*   The UKBB-HPA pipeline (e.g., `run_full_ukbb_hpa_mapping.py`) still runs successfully, demonstrating that cache interactions are working as expected through the new `CacheManager`.

## 5. Implementation Requirements

*   **Input files/data:** Primarily involves modifying Python source code files:
    *   `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/biomapper/core/mapping_executor.py`
    *   Create: `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/biomapper/core/engine_components/cache_manager.py`
*   **Expected outputs:** Modified Python files as described.
*   **Code standards:** Maintain existing code style, comprehensive type hinting, and adherence to async/await patterns.
*   **Validation requirements:** After refactoring, run an existing pipeline script (e.g., `run_full_ukbb_hpa_mapping.py`) to ensure that mapping and caching still function correctly. Examine logs for any errors related to cache operations.

## 6. Error Recovery Instructions

*   **Import Errors:** Double-check import paths. Ensure new files are correctly placed and that relative/absolute imports are appropriate.
*   **Attribute Errors:** Verify that `CacheManager` is correctly instantiated in `MappingExecutor` and that methods are called on the instance (e.g., `self.cache_manager.method_name(...)`). Ensure `AsyncSession` and logger are correctly passed and used within `CacheManager`.
*   **Type Errors:** Carefully review type hints during migration and ensure data passed between `MappingExecutor` and `CacheManager`, and within `CacheManager` methods, matches the expected types.
*   **Async/Await Issues:** Ensure all database operations within `CacheManager` are `await`ed and that calling methods are also `async` and `await`ed correctly.
*   If tests exist for `MappingExecutor`'s caching behavior, they will need to be updated or new tests created for `CacheManager`.

## 7. Feedback Section

*   **File paths of all modified files:**
*   **Summary of changes:**
*   **Confirmation of successful pipeline run (e.g., UKBB-HPA) after changes:**
*   **Any challenges encountered and how they were resolved:**
*   **Suggestions for further improvements or pending issues:**
*   **Completed Subtasks:** (checklist from Detailed Plan/Steps)
*   **Issues Encountered:**
*   **Next Action Recommendation:**
*   **Confidence Assessment:**
*   **Environment Changes:**
*   **Lessons Learned:**
