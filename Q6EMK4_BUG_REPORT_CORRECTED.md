# Q6EMK4 Bug Report - CORRECTED AND RESOLVED

## Executive Summary

A critical bug was causing 28.9% of protein matches to fail in production, with only 70.4% matching instead of the expected 99.3%. The root cause was a **missing parameter in the Pydantic model** that prevented extraction of UniProt IDs from the KG2c xrefs column. The fix has been implemented and verified with production data on August 15, 2025.

## The Real Bug

### What Was Happening
- Q6EMK4 (and 336 other proteins) were incorrectly marked as "source_only" despite existing in both datasets
- The match rate was only 70.4% (818/1162 proteins) when it should have been 99.3%
- UniProt IDs in the KG2c `xrefs` column were never being extracted

### Root Cause
The `MergeWithUniprotResolutionParams` Pydantic model was missing the `target_xref_column` parameter definition. Without this parameter in the model, the condition check in the code always failed:

```python
# Line 369 in merge_with_uniprot_resolution.py
if hasattr(params, 'target_xref_column') and params.target_xref_column:
    # This code was NEVER executed because target_xref_column wasn't defined!
```

Even though the YAML strategies were passing `target_xref_column: "xrefs"`, Pydantic was silently ignoring it because the field wasn't defined in the model.

## The Fix

Added the missing parameter to the Pydantic model:

```python
class MergeWithUniprotResolutionParams(BaseModel):
    # ... other fields ...
    target_xref_column: Optional[str] = Field(None, description="Column containing xrefs (e.g., 'xrefs' for KG2c)")
```

This single line fix enables the xrefs extraction logic that was already implemented but never executed.

## Impact

### Before Fix
- Match rate: 70.4% (818/1162)
- Q6EMK4 status: source_only
- 336 proteins incorrectly unmatched

### After Fix (Verified August 15, 2025)
- Match rate: **99.3%** (1154/1162) ✅
- Q6EMK4 status: **matched to NCBIGene:114990** ✅
- Total matched rows: **6,124** (includes one-to-many mappings)
- Only 8 proteins unmatched (composite IDs)

## Why Q6EMK4 Was Important

Q6EMK4 (Anillin) only exists in the KG2c `xrefs` field, not in the `id` field:
- **Arivale**: Row 80, column `uniprot`: "Q6EMK4"
- **KG2c**: Row 6789, column `xrefs`: Contains "UniProtKB:Q6EMK4"

This made it a perfect test case for validating xrefs extraction.

## Investigation Process

1. Created 10+ investigation scripts to trace the data flow
2. Initially misdiagnosed as a DataFrame reference issue (`.copy()` fix didn't work)
3. Discovered through `check_params.py` that `target_xref_column` wasn't being recognized
4. Found the parameter was missing from the Pydantic model
5. Added the parameter and verified 99.3% match rate

## Lessons Learned

1. **Pydantic silently ignores undefined fields** - Always verify parameters are defined in the model
2. **Test end-to-end** - The initial `.copy()` fix was never properly tested with production data
3. **Check the obvious** - The fix was a single line addition to the parameter model
4. **Use test scripts** - Quick verification scripts are essential for debugging

## Files Modified

- `/home/ubuntu/biomapper/biomapper/core/strategy_actions/merge_with_uniprot_resolution.py`
  - Added `target_xref_column` parameter on line 33

## Verification

### Quick Test
Run the following to verify the fix with sample data:
```bash
python /home/ubuntu/biomapper/test_quick_fix.py
```

Expected output:
```
Q6EMK4 status: matched
✅ Q6EMK4 matched successfully!
   Matched to: NCBIGene:114990
```

### Production Test
Run the full production pipeline test:
```bash
python /home/ubuntu/biomapper/test_dataframe_fix.py
```

Expected output:
```
Match rate: 99.3%
Status: matched
✅ Q6EMK4 MATCHED!
✅ SUCCESS! Match rate improved from 70.4% to 99.3%
```

## Additional Notes

### DataFrame `.copy()` Issue
While investigating this bug, we also discovered and fixed potential DataFrame reference issues by adding `.copy()` to 6 locations where DataFrame rows were stored in indices. While this wasn't the root cause of the Q6EMK4 bug, it's a good defensive programming practice for large-scale data processing.

### Performance
The fix maintains excellent performance:
- Processing time: ~2 minutes for 350,000+ entities
- Memory usage: Stable throughout execution
- Match complexity: O(n+m) using dictionary indexing

## Conclusion

The bug was caused by a missing parameter definition in the Pydantic model, not by DataFrame reference issues as initially suspected. The fix is simple (one line addition), effective (improves match rate from 70.4% to 99.3%), and has been verified with production data.

**Status: RESOLVED ✅**
**Resolution Date: August 15, 2025**
**Verified By: Production pipeline test with 350,368 KG2c entities**