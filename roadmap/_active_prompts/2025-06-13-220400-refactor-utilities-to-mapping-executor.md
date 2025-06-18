# Task: Refactor Script Utilities into MappingExecutor Core API

**Source Prompt Reference:** This task is defined by the prompt: `/home/ubuntu/biomapper/roadmap/_active_prompts/2025-06-13-220400-refactor-utilities-to-mapping-executor.md`

## 1. Task Objective
Eliminate code duplication by moving universal utility functions from scripts into MappingExecutor, providing a cleaner, more maintainable API for all biomapper scripts. Create a comprehensive interface that scripts can use instead of reimplementing common patterns.

**Success Criteria:**
- All identified utility functions moved to MappingExecutor with consistent API
- All existing scripts updated to use new MappingExecutor methods
- Zero functional changes - all scripts work exactly as before
- Comprehensive test coverage for new methods

## 2. Prerequisites
- [ ] Required files exist: `/home/ubuntu/biomapper/biomapper/core/mapping_executor.py`
- [ ] Required files exist: `/home/ubuntu/biomapper/scripts/main_pipelines/run_full_ukbb_hpa_mapping_bidirectional.py`
- [ ] Required files exist: `/home/ubuntu/biomapper/scripts/main_pipelines/run_full_ukbb_hpa_mapping.py`
- [ ] Required permissions: Write access to core biomapper files and test directories
- [ ] Required dependencies: Poetry environment active with pytest
- [ ] Environment state: Git working directory clean for easy change tracking

## 3. Context from Previous Attempts
This is a fresh architectural refactoring task based on analysis of code duplication patterns observed in the bidirectional mapping implementation.

## 4. Task Decomposition
Break this task into the following verifiable subtasks:
1. **Analyze duplicated functions:** Identify exact functions and their variations across scripts
2. **Design MappingExecutor API:** Create clean method signatures with proper async/await patterns
3. **Implement core methods:** Add new methods to MappingExecutor with comprehensive error handling
4. **Create unit tests:** Test new methods with mocked dependencies and edge cases
5. **Update scripts:** Refactor all scripts to use new MappingExecutor methods
6. **Integration testing:** Verify all scripts work identically to before
7. **Documentation:** Update docstrings and method documentation

## 5. Implementation Requirements

**Target Functions to Move (from `/home/ubuntu/biomapper/scripts/main_pipelines/run_full_ukbb_hpa_mapping_bidirectional.py`):**
- `check_strategy_exists(executor, strategy_name)` → `executor.get_strategy(strategy_name)`
- `get_column_for_ontology_type(executor, endpoint_name, ontology_type)` → `executor.get_ontology_column(endpoint_name, ontology_type)`
- `load_identifiers_from_endpoint(executor, endpoint_name, ontology_type)` → `executor.load_endpoint_identifiers(endpoint_name, ontology_type)`

**Additional API Methods to Add:**
- `async def execute_strategy_with_comprehensive_results(strategy_name, source_endpoint, target_endpoint, input_identifiers, **kwargs)` - High-level execution with enhanced result processing
- `async def get_strategy_info(strategy_name)` - Get strategy metadata and step information
- `async def validate_strategy_prerequisites(strategy_name, source_endpoint, target_endpoint)` - Pre-flight checks

**Expected outputs:**
- Updated `/home/ubuntu/biomapper/biomapper/core/mapping_executor.py` with new methods
- New test file `/home/ubuntu/biomapper/tests/unit/core/test_mapping_executor_utilities.py`
- Updated script files with refactored implementations
- Updated script files in `/home/ubuntu/biomapper/scripts/main_pipelines/`

**Code standards:**
- Follow existing MappingExecutor patterns for async methods
- Comprehensive type hints for all parameters and return values
- Detailed docstrings with examples
- Proper error handling with informative messages

## 6. Error Recovery Instructions
If you encounter errors during execution:
- **Import/Module Errors:** Check that all necessary imports are added to MappingExecutor
- **Async/Await Errors:** Ensure new methods properly handle async patterns and session management
- **Test Failures:** Mock external dependencies (DB, file systems) appropriately
- **Script Integration Errors:** Verify that script updates maintain exact same functionality

For each error type, indicate in your feedback:
- Error classification: [RETRY_WITH_MODIFICATIONS | ESCALATE_TO_USER | REQUIRE_DIFFERENT_APPROACH]
- Specific changes needed for retry (if applicable)
- Confidence level in proposed solution

## 7. Success Criteria and Validation
Task is complete when:
- [ ] All new MappingExecutor methods implemented with proper async patterns
- [ ] Comprehensive unit tests pass for all new methods
- [ ] All scripts in `/home/ubuntu/biomapper/scripts/main_pipelines/` updated to use new API
- [ ] Integration test: `python scripts/main_pipelines/run_full_ukbb_hpa_mapping.py` works identically
- [ ] Integration test: All script functions that were duplicated are now removed
- [ ] No functional regression - all script behaviors unchanged

## 8. Feedback Requirements
Create a detailed Markdown feedback file at:
`/home/ubuntu/biomapper/roadmap/_active_prompts/feedback/2025-06-13-220400-feedback-refactor-utilities.md`

**Mandatory Feedback Sections:**
- **Execution Status:** [COMPLETE_SUCCESS | PARTIAL_SUCCESS | FAILED_WITH_RECOVERY_OPTIONS | FAILED_NEEDS_ESCALATION]
- **Completed Subtasks:** [checklist of what was accomplished]
- **API Design Decisions:** [explain choices made for method signatures and error handling]
- **Script Migration Summary:** [which scripts were updated and how]
- **Testing Coverage:** [describe test scenarios and edge cases covered]
- **Integration Verification:** [results of running updated scripts]
- **Code Quality Assessment:** [maintainability, documentation, error handling quality]
- **Next Action Recommendation:** [any follow-up work needed]
- **Environment Changes:** [files created/modified, dependencies added]

## 9. Additional Context
**Project Architecture:** The biomapper uses an action-based strategy system where MappingExecutor runs YAML-defined strategies. This refactoring should strengthen MappingExecutor as the central API while maintaining the existing strategy system.

**Performance Considerations:** New methods should be efficient and not add overhead. Consider caching strategy metadata and endpoint information where appropriate.

**Backward Compatibility:** Existing code using execute_yaml_strategy should continue working unchanged. New methods are additive API improvements.