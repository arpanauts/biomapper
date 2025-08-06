# Biomapper Strategy Quick Reference

## /biomapper-strategy Command Helper

### Quick Start
```bash
# 1. Check your data
head -5 your_data.csv | cut -d',' -f1-5

# 2. Start with template
cp configs/strategies/metabolomics_progressive_enhancement.yaml my_strategy.yaml

# 3. Test with simple runner
poetry run python scripts/run_metabolomics_fix.py
```

### Action Type Cheatsheet
| Purpose | Action Type | Key Parameters |
|---------|------------|----------------|
| Load data | LOAD_DATASET_IDENTIFIERS | file_path, identifier_column, output_key |
| Basic match | BASELINE_FUZZY_MATCH | threshold, source/target_dataset_key |
| Platform match | NIGHTINGALE_NMR_MATCH | source/target columns, confidence_threshold |
| API enrich | CTS_ENRICHED_MATCH | identifier_columns, cts_config |
| Vector search | VECTOR_ENHANCED_MATCH | qdrant_config, similarity_threshold |
| Report | GENERATE_ENHANCEMENT_REPORT | metrics_keys, output_path |

### Common Issues & Fixes
| Error | Cause | Fix |
|-------|-------|-----|
| "dataset not found" | Wrong output_key | Check LOAD action output_key matches |
| "float has no attribute" | NaN values | Add data validation in load |
| "Unknown action type" | Not registered | Check action imports and spelling |
| "No unmatched data" | Wrong key | Check unmatched_key in previous action |

### Strategy Structure
```yaml
name: YOUR_STRATEGY_NAME
description: What this does
parameters:
  # Variables for interpolation
  data_dir: "/path/to/data"
  threshold: 0.85
steps:
  # 1. Load (always first)
  - name: load_data
    action:
      type: LOAD_DATASET_IDENTIFIERS
      params:
        file_path: "${parameters.data_dir}/file.csv"
        
  # 2. Match (progressive stages)
  - name: baseline
    action:
      type: BASELINE_FUZZY_MATCH
      params:
        track_metrics: true
        
  # 3. Report (always last)
  - name: report
    action:
      type: GENERATE_ENHANCEMENT_REPORT
```

### Debug Commands
```python
# Check context between actions
print(context['custom_action_data']['datasets'].keys())

# Verify data loaded
print(f"Loaded {len(context['custom_action_data']['datasets']['my_data'])} rows")

# Check metrics
print(context.get('metrics', {}))
```

### Performance Tips
- Filter early: Load only needed columns
- Batch API calls: Use batch_size parameter
- Cache results: Enable caching in API configs
- Track metrics: Use track_metrics: true

### Remember
1. Data quality first - validate before processing
2. Progressive enhancement - each stage improves
3. Context flows through - data persists in custom_action_data
4. Test small first - 10 rows before 10,000
5. Log everything - future you will thank you