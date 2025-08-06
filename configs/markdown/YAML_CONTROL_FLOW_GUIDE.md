# YAML Strategy Control Flow Guide

## Overview

The biomapper YAML strategy system now supports advanced control flow constructs that enable complex workflows while maintaining readability. This guide covers all control flow features with practical examples.

## Table of Contents

1. [Conditional Execution](#conditional-execution)
2. [Loops and Iteration](#loops-and-iteration)
3. [Error Handling](#error-handling)
4. [Parallel Execution](#parallel-execution)
5. [Variables and Expressions](#variables-and-expressions)
6. [Checkpointing](#checkpointing)
7. [Complete Examples](#complete-examples)
8. [Migration Guide](#migration-guide)

## Conditional Execution

### Simple Conditions

Execute steps based on boolean expressions:

```yaml
name: conditional_strategy
variables:
  threshold: 0.85

steps:
  - name: baseline_match
    action:
      type: BASELINE_FUZZY_MATCH
      params:
        threshold: "${variables.threshold}"
    
  - name: api_enrichment
    # Only run if baseline matching had low success
    condition: "${steps.baseline_match.metrics.match_rate} < 0.5"
    action:
      type: METABOLITE_API_ENRICHMENT
      params:
        input: "${steps.baseline_match.outputs.unmatched}"
```

### Complex Conditions (AND/OR)

Use `all` for AND logic and `any` for OR logic:

```yaml
steps:
  - name: semantic_match
    condition:
      type: all  # All conditions must be true
      all:
        - "${steps.api_enrichment.metrics.match_rate} < 0.7"
        - "${parameters.enable_llm} == true"
        - "${context.env.OPENAI_API_KEY} != null"
    action:
      type: SEMANTIC_METABOLITE_MATCH
      params:
        model: "gpt-4"

  - name: fallback_match
    condition:
      type: any  # At least one condition must be true
      any:
        - "${steps.baseline_match.failed} == true"
        - "${steps.api_enrichment.failed} == true"
        - "${variables.force_fallback} == true"
    action:
      type: SIMPLE_NAME_MATCH
```

### Skip Conditions

Skip steps if certain conditions are already met:

```yaml
steps:
  - name: download_data
    skip_if_exists: "/data/downloaded_file.csv"
    action:
      type: DOWNLOAD_FILE
      params:
        url: "https://example.com/data.csv"
        output: "/data/downloaded_file.csv"
```

## Loops and Iteration

### For-Each Loops

Iterate over collections:

```yaml
parameters:
  dataset_paths:
    - "/data/dataset1.csv"
    - "/data/dataset2.csv"
    - "/data/dataset3.csv"

steps:
  - name: load_datasets
    for_each:
      items: "${parameters.dataset_paths}"
      as_variable: dataset_path
    action:
      type: LOAD_DATASET_IDENTIFIERS
      params:
        file_path: "${dataset_path}"
        output_key: "dataset_${foreach.index}"
```

### Repeat Loops

Execute steps repeatedly with conditions:

```yaml
steps:
  - name: iterative_refinement
    repeat:
      max_iterations: 5
      while_condition: "${steps.iterative_refinement.metrics.quality_score} < 0.95"
    action:
      type: REFINE_MATCHES
      params:
        input: "${steps.iterative_refinement.result:-initial_data}"
    set_variables:
      iteration_count: "${repeat.iteration}"
```

### Parallel For-Each

Execute iterations in parallel:

```yaml
steps:
  - name: parallel_enrichment
    parallel:
      max_workers: 3
      fail_fast: false  # Continue even if some fail
    for_each:
      items: ["hmdb", "pubchem", "chebi"]
      as_variable: database
    action:
      type: DATABASE_ENRICHMENT
      params:
        database: "${database}"
        input: "${context.unmatched_metabolites}"
```

## Error Handling

### Global Error Configuration

Set default error handling for all steps:

```yaml
error_handling:
  default: retry  # stop | continue | retry | skip
  max_retries: 3
  retry_delay: 5  # seconds
  continue_on_error: false
```

### Step-Level Error Handling

Override error handling for specific steps:

```yaml
steps:
  - name: critical_step
    action:
      type: LOAD_DATASET_IDENTIFIERS
      params:
        file_path: "${parameters.input_file}"
    on_error: stop  # This step must succeed
    
  - name: api_call
    action:
      type: METABOLITE_API_ENRICHMENT
    on_error:
      action: retry
      max_attempts: 5
      backoff: exponential  # or linear
      delay: 2
      fallback:
        action: continue
        set_variable: "api_failed=true"
        message: "API enrichment failed, continuing without it"
  
  - name: optional_step
    action:
      type: VECTOR_ENHANCED_MATCH
    on_error: skip  # Skip and continue if this fails
```

### Error Variables

Set variables when errors occur:

```yaml
steps:
  - name: risky_operation
    action:
      type: EXTERNAL_API_CALL
    on_error:
      action: continue
      set_variable: "external_api_available=false"
  
  - name: conditional_step
    condition: "${variables.external_api_available:-true} == true"
    action:
      type: USE_API_DATA
```

## Parallel Execution

### DAG-Based Execution

Define dependencies for parallel execution:

```yaml
execution:
  mode: dag  # Execute as directed acyclic graph

steps:
  # These steps can run in parallel
  - name: load_israeli10k
    action:
      type: LOAD_DATASET_IDENTIFIERS
      params:
        file_path: "/data/israeli10k.csv"
      
  - name: load_ukbb
    action:
      type: LOAD_DATASET_IDENTIFIERS
      params:
        file_path: "/data/ukbb.csv"
      
  - name: load_arivale
    action:
      type: LOAD_DATASET_IDENTIFIERS
      params:
        file_path: "/data/arivale.csv"
    
  # This step waits for two dependencies
  - name: match_nightingale
    depends_on:
      - load_israeli10k
      - load_ukbb
    action:
      type: NIGHTINGALE_NMR_MATCH
      params:
        dataset1: "${steps.load_israeli10k.result}"
        dataset2: "${steps.load_ukbb.result}"
  
  # This step waits for its dependencies
  - name: three_way_match
    depends_on:
      - match_nightingale
      - load_arivale
    action:
      type: CALCULATE_THREE_WAY_OVERLAP
      params:
        datasets:
          - "${steps.match_nightingale.result}"
          - "${steps.load_arivale.result}"
```

## Variables and Expressions

### Variable Definition and Usage

```yaml
# Define variables at strategy level
variables:
  confidence_threshold: 0.85
  output_format: "csv"
  enable_debugging: "${env.DEBUG:-false}"  # Default value syntax

parameters:  # Runtime parameters (can be overridden)
  input_file: "/default/path.csv"
  max_results: 1000

steps:
  - name: calculate_threshold
    set_variables:
      # Dynamic variable based on data characteristics
      adjusted_threshold: |
        ${
          context.dataset_size > 1000 
            ? variables.confidence_threshold * 0.9 
            : variables.confidence_threshold
        }
      
  - name: use_threshold
    action:
      type: BASELINE_FUZZY_MATCH
      params:
        threshold: "${variables.adjusted_threshold}"
```

### Expression Syntax

Supported expression features:

```yaml
# Arithmetic
"${value} * 0.9"
"${a} + ${b} - ${c}"
"${count} / ${total} * 100"

# Comparison
"${score} > 0.8"
"${name} == 'test'"
"${count} >= 100"

# Logical
"${enabled} and ${score} > 0.5"
"${flag1} or ${flag2}"
"not ${disabled}"

# Ternary operator
"${size} > 1000 ? 'large' : 'small'"

# Nested access
"${steps.baseline.metrics.score}"
"${datasets[0].name}"
"${context.env.API_KEY}"

# Safe functions
"len(${array})"
"max(${values})"
"sum(${numbers})"

# Default values
"${missing_var:-'default'}"
"${env.PORT:-8080}"
```

## Checkpointing

### Enable Checkpointing

Save execution state for recovery:

```yaml
checkpointing:
  enabled: true
  strategy: after_critical_steps  # or "after_each_step", "manual"
  storage: local  # or "s3", "database"
  retention: 7d  # Keep for 7 days
  path: "/var/biomapper/checkpoints"

steps:
  - name: expensive_operation
    checkpoint: before  # Save state before this step
    action:
      type: SEMANTIC_METABOLITE_MATCH
      params:
        model: "gpt-4"
        dataset_size: 10000
    
  - name: save_results
    checkpoint: after  # Save state after completion
    is_critical: true  # Mark as critical step
    action:
      type: EXPORT_RESULTS
      params:
        format: "csv"
```

## Complete Examples

### Example 1: Metabolomics Harmonization with Fallbacks

```yaml
name: metabolomics_harmonization_with_fallbacks
description: "Harmonize metabolomics data with multiple fallback strategies"
version: "1.0"

variables:
  confidence_threshold: 0.95
  enable_llm: true

parameters:
  israeli10k_file: "/data/israeli10k.csv"
  ukbb_file: "/data/ukbb.csv"
  arivale_file: "/data/arivale.csv"
  output_dir: "/results"

error_handling:
  default: retry
  max_retries: 3
  retry_delay: 5

steps:
  # Load all datasets in parallel
  - name: load_israeli10k
    action:
      type: LOAD_DATASET_IDENTIFIERS
      params:
        file_path: "${parameters.israeli10k_file}"
        
  - name: load_ukbb
    action:
      type: LOAD_DATASET_IDENTIFIERS
      params:
        file_path: "${parameters.ukbb_file}"
        
  - name: load_arivale
    action:
      type: LOAD_DATASET_IDENTIFIERS
      params:
        file_path: "${parameters.arivale_file}"

  # Try Nightingale matching first
  - name: nightingale_match
    depends_on: [load_israeli10k, load_ukbb, load_arivale]
    action:
      type: NIGHTINGALE_NMR_MATCH
      params:
        threshold: "${variables.confidence_threshold}"
    on_error:
      action: continue
      set_variable: "nightingale_failed=true"

  # Fallback to baseline matching if Nightingale fails or has low success
  - name: baseline_match
    condition: |
      ${variables.nightingale_failed:-false} == true or 
      ${steps.nightingale_match.metrics.match_rate:-0} < 0.7
    action:
      type: BASELINE_FUZZY_MATCH
      params:
        threshold: "${variables.confidence_threshold} * 0.9"

  # Try API enrichment for unmatched items
  - name: api_enrichment
    condition: "${steps.baseline_match.outputs.unmatched_count:-0} > 0"
    for_each:
      items: ["hmdb", "pubchem", "chebi"]
      as_variable: database
    parallel:
      max_workers: 3
    action:
      type: METABOLITE_API_ENRICHMENT
      params:
        database: "${database}"
        input: "${steps.baseline_match.outputs.unmatched}"
    on_error:
      action: continue
      message: "API ${database} failed, skipping"

  # Use LLM for remaining unmatched if enabled
  - name: semantic_match
    condition:
      type: all
      all:
        - "${variables.enable_llm} == true"
        - "${env.OPENAI_API_KEY} != null"
        - "${steps.api_enrichment.outputs.unmatched_count:-0} > 0"
    action:
      type: SEMANTIC_METABOLITE_MATCH
      params:
        model: "gpt-4"
        input: "${steps.api_enrichment.outputs.unmatched}"
    on_error: skip

  # Calculate final overlap
  - name: calculate_overlap
    action:
      type: CALCULATE_THREE_WAY_OVERLAP
      params:
        method: "jaccard"

  # Generate report
  - name: generate_report
    action:
      type: GENERATE_METABOLOMICS_REPORT
      params:
        output_dir: "${parameters.output_dir}"
        include_metrics: true

finally:
  - name: cleanup
    action:
      type: CLEANUP_TEMP_FILES
```

### Example 2: Iterative Quality Improvement

```yaml
name: iterative_quality_improvement
description: "Iteratively improve matching quality"
version: "1.0"

variables:
  target_quality: 0.95
  max_iterations: 10

steps:
  - name: initial_match
    action:
      type: BASELINE_FUZZY_MATCH
      params:
        threshold: 0.8

  - name: quality_improvement_loop
    repeat:
      max_iterations: "${variables.max_iterations}"
      while_condition: |
        ${steps.quality_improvement_loop.metrics.quality_score:-0} < 
        ${variables.target_quality}
    action:
      type: REFINE_MATCHES
      params:
        input: "${steps.quality_improvement_loop.result:-steps.initial_match.result}"
        iteration: "${repeat.iteration}"
    set_variables:
      current_quality: "${steps.quality_improvement_loop.metrics.quality_score}"
      iterations_completed: "${repeat.iteration}"

  - name: report_success
    condition: "${variables.current_quality} >= ${variables.target_quality}"
    action:
      type: LOG_MESSAGE
      params:
        message: "Target quality achieved after ${variables.iterations_completed} iterations"

  - name: report_failure
    condition: "${variables.current_quality} < ${variables.target_quality}"
    action:
      type: LOG_MESSAGE
      params:
        level: "warning"
        message: "Failed to achieve target quality after ${variables.iterations_completed} iterations"
```

## Migration Guide

### Migrating Existing Strategies

Existing strategies continue to work without modification. To add control flow features:

1. **Add conditions to existing steps:**
   ```yaml
   # Before
   - name: api_enrichment
     action:
       type: METABOLITE_API_ENRICHMENT
   
   # After
   - name: api_enrichment
     condition: "${steps.baseline.metrics.match_rate} < 0.7"
     on_error: continue
     action:
       type: METABOLITE_API_ENRICHMENT
   ```

2. **Convert sequential steps to DAG:**
   ```yaml
   # Add execution mode
   execution:
     mode: dag
   
   # Add dependencies to steps
   - name: combine_results
     depends_on: [step1, step2, step3]
     action:
       type: MERGE_DATASETS
   ```

3. **Add error handling:**
   ```yaml
   # Global default
   error_handling:
     default: retry
     max_retries: 3
   
   # Or per-step
   - name: critical_step
     on_error: stop
   ```

### Best Practices

1. **Keep conditions simple and readable**
   - Use meaningful variable names
   - Break complex conditions into multiple steps
   - Document why conditions exist

2. **Use appropriate error handling**
   - `stop` for critical steps
   - `retry` for transient failures (network, APIs)
   - `continue` or `skip` for optional enhancements

3. **Avoid deeply nested conditions**
   - Use step dependencies instead
   - Consider splitting into multiple strategies

4. **Test control flow paths**
   - Test both success and failure paths
   - Verify loop termination conditions
   - Check edge cases in conditions

5. **Use checkpointing for long-running strategies**
   - Checkpoint before expensive operations
   - Enable for strategies that process large datasets

6. **Monitor parallel execution**
   - Set appropriate `max_workers` limits
   - Consider `fail_fast` for critical parallel tasks
   - Add timeouts for long-running parallel steps

## Limitations and Considerations

1. **Expression Safety**: Only safe operations are allowed in expressions. No arbitrary code execution.

2. **Loop Limits**: Maximum iterations are enforced to prevent infinite loops (default: 1000).

3. **Parallel Execution**: Limited by system resources and configured max_workers.

4. **Checkpointing Storage**: Local checkpoints require sufficient disk space.

5. **Variable Scope**: Variables are global within a strategy execution.

## Troubleshooting

### Common Issues

1. **Condition not evaluating correctly**
   - Check variable names and paths
   - Verify data types in comparisons
   - Use default values for potentially missing variables

2. **Loop not terminating**
   - Verify while_condition logic
   - Check that loop modifies the condition variable
   - Set reasonable max_iterations

3. **DAG execution order unexpected**
   - Review dependencies
   - Check for circular dependencies
   - Verify step names match exactly

4. **Error handling not working**
   - Check error action spelling
   - Verify on_error configuration
   - Review logs for actual error messages

### Debug Mode

Enable detailed logging:

```yaml
execution:
  dry_run: false  # Set to true for testing without execution
  
variables:
  debug: true  # Your custom debug flag

steps:
  - name: debug_step
    condition: "${variables.debug} == true"
    action:
      type: LOG_CONTEXT
      params:
        level: "debug"
```