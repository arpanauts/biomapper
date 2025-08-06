# CLAUDE.md - Biomapper Strategy Development Guide

This guide helps LLM assistants effectively support developers creating biomapper mapping strategies. It incorporates hard-won lessons from real-world implementation.

## Core Mental Models

### 1. Progressive Enhancement Philosophy
Think of biological data harmonization as a series of enhancement stages, each building on the previous:
```
Raw Data → Baseline Match (45%) → API Enrichment (+15%) → Semantic Search (+10%) → Final Result (70%)
```
Each stage should handle failures gracefully and pass unmatched items to the next stage.

### 2. Context as Shared State
The context object is the "memory" flowing through all actions:
- Actions read from context
- Actions write to context
- Context persists across the entire pipeline
- Use `custom_action_data['datasets']` for data storage

### 3. Data Quality First
Never assume data quality. Always:
- Check for NaN/null values
- Validate column existence
- Handle empty strings
- Filter before processing

## Strategy Development Workflow

### Step 1: Understand the Data
Before writing any YAML:
```bash
# Examine the data files
head -10 /path/to/data.csv
# Check column names
head -1 /path/to/data.csv
# Count rows
wc -l /path/to/data.csv
# Look for empty values
grep -c "^," /path/to/data.csv
```

### Step 2: Design the Pipeline
Always follow this order:
1. **Data Loading** - LOAD_DATASET_IDENTIFIERS for each dataset
2. **Validation** - Check data quality and log statistics
3. **Matching** - Progressive stages with measurable improvements
4. **Reporting** - GENERATE_ENHANCEMENT_REPORT with metrics

### Step 3: Choose Action Types

**Decision Tree:**
```
Is this loading data?
  → Yes: LOAD_DATASET_IDENTIFIERS
  → No: Continue

Is this matching within same platform (e.g., Nightingale)?
  → Yes: NIGHTINGALE_NMR_MATCH or platform-specific action
  → No: Continue

Is this basic string matching?
  → Yes: BASELINE_FUZZY_MATCH
  → No: Continue

Does this need external API enrichment?
  → Yes: CTS_ENRICHED_MATCH or API-specific action
  → No: Continue

Is this semantic/similarity search?
  → Yes: VECTOR_ENHANCED_MATCH
  → No: Continue

Is this combining results?
  → Yes: MERGE_DATASETS
  → No: Continue

Is this generating reports?
  → Yes: GENERATE_ENHANCEMENT_REPORT
```

## Common Patterns

### Pattern 1: Progressive Unmatched Tracking
```yaml
- action_type: BASELINE_FUZZY_MATCH
  params:
    output_key: "baseline_matches"
    unmatched_key: "unmatched.baseline.${dataset}"

- action_type: CTS_ENRICHED_MATCH
  params:
    unmatched_dataset_key: "unmatched.baseline.${dataset}"
    output_key: "api_matches"
    unmatched_key: "unmatched.api.${dataset}"
```

### Pattern 2: Metrics Aggregation
```yaml
- action_type: BASELINE_FUZZY_MATCH
  params:
    track_metrics: true
    metrics_key: "metrics.baseline"

- action_type: GENERATE_ENHANCEMENT_REPORT
  params:
    metrics_keys: ["metrics.baseline", "metrics.api", "metrics.vector"]
```

### Pattern 3: Parameter Interpolation
```yaml
parameters:
  data_dir: "/procedure/data/local_data"
  threshold: 0.85

steps:
  - action_type: LOAD_DATASET_IDENTIFIERS
    params:
      file_path: "${parameters.data_dir}/dataset.csv"
      confidence_threshold: "${parameters.threshold}"
```

## Anti-Patterns to Avoid

### ❌ Don't Load Everything Into Memory
```yaml
# BAD: Loading huge dataset without filtering
- action_type: LOAD_DATASET_IDENTIFIERS
  params:
    file_path: "huge_dataset.csv"

# GOOD: Filter and load only needed columns
- action_type: LOAD_DATASET_IDENTIFIERS
  params:
    file_path: "huge_dataset.csv"
    identifier_column: "id"
    additional_columns: ["name", "type"]  # Only what's needed
```

### ❌ Don't Ignore Data Quality
```yaml
# BAD: Direct matching without validation
- action_type: NIGHTINGALE_NMR_MATCH
  params:
    source_dataset_key: "raw_data"

# GOOD: Validate first
- action_type: LOAD_DATASET_IDENTIFIERS
  params:
    drop_empty: true
    validate_columns: true
```

### ❌ Don't Create Monolithic Actions
```yaml
# BAD: One action doing everything
- action_type: DO_EVERYTHING_ACTION

# GOOD: Separate concerns
- action_type: LOAD_DATASET_IDENTIFIERS
- action_type: VALIDATE_DATA
- action_type: FUZZY_MATCH
- action_type: GENERATE_REPORT
```

## Debugging Strategies

### 1. Start Simple
```python
# Create a minimal test runner
import yaml
config = yaml.safe_load(open('strategy.yaml'))
print(f"Steps: {len(config['steps'])}")
for step in config['steps']:
    print(f"- {step['name']}: {step['action']['type']}")
```

### 2. Add Debugging Actions
```yaml
# Insert between problematic actions
- name: debug_context
  action:
    type: LOG_CONTEXT
    params:
      keys_to_log: ["datasets", "metrics", "custom_action_data"]
```

### 3. Common Error Messages and Solutions

**"Source dataset 'X' not found in context"**
- Check the output_key in LOAD_DATASET_IDENTIFIERS matches the dataset_key in later actions
- Verify data is stored in context['custom_action_data']['datasets']

**"'float' object has no attribute 'lower'"**
- Data contains NaN values
- Add data validation in loading action
- Handle non-string values in matching actions

**"Unknown action type: X"**
- Check action is registered with @register_action decorator
- Verify action is imported in __init__.py
- Check spelling and case sensitivity

## Templates

### Template 1: Basic Three-Dataset Harmonization
```yaml
name: THREE_DATASET_HARMONIZATION
description: Harmonize three biological datasets with progressive enhancement

parameters:
  dataset1_file: "/data/dataset1.csv"
  dataset2_file: "/data/dataset2.csv"  
  dataset3_file: "/data/dataset3.csv"
  output_dir: "/results"

steps:
  # Load all datasets
  - name: load_dataset1
    action:
      type: LOAD_DATASET_IDENTIFIERS
      params:
        file_path: "${parameters.dataset1_file}"
        identifier_column: "id"
        output_key: "dataset1"

  # Baseline matching
  - name: baseline_match
    action:
      type: BASELINE_FUZZY_MATCH
      params:
        source_dataset_key: "dataset1"
        target_dataset_key: "dataset2"
        threshold: 0.80
        output_key: "baseline_matches"
        unmatched_key: "unmatched.baseline"
        track_metrics: true

  # Generate report
  - name: final_report
    action:
      type: GENERATE_ENHANCEMENT_REPORT
      params:
        metrics_keys: ["metrics.baseline"]
        output_path: "${parameters.output_dir}/report.md"
```

### Template 2: Progressive Enhancement Pipeline
```yaml
# See /home/ubuntu/biomapper/configs/strategies/metabolomics_progressive_enhancement.yaml
# for a complete real-world example
```

## Key Implementation Tips

1. **Always use TypedStrategyAction for new actions**
   - Provides type safety with Pydantic
   - Better error messages
   - Consistent interface

2. **Test with small datasets first**
   - Create test files with 10-20 rows
   - Verify pipeline works end-to-end
   - Then scale to full datasets

3. **Log everything**
   ```python
   logger.info(f"Processing {len(data)} items")
   logger.debug(f"First 5 items: {data[:5]}")
   ```

4. **Handle external service failures**
   ```python
   try:
       result = await api_call()
   except Exception as e:
       logger.warning(f"API call failed: {e}")
       return fallback_result()
   ```

5. **Track provenance**
   ```python
   provenance = {
       "action": "CTS_ENRICHED_MATCH",
       "timestamp": datetime.now().isoformat(),
       "input_count": len(input_data),
       "output_count": len(output_data),
       "api_calls": api_call_count,
       "cache_hits": cache_hit_count
   }
   ```

## When Helping Developers

1. **Always ask to see the data first**
   - Column names
   - Sample rows
   - Data types
   - File sizes

2. **Start with working examples**
   - Point to metabolomics_progressive_enhancement.yaml
   - Adapt rather than create from scratch

3. **Emphasize testing**
   - TDD approach
   - Unit tests for actions
   - Integration tests for pipelines

4. **Be explicit about dependencies**
   - External services (Docker, APIs)
   - Python packages
   - Data file locations

5. **Provide debugging steps**
   - How to check context state
   - How to validate data loading
   - How to test individual actions

Remember: The goal is not just to make it work, but to make it measurable, debuggable, and maintainable.