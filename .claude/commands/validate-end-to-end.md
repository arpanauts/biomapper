# End-to-End Pipeline Validation

MANDATORY: Complete validation before declaring any success.

USAGE: `/validate-end-to-end [strategy_name]`

## Comprehensive Validation Protocol

### 1. Parameter Resolution Check
```bash
python scripts/check_yaml_params.py src/configs/strategies/${STRATEGY}.yaml
```
✅ All `${parameters.variable}` resolve correctly
✅ No hardcoded paths
✅ Environment variables have defaults

### 2. Progressive Mapping Validation
```bash
python scripts/check_authentic_coverage.py ${STRATEGY}
```
✅ Stage 1: Direct matches with expected coverage
✅ Stage 2: Composite parsing shows incremental improvement  
✅ Stage 3: Historical resolution adds final coverage
✅ **AUTHENTIC COVERAGE**: No duplicate entity counting

### 3. Output Generation Verification
Check for all required files:
```bash
ls -la /tmp/biomapper/${STRATEGY}/
```
✅ mapping_statistics.tsv
✅ mapping_summary.txt
✅ mapping_report.json
✅ Visualization files (PNG/SVG)
✅ LLM analysis report (if enabled)

### 4. Import Verification
```bash
python scripts/check_import_paths.py
```
✅ All modules import successfully
✅ Action registry populated
✅ No circular dependencies

### 5. TDD Compliance
```bash
python .claude/hooks/tdd_enforcer.py src/configs/strategies/${STRATEGY}.yaml
```
✅ Tests exist for all custom actions
✅ Tests pass

## Quick All-in-One Validation
```bash
# Run complete validation suite
python scripts/prevent_partial_victory.py ${STRATEGY}
```

## Success Criteria
**ALL checks must pass** before declaring success:
- [ ] Parameters resolve
- [ ] Coverage is authentic
- [ ] All outputs generated
- [ ] Imports work
- [ ] Tests exist and pass

**FORBIDDEN**: Declaring success with any failures.