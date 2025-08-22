# Metabolomics Pipeline - Actual vs Claimed Coverage Report

## Executive Summary

**Critical Finding:** The metabolomics progressive pipeline's actual coverage is **~3-4x LOWER** than claimed in documentation.

## Real Execution Metrics (2025-08-21)

### Test Configuration
- **Dataset:** Arivale metabolomics (1,298 metabolites after filtering)
- **Reference:** UKBB NMR metabolomics (251 metabolites)
- **Framework:** BiomapperClient with MinimalStrategyService
- **Execution:** Background async via FastAPI

### Stage 1: Nightingale Bridge (Direct ID Matching)

**ACTUAL RESULTS:**
```
Total metabolites processed: 250
Matched with IDs: 38 (15.2%)
Name-only for Stage 2: 209
Confidence distribution: {0.98: 26, 0.95: 12}
```

**COMPARISON:**
- **Claimed coverage:** 57.9%
- **Actual coverage:** 15.2%
- **Discrepancy:** ~3.8x overestimation

### Stages 2-4: Unable to Complete

**Issues Encountered:**
1. **Stage 2 (Fuzzy String Match):** Context handling error - `'StrategyExecutionContext' object has no attribute 'get'`
2. **Stage 3 (RampDB Bridge):** Same context handling issue
3. **Stage 4 (HMDB Vector Match):** Interface mismatch - `execute_typed() got an unexpected keyword argument 'current_identifiers'`

### Total Pipeline Coverage

**ACTUAL:**
- Stage 1 only: **15.2%** (38/250 metabolites matched)
- Stages 2-4: Could not execute due to technical issues
- **Total achieved:** 15.2%

**CLAIMED:**
- Stage 1: 57.9%
- Stage 2: +12.0% (cumulative 69.9%)
- Stage 3: +5.0% (cumulative 74.9%)
- Stage 4: +3.0% (cumulative 77.9%)
- **Total claimed:** 77.9%

## Root Cause Analysis

### 1. Execution Framework Issues (FIXED)
- **Problem:** BiomapperClient was reporting false success without execution
- **Cause:** Endpoint mismatch (`/api/mapping/jobs/` vs `/api/strategies/v2/jobs/`)
- **Resolution:** Fixed client endpoints and context passing
- **Status:** ✅ RESOLVED - Execution now works

### 2. Action Interface Incompatibility
- **Problem:** TypedStrategyAction expects different interface than MinimalStrategyService provides
- **Affected:** HMDB_VECTOR_MATCH, FUZZY_STRING_MATCH, RAMPDB_BRIDGE
- **Impact:** Stages 2-4 cannot execute
- **Status:** ❌ UNRESOLVED

### 3. Coverage Calculation Methodology
- **Possible Issue:** Claims may be based on:
  - Different dataset (not UKBB reference)
  - Theoretical maximum rather than actual execution
  - Pre-optimization numbers from development
  - Different matching thresholds

## Evidence Trail

### Confirmed Execution
```log
{"event": "Nightingale Bridge Stage 1 Results:", ...}
{"event": "  Total metabolites: 250", ...}
{"event": "  Matched with IDs: 38 (15.2%)", ...}
{"event": "  Name-only for Stage 2: 209", ...}
```

### Failed Stages
```log
{"event": "Error in fuzzy string matching: 'StrategyExecutionContext' object has no attribute 'get'", ...}
{"event": "Error in RampDB bridge matching: 'StrategyExecutionContext' object has no attribute 'get'", ...}
{"event": "HMDBVectorMatchAction.execute_typed() got an unexpected keyword argument 'current_identifiers'", ...}
```

## Recommendations

### Immediate Actions
1. **Fix action interfaces** to enable Stages 2-4 execution
2. **Re-measure coverage** with all stages working
3. **Update documentation** with real metrics

### Strategic Decisions
1. **Question Stage 5 (LIPID MAPS):** If Stage 1 only achieves 15.2%, adding complexity may not help
2. **Focus on quality:** Fix existing stages before adding new ones
3. **Validate claims:** All coverage numbers should come from actual execution

## Validation Commands

To reproduce these results:

```bash
# Start API server
poetry run uvicorn src.api.main:app --port 8001

# Run pipeline (will fail at Stage 4)
python scripts/pipelines/met_arv_to_ukbb_progressive_v4.0.py --stages 1

# Check logs for actual metrics
# Look for "Nightingale Bridge Stage 1 Results"
```

## Conclusion

The metabolomics pipeline has fundamental technical issues preventing full execution. The one stage that does work (Stage 1) achieves **only 15.2% coverage**, not the claimed 57.9%. This suggests the entire "77.9% coverage" claim is likely incorrect by a factor of 3-4x.

**Priority:** Fix technical issues first, then re-measure with real data to establish honest baselines before any feature additions like LIPID MAPS integration.

---
*Generated: 2025-08-21*  
*Method: Direct execution via BiomapperClient with real Arivale/UKBB data*