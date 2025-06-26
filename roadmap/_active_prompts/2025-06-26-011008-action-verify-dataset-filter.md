# Task 5: Verify and Document `DatasetFilter` Strategy Action

**Source Prompt Reference:** This task is part of recreating the legacy `UKBB_TO_HPA_PROTEIN_PIPELINE`.

## 1. Task Objective
Thoroughly review, test, and document the existing `DatasetFilter` action (likely implemented in `filter_by_target_presence.py`) to ensure it is robust and ready for production use. This action is the equivalent of the legacy `FILTER_BY_TARGET_PRESENCE`.

## 2. Service Architecture Context
- **Primary Service:** `biomapper` (core library)
- **Affected Module:** `biomapper.core.strategy_actions.filter_by_target_presence`
- **Service Dependencies:** None.

## 3. Task Decomposition
1.  **Code Review:** Perform a detailed review of the implementation in `biomapper/core/strategy_actions/filter_by_target_presence.py`. Check for efficiency, especially with large datasets.
2.  **Enhance Unit Tests:** Review the existing unit tests. Add tests for edge cases, such as empty input lists, an empty filter list, and cases with no overlap. Aim for 100% test coverage.
3.  **Validate Registration:** Confirm the action is registered with a clear name (e.g., `DATASET_FILTER`).
4.  **Improve Documentation:** Update the docstring to be comprehensive. Explain all parameters and provide a clear YAML usage example.

## 4. Implementation Requirements
- **Action File:** `/home/trentleslie/github/biomapper/biomapper/core/strategy_actions/filter_by_target_presence.py`
- **Test File:** `/home/trentleslie/github/biomapper/tests/unit/strategy_actions/test_filter_by_target_presence.py`
- The action should be optimized for performance (e.g., using sets for filtering).

## 5. Success Criteria and Validation
- [ ] The action has been peer-reviewed (simulated by you).
- [ ] Unit tests achieve 100% code coverage.
- [ ] The docstring is complete and includes a clear usage example.
- [ ] The action is confirmed to be robust and ready for production use.
