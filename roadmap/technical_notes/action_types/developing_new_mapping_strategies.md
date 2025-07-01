# Developing New Mapping Strategies

This guide provides a comprehensive overview of how to create new mapping strategies in Biomapper using YAML. Mapping strategies are the core of Biomapper's workflow orchestration, defining a series of actions to be executed to transform, map, and analyze biological data.

## 1. Introduction to Mapping Strategies

A mapping strategy is a declarative workflow defined in a YAML file. It specifies a sequence of steps, where each step invokes a specific registered action to perform a task. Strategies are designed to be modular, reusable, and easy to understand.

## 2. Anatomy of a Strategy YAML File

Based on the actual implementation, a strategy YAML file has the following structure:

```yaml
name: UNIQUE_STRATEGY_NAME
description: "A clear description of what this strategy accomplishes"

# Optional: User-configurable parameters
parameters:
  - name: "PARAMETER_NAME"
    description: "What this parameter controls"
    required: false
    default: "default_value"

# The sequence of actions to execute
steps:
  - name: STEP_NAME
    description: "What this step does"
    action:
      type: ACTION_TYPE  # Must match a registered action
      params:
        # Parameters specific to this action
        param_name: "value"
    is_required: true  # Optional: whether step failure stops execution
```

### Key Fields:

- **`name`**: A unique identifier for the strategy (required)
- **`description`**: Human-readable explanation of the strategy's purpose (required)
- **`parameters`**: Optional list of user-configurable parameters that can be referenced in steps
- **`steps`**: List of actions to execute in sequence (required)

### Step Fields:

- **`name`**: Unique name for the step within the strategy
- **`description`**: Explanation of what this step accomplishes
- **`action`**: The action configuration
  - **`type`**: The registered action type to execute (e.g., `LOCAL_ID_CONVERTER`)
  - **`params`**: Dictionary of parameters passed to the action
- **`is_required`**: Optional boolean (default: true) - if false, step failure won't stop execution

## 3. Data Flow and Context

### The Execution Context

All steps in a strategy share a context dictionary that flows through the execution. This allows steps to:
- Access results from previous steps
- Store data for subsequent steps
- Share state across the workflow

### Initial Context

When a strategy is executed via the API, the initial context includes:
- `input_identifiers`: List of identifiers provided in the request
- `SOURCE`: Name of the source endpoint
- `TARGET`: Name of the target endpoint
- Any additional parameters from the API request

### Context Key Conventions

Actions typically use these parameter patterns:
- `input_context_key`: Key to read input data from context
- `output_context_key`: Key to store output data in context
- `endpoint_context`: "SOURCE" or "TARGET" to reference endpoints
- `dataset1_context_key`, `dataset2_context_key`: For comparison actions

Example:
```yaml
steps:
  - name: load_data
    action:
      type: LOAD_ENDPOINT_IDENTIFIERS
      params:
        endpoint_name: "HPA_PROTEIN_DATA"
        output_context_key: "hpa_proteins"  # Stores result here
  
  - name: analyze_data
    action:
      type: DATASET_OVERLAP_ANALYZER
      params:
        dataset1_context_key: "input_identifiers"  # From initial context
        dataset2_context_key: "hpa_proteins"       # From previous step
        output_context_key: "overlap_results"
```

## 4. Using Strategy Parameters

Strategy parameters allow users to customize behavior without modifying the YAML:

```yaml
parameters:
  - name: "OUTPUT_DIR"
    description: "Directory for saving results"
    required: false
    default: "./results"
  
  - name: "MIN_CONFIDENCE"
    description: "Minimum confidence threshold"
    required: false
    default: 0.8

steps:
  - name: save_results
    action:
      type: SAVE_RESULTS
      params:
        output_directory: "${OUTPUT_DIR}"  # Reference parameter
        confidence_threshold: "${MIN_CONFIDENCE}"
```

## 5. Available Action Types

### Data Loading Actions
- **`LOAD_ENDPOINT_IDENTIFIERS`**: Load all identifiers from a named endpoint
- **`LOAD_IDENTIFIERS_FROM_ENDPOINT`**: Load from SOURCE/TARGET context

### ID Conversion Actions
- **`LOCAL_ID_CONVERTER`**: Convert IDs using local mapping files
- **`CONVERT_IDENTIFIERS_LOCAL`**: Convert with endpoint context
- **`COMPOSITE_ID_SPLITTER`**: Split composite identifiers (e.g., "ID1;ID2")

### Analysis Actions
- **`DATASET_OVERLAP_ANALYZER`**: Compare two identifier sets
- **`BIDIRECTIONAL_MATCH`**: Match identifiers between datasets
- **`FILTER_BY_TARGET_PRESENCE`**: Filter by presence in target dataset

### API Resolution Actions
- **`RESOLVE_AND_MATCH_FORWARD`**: Resolve unmatched IDs via external API
- **`RESOLVE_AND_MATCH_REVERSE`**: Reverse resolution via API

### Output Actions
- **`GENERATE_SUMMARY_STATS`**: Create mapping statistics
- **`FORMAT_AND_SAVE_RESULTS`**: Save results to files
- **`GENERATE_MARKDOWN_REPORT`**: Create detailed reports

## 6. Real-World Example: UKBB-HPA Analysis

Here's a complete example that demonstrates key concepts:

```yaml
name: UKBB_HPA_PROTEIN_OVERLAP_ANALYSIS
description: "Maps UKBB protein assay IDs to HPA gene names using local files"

steps:
  # Step 1: Convert UKBB assay IDs to UniProt
  - name: CONVERT_UKBB_ASSAY_TO_UNIPROT
    action:
      type: LOCAL_ID_CONVERTER
      params:
        input_context_key: "input_identifiers"  # From API request
        output_context_key: "ukbb_uniprot_ids"
        mapping_file: "/procedure/data/local_data/MAPPING_ONTOLOGIES/ukbb/UKBB_Protein_Meta.tsv"
        source_column: "Assay"
        target_column: "UniProt"
        output_ontology_type: "PROTEIN_UNIPROTKB_AC_ONTOLOGY"

  # Step 2: Load HPA protein data
  - name: LOAD_HPA_UNIPROT_IDS
    action:
      type: LOAD_ENDPOINT_IDENTIFIERS
      params:
        endpoint_name: "HPA_PROTEIN_DATA"
        output_context_key: "hpa_uniprot_ids"

  # Step 3: Find overlapping proteins
  - name: ANALYZE_OVERLAP
    action:
      type: DATASET_OVERLAP_ANALYZER
      params:
        dataset1_context_key: "ukbb_uniprot_ids"
        dataset2_context_key: "hpa_uniprot_ids"
        output_context_key: "overlapping_uniprot_ids"
        dataset1_name: "UKBB"
        dataset2_name: "HPA"
        generate_statistics: true

  # Step 4: Convert overlapping UniProt IDs to HPA genes
  - name: CONVERT_UNIPROT_TO_HPA_GENE
    action:
      type: LOCAL_ID_CONVERTER
      params:
        input_context_key: "overlapping_uniprot_ids"
        output_context_key: "final_hpa_genes"
        mapping_file: "/procedure/data/local_data/MAPPING_ONTOLOGIES/isb_osp/hpa_osps.csv"
        source_column: "uniprot"
        target_column: "gene"
        output_ontology_type: "HPA_GENE_ONTOLOGY"
```

## 7. Testing Your Strategy

### Via the API

1. Start the API server:
```bash
cd /home/ubuntu/biomapper/biomapper-api
poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

2. Execute the strategy:
```bash
curl -X POST http://localhost:8000/api/strategies/YOUR_STRATEGY_NAME/execute \
  -H "Content-Type: application/json" \
  -d '{
    "source_endpoint_name": "SOURCE_ENDPOINT",
    "target_endpoint_name": "TARGET_ENDPOINT",
    "input_identifiers": ["ID1", "ID2", "ID3"],
    "options": {
      "OUTPUT_DIR": "/custom/output/path"
    }
  }'
```

### Updating Database Strategies

If your strategy needs to be stored in the database:

```python
# Create a script to update the database
poetry run python scripts/update_strategy.py
```

## 8. Best Practices

### Strategy Design
- **Single Responsibility**: Each strategy should solve one biological question
- **Clear Naming**: Use descriptive names for strategies and steps
- **Modular Steps**: Break complex operations into multiple steps
- **Error Handling**: Use `is_required: false` for optional steps

### Context Management
- **Document Context Keys**: Comment what each key contains
- **Consistent Naming**: Use clear, consistent key names
- **Avoid Collisions**: Use unique keys for each step's output

### Parameter Usage
- **Sensible Defaults**: Provide reasonable default values
- **Clear Descriptions**: Explain what each parameter controls
- **Validation**: Actions should validate parameter values

## 9. Common Patterns

### Loading and Converting Pattern
```yaml
- name: load_source
  action:
    type: LOAD_IDENTIFIERS_FROM_ENDPOINT
    params:
      endpoint_context: "SOURCE"
      output_context_key: "source_ids"

- name: convert_ids
  action:
    type: CONVERT_IDENTIFIERS_LOCAL
    params:
      input_context_key: "source_ids"
      output_ontology_type: "TARGET_ONTOLOGY"
      output_context_key: "converted_ids"
```

### Bidirectional Analysis Pattern
```yaml
- name: forward_match
  action:
    type: BIDIRECTIONAL_MATCH
    params:
      source_ids_context_key: "dataset_a"
      target_ids_context_key: "dataset_b"
      matched_pairs_output_key: "matches"
      unmatched_source_output_key: "unmatched_a"
      unmatched_target_output_key: "unmatched_b"

- name: resolve_unmatched
  action:
    type: RESOLVE_AND_MATCH_FORWARD
    params:
      input_context_key: "unmatched_a"
      target_ids_context_key: "dataset_b"
      api_endpoint: "UNIPROT_HISTORY"
      output_matched_key: "resolved_matches"
```

## 10. Troubleshooting

### Common Issues

1. **"Unknown action type"**
   - Verify the action type is registered
   - Check spelling and case sensitivity

2. **"Parameter X is required"**
   - Check the action's documentation for required params
   - Ensure parameter names match exactly

3. **Empty Results**
   - Check context key names are consistent
   - Verify data is being passed between steps
   - Add logging to trace data flow

### Debugging Tips

1. **Check API Logs**: 
   ```bash
   tail -f /tmp/api_server.log
   ```

2. **Validate YAML Syntax**:
   ```bash
   python -c "import yaml; yaml.safe_load(open('your_strategy.yaml'))"
   ```

3. **Test Steps Individually**: Create minimal strategies to test each step

## 11. Advanced Features

### Conditional Execution
Use `is_required: false` for steps that might fail:
```yaml
- name: try_api_resolution
  action:
    type: API_RESOLVER
    params:
      # ... parameters
  is_required: false  # Continue even if this fails
```

### Complex Context Manipulation
Some actions can merge or transform context data:
```yaml
- name: merge_results
  action:
    type: MERGE_CONTEXT_ITEMS
    params:
      input_keys:
        - "results_1"
        - "results_2"
        - "results_3"
      output_key: "all_results"
      merge_type: "union"
```

Remember: The power of Biomapper comes from combining simple, well-tested actions into sophisticated mapping workflows!