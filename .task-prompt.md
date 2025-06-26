# Task 2: Implement and Test `LocalIdConverter` Strategy Action

**Source Prompt Reference:** This task is part of recreating the legacy `UKBB_TO_HPA_PROTEIN_PIPELINE`.

## 1. Task Objective
Review, test, and finalize the `LocalIdConverter` strategy action. This action is responsible for mapping identifiers from a source ontology to a target ontology using a local data file, mirroring the functionality of the legacy `CONVERT_IDENTIFIERS_LOCAL` action.

## 2. Service Architecture Context
- **Primary Service:** `biomapper` (core library)
- **Affected Module:** `biomapper.core.strategy_actions.convert_identifiers_local`
- **Service Dependencies:** None. This is a self-contained library component.

## 3. Task Decomposition
1.  **Review Existing Code:** Analyze the existing implementation in `biomapper/core/strategy_actions/convert_identifiers_local.py`.
2.  **Define Action Interface:** Ensure the action accepts parameters for input/output context keys, the path to the local mapping file, and source/target column names.
3.  **Implement Core Logic:** The core logic should read the mapping file (e.g., a CSV or TSV) into a dictionary and use it to transform the input identifiers.
4.  **Add Unit Tests:** Create comprehensive unit tests in `tests/unit/strategy_actions/` to validate the action's functionality. Cover happy paths, edge cases (e.g., missing mappings, empty input), and error conditions.
5.  **Register the Action:** Ensure the action is correctly registered with a clear name (e.g., `LOCAL_ID_CONVERTER`) using the `@register_action` decorator.
6.  **Add Documentation:** Write a clear docstring explaining what the action does, its parameters, and an example of its usage in a strategy YAML.

## 4. Implementation Requirements
- **Action File:** `/home/trentleslie/github/biomapper/biomapper/core/strategy_actions/convert_identifiers_local.py`
- **Test File:** `/home/trentleslie/github/biomapper/tests/unit/strategy_actions/test_convert_identifiers_local.py`
- The action must be stateless and reusable.
- The action must produce detailed provenance information.

## 5. Success Criteria and Validation
- [ ] The action is implemented and registered in the action registry.
- [ ] Unit tests achieve 100% code coverage for the action.
- [ ] The action is well-documented with a clear docstring and examples.
- [ ] The implementation is clean, follows project coding standards, and is free of linting errors.
