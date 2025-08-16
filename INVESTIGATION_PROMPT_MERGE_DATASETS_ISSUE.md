# Investigation Request: MERGE_DATASETS Join Column Configuration Issue

## Context
The v3.0 progressive protein mapping strategy now successfully creates the `kg2c_normalized` dataset after fixing the column name issue. However, the pipeline fails at Step 7 (direct_uniprot_match) during the MERGE_DATASETS action with a join column configuration error.

## The Problem
The pipeline fails with:
```
ERROR - Error during merge: No join column specified for dataset 'arivale_normalized'
```

This occurs even though the YAML appears to specify join columns for both datasets.

## Current Pipeline Status
- ✅ Step 1: load_arivale_proteins → `arivale_raw` (1,197 rows)
- ✅ Step 2: load_kg2c_entities → `kg2c_raw` (266,487 rows)  
- ✅ Step 3: initialize_progressive_stats → context stats initialized
- ✅ Step 4: extract_uniprot_from_kg2c → `kg2c_with_uniprot` (85,711 rows)
- ✅ Step 5: normalize_arivale_accessions → `arivale_normalized` (1,197 rows)
- ✅ Step 6: normalize_kg2c_accessions → `kg2c_normalized` (85,711 rows)
- ❌ Step 7: direct_uniprot_match → FAILS with join column error

## Investigation Needed
Please conduct a thorough investigation WITHOUT making any edits to determine why the join column configuration is not working properly.

## Key Files to Examine

### 1. The Strategy Configuration
**File**: `/home/ubuntu/biomapper/configs/strategies/experimental/prot_arv_to_kg2c_uniprot_v3.0_progressive.yaml`
**Lines**: 106-115 (the direct_uniprot_match step)
```yaml
- name: direct_uniprot_match
  action:
    type: MERGE_DATASETS
    params:
      input_key: arivale_normalized
      dataset2_key: kg2c_normalized
      join_columns:
        ${parameters.arivale_id_column}: extracted_uniprot
      join_type: inner
      output_key: direct_match
```

**Key Questions**:
- Is the parameter substitution `${parameters.arivale_id_column}` working?
- Should this be a literal key name instead?
- Is the join_columns format correct?

### 2. The MERGE_DATASETS Action
**File**: `/home/ubuntu/biomapper/biomapper/core/strategy_actions/merge_datasets.py`
**Lines**: 278-285 (where the error occurs)
```python
if params.join_columns:
    # New format with explicit column mapping
    first_key, first_df = dfs_with_keys[0]
    first_col = params.join_columns.get(first_key)
    if not first_col:
        raise ValueError(
            f"No join column specified for dataset '{first_key}'"
        )
```

**Investigation Points**:
- How does `params.join_columns` get populated?
- What format does it expect for keys?
- Is parameter substitution happening before this point?

### 3. The Execution Log
**File**: `/tmp/v3.0_after_fix.log`
**Lines around the error**:
```
INFO - Found dataset 'arivale_normalized' with 1197 rows
INFO - Found dataset 'kg2c_normalized' with 85711 rows
INFO - Using join strategy with how='inner'
ERROR - Error during merge: No join column specified for dataset 'arivale_normalized'
```

## Specific Questions to Answer

### 1. Parameter Substitution Issue
**Question**: Is `${parameters.arivale_id_column}` being substituted with "uniprot"?
- Check if the MinimalStrategyService performs parameter substitution
- Look for where `${parameters.xxx}` gets replaced with actual values
- Verify if this happens before params reach the action

### 2. Join Columns Dictionary Structure
**Question**: What does `params.join_columns` actually contain at runtime?
- Is it `{'${parameters.arivale_id_column}': 'extracted_uniprot'}`?
- Or is it `{'uniprot': 'extracted_uniprot'}`?
- Or something else entirely?

### 3. Dataset Key Matching
**Question**: How does the action match dataset keys to join columns?
- The error says it's looking for key 'arivale_normalized'
- But the YAML uses `${parameters.arivale_id_column}` as the key
- Is there a mismatch in how keys are interpreted?

### 4. Alternative Formats
**Question**: Should the join_columns use dataset keys instead of column names as keys?
```yaml
# Current format (using column name variable as key):
join_columns:
  ${parameters.arivale_id_column}: extracted_uniprot

# Alternative format 1 (using dataset keys):
join_columns:
  arivale_normalized: uniprot
  kg2c_normalized: extracted_uniprot

# Alternative format 2 (using input_key/dataset2_key references):
join_column1: uniprot
join_column2: extracted_uniprot
```

## Data Structure Investigation

### 1. Column Names in Datasets
**Check what columns actually exist**:
```bash
# Check arivale_normalized columns
grep -A5 "normalize_arivale_accessions" /tmp/v3.0_after_fix.log | grep -i "column"

# Check if 'uniprot' column exists in arivale_normalized
# Check if 'extracted_uniprot' exists in kg2c_normalized
```

### 2. Data Format Issues
**The normalization warnings suggest a format problem**:
```
WARNING - Invalid UniProt format after normalization: ['P12345'] -> ['P12345']
```

**Questions**:
- Is `extracted_uniprot` a column of lists instead of strings?
- Can MERGE_DATASETS handle joining on list columns?
- Should we be extracting just the first element?

## Parameter Flow Analysis

### 1. Strategy Parameter Definition
**Line 26 in YAML**:
```yaml
parameters:
  arivale_id_column: uniprot
```

### 2. Parameter Usage in Step
**Line 113 in YAML**:
```yaml
join_columns:
  ${parameters.arivale_id_column}: extracted_uniprot
```

### 3. Expected Resolution
After substitution, this should become:
```yaml
join_columns:
  uniprot: extracted_uniprot
```

### 4. Actual Interpretation
The error suggests the action is expecting:
```yaml
join_columns:
  arivale_normalized: <column_name>
  kg2c_normalized: <column_name>
```

## Code Path Analysis

### In merge_datasets.py
1. **Line 91-92**: Converts old format parameters to new format
2. **Line 96-100**: Sets up join_columns if using old format
3. **Line 278-285**: New format processing where error occurs
4. **Line 281**: `first_col = params.join_columns.get(first_key)`
   - `first_key` = 'arivale_normalized' (the dataset key)
   - `params.join_columns` = {'uniprot': 'extracted_uniprot'} (probably)
   - `.get(first_key)` returns None because keys don't match!

## Hypothesis to Test (Without Editing)

### Hypothesis 1: Key Mismatch
**Theory**: The join_columns dictionary uses column names as keys, but the code expects dataset keys.
- YAML provides: `{'uniprot': 'extracted_uniprot'}`
- Code expects: `{'arivale_normalized': 'uniprot', 'kg2c_normalized': 'extracted_uniprot'}`

### Hypothesis 2: Parameter Substitution Failure
**Theory**: The `${parameters.arivale_id_column}` is not being substituted.
- Check if MinimalStrategyService has parameter substitution logic
- Look for string replacement or template processing code

### Hypothesis 3: Wrong Parameter Format
**Theory**: The YAML should use the old format parameters instead.
- Check if using `join_column1` and `join_column2` would work
- Look at working examples in other strategies

## Diagnostic Commands

```bash
# Check if parameter substitution is mentioned in the service
grep -n "parameters\." /home/ubuntu/biomapper/biomapper/core/minimal_strategy_service.py

# Look for working MERGE_DATASETS examples
grep -B5 -A10 "MERGE_DATASETS" /home/ubuntu/biomapper/configs/strategies/experimental/prot_production_simple_working.yaml

# Check if there's a working example with join_columns
find /home/ubuntu/biomapper/configs/strategies -name "*.yaml" -exec grep -l "join_columns:" {} \;

# See how join_columns is used in tests
grep -r "join_columns" /home/ubuntu/biomapper/tests/

# Check for parameter substitution in action execution
grep -n "substitute\|replace\|parameters" /home/ubuntu/biomapper/biomapper/core/minimal_strategy_service.py
```

## Working Example Comparison

### Find a Working Merge
Look for successful MERGE_DATASETS usage in:
- `/home/ubuntu/biomapper/configs/strategies/experimental/prot_production_simple_working.yaml`
- `/home/ubuntu/biomapper/configs/strategies/experimental/prot_simple_production_with_gdrive.yaml`

Compare their parameter structure with the failing v3.0 strategy.

## Expected Outputs

### 1. Root Cause Identification
Explain exactly why the join column configuration fails, with evidence from code.

### 2. Correct Configuration Format
Provide the exact YAML configuration that would work, based on code analysis.

### 3. Parameter Substitution Status
Clarify whether `${parameters.xxx}` substitution works and where it happens.

### 4. Data Format Issues
Explain the list vs string issue in extracted_uniprot and its impact on joining.

## Additional Investigation Areas

### 1. Alternative Join Approach
Check if the old format would work:
```yaml
params:
  input_key: arivale_normalized
  dataset2_key: kg2c_normalized
  join_column1: uniprot
  join_column2: extracted_uniprot
  join_type: inner
```

### 2. List Column Handling
Investigate if the issue is that `extracted_uniprot` contains lists:
- The warnings show values like `['P12345']`
- Can MERGE_DATASETS join on list columns?
- Should the extraction create strings instead?

### 3. Debug Output
Look for any debug logging that shows:
- The actual content of params.join_columns
- The structure of the datasets being merged
- Column names and types

## Priority Investigation Path

1. **FIRST**: Confirm the exact structure of `params.join_columns` at runtime
2. **SECOND**: Verify what keys the merge action expects (dataset keys vs column names)
3. **THIRD**: Check if parameter substitution is working
4. **FOURTH**: Investigate the list vs string format issue
5. **FIFTH**: Find a working example and compare

## Note for Investigating Agent

The most likely issue is that the YAML provides column names as dictionary keys (`{'uniprot': 'extracted_uniprot'}`) but the merge action expects dataset keys (`{'arivale_normalized': 'uniprot', 'kg2c_normalized': 'extracted_uniprot'}`). 

Focus on understanding:
1. What format the action actually expects
2. Whether parameter substitution is happening
3. If there's a working example that shows the correct format

The solution will likely involve changing the YAML to use the correct dictionary structure for join_columns.