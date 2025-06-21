# Task 2: Refactor Bidirectional Mapping Optimization Tests

## 1. Objective

Refactor the tests within `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/tests/core/test_bidirectional_mapping_optimization.py`. These tests are currently skipped or failing because they are tightly coupled to the previous implementation of `MappingExecutor` and its internal methods.

## 2. Context and Background

The `test_bidirectional_mapping_optimization.py` file contains critical tests for complex logic, including path caching, concurrent processing, and metrics tracking. The recent refactoring of `MappingExecutor` into a service-oriented architecture has broken these tests. The feedback from the previous test-fixing task specifically called out `test_path_caching`, `test_concurrent_batch_processing`, and `test_metrics_tracking` as needing a complete rewrite.

## 3. Prerequisites

- The agent must have a deep understanding of the bidirectional mapping strategy and how it's orchestrated by the new services.
- Familiarity with `PathFinder` (for caching), `StrategyExecutionService` (for orchestration), and `MetricsService` (if applicable, or where metrics logic now resides) is essential.

## 4. Task Breakdown

1.  **Analyze `test_path_caching`:**
    - This test likely checked the internal cache of `MappingExecutor`. Path caching is now handled by `PathFinder`.
    - **Action:** Rewrite this test to target the `PathFinder` service directly. Mock its database dependency and verify that calling `find_path` multiple times with the same parameters results in a cache hit (i.e., the database is only queried once).

2.  **Analyze `test_concurrent_batch_processing`:**
    - This test likely used the old `_run_path_steps` method. Concurrent logic is now managed within services.
    - **Action:** Rewrite this test to target the relevant service (likely `StrategyExecutionService` or a batch processing service it uses). The test should verify that when given a large list of identifiers, the service correctly processes them in concurrent batches.

3.  **Analyze `test_metrics_tracking`:**
    - This test checked internal metrics counters in `MappingExecutor`.
    - **Action:** Determine where metrics logic now resides. It might be in a dedicated `MetricsService` or within the `execution_context` passed between strategy actions. Rewrite the test to verify that metrics (e.g., 'mapped_count', 'unmapped_count') are correctly tracked and reported after a mapping run.

4.  **Review and Refactor Other Tests:** Go through any other tests in the file and apply the same principles: identify the new location of the logic and rewrite the test to target the correct service, using mocking and dependency injection.

## 5. Implementation Requirements

- **Target File:** `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/tests/core/test_bidirectional_mapping_optimization.py`
- **Code Standards:** Use `pytest` and `unittest.mock`. All tests must be `async def`.
- **Focus on Public APIs:** Tests should interact with the public methods of the service classes, not their internal, private methods.

## 6. Validation and Success Criteria

- **Success:** All tests in `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/tests/core/test_bidirectional_mapping_optimization.py` pass.
- **No Skipped Tests:** All `pytest.mark.skip` markers are removed from the file.
- **Clarity:** The new tests are clean, readable, and clearly state what behavior they are verifying.

## 7. Feedback and Reporting

- Provide the `diff` of the changes made to the target test file.
- Confirm that all tests in the file now pass by providing the `pytest` output.
