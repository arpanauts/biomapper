# Suggested Next Prompt for Biomapper Development

## Context Brief
The biomapper project has successfully implemented a complete bidirectional mapping strategy with three new action types, fixing critical context persistence issues along the way. The optimized UKBB→HPA strategy eliminates unnecessary conversions and is ready for full dataset testing, though performance optimization is needed for large-scale UniProt resolution.

## Initial Steps
1. Begin by reviewing `/home/ubuntu/biomapper/CLAUDE.md` for overall project context and guidelines
2. Check `/home/ubuntu/biomapper/roadmap/_status_updates/2025-06-13-comprehensive-action-types-implementation.md` for the full implementation details
3. Review the new action implementations in `/home/ubuntu/biomapper/biomapper/core/strategy_actions/`
4. Look at `/home/ubuntu/biomapper/scripts/main_pipelines/run_full_ukbb_hpa_mapping_bidirectional.py` for the optimized pipeline

## Work Priorities

### Priority 1: Performance Optimization for Large-Scale Resolution
The RESOLVE_AND_MATCH_REVERSE action times out with 2991 HPA identifiers. Critical optimizations needed:
- Implement concurrent API calls within rate limits
- Add comprehensive progress tracking
- Optimize batch processing strategy
- Consider more aggressive caching

### Priority 2: Full Dataset Comparison
Once performance is optimized:
- Run original UKBB→HPA strategy and capture metrics
- Run bidirectional strategy on same dataset
- Compare: execution time, coverage, memory usage
- Document findings and recommendations

### Priority 3: Strategy Comparison Framework
Build tooling to systematically compare strategies:
- Create comparison script that runs multiple strategies
- Capture standardized metrics
- Generate comparison reports
- Help users select optimal strategies

## References
- **New action implementations**: `/home/ubuntu/biomapper/biomapper/core/strategy_actions/[bidirectional_match|resolve_and_match_forward|resolve_and_match_reverse].py`
- **Test suites**: `/home/ubuntu/biomapper/tests/unit/core/strategy_actions/test_*.py`
- **Bidirectional pipeline**: `/home/ubuntu/biomapper/scripts/main_pipelines/run_full_ukbb_hpa_mapping_bidirectional.py`
- **Test script**: `/home/ubuntu/biomapper/scripts/main_pipelines/test_bidirectional_ukbb_hpa_mapping.py`
- **Strategy config**: `/home/ubuntu/biomapper/configs/mapping_strategies_config.yaml`

## Workflow Integration

Consider using Claude for specific tasks:

### 1. **Performance Optimization Task**
Provide Claude with the timeout issue details and ask for optimization:
```
The RESOLVE_AND_MATCH_REVERSE action at /home/ubuntu/biomapper/biomapper/core/strategy_actions/resolve_and_match_reverse.py times out when processing 2991 identifiers through the UniProt API. Current implementation processes in batches of 100 sequentially.

Please optimize this to:
1. Use concurrent API calls while respecting rate limits
2. Add progress tracking that works with the MappingExecutor's progress_callback
3. Implement smarter batching based on API response times
4. Add timeout handling and retry logic
```

### 2. **Strategy Comparison Framework**
Ask Claude to design the comparison framework:
```
Please create a strategy comparison framework at /home/ubuntu/biomapper/scripts/analysis_and_reporting/compare_mapping_strategies.py that:

1. Accepts a list of strategy names and a common dataset
2. Runs each strategy and captures: execution time, memory usage, coverage metrics, step-by-step timings
3. Handles strategy failures gracefully
4. Generates both JSON metrics and human-readable reports
5. Includes visualization of results (coverage vs time trade-offs)

The framework should work with the existing MappingExecutor and support progress tracking.
```

### 3. **Jupyter Notebook Updates**
For async handling in notebooks:
```
The notebook at /home/ubuntu/biomapper/notebooks/2_use_cases/ukbb_to_hpa_protein.ipynb needs to work with async MappingExecutor methods. Please:

1. Show the best pattern for handling async calls in Jupyter
2. Demonstrate both original and bidirectional strategies
3. Add progress bars for long operations
4. Visualize the matching process showing context flow
5. Create comparison visualizations

Include proper error handling and make it educational for users learning the system.
```

## Next Session Recommendations

Start with performance optimization as it blocks full dataset testing. The timeout issue with 2991 identifiers is the critical path. Once resolved, the strategy comparison can provide quantitative evidence for the improvements achieved with the bidirectional approach.

The parallel development approach proved highly effective - consider using multiple Claude instances again for independent tasks like creating the comparison framework while optimizing performance.