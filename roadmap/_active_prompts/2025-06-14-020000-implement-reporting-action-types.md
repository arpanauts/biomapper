# Task: Implement Reporting as Action Types for Strategy Integration

**Source Prompt Reference:** This task is defined by the prompt: `/home/ubuntu/biomapper/roadmap/_active_prompts/2025-06-14-020000-implement-reporting-action-types.md`

## 1. Task Objective
Transform reporting functionality from script utilities into action types that can be integrated directly into mapping strategies, providing standardized reporting capabilities and eliminating reporting code duplication across scripts.

**Success Criteria:**
- New reporting action types implemented and tested
- Reporting can be embedded in YAML strategy definitions
- All scripts updated to use strategy-based reporting
- Consistent reporting format across all pipelines
- Comprehensive test coverage for reporting actions

## 2. Prerequisites
- [ ] Required files exist: `/home/ubuntu/biomapper/biomapper/core/mapping_executor.py`
- [ ] Required files exist: `/home/ubuntu/biomapper/scripts/main_pipelines/run_full_ukbb_hpa_mapping_bidirectional.py`
- [ ] Required files exist: `/home/ubuntu/biomapper/configs/mapping_strategies_config.yaml`
- [ ] Required permissions: Write access to core biomapper files and test directories
- [ ] Required dependencies: Poetry environment active with pytest
- [ ] Environment state: Git working directory clean for easy change tracking

## 3. Context from Previous Attempts
This is a fresh implementation task based on architectural analysis identifying reporting code duplication patterns in bidirectional mapping scripts. The goal is to make reporting a first-class citizen in the strategy system.

## 4. Task Decomposition
Break this task into the following verifiable subtasks:
1. **Analyze reporting patterns:** Identify common reporting functions across scripts
2. **Design reporting action types:** Create action specifications for different report types
3. **Implement core reporting actions:** Build action classes with proper async patterns
4. **Create unit tests:** Test reporting actions with mocked data and edge cases
5. **Update strategy configurations:** Add reporting steps to YAML strategies
6. **Update scripts:** Remove reporting code and rely on strategy-based reporting
7. **Integration testing:** Verify reporting works within complete strategies

## 5. Implementation Requirements

**Target Reporting Actions to Implement:**

- **GENERATE_MAPPING_SUMMARY** - High-level summary of mapping results
  - Parameters: `output_format` (console|json|csv), `include_statistics` (bool)
  - Outputs: Summary statistics, coverage metrics, timing information
  - Context inputs: Uses all context data from previous steps

- **GENERATE_DETAILED_REPORT** - Comprehensive mapping analysis
  - Parameters: `output_file` (optional), `include_unmatched` (bool), `grouping_strategy` (by_step|by_ontology)
  - Outputs: Detailed breakdown by mapping step, unmatched identifier analysis
  - Context inputs: Step-by-step results, provenance data

- **EXPORT_RESULTS** - Export mapping results in various formats
  - Parameters: `output_format` (csv|json|tsv), `output_file`, `columns` (list)
  - Outputs: Structured data files with mapping results
  - Context inputs: Final mapped identifiers, intermediate results

- **VISUALIZE_MAPPING_FLOW** - Generate visual representation of mapping process
  - Parameters: `output_file`, `chart_type` (sankey|bar|flow), `show_statistics` (bool)
  - Outputs: Charts showing identifier flow through strategy steps
  - Context inputs: Step-by-step identifier counts, transformation data

**Expected outputs:**
- New action files in `/home/ubuntu/biomapper/biomapper/core/strategy_actions/`
- Test files in `/home/ubuntu/biomapper/tests/unit/core/strategy_actions/`
- Updated strategy configurations with reporting steps
- Updated scripts with simplified reporting logic

**Code standards:**
- Follow existing action type patterns (async execute methods, context handling)
- Comprehensive type hints and docstrings with examples
- Proper error handling for file I/O and data formatting
- Support for both console output and file export

## 6. Error Recovery Instructions
If you encounter errors during execution:
- **Import/Module Errors:** Ensure all visualization libraries are available or make them optional dependencies
- **File I/O Errors:** Implement proper path handling and permission checking
- **Data Format Errors:** Add validation for output formats and graceful fallbacks
- **Context Data Errors:** Handle missing or malformed context data appropriately

For each error type, indicate in your feedback:
- Error classification: [RETRY_WITH_MODIFICATIONS | ESCALATE_TO_USER | REQUIRE_DIFFERENT_APPROACH]
- Specific changes needed for retry (if applicable)
- Confidence level in proposed solution

## 7. Success Criteria and Validation
Task is complete when:
- [ ] All four reporting action types implemented with proper async patterns
- [ ] Comprehensive unit tests pass for all reporting actions
- [ ] Updated strategy in `mapping_strategies_config.yaml` includes reporting steps
- [ ] Bidirectional script simplified by removing reporting code
- [ ] Integration test: Full strategy with reporting produces expected outputs
- [ ] All reporting outputs are consistent and well-formatted

## 8. Feedback Requirements
Create a detailed Markdown feedback file at:
`/home/ubuntu/biomapper/roadmap/_active_prompts/feedback/2025-06-14-020000-feedback-reporting-actions.md`

**Mandatory Feedback Sections:**
- **Execution Status:** [COMPLETE_SUCCESS | PARTIAL_SUCCESS | FAILED_WITH_RECOVERY_OPTIONS | FAILED_NEEDS_ESCALATION]
- **Completed Subtasks:** [checklist of what was accomplished]
- **Action Design Decisions:** [explain choices for reporting action interfaces]
- **Strategy Integration:** [how reporting steps integrate with existing strategies]
- **Testing Coverage:** [describe test scenarios and output validation]
- **Script Simplification:** [how much reporting code was eliminated]
- **Output Quality Assessment:** [quality and usefulness of generated reports]
- **Next Action Recommendation:** [any follow-up work needed]
- **Environment Changes:** [files created/modified, dependencies added]

## 9. Additional Context
**Project Architecture:** The biomapper uses YAML-defined strategies where each step is an action type. Reporting should integrate seamlessly as final steps in strategies, with access to all context data accumulated during execution.

**Output Requirements:** Reporting actions should generate both human-readable and machine-readable outputs. Consider integration with Jupyter notebooks where visual outputs are particularly valuable.

**Performance Considerations:** Reporting actions should be efficient and not significantly impact strategy execution time. Consider lazy evaluation for expensive visualizations.

**Flexibility:** Design reporting actions to be reusable across different mapping strategies and entity types. Use parameters to customize output without creating action type proliferation.