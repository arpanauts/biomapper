# Investigation Request: Missing kg2c_normalized Dataset Issue

## Context
We have a progressive protein mapping strategy (v3.0) that was working previously but is now failing at the normalization step. The strategy follows a waterfall approach (direct → composite → historical) for mapping proteins from Arivale to KG2C.

## The Problem
The pipeline fails at Step 6 (direct_uniprot_match) with:
```
WARNING - Dataset 'kg2c_normalized' not found in context
```

This happens even though Step 5 (normalize_kg2c_accessions) appears to execute without errors.

## Investigation Needed
Please conduct a thorough investigation WITHOUT making any edits to determine why the kg2c_normalized dataset is not being created/stored properly.

## Key Files to Examine

### 1. The Strategy Configuration
**File**: `/home/ubuntu/biomapper/configs/strategies/experimental/prot_arv_to_kg2c_uniprot_v3.0_progressive.yaml`
- Check Step 4 (extract_uniprot_from_kg2c) - outputs to `kg2c_with_uniprot`
- Check Step 5 (normalize_kg2c_accessions) - should output to `kg2c_normalized`
- Verify parameter names match the action's expected parameters

### 2. The Normalization Action
**File**: `/home/ubuntu/biomapper/biomapper/core/strategy_actions/entities/proteins/annotation/normalize_accessions.py`
- Check the execute_typed method
- Verify how it stores data in context
- Look for any conditions that might prevent output storage
- Check if it's using the correct context handler

### 3. The Extract UniProt Action
**File**: `/home/ubuntu/biomapper/biomapper/core/strategy_actions/entities/proteins/annotation/extract_uniprot_from_xrefs.py`
- Verify it's outputting to the correct key (`kg2c_with_uniprot`)
- Check if the output format is compatible with normalize_accessions input

### 4. The Execution Log
**File**: `/tmp/v3.0_final_run.log`
- Line 61: `Executing step 'extract_uniprot_from_kg2c'` - no success message
- Line 62: `Executing step 'normalize_kg2c_accessions'` - started but no completion message
- Line 64: Processing column but no statistics reported

## Specific Questions to Answer

### Data Flow Analysis
1. **Does extract_uniprot_from_kg2c actually create kg2c_with_uniprot?**
   - Check if there's a success log message
   - Verify the action completes without errors
   - Confirm data is stored in context

2. **Why doesn't normalize_kg2c_accessions create kg2c_normalized?**
   - Is the input data missing/malformed?
   - Does the action silently fail?
   - Is there a conditional that skips output storage?

### Parameter Compatibility
3. **Are the parameters correctly aligned between YAML and action code?**
   - extract_uniprot_from_kg2c expects: `input_key`, `xrefs_column`, `output_key`
   - normalize_accessions expects: `input_key`, `id_columns`, `output_key`

### Context Handling
4. **Is there a context type mismatch?**
   - The log shows "Context preference was: pydantic"
   - Check if actions handle both dict and Pydantic contexts correctly
   - Look for context adapter usage

## What Changed Recently

### Known Recent Changes (from our session):
1. **Parameter Standardization**: Changed from `dataset_key` to `input_key` throughout
2. **Parse Composite Parameters**: Fixed `input_context_key` → `input_key`
3. **FILTER_DATASET Replacement**: Replaced with CUSTOM_TRANSFORM expressions

### Potential Breaking Changes to Investigate:
1. **Context Handling Changes**: Was there a shift in how contexts are wrapped/unwrapped?
2. **Action Registration**: Are actions being re-registered (see warnings about overwrites)?
3. **Async Execution**: Did async changes affect data persistence?

## Previous Working Version Comparison

### Check Working Strategy
**File**: `/home/ubuntu/biomapper/configs/strategies/experimental/prot_production_simple_working.yaml`
- Compare how it handles the same operations
- Note any differences in parameter names or structure

### Success Indicators to Look For
- Actions that successfully store data show: "Successfully loaded X rows into context key 'Y'"
- The normalize action should show statistics like it does for arivale_normalized

## Critical Code Sections to Examine

### In normalize_accessions.py:
```python
# Look for where output is stored - should be something like:
ctx["datasets"][params.output_key] = processed_data
# or
ctx.set_dataset(params.output_key, processed_data)
```

### In extract_uniprot_from_xrefs.py:
```python
# Check the output storage pattern:
ctx["datasets"][output_key] = df.to_dict("records")
```

## Hypothesis to Test (Without Editing)

1. **Missing Column Hypothesis**: The kg2c dataset might not have an 'xrefs' column
   - Check kg2c_proteins.csv structure
   - Verify column names match expectations

2. **Silent Failure Hypothesis**: The extraction might fail without raising an error
   - Look for try/except blocks that swallow exceptions
   - Check for conditional returns that skip processing

3. **Empty Result Hypothesis**: The extraction might succeed but produce empty results
   - Check if there's validation that removes empty datasets
   - Look for conditions like "if not df.empty" before storing

4. **Context Type Mismatch**: Different actions might expect different context types
   - Check if some use UniversalContext.wrap() and others don't
   - Look for inconsistent context access patterns

## Output Format Requested

Please provide:
1. **Root Cause**: A clear explanation of why kg2c_normalized is missing
2. **Evidence**: Specific line numbers and code snippets that prove the cause
3. **Fix Strategy**: Detailed steps to fix the issue (but don't implement)
4. **Risk Assessment**: What other parts might be affected by the same issue

## Additional Investigation Commands

Run these to gather more information:
```bash
# Check if the kg2c CSV has the expected columns
head -n 2 /procedure/data/local_data/MAPPING_ONTOLOGIES/kg2c_ontologies/kg2c_proteins.csv | cut -d',' -f1-10

# Look for the xrefs column specifically
head -n 1 /procedure/data/local_data/MAPPING_ONTOLOGIES/kg2c_ontologies/kg2c_proteins.csv | tr ',' '\n' | grep -n xref

# Check if normalize_accessions has been modified recently
grep -n "output_key" /home/ubuntu/biomapper/biomapper/core/strategy_actions/entities/proteins/annotation/normalize_accessions.py

# Check for any TODO or FIXME comments that might indicate known issues
grep -r "TODO\|FIXME" /home/ubuntu/biomapper/biomapper/core/strategy_actions/entities/proteins/annotation/
```

## Priority Focus Areas

1. **IMMEDIATE**: Why is kg2c_with_uniprot not being created by extract_uniprot_from_xrefs?
2. **SECONDARY**: If kg2c_with_uniprot exists, why doesn't normalize_accessions process it?
3. **TERTIARY**: Are there cascading failures from the first missing dataset?

Please investigate thoroughly and provide a detailed analysis without making any code changes.