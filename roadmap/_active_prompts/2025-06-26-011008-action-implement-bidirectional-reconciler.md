# Task 6: Implement and Test `BidirectionalReconciler` Strategy Action

**Source Prompt Reference:** This task is part of recreating the legacy `UKBB_TO_HPA_PROTEIN_PIPELINE`.

## 1. Task Objective
Implement and test the `BidirectionalReconciler` strategy action. This action is responsible for comparing a forward mapping (Source -> Target) with a reverse mapping (Target -> Source) and producing a final, reconciled list of one-to-one matches. This replaces the legacy `RECONCILE_MAPPINGS` action.

## 2. Service Architecture Context
- **Primary Service:** `biomapper` (core library)
- **Affected Module:** `biomapper.core.strategy_actions.reconcile_bidirectional_action`
- **Service Dependencies:** None.

## 3. Task Decomposition
1.  **Review Existing Code:** Analyze the implementation in `biomapper/core/strategy_actions/reconcile_bidirectional_action.py`.
2.  **Define Action Interface:** The action needs parameters for the forward mapping context key, the reverse mapping context key, and the output context key.
3.  **Implement Core Logic:** The logic should identify pairs that appear in both mapping sets (i.e., if A->B in the forward map, B->A must exist in the reverse map).
4.  **Add Unit Tests:** Create unit tests in `tests/unit/strategy_actions/`. Test various scenarios: perfect matches, one-way-only matches, and complex many-to-one situations to ensure the reconciliation logic is correct.
5.  **Register the Action:** Ensure the action is registered as `BIDIRECTIONAL_RECONCILER`.
6.  **Add Documentation:** Write a clear docstring explaining the purpose of the action, its parameters, and a YAML usage example.

## 4. Implementation Requirements
- **Action File:** `/home/trentleslie/github/biomapper/biomapper/core/strategy_actions/reconcile_bidirectional_action.py`
- **Test File:** `/home/trentleslie/github/biomapper/tests/unit/strategy_actions/test_reconcile_bidirectional_action.py`
- The action must handle complex mapping scenarios correctly.

## 5. Success Criteria and Validation
- [ ] The action is implemented and registered.
- [ ] Unit tests achieve 100% code coverage.
- [ ] The docstring is complete and includes a clear usage example.
- [ ] The reconciliation logic is confirmed to be correct and robust.
