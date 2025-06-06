# Task: Implement UKBB to HPA Protein Mapping via YAML Strategy

**Source Prompt Reference:** This task is defined by the prompt: `/home/ubuntu/biomapper/roadmap/_active_prompts/2025-06-05-013344-implement-ukbb-hpa-yaml-strategy.md`

## 1. Task Objective
Implement and test the unidirectional UKBB to HPA protein mapping pipeline using the newly defined YAML-based mapping strategy framework. This involves:
1.  Defining the UKBB-to-HPA mapping strategy in `protein_config.yaml`.
2.  Updating `populate_metamapper_db.py` to parse and store `mapping_strategies` in `metamapper.db`.
3.  Enhancing `MappingExecutor` to load and execute these YAML-defined strategies.
4.  Developing the necessary Python `action.type` handler modules.
5.  Creating an integration test to verify the end-to-end mapping process.

## 2. Prerequisites
- [X] Familiarity with the Biomapper project structure and goals (review `/home/ubuntu/biomapper/CLAUDE.md`).
- [X] Understanding of the YAML-defined mapping strategy concept (review `/home/ubuntu/biomapper/roadmap/technical_notes/core_mapping_logic/yaml_defined_mapping_strategies.md`).
- [X] Understanding of the specific UKBB/HPA/QIN mapping requirements (review `/home/ubuntu/biomapper/roadmap/guides/configuring_ukbb_hpa_qin_mapping.md`).
- [X] Python development environment with Biomapper dependencies installed (via Poetry).
- [X] Access to the Biomapper codebase at `/home/ubuntu/biomapper/`.
- [X] Core files exist:
    - `/home/ubuntu/biomapper/configs/protein_config.yaml`
    - `/home/ubuntu/biomapper/scripts/populate_metamapper_db.py`
    - `/home/ubuntu/biomapper/biomapper/core/mapping_executor.py`
    - `/home/ubuntu/biomapper/biomapper/db/models.py`
- [ ] (Optional but Recommended) Sample data files for UKBB (e.g., `UKBB_Protein_Meta.tsv`) and HPA (e.g., `proteinatlas.tsv`) are available in `/home/ubuntu/biomapper/data/` for testing. If not, mock data will need to be created for tests.

## 3. Context from Previous Attempts (if applicable)
N/A - This is the first attempt for this comprehensive task.

## 4. Task Decomposition
Break this task into the following verifiable subtasks. Address them sequentially, ensuring each is functional before proceeding to the next.

1.  **Subtask 1: Define UKBB-to-HPA Mapping Strategy in YAML**
    *   **Description:** Add the `UKBB_TO_HPA_PROTEIN_PIPELINE` mapping strategy to `/home/ubuntu/biomapper/configs/protein_config.yaml`. Use the conceptual YAML structure discussed (UKBB Native ID -> UKBB UniProt AC -> Resolve History -> Filter by HPA UniProt -> HPA UniProt AC -> HPA Native ID).
    *   **Validation:** The YAML structure is valid and correctly represents the intended mapping flow.

2.  **Subtask 2: Extend `populate_metamapper_db.py` for Mapping Strategies**
    *   **Description:** Modify `/home/ubuntu/biomapper/scripts/populate_metamapper_db.py` and `/home/ubuntu/biomapper/biomapper/db/models.py`.
        *   Define new SQLAlchemy models (e.g., `MappingStrategy`, `MappingStrategyStep`) in `models.py` to store strategies and their ordered steps, including `action.type` and parameters.
        *   Implement parsing logic in `populate_metamapper_db.py` to read the `mapping_strategies` section from YAML configuration files.
        *   Populate the new database tables with the parsed strategy data.
        *   Update the `ConfigurationValidator` in `populate_metamapper_db.py` to validate the `mapping_strategies` section.
    *   **Validation:** The script successfully parses the strategy from `protein_config.yaml` and stores it correctly in `metamapper.db`. The validator catches malformed strategies.

3.  **Subtask 3: Enhance `MappingExecutor` for Strategy Execution**
    *   **Description:** Modify `/home/ubuntu/biomapper/biomapper/core/mapping_executor.py`.
        *   Add a new method, e.g., `execute_yaml_strategy(self, strategy_name: str, input_ids: List[str], source_ontology_type: str, target_ontology_type: str) -> List[Tuple[str, str]]`.
        *   This method should load the named strategy (and its steps) from `metamapper.db`.
        *   Implement a loop to iterate through the strategy's steps in order.
        *   Implement a dispatch mechanism that takes the `action.type` string from a step and calls the corresponding Python handler module/function (initially, these can be stubs/placeholders if handlers are developed in Subtask 4).
        *   Define and manage the flow of data (e.g., the list of identifiers being processed) between steps.
    *   **Validation:** `MappingExecutor` can load a strategy and attempt to dispatch to action handlers (even if they are just stubs initially).

4.  **Subtask 4: Implement Core Action Handler Modules**
    *   **Description:** Create a new directory, e.g., `/home/ubuntu/biomapper/biomapper/core/strategy_actions/`. Implement the following action handlers as Python modules/functions. Each handler should accept the current list of identifiers and parameters defined in the YAML step.
        *   `CONVERT_IDENTIFIERS_LOCAL`: Converts identifiers using data within a single specified endpoint. Parameters: `endpoint_context` (SOURCE/TARGET), `output_ontology_type` (and optionally `input_ontology_type`).
        *   `EXECUTE_MAPPING_PATH`: Executes a pre-defined mapping path from `metamapper.db`. Parameter: `path_name`. Ensure the `RESOLVE_UNIPROT_HISTORY_VIA_API` path (using `UniProtHistoricalResolverClient`) is defined in `protein_config.yaml` and populated if it doesn't exist.
        *   `FILTER_IDENTIFIERS_BY_TARGET_PRESENCE`: Filters identifiers based on their presence in the target endpoint. Parameters: `endpoint_context` (TARGET), `ontology_type_to_match`.
    *   **Validation:** Each action handler passes unit tests with mock inputs and parameters.

5.  **Subtask 5: Integration Testing**
    *   **Description:** Create a new test script (e.g., in `/home/ubuntu/biomapper/tests/integration/`) that uses `MappingExecutor.execute_yaml_strategy` to run the full `UKBB_TO_HPA_PROTEIN_PIPELINE`.
    *   Use a small, well-defined set of sample UKBB input identifiers.
    *   Assert that the final output (mapped HPA Ensembl Gene IDs) is correct based on known data or expected outcomes of each step.
    *   **Validation:** The integration test passes, demonstrating a successful end-to-end UKBB to HPA mapping via the YAML strategy.

## 5. Implementation Requirements
- **Input files/data (to be modified or used):**
    - `/home/ubuntu/biomapper/configs/protein_config.yaml`
    - `/home/ubuntu/biomapper/scripts/populate_metamapper_db.py`
    - `/home/ubuntu/biomapper/biomapper/core/mapping_executor.py`
    - `/home/ubuntu/biomapper/biomapper/db/models.py`
    - Reference Documents:
        - `/home/ubuntu/biomapper/roadmap/guides/configuring_ukbb_hpa_qin_mapping.md`
        - `/home/ubuntu/biomapper/roadmap/technical_notes/core_mapping_logic/yaml_defined_mapping_strategies.md`
- **Expected outputs (new or modified files/directories):**
    - Modified `/home/ubuntu/biomapper/configs/protein_config.yaml`
    - Modified `/home/ubuntu/biomapper/scripts/populate_metamapper_db.py`
    - Modified `/home/ubuntu/biomapper/biomapper/core/mapping_executor.py`
    - Modified `/home/ubuntu/biomapper/biomapper/db/models.py`
    - New directory: `/home/ubuntu/biomapper/biomapper/core/strategy_actions/`
    - New Python modules within `strategy_actions/` for each action type.
    - New test script in `/home/ubuntu/biomapper/tests/integration/`.
- **Code standards:** Adhere to existing project conventions (PEP 8, type hints). All new functionality must be accompanied by unit tests (use `pytest`).
- **Validation requirements:** Each subtask has specific validation criteria. The overall success is determined by the passing integration test.

## 6. Error Recovery Instructions
If you encounter errors during execution:
- **Permission/Tool Errors:** Ensure you have write permissions to the necessary files and directories. Verify Poetry environment is active.
- **Dependency Errors:** Use `poetry install` or `poetry add <package>` if dependencies are missing. Consult `pyproject.toml`.
- **Configuration Errors (YAML/DB):** Carefully check YAML syntax in `protein_config.yaml`. Verify database schema changes and data population logic in `populate_metamapper_db.py`.
- **Logic/Implementation Errors:** Use `pdb` or print statements for debugging. Break down complex logic into smaller, testable functions. Refer to existing code patterns in Biomapper.

For each error type, indicate in your feedback:
- Error classification: [RETRY_WITH_MODIFICATIONS | ESCALATE_TO_USER | REQUIRE_DIFFERENT_APPROACH]
- Specific changes needed for retry (if applicable)
- Confidence level in proposed solution

## 7. Success Criteria and Validation
Task is complete when:
- [ ] **Subtask 1:** `UKBB_TO_HPA_PROTEIN_PIPELINE` strategy is correctly defined in `/home/ubuntu/biomapper/configs/protein_config.yaml`.
- [ ] **Subtask 2:** `populate_metamapper_db.py` successfully parses and stores the `mapping_strategies` into new/updated tables in `metamapper.db`. The validator works.
- [ ] **Subtask 3:** `MappingExecutor` has a functional `execute_yaml_strategy` method that loads strategies and dispatches to action handlers.
- [ ] **Subtask 4:** Action handlers (`CONVERT_IDENTIFIERS_LOCAL`, `EXECUTE_MAPPING_PATH`, `FILTER_IDENTIFIERS_BY_TARGET_PRESENCE`) are implemented and unit-tested.
- [ ] **Subtask 5:** The integration test for the `UKBB_TO_HPA_PROTEIN_PIPELINE` passes, producing correct HPA IDs from sample UKBB IDs.
- [ ] All new code includes appropriate docstrings and type hints.
- [ ] All new functional code is covered by unit tests.

## 8. Feedback Requirements
Create a detailed Markdown feedback file at:
`/home/ubuntu/biomapper/roadmap/_active_prompts/feedback/YYYY-MM-DD-HHMMSS-feedback-implement-ukbb-hpa-yaml-strategy.md`
(Use the timestamp of when you complete the task for YYYY-MM-DD-HHMMSS).

**Mandatory Feedback Sections:**
- **Execution Status:** [COMPLETE_SUCCESS | PARTIAL_SUCCESS | FAILED_WITH_RECOVERY_OPTIONS | FAILED_NEEDS_ESCALATION]
- **Completed Subtasks:** [Checklist of subtasks from Section 4 that were accomplished]
- **Issues Encountered:** [Detailed error descriptions with context, tracebacks, and attempted fixes]
- **Next Action Recommendation:** [Specific follow-up needed, or confirmation of completion]
- **Confidence Assessment:** [Quality of implementation, testing coverage, potential risks or areas for improvement]
- **Environment Changes:** [List any new files/directories created, critical environment variables set, or dependencies added/changed]
- **Lessons Learned:** [Patterns that worked well, challenges, or insights for future tasks]
- **Code Snippets (Optional but helpful for key changes):** [Brief snippets of important new/modified code sections]
