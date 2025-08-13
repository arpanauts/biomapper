# CRITICAL FIX REQUIRED: Variable Substitution Issue

## Problem Statement
All 26 strategies in `/home/ubuntu/biomapper/configs/strategies/experimental/` are failing with 0% success rate due to unresolved variable substitution: `${metadata.source_files[0].path}` is not being replaced with actual file paths.

## Root Cause
The `MinimalStrategyService._substitute_parameters()` method at line 50 of `/home/ubuntu/biomapper/biomapper/core/minimal_strategy_service.py` only passes `parameters` to the Jinja2 template context, but strategies reference `${metadata.*}` which requires the metadata object to be available.

## Impact
- **100% strategy failure rate** across all entity types
- Blocks all testing and validation efforts
- Prevents any strategies from executing successfully

## Solution Options

### Option 1: Use Existing ParameterResolver (RECOMMENDED)
There's already a robust `ParameterResolver` class in `/home/ubuntu/biomapper/biomapper/core/infrastructure/parameter_resolver.py` that handles metadata references correctly.

**Implementation:**
```python
# In MinimalStrategyService.__init__
from biomapper.core.infrastructure.parameter_resolver import ParameterResolver
self.parameter_resolver = ParameterResolver()

# In MinimalStrategyService.execute_strategy
# Replace the manual substitution with:
resolved_strategy = self.parameter_resolver.resolve_strategy_parameters(strategy_config)
```

### Option 2: Quick Fix to Current Method
Modify `_substitute_parameters` to include metadata in the template context:

```python
def _substitute_parameters(self, obj: Any, parameters: Dict[str, Any], metadata: Dict[str, Any] = None) -> Any:
    if isinstance(obj, str):
        if "${" in obj:
            template_str = re.sub(r"\$\{([^}]+)\}", r"{{ \1 }}", obj)
            template = Template(template_str)
            try:
                # Pass both parameters and metadata to template
                context = {"parameters": parameters}
                if metadata:
                    context["metadata"] = metadata
                return template.render(**context)
            except Exception as e:
                logger.warning(f"Failed to substitute parameters in '{obj}': {e}")
                return obj
    # ... rest of method
```

Then update the call site at line 354:
```python
action_params = self._substitute_parameters(raw_params, parameters, strategy_config.get("metadata"))
```

### Option 3: Update All Strategies
Refactor all 26 strategies to use `${parameters.*}` instead of `${metadata.*}` references. This is labor-intensive and not recommended.

## Other Critical Issues Found

### 1. Missing Protein Strategies
The test references 6 protein strategies that don't exist:
- prot_arv_to_kg2c_uniprot_v1_base.yaml (and 5 others)

Only 2 protein strategies exist with different names:
- ARIVALE_TO_KG2C_PROTEINS
- UKBB_TO_KG2C_PROTEINS

### 2. Missing Actions
Multiple actions are not implemented:
- CUSTOM_TRANSFORM (blocks existing protein strategies)
- PROTEIN_EXTRACT_UNIPROT_FROM_XREFS
- PROTEIN_NORMALIZE_ACCESSIONS
- CHEMISTRY_EXTRACT_LOINC
- CHEMISTRY_FUZZY_TEST_MATCH
- CHEMISTRY_VENDOR_HARMONIZATION
- CHEMISTRY_TO_PHENOTYPE_BRIDGE

### 3. Strategy Discovery Inconsistency
- Chemistry tester: rglob fix working, finds all strategies
- Metabolite tester: Can't find strategies in experimental/
- This suggests the fix was applied between tests or different service instances

### 4. Naming Mismatch
Strategies load with UPPERCASE names in registry but have lowercase filenames:
- File: `chem_arv_to_spoke_loinc_v1_base.yaml`
- Registry: `CHEM_ARV_TO_SPOKE_LOINC_V1_BASE`

## Recommended Action Plan

### Phase 1: Immediate (Fix Variable Substitution)
1. Implement Option 1 or 2 above to fix variable substitution
2. Test with one simple strategy to confirm fix works
3. Document the fix in CLAUDE.md

### Phase 2: Quick Wins (1-2 days)
1. Implement CUSTOM_TRANSFORM action (unblocks existing protein strategies)
2. Create the 6 missing protein strategy YAML files
3. Standardize strategy naming convention

### Phase 3: Complete Actions (1 week)
1. Implement remaining missing actions with tests
2. Update all strategies to use parameterized paths
3. Create integration tests for each entity type

### Phase 4: Infrastructure (2 weeks)
1. Standardize column names across datasets
2. Implement cross-dataset participant matching
3. Add temporal analysis capabilities
4. Create comprehensive documentation

## Test Validation
After implementing the variable substitution fix, test with:
```bash
cd /home/ubuntu/biomapper/biomapper-api
poetry run uvicorn app.main:app --reload --port 8001 &

# Test simplest strategy
curl -X POST "http://localhost:8001/api/v1/strategies/execute" \
  -H "Content-Type: application/json" \
  -d '{"strategy_name": "chem_arv_to_kg2c_phenotypes_v1_base"}'
```

## Contact
If you need clarification on any of these issues, please refer to the detailed test reports in:
- `/tmp/protein_strategy_test_report.md`
- `/tmp/metabolite_strategy_test_report.md`
- `/tmp/chemistry_nmr_test_results.json`
- `/tmp/multi_entity_test_results.json`