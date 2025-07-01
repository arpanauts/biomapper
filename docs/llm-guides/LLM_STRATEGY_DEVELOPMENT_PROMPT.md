# Biomapper Strategy Development Prompt

## Context

You are working with Biomapper's YAML-based strategy system. Strategies define multi-step workflows that orchestrate actions to transform biological identifiers through various mappings and analyses.

**Key Architecture Facts:**
- Strategies are defined in YAML files in `/home/ubuntu/biomapper/configs/`
- Each strategy consists of named steps that execute registered actions
- Steps communicate via a shared context that flows through the workflow
- Strategies can be executed via the REST API or stored in the database

## YAML Strategy Structure

**CORRECT Structure (as implemented):**
```yaml
name: STRATEGY_NAME
description: "What this strategy accomplishes"
parameters:  # Optional: for user-configurable values
  - name: "PARAM_NAME"
    description: "Parameter description"
    required: false
    default: "default_value"

steps:
  - name: STEP_NAME
    description: "What this step does"
    action:
      type: ACTION_TYPE  # Must match registered action
      params:
        param_key: "param_value"
        context_key: "key_in_context"
    is_required: true  # Optional: whether step can fail

  - name: NEXT_STEP
    action:
      type: ANOTHER_ACTION
      params:
        input_context_key: "previous_output"
        output_context_key: "new_output"
```

## Context Flow Patterns

### 1. Initial Context
The initial context includes:
- `input_identifiers`: List passed from API call
- `SOURCE` and `TARGET`: Endpoint names
- User-provided parameters

### 2. Context Keys Convention
Actions typically use these parameter names:
- `input_context_key`: Where to read input from context
- `output_context_key`: Where to store output in context
- `dataset1_context_key`, `dataset2_context_key`: For comparison actions
- `endpoint_name`: When loading from specific endpoints

### 3. Parameter Substitution
Use `${PARAM_NAME}` for strategy parameters:
```yaml
parameters:
  - name: "OUTPUT_DIR"
    default: "./results"

steps:
  - name: save_results
    action:
      type: SAVE_TO_FILE
      params:
        output_directory: "${OUTPUT_DIR}"
```

## Available Actions

**Data Loading:**
- `LOAD_ENDPOINT_IDENTIFIERS`: Load all IDs from an endpoint
- `LOAD_IDENTIFIERS_FROM_ENDPOINT`: Load from SOURCE/TARGET context

**ID Conversion:**
- `LOCAL_ID_CONVERTER`: Convert using local mapping files
- `CONVERT_IDENTIFIERS_LOCAL`: Convert with endpoint context
- `COMPOSITE_ID_SPLITTER`: Split composite identifiers

**Analysis:**
- `DATASET_OVERLAP_ANALYZER`: Compare two ID sets
- `BIDIRECTIONAL_MATCH`: Match IDs between datasets
- `FILTER_BY_TARGET_PRESENCE`: Filter by presence in target

**API Resolution:**
- `RESOLVE_AND_MATCH_FORWARD`: Resolve unmatched via API
- `RESOLVE_AND_MATCH_REVERSE`: Reverse resolution

**Output:**
- `GENERATE_SUMMARY_STATS`: Create statistics
- `FORMAT_AND_SAVE_RESULTS`: Save to files
- `GENERATE_MARKDOWN_REPORT`: Create reports

## Task Requirements

**Current Task**: [Describe the specific strategy development task]

**Strategy Name**: [STRATEGY_NAME]

**Purpose**: [What biological question does this solve?]

**Input Data**:
- Source endpoint: [Name and description]
- Target endpoint: [Name and description]
- Input format: [What identifiers are provided?]

**Desired Output**:
- Output format: [What should be produced?]
- Key metrics: [What should be measured?]

**Workflow Steps**:
1. [High-level step 1]
2. [High-level step 2]
3. [etc.]

## Implementation Constraints

1. **MUST** use only registered actions (check ACTION_REGISTRY)
2. **MUST** use correct parameter names for each action
3. **MUST** maintain clear context flow between steps
4. **MUST** handle both endpoints if doing bidirectional mapping
5. **SHOULD** include error handling with `is_required` flags
6. **SHOULD** generate statistics and provenance
7. **SHOULD** follow existing naming conventions

## Common Patterns

### Loading and Converting
```yaml
- name: load_source_ids
  action:
    type: LOAD_IDENTIFIERS_FROM_ENDPOINT
    params:
      endpoint_context: "SOURCE"
      output_context_key: "source_native_ids"

- name: convert_to_uniprot
  action:
    type: CONVERT_IDENTIFIERS_LOCAL
    params:
      endpoint_context: "SOURCE"
      input_context_key: "source_native_ids"
      output_ontology_type: "PROTEIN_UNIPROTKB_AC_ONTOLOGY"
      output_context_key: "source_uniprot_ids"
```

### Bidirectional Matching
```yaml
- name: match_datasets
  action:
    type: BIDIRECTIONAL_MATCH
    params:
      source_ids_context_key: "dataset1_ids"
      target_ids_context_key: "dataset2_ids"
      matched_pairs_output_key: "matched_pairs"
      unmatched_source_output_key: "unmatched_from_dataset1"
      unmatched_target_output_key: "unmatched_from_dataset2"
```

## Files to Create/Modify

1. **Strategy YAML**:
   `/home/ubuntu/biomapper/configs/[strategy_name].yaml`

2. **Update Database** (if needed):
   Run update script to load strategy into database

3. **Test Script**:
   Create a test script to validate the strategy

## Testing the Strategy

1. **Start API Server**:
   ```bash
   cd /home/ubuntu/biomapper/biomapper-api
   poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

2. **Execute Strategy**:
   ```bash
   curl -X POST http://localhost:8000/api/strategies/STRATEGY_NAME/execute \
     -H "Content-Type: application/json" \
     -d '{
       "source_endpoint_name": "SOURCE_ENDPOINT",
       "target_endpoint_name": "TARGET_ENDPOINT", 
       "input_identifiers": ["id1", "id2"],
       "options": {}
     }'
   ```

## Success Criteria

- [ ] Strategy validates without errors
- [ ] All actions exist and parameters are correct
- [ ] Context flows properly between steps
- [ ] Produces expected output format
- [ ] Handles edge cases appropriately
- [ ] Performance is acceptable for data size

Remember: Focus on clear, maintainable workflows that solve real biological questions.