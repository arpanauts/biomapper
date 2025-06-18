# Task: Simplify MappingExecutor by Integrating Robust Functionality

**Source Prompt Reference:** This task is defined by the prompt: /home/ubuntu/biomapper/roadmap/_active_prompts/2025-06-15-175500-simplify-mapping-executor.md

## 1. Task Objective
Merge the RobustExecutionMixin functionality directly into MappingExecutor to simplify the codebase, eliminating the need for EnhancedMappingExecutor as a separate class. The goal is to have a single, unified MappingExecutor class with all robust features built-in while maintaining complete backward compatibility.

## 2. Prerequisites
- [ ] Required files exist:
  - /home/ubuntu/biomapper/biomapper/core/mapping_executor.py
  - /home/ubuntu/biomapper/biomapper/core/mapping_executor_robust.py
  - /home/ubuntu/biomapper/biomapper/core/mapping_executor_enhanced.py
  - /home/ubuntu/biomapper/biomapper/core/__init__.py
  - /home/ubuntu/biomapper/scripts/main_pipelines/run_full_ukbb_hpa_mapping_bidirectional.py
- [ ] Required permissions: Write access to all files above
- [ ] Required dependencies: None (refactoring only)
- [ ] Environment state: Working biomapper installation with Poetry

## 3. Context from Previous Attempts
- **Previous attempt timestamp:** N/A (first attempt)
- **Issues encountered:** N/A
- **Partial successes:** N/A
- **Recommended modifications:** N/A

## 4. Task Decomposition
Break this task into the following verifiable subtasks:
1. **Add robust parameters to MappingExecutor.__init__:** Add checkpoint_enabled, checkpoint_dir, batch_size, max_retries, retry_delay with backward-compatible defaults
2. **Copy methods from RobustExecutionMixin:** Transfer all methods including checkpointing, retry logic, progress tracking, and batch processing
3. **Update imports in __init__.py:** Ensure MappingExecutor is the primary export, optionally keep EnhancedMappingExecutor as deprecated alias
4. **Update scripts to use MappingExecutor:** Change run_full_ukbb_hpa_mapping_bidirectional.py to use MappingExecutor
5. **Test backward compatibility:** Verify existing code still works
6. **Clean up obsolete files:** Remove or deprecate mapping_executor_robust.py and mapping_executor_enhanced.py

## 5. Implementation Requirements
- **Input files/data:** 
  - /home/ubuntu/biomapper/biomapper/core/mapping_executor_robust.py (source of methods to copy)
  - /home/ubuntu/biomapper/biomapper/core/mapping_executor_enhanced.py (to understand parameter passing)
  - /home/ubuntu/biomapper/biomapper/core/mapping_executor.py (target for integration)
- **Expected outputs:**
  - Modified /home/ubuntu/biomapper/biomapper/core/mapping_executor.py with integrated robust features
  - Updated /home/ubuntu/biomapper/biomapper/core/__init__.py
  - Updated /home/ubuntu/biomapper/scripts/main_pipelines/run_full_ukbb_hpa_mapping_bidirectional.py
  - Optional: Deprecated versions of robust.py and enhanced.py with warnings
- **Code standards:**
  - Maintain existing code style and documentation
  - Add deprecation warnings where appropriate
  - Preserve all type hints
  - Keep comprehensive docstrings
- **Validation requirements:**
  - Run a test mapping to ensure functionality is preserved
  - Check that existing scripts can still instantiate MappingExecutor without errors

## 6. Error Recovery Instructions
If you encounter errors during execution:
- **Import Errors:** Ensure all necessary imports from RobustExecutionMixin are added to MappingExecutor
- **Method Resolution Order (MRO) Errors:** Remove the mixin inheritance pattern and integrate methods directly
- **Parameter Conflicts:** Use the same parameter names and defaults as in RobustExecutionMixin
- **Logic/Implementation Errors:** Compare behavior with current EnhancedMappingExecutor to ensure equivalence

For each error type, indicate in your feedback:
- Error classification: [RETRY_WITH_MODIFICATIONS | ESCALATE_TO_USER | REQUIRE_DIFFERENT_APPROACH]
- Specific changes needed for retry (if applicable)
- Confidence level in proposed solution

## 7. Success Criteria and Validation
Task is complete when:
- [ ] MappingExecutor has all robust functionality integrated (checkpointing, retry, progress tracking, batch processing)
- [ ] All robust parameters have backward-compatible defaults (checkpoint_enabled=False, etc.)
- [ ] The script run_full_ukbb_hpa_mapping_bidirectional.py works with MappingExecutor instead of EnhancedMappingExecutor
- [ ] A test run of `python /home/ubuntu/biomapper/scripts/main_pipelines/run_full_ukbb_hpa_mapping_bidirectional.py --help` shows the robust options
- [ ] Existing code that uses MappingExecutor continues to work without modification

## 8. Feedback Requirements
Create a detailed Markdown feedback file at:
`/home/ubuntu/biomapper/roadmap/_active_prompts/feedback/2025-06-15-175500-feedback-simplify-mapping-executor.md`

**Mandatory Feedback Sections:**
- **Execution Status:** [COMPLETE_SUCCESS | PARTIAL_SUCCESS | FAILED_WITH_RECOVERY_OPTIONS | FAILED_NEEDS_ESCALATION]
- **Completed Subtasks:** [checklist of what was accomplished]
- **Issues Encountered:** [detailed error descriptions with context]
- **Next Action Recommendation:** [specific follow-up needed]
- **Confidence Assessment:** [quality, testing coverage, risk level]
- **Environment Changes:** [any files created, permissions changed, etc.]
- **Lessons Learned:** [patterns that worked or should be avoided]

## Additional Context

The current architecture has three classes:
1. **RobustExecutionMixin** - Contains checkpointing, retry logic, progress tracking, batch processing
2. **MappingExecutor** - The core mapping functionality
3. **EnhancedMappingExecutor** - Simply inherits from both with no additional logic

The goal is to have just one class (MappingExecutor) with all functionality, making the codebase simpler and easier to maintain. The key challenge is maintaining backward compatibility while integrating all the robust features.

Key methods to integrate from RobustExecutionMixin:
- `__init__` modifications for new parameters
- `add_progress_callback`
- `_report_progress`
- `save_checkpoint`, `load_checkpoint`, `clear_checkpoint`
- `execute_with_retry`
- `process_in_batches`
- `execute_yaml_strategy_robust`

Remember to:
1. Preserve the existing MappingExecutor functionality
2. Add all parameters with defaults that maintain current behavior
3. Keep EnhancedMappingExecutor as a deprecated alias for smooth transition
4. Update documentation strings to reflect the integrated functionality