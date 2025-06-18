# Suggested Next Work Session Prompt

## Context Brief
The biomapper project now has robust execution capabilities integrated via EnhancedMappingExecutor with working checkpointing, retry logic, and batch processing. The UKBB-HPA bidirectional mapping successfully processes 2,923 proteins with 16.9% coverage (493 mapped). However, the checkpoint functionality is only fully implemented for batch processing, not for the main strategy execution flow.

## Initial Steps
1. Begin by reviewing `/home/ubuntu/biomapper/CLAUDE.md` for overall project context and development guidelines
2. Check `/home/ubuntu/biomapper/roadmap/_status_updates/2025-06-15-robust-executor-integration.md` for detailed status of robust executor implementation
3. Review `/home/ubuntu/biomapper/biomapper/core/mapping_executor_robust.py` to understand current checkpoint implementation

## Work Priorities

### Priority 1: Implement Full Strategy-Level Checkpointing
- Enhance `execute_yaml_strategy_robust` method to save checkpoints after each strategy step
- Design checkpoint format that captures:
  - Current step index
  - Context state after each step
  - Partial results
  - Step execution metadata
- Implement resume logic that can start from any saved step
- Test with a long-running strategy to verify checkpoint/resume functionality

### Priority 2: Optimize Results Post-Processing 
- Investigate why creating final DataFrames times out for large datasets
- Consider implementing streaming CSV writer that doesn't require full DataFrame in memory
- Profile the current implementation in `/home/ubuntu/biomapper/scripts/main_pipelines/run_full_ukbb_hpa_mapping_bidirectional.py` to identify bottlenecks
- Test optimizations with full 2,923 identifier dataset

### Priority 3: Improve Export Format
- Fix the current export format that separates UNMAPPED and NEW entries
- Design a cleaner format with proper source-to-target mappings in single rows
- Update the EXPORT_RESULTS action in `/home/ubuntu/biomapper/biomapper/core/strategy_actions/export_results.py`
- Ensure backward compatibility or provide migration path

## References
- Enhanced Executor Implementation: `/home/ubuntu/biomapper/biomapper/core/mapping_executor_enhanced.py`
- Robust Execution Mixin: `/home/ubuntu/biomapper/biomapper/core/mapping_executor_robust.py`
- Bidirectional Mapping Script: `/home/ubuntu/biomapper/scripts/main_pipelines/run_full_ukbb_hpa_mapping_bidirectional.py`
- Working Batch Example: `/home/ubuntu/biomapper/run_full_mapping_with_batches.py`
- Strategy Config: `/home/ubuntu/biomapper/configs/mapping_strategies_config.yaml`

## Workflow Integration

### For Priority 1 (Strategy Checkpointing), consider using Claude to:
1. **Design the checkpoint format**: 
   ```
   "I need to design a checkpoint format for the biomapper strategy execution that captures the state after each step. The strategy has multiple steps (S1, S2, etc.) and maintains a context dictionary. Please help me design a checkpoint structure that:
   - Captures the current step index and context state
   - Allows resumption from any step
   - Handles both successful and failed step states
   - Is serializable and efficient
   Here's the current strategy execution flow: [provide relevant code]"
   ```

2. **Review the implementation approach**:
   ```
   "I'm implementing checkpointing for strategy execution in biomapper. Here's my planned approach: [describe approach]. Please review for:
   - Potential edge cases I might have missed
   - Performance implications
   - Better design patterns for this use case
   The current codebase uses pickle for checkpointing in batch processing: [show example]"
   ```

### For Priority 2 (Performance Optimization), leverage Claude for:
1. **Memory profiling analysis**:
   ```
   "I have a Python script that times out when creating a DataFrame with 2,923 rows. Here's the code that's timing out: [provide code]. Please help me:
   - Identify why this might be slow
   - Suggest memory-efficient alternatives
   - Recommend profiling approaches to find the bottleneck"
   ```

2. **Streaming implementation**:
   ```
   "I need to implement a streaming CSV writer for biomapper results that doesn't build the full DataFrame in memory. Current implementation: [show code]. Requirements:
   - Handle results as they're generated
   - Maintain the same output format
   - Support progress tracking
   Please suggest an efficient implementation."
   ```

This approach allows you to tackle the highest priority items while leveraging Claude's expertise for complex design decisions and performance optimization strategies.