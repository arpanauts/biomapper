# Task 8: Assemble Full-Featured UKBB-HPA Strategy YAML

**Source Prompt Reference:** This is the final integration task to recreate the legacy `UKBB_TO_HPA_PROTEIN_PIPELINE`.

## 1. Task Objective
Create a new YAML strategy file that orchestrates the full-featured UKBB-HPA mapping pipeline by chaining together the newly implemented and verified strategy actions. This new strategy should replicate the complete functionality of the legacy pipeline.

## 2. Service Architecture Context
- **Primary Service:** `biomapper-api` (configuration)
- **Affected Module:** A new YAML file in the `configs/` directory.
- **Service Dependencies:** This task depends on the successful completion and registration of all the individual strategy actions (Tasks 2-7).

## 3. Task Decomposition
1.  **Assume Actions are Ready:** For the purpose of this task, assume that all required actions (`LOCAL_ID_CONVERTER`, `API_RESOLVER`, `COMPOSITE_ID_SPLITTER`, `DATASET_FILTER`, `BIDIRECTIONAL_RECONCILER`, `SAVE_RESULTS`) have been implemented and registered.
2.  **Design the Strategy Flow:** Define the sequence of steps needed to replicate the legacy pipeline. This involves mapping each legacy step to its new action and ensuring the `input_context_key` and `output_context_key` values are chained correctly to pass data between the steps.
3.  **Write the YAML File:** Create a new file named `full_featured_ukbb_hpa_strategy.yaml` in the `/home/trentleslie/github/biomapper/configs/` directory.
4.  **Populate the YAML:** Write the full strategy definition in the new file, including a clear name, description, and the complete list of steps with their actions and parameters.
5.  **Add Documentation:** Include comments in the YAML file where necessary to explain complex steps or parameter choices.

## 4. Implementation Requirements
- **New Strategy File:** `/home/trentleslie/github/biomapper/configs/full_featured_ukbb_hpa_strategy.yaml`
- The strategy must be named `UKBB_HPA_FULL_PIPELINE`.
- The flow of data through the context keys must be logical and correct.

## 5. Success Criteria and Validation
- [ ] A new `full_featured_ukbb_hpa_strategy.yaml` file is created.
- [ ] The YAML is well-formed and syntactically correct.
- [ ] The strategy correctly chains together all the required actions in the logical order of the legacy pipeline.
- [ ] The strategy is well-documented, both in its description and with comments.
