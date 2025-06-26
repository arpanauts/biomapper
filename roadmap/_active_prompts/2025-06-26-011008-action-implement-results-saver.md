# Task 7: Implement and Test `ResultsSaver` Strategy Action

**Source Prompt Reference:** This task is part of recreating the legacy `UKBB_TO_HPA_PROTEIN_PIPELINE`.

## 1. Task Objective
Implement and test a generic `ResultsSaver` strategy action that can take data from a specified context key and save it to a file in various formats (e.g., CSV, JSON). This replaces the legacy `SaveBidirectionalResultsAction`.

## 2. Service Architecture Context
- **Primary Service:** `biomapper` (core library)
- **Affected Module:** `biomapper.core.strategy_actions.save_results`
- **Service Dependencies:** None.

## 3. Task Decomposition
1.  **Review Existing Code:** Analyze the implementation in `biomapper/core/strategy_actions/save_results.py` and `save_bidirectional_results_action.py`.
2.  **Define Action Interface:** The action should take parameters for the input context key, the output directory, the filename, and the desired format (`csv` or `json`).
3.  **Implement Core Logic:** Implement logic to handle different data structures (e.g., lists of dictionaries, pandas DataFrames) and write them to the specified file format.
4.  **Add Unit Tests:** Create unit tests that save mock data to a temporary directory and then verify the contents of the created file. Test both CSV and JSON outputs.
5.  **Register the Action:** Register the action as `SAVE_RESULTS`.
6.  **Add Documentation:** Write a clear docstring with examples for saving both CSV and JSON files.

## 4. Implementation Requirements
- **Action File:** `/home/trentleslie/github/biomapper/biomapper/core/strategy_actions/save_results.py`
- **Test File:** `/home/trentleslie/github/biomapper/tests/unit/strategy_actions/test_save_results.py`
- The action must handle file system errors gracefully (e.g., permission denied).

## 5. Success Criteria and Validation
- [ ] The action is implemented and registered.
- [ ] Unit tests achieve 100% code coverage.
- [ ] The action can successfully write both CSV and JSON files.
- [ ] The docstring is complete and includes clear usage examples.
