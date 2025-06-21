# Task: Fix `TypeError` in `execute_yaml_strategy` Method

## 1. Objective

Resolve the critical runtime bug `TypeError: MappingExecutor.execute_yaml_strategy() got an unexpected keyword argument 'initial_context'`. The fix involves updating the method's signature to accept dynamic context parameters, which is essential for our newly refactored, flexible pipeline execution.

## 2. Context and Background

We recently refactored the main pipeline script (`run_full_ukbb_hpa_mapping.py`) to invoke a self-contained YAML strategy. As part of this refactoring, the script now passes an `initial_context` dictionary to the `MappingExecutor.execute_yaml_strategy` method. This dictionary is intended to carry runtime parameters, such as the output directory for saving results.

However, the pipeline currently fails immediately with a `TypeError` because the method signature for `execute_yaml_strategy` was not updated to accept this new `initial_context` argument. This task is to correct that oversight.

## 3. Prerequisites

- The agent must understand the role of `MappingExecutor` and how it executes YAML-defined strategies.
- The target file for this fix is `biomapper/core/mapping_executor.py`.

## 4. Task Breakdown

1.  **Locate the `execute_yaml_strategy` method** within `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/biomapper/core/mapping_executor.py`.
2.  **Update the Method Signature:**
    - Add a new optional parameter to the method definition: `initial_context: Optional[Dict[str, Any]] = None`.
3.  **Integrate the Initial Context:**
    - Inside the method, locate where the `execution_context` dictionary is initialized.
    - If `initial_context` is provided (i.e., not `None`), merge its contents into the main `execution_context`. The initial context should take precedence if there are any key conflicts.
    - A simple way to do this is:
      ```python
      execution_context = {}
      if initial_context:
          execution_context.update(initial_context)
      ```
      Ensure this is placed correctly before the strategy's steps are executed.

## 5. Implementation Requirements

- **Input File:** `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/biomapper/core/mapping_executor.py`
- **Expected Outputs:** The modified `mapping_executor.py` file with the bug fix applied.
- **Code Standards:** Maintain existing code style, including full type hinting.

## 6. Error Recovery Instructions

- **`TypeError` Persists:** If the error continues, double-check that you have modified the correct method signature and that there are no other layers (e.g., wrapper methods) that are blocking the parameter from being passed through.
- **`AttributeError`:** If you encounter an `AttributeError`, it may indicate that the context is not being passed correctly to the underlying `StrategyExecutionService`. Ensure the `execution_context` is properly updated and passed in the service call.

## 7. Validation and Success Criteria

- **Primary Validation:** The fix is considered successful when the main pipeline script can be executed without the `TypeError`.
- **Execution Command:** Run the following command from the project root (`/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/`):
  ```bash
  poetry run python scripts/main_pipelines/run_full_ukbb_hpa_mapping.py
  ```
- **Expected Outcome:** The script should start, and the log output should show the strategy execution beginning, without the immediate crash we saw previously.

## 8. Feedback and Reporting

- Provide the `diff` of the changes made to `mapping_executor.py`.
- Confirm that you ran the validation command and that the `TypeError` is resolved.
- Provide the first 20-30 lines of the log output from the successful run to show the pipeline is progressing.
