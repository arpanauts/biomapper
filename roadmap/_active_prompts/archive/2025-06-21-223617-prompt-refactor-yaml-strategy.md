# Task: Refactor YAML Mapping Strategy for Robustness and Flexibility

## 1. Objective

Update the `UKBB_TO_HPA_BIDIRECTIONAL_EFFICIENT` mapping strategy in `configs/mapping_strategies_config.yaml` to improve its robustness and reusability. The primary goals are to use full database endpoint names instead of simplified aliases and to ensure output file paths are handled flexibly.

## 2. Context and Background

We have recently implemented several `StrategyAction` classes (`LoadEndpointIdentifiersAction`, `ReconcileBidirectionalAction`, `SaveBidirectionalResultsAction`) to modularize logic previously hardcoded in Python scripts. The current YAML strategy (`UKBB_TO_HPA_BIDIRECTIONAL_EFFICIENT`) uses these new actions but contains two key issues that prevent it from being fully robust:

1.  **Incorrect Endpoint Names:** It uses simplified names like `UKBB` and `HPA`. The `MappingExecutor` requires the full endpoint names as defined in the database (e.g., `UKBB_PROTEIN`).
2.  ** inflexible File Paths:** While the `SaveBidirectionalResultsAction` is designed to use a context variable for the output directory, we need to ensure the YAML configuration relies on this dynamic resolution rather than containing any hardcoded absolute paths.

This refactoring is the final step to fully decouple the mapping logic from the execution script, making our pipelines more modular and maintainable.

## 3. Prerequisites

- Familiarity with the Biomapper YAML strategy format.
- Understanding of how `StrategyAction` classes are parameterized from YAML.
- The target file is located at `configs/mapping_strategies_config.yaml`.

## 4. Task Breakdown

1.  **Locate the `UKBB_TO_HPA_BIDIRECTIONAL_EFFICIENT` strategy** within `configs/mapping_strategies_config.yaml`.
2.  **Update Endpoint Names in All Steps:**
    - In the `S1_LOAD_UKBB_IDENTIFIERS` step, change `source_endpoint: "UKBB"` to `source_endpoint: "UKBB_PROTEIN"`.
    - In the `S2_EXECUTE_FORWARD_MAPPING` step, change `target_endpoint_name: "HPA"` to `target_endpoint_name: "HPA_PROTEIN"`.
    - In the `S3_EXECUTE_REVERSE_MAPPING` step, change `source_endpoint_name: "HPA"` to `source_endpoint_name: "HPA_PROTEIN"` and `target_endpoint_name: "UKBB"` to `target_endpoint_name: "UKBB_PROTEIN"`.
3.  **Verify Output Path Parameterization:**
    - Confirm that the `S6_SAVE_RESULTS` step uses the `output_dir_key` parameter to dynamically resolve the output directory from the execution context. The current implementation is likely correct, but verify that no absolute paths are hardcoded.
4.  **Review and Save:** Ensure the entire file is still valid YAML after your changes.

## 5. Implementation Requirements

- **Input File:** `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/configs/mapping_strategies_config.yaml`
- **Expected Outputs:** The modified `configs/mapping_strategies_config.yaml` file with the specified changes applied.
- **Code Standards:** Maintain valid YAML syntax, formatting, and indentation.

## 6. Error Recovery Instructions

- **YAML Parsing Errors:** If the file cannot be parsed after your changes, carefully review your edits for syntax errors, paying close attention to indentation, quoting, and correct list/dictionary structure.
- **Incorrect Endpoint Names:** If you are unsure of the correct database endpoint names, they are defined in `configs/protein_config.yaml` under the `endpoints` section.

## 7. Validation and Success Criteria

- The `UKBB_TO_HPA_BIDIRECTIONAL_EFFICIENT` strategy in `configs/mapping_strategies_config.yaml` must be successfully updated.
- All instances of `UKBB` and `HPA` as endpoint names within this strategy must be replaced with `UKBB_PROTEIN` and `HPA_PROTEIN`, respectively.
- The `SaveBidirectionalResultsAction` step must be correctly configured to use a dynamic output directory via `output_dir_key`.
- The final YAML file must be syntactically valid.

## 8. Feedback and Reporting

- Provide the full, updated content of the `configs/mapping_strategies_config.yaml` file in your response.
- Explicitly confirm that all specified endpoint names have been corrected.
- Note any ambiguities or difficulties encountered during the task.
