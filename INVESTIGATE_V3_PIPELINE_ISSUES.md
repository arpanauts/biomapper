# Investigation Request: V3.0 Pipeline Remaining Issues

## Context
We have successfully implemented and run the v3.0 progressive protein mapping pipeline (`prot_arv_to_kg2c_uniprot_v3.0_progressive`) which achieves ~97% match rate and successfully uploads results to Google Drive. However, there are three non-critical issues that need investigation and resolution.

## Investigation Scope
Please investigate the following issues **WITHOUT making any edits** initially. Focus on understanding root causes and proposing solutions.

## Issue 1: Historical Resolution Dataset Not Found

### Error Message
```
ERROR:ProteinHistoricalResolution:Historical resolution failed: Dataset key 'unmatched_after_composite' not found in context
```

### Location
- Strategy: `/home/ubuntu/biomapper/configs/strategies/experimental/prot_arv_to_kg2c_uniprot_v3.0_progressive.yaml`
- Step: `historical_resolution` (line ~251)
- Action: `PROTEIN_HISTORICAL_RESOLUTION`

### Investigation Points
1. Check the `identify_unmatched_after_composite` step (line ~235) - it should create the `unmatched_after_composite` dataset
2. Examine the CUSTOM_TRANSFORM expression that filters unmatched proteins
3. Verify the output_key is correctly set to `unmatched_after_composite`
4. Check if the filtering expression is actually returning an empty DataFrame instead of storing it

### Relevant Files
- `/home/ubuntu/biomapper/biomapper/core/strategy_actions/entities/proteins/matching/historical_resolution.py`
- `/home/ubuntu/biomapper/biomapper/core/strategy_actions/utils/data_processing/custom_transform_expression.py`

## Issue 2: Visualization Action Signature Mismatch

### Error Message
```
ERROR:biomapper.core.strategy_actions.reports.generate_visualizations_v2.GenerateMappingVisualizationsAction:Error executing action: GenerateMappingVisualizationsAction.execute_typed() got an unexpected keyword argument 'current_identifiers'
```

### Location
- Strategy: Currently commented out (lines ~372-386)
- Action: `GENERATE_MAPPING_VISUALIZATIONS_V2`

### Investigation Points
1. Check the signature of `execute_typed` in `/home/ubuntu/biomapper/biomapper/core/strategy_actions/reports/generate_visualizations_v2.py`
2. Compare with the base class `TypedStrategyAction` to understand expected signature
3. Determine if this action uses the old 4-parameter signature vs new 2-parameter signature
4. Check if action needs migration to new signature pattern

### Expected Signature Patterns
- **New pattern (2025 standard)**: `async def execute_typed(self, params: ParamsType, context: Dict)`
- **Old pattern**: `async def execute_typed(self, current_identifiers, current_ontology_type, params, source_endpoint, target_endpoint, context)`

## Issue 3: Export Progressive Summary Parameter Validation

### Error Message
```
ERROR:biomapper.core.strategy_actions.utils.data_processing.custom_transform_expression.CustomTransformAction:Invalid action parameters: 1 validation error for CustomTransformExpressionParams
transformations
  Field required [type=missing, input_value={'input_key': 'final_merg...end(output_path)\ndf\n'}, input_type=dict]
```

### Location
- Strategy: `export_progressive_summary` step (line ~409)
- Action: `CUSTOM_TRANSFORM`

### Investigation Points
1. The step mixes `transformations` list with `expression` field
2. Check if both can be used together or if they're mutually exclusive
3. Review the CustomTransformExpressionParams model definition
4. Determine correct structure for this complex transformation

### Current Configuration (line ~409-439)
```yaml
- name: export_progressive_summary
  action:
    type: CUSTOM_TRANSFORM
    params:
      input_key: final_merged
      output_key: summary_exported
      expression: |
        # Create comprehensive summary
        import json
        # ... rest of expression
```

## Key Context Files

### Strategy File
- `/home/ubuntu/biomapper/configs/strategies/experimental/prot_arv_to_kg2c_uniprot_v3.0_progressive.yaml`

### Execution Logs
- `/tmp/v3.0_final_with_gdrive.log` - Latest successful run with issues
- `/tmp/v3.0_correct_kg2c.log` - Earlier run showing same issues

### Action Implementations
- `/home/ubuntu/biomapper/biomapper/core/strategy_actions/entities/proteins/matching/historical_resolution.py`
- `/home/ubuntu/biomapper/biomapper/core/strategy_actions/reports/generate_visualizations_v2.py`
- `/home/ubuntu/biomapper/biomapper/core/strategy_actions/utils/data_processing/custom_transform_expression.py`

## Investigation Commands

```bash
# Check dataset creation in context
grep -n "output_key.*unmatched_after_composite" /home/ubuntu/biomapper/configs/strategies/experimental/prot_arv_to_kg2c_uniprot_v3.0_progressive.yaml

# Check visualization action signature
grep -A5 "async def execute_typed" /home/ubuntu/biomapper/biomapper/core/strategy_actions/reports/generate_visualizations_v2.py

# Check CUSTOM_TRANSFORM parameter model
grep -A20 "class CustomTransformExpressionParams" /home/ubuntu/biomapper/biomapper/core/strategy_actions/utils/data_processing/custom_transform_expression.py

# Review actual context keys during execution
grep "Available keys:" /tmp/v3.0_final_with_gdrive.log
```

## Success Criteria

For each issue, provide:
1. **Root Cause**: Clear explanation of why the error occurs
2. **Impact Assessment**: Whether it affects pipeline results (currently none do)
3. **Proposed Fix**: Specific code changes needed
4. **Testing Strategy**: How to verify the fix works

## Important Notes

1. **The pipeline works successfully** despite these issues - achieving 97% match rate and uploading to Google Drive
2. These are **non-critical issues** - historical resolution adds minimal value, visualizations are nice-to-have
3. The main data flow is correct - these are auxiliary features
4. Focus on understanding the **2025 standardized framework** patterns:
   - Standard parameter names (input_key, output_key, file_path)
   - Proper TypedStrategyAction signatures
   - Pydantic model validation

## Additional Context

The pipeline successfully:
- Loads 1,197 Arivale proteins
- Extracts UniProt IDs from 350,367 KG2C entities (expanding to 438,931 with multiple IDs)
- Achieves 3,651 direct matches (~97% match rate)
- Exports results to `/tmp/biomapper/protein_mapping_v3.0_progressive/all_mappings_v3.0.tsv`
- Uploads to Google Drive folder: `prot_arv_to_kg2c_uniprot/v3_0/v3.0_progressive_results/`

Please investigate these issues systematically and provide detailed findings and recommendations.