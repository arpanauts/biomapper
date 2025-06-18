# Task: Continue Refactoring MappingExecutor for UKBB-HPA Pipeline Custom Actions

## 1. Task Objective
Implement placeholder custom `StrategyAction` classes required for the `UKBB_TO_HPA_BIDIRECTIONAL_EFFICIENT` mapping strategy. This involves creating the Python class files, defining basic structures, and ensuring they can be registered by the `MappingExecutor`. The goal is to prepare for moving specific logic from the `run_full_ukbb_hpa_mapping_bidirectional.py` script into these actions.

## 2. Background & Context
The `MappingExecutor` has been refactored to support YAML-defined strategies composed of `StrategyAction` instances. The next phase is to implement custom actions tailored for specific pipeline needs, starting with the UKBB-HPA bidirectional mapping.

**Relevant Memories & Context:**
-   **Memory `d3bf2627-64a7-4bfb-a9ad-5b13620b79c9`:** Outlines the multi-step refactoring plan for `mapping_executor.py` and identifies the "Next Major Phase: Implement placeholder custom strategy actions for the UKBB-HPA pipeline."
-   **Memory `bba5c7fb-3b3c-4093-8e3f-e4d31432df41`:** Details the logic from `run_full_ukbb_hpa_mapping_bidirectional.py` to be moved into `StrategyActions`, and requirements for the YAML strategy (`UKBB_TO_HPA_BIDIRECTIONAL_EFFICIENT` in `configs/mapping_strategies_config.yaml`). Specifically:
    -   New first step for loading input identifiers (e.g., `LoadEndpointIdentifiersAction`).
    -   New action(s) to replicate script's detailed result output (CSV and JSON summary, e.g., `SaveBidirectionalResultsAction`).
    -   A reconciliation action (e.g., `ReconcileBidirectionalAction`) is also implied by the bidirectional nature.
-   **Starter Prompt Guidance:** New actions should be created in `biomapper/core/strategy_actions/`, inherit from `BaseStrategyAction`, and implement `__init__` and `async execute`.

**Current State of `MappingExecutor`:**
-   Handles YAML strategy parsing and action registration.
-   Core components like `PathFinder` and `ReversiblePath` are in place.

**Target Script for Refactoring:**
-   `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/scripts/main_pipelines/run_full_ukbb_hpa_mapping_bidirectional.py`

**Target YAML Strategy:**
-   `UKBB_TO_HPA_BIDIRECTIONAL_EFFICIENT` in `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/configs/mapping_strategies_config.yaml`

## 3. Detailed Steps & Requirements

1.  **Create `LoadEndpointIdentifiersAction`:**
    *   **File:** `biomapper/core/strategy_actions/load_endpoint_identifiers_action.py`
    *   **Class:** `LoadEndpointIdentifiersAction(BaseStrategyAction)`
    *   **`__init__(self, params: dict)`:**
        *   Expect `endpoint_name` (str) and `output_context_key` (str) from `params`.
        *   Validate their presence.
    *   **`async execute(self, context: dict, executor: 'MappingExecutor') -> dict:`:**
        *   Placeholder logic: Log that it's loading identifiers for `self.endpoint_name`.
        *   Access `executor.db_manager` to simulate fetching identifiers (actual DB query not needed for placeholder).
        *   Create a dummy list of identifiers (e.g., `["ID1", "ID2", "ID3"]`).
        *   Store this list in the `context` under the key `self.output_context_key`.
        *   Return the updated `context`.

2.  **Create `ReconcileBidirectionalAction`:**
    *   **File:** `biomapper/core/strategy_actions/reconcile_bidirectional_action.py`
    *   **Class:** `ReconcileBidirectionalAction(BaseStrategyAction)`
    *   **`__init__(self, params: dict)`:**
        *   Expect `forward_mapping_key` (str, context key for source->target results), `reverse_mapping_key` (str, context key for target->source results), and `output_reconciled_key` (str) from `params`.
        *   Validate their presence.
    *   **`async execute(self, context: dict, executor: 'MappingExecutor') -> dict:`:**
        *   Placeholder logic: Log that it's reconciling mappings from `self.forward_mapping_key` and `self.reverse_mapping_key`.
        *   Access dummy data from these keys in the `context` (assume they would contain lists of mapped pairs or similar structures).
        *   Create a dummy reconciled result (e.g., a dictionary or list representing reconciled pairs).
        *   Store this dummy result in the `context` under `self.output_reconciled_key`.
        *   Return the updated `context`.

3.  **Create `SaveBidirectionalResultsAction`:**
    *   **File:** `biomapper/core/strategy_actions/save_bidirectional_results_action.py`
    *   **Class:** `SaveBidirectionalResultsAction(BaseStrategyAction)`
    *   **`__init__(self, params: dict)`:**
        *   Expect `reconciled_data_key` (str, context key for reconciled results), `output_dir_key` (str, context key for output directory path), `csv_filename` (str), and `json_summary_filename` (str) from `params`.
        *   The `output_dir_key` will provide the base path, which might come from the initial context passed to `MappingExecutor.execute_strategy`.
        *   Validate presence of these parameters.
    *   **`async execute(self, context: dict, executor: 'MappingExecutor') -> dict:`:**
        *   Placeholder logic: Log that it's saving results from `self.reconciled_data_key`.
        *   Retrieve the output directory path from `context[self.output_dir_key]`.
        *   Log the intended full paths for the CSV and JSON files (e.g., `os.path.join(output_dir, self.csv_filename)`).
        *   (Actual file writing not required for placeholder).
        *   Return the `context` (can be unchanged if only side effects like saving occur).

4.  **Update `biomapper/core/strategy_actions/__init__.py`:**
    *   Ensure the new action classes are imported and added to `__all__` so they can be discovered by `MappingExecutor`'s action registration mechanism.

5.  **Verify Action Registration (Conceptual):**
    *   While full execution isn't required by this prompt, consider (or briefly test if feasible without full pipeline setup) if `MappingExecutor.register_actions()` would pick up these new classes. This might involve temporarily adding these actions to a dummy YAML strategy and running a snippet that initializes `MappingExecutor` and calls `load_strategy`.

## 4. Success Criteria & Validation
-   The three Python files for `LoadEndpointIdentifiersAction`, `ReconcileBidirectionalAction`, and `SaveBidirectionalResultsAction` are created in `biomapper/core/strategy_actions/`.
-   Each class inherits from `BaseStrategyAction` and has the specified `__init__` and `async execute` methods with placeholder logic (logging, dummy data manipulation).
-   Required parameters are checked in `__init__`.
-   The `biomapper/core/strategy_actions/__init__.py` is updated to include these new actions.
-   The code is free of syntax errors and adheres to basic Python best practices (e.g., type hints for method signatures).

## 5. Implementation Requirements
-   **Input files/data:** Existing `biomapper/core/strategy_actions/base_action.py`.
-   **Expected outputs:**
    -   `biomapper/core/strategy_actions/load_endpoint_identifiers_action.py`
    -   `biomapper/core/strategy_actions/reconcile_bidirectional_action.py`
    -   `biomapper/core/strategy_actions/save_bidirectional_results_action.py`
    -   Updated `biomapper/core/strategy_actions/__init__.py`
-   **Code standards:** Follow existing project conventions (PEP 8, type hints, class structure). Ensure imports are correct.

## 6. Error Recovery Instructions
-   If `BaseStrategyAction` or other core components cannot be imported, double-check relative import paths.
-   If unsure about parameter names or context keys, make a reasonable assumption and document it in the feedback. The exact keys can be refined when these actions are integrated into the YAML strategy.

## 7. Feedback Format
Please provide the following in your feedback:
-   **Files Created/Modified:** List of all files touched.
-   **Confirmation of Requirements:** Confirm that each placeholder action class was created with the specified methods and placeholder logic.
-   **`__init__.py` Update:** Confirm the `__init__.py` file was updated.
-   **Potential Issues/Questions:** Any challenges encountered or questions for clarification (e.g., about parameter names, context flow).
-   **Confidence Assessment:** Your confidence that the actions are correctly structured as placeholders.
-   **Completed Subtasks:** Checklist of what was accomplished.
