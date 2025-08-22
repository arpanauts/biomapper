# Quick BiOMapper Pipeline Diagnostics

Run comprehensive diagnostics in 30 seconds for BiOMapper pipeline issues.

USAGE: `/diagnose [strategy_name]`

## Validation Checklist

```bash
#!/bin/bash
echo "🔍 BiOMapper Pipeline Diagnosis"
echo "Strategy: ${ARGUMENTS:-"all strategies"}"
echo "================================"

# Set up Python path
export PYTHONPATH="${PWD}/src:${PYTHONPATH}"

# Check 1: Parameter Substitution
echo ""
echo "📋 Checking Parameter Substitution..."
python scripts/check_yaml_params.py ${ARGUMENTS}
PARAM_STATUS=$?

# Check 2: Import Path Verification
echo ""
echo "📋 Checking Import Paths..."
python scripts/check_import_paths.py
IMPORT_STATUS=$?

# Check 3: Authentic Biological Coverage
echo ""
echo "📋 Checking Biological Coverage..."
python scripts/check_authentic_coverage.py ${ARGUMENTS}
COVERAGE_STATUS=$?

# Check 4: TDD Compliance (sample check)
echo ""
echo "📋 Checking TDD Compliance..."
if [ -n "${ARGUMENTS}" ]; then
    python .claude/hooks/tdd_enforcer.py "src/configs/strategies/${ARGUMENTS}.yaml"
else
    echo "✅ TDD check skipped (no specific strategy)"
fi
TDD_STATUS=$?

# Summary
echo ""
echo "================================"
echo "📊 DIAGNOSTIC SUMMARY"
echo "================================"

if [ $PARAM_STATUS -eq 0 ]; then
    echo "✅ Parameter Substitution: PASSED"
else
    echo "❌ Parameter Substitution: FAILED"
fi

if [ $IMPORT_STATUS -eq 0 ]; then
    echo "✅ Import Paths: PASSED"
else
    echo "❌ Import Paths: FAILED"
fi

if [ $COVERAGE_STATUS -eq 0 ]; then
    echo "✅ Biological Coverage: PASSED"
else
    echo "❌ Biological Coverage: FAILED"
fi

echo ""
if [ $PARAM_STATUS -eq 0 ] && [ $IMPORT_STATUS -eq 0 ] && [ $COVERAGE_STATUS -eq 0 ]; then
    echo "✅ All diagnostics passed! System healthy."
else
    echo "❌ Issues detected. Fix before declaring success."
fi
```

## Quick Fixes

### Parameter Issues
```bash
# Check specific strategy
python scripts/check_yaml_params.py your_strategy.yaml

# Fix by adding to parameters section:
# parameters:
#   your_param: "value"
```

### Import Issues
```bash
# Fix PYTHONPATH
export PYTHONPATH="${PWD}/src:${PYTHONPATH}"

# Verify fix
python scripts/check_import_paths.py
```

### Coverage Issues
```bash
# Check for entity duplication
python scripts/check_authentic_coverage.py

# Verify progressive improvement
cat /tmp/biomapper/mapping_report.json | jq '.progressive_stats'
```

### TDD Issues
```bash
# Check test exists
python .claude/hooks/tdd_enforcer.py src/actions/my_action.py

# Create test stub
mkdir -p tests/unit/core/strategy_actions/
touch tests/unit/core/strategy_actions/test_my_action.py
```

**CRITICAL**: Run this command before any "SUCCESS!" declaration.