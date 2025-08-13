# Biomapper Strategy Testing Coordination Summary

## Overview
26 experimental strategies divided into 4 parallel test groups for independent execution by separate Claude Code instances.

## Test Group Assignments

### Group 1: Protein Strategies (6 strategies)
**File:** `test_group_1_protein_strategies.md`
**Port:** 8000
**Focus:** UniProt protein mapping across Arivale and UKBB datasets
**Key Actions:** PROTEIN_EXTRACT_UNIPROT_FROM_XREFS, PROTEIN_MULTI_BRIDGE
**Expected Runtime:** 15-30 minutes total

### Group 2: Metabolite Strategies (8 strategies)
**File:** `test_group_2_metabolite_strategies.md`
**Port:** 8001
**Focus:** Basic and semantic metabolite mapping (HMDB, InChIKey, CTS)
**Key Actions:** METABOLITE_NORMALIZE_HMDB, METABOLITE_CTS_BRIDGE, SEMANTIC_METABOLITE_MATCH
**Expected Runtime:** 20-40 minutes total

### Group 3: Chemistry & Nightingale Strategies (8 strategies)
**File:** `test_group_3_chemistry_nightingale_strategies.md`
**Port:** 8002
**Focus:** Clinical chemistry LOINC extraction and Nightingale NMR biomarkers
**Key Actions:** CHEMISTRY_EXTRACT_LOINC, CHEMISTRY_FUZZY_TEST_MATCH, NIGHTINGALE_NMR_MATCH
**Expected Runtime:** 20-35 minutes total

### Group 4: Multi-Entity Strategies (4 strategies)
**File:** `test_group_4_multi_entity_strategies.md`
**Port:** 8003
**Focus:** Complex multi-omics integration and cross-dataset harmonization
**Key Actions:** CALCULATE_THREE_WAY_OVERLAP, GENERATE_METABOLOMICS_REPORT, pathway analysis
**Expected Runtime:** 25-45 minutes total

## Parallel Execution Instructions

### Step 1: Distribute Prompts
Open 4 separate Claude Code instances and provide each with:
1. The corresponding test group markdown file
2. Access to `/home/ubuntu/biomapper` directory
3. Confirmation that Poetry environment is activated

### Step 2: Coordinate API Ports
Each group uses a different API port to avoid conflicts:
- Group 1: Port 8000
- Group 2: Port 8001
- Group 3: Port 8002
- Group 4: Port 8003

### Step 3: Monitor Progress
Each group creates its own results directory:
- `/tmp/protein_test_results/`
- `/tmp/metabolite_test_results/`
- `/tmp/chemistry_test_results/`
- `/tmp/multi_entity_test_results/`

### Step 4: Collect Results
Each group generates a `FINAL_REPORT.json` in their results directory.

## Dependency Matrix

| Group | Independent | Soft Dependencies | Hard Dependencies |
|-------|------------|-------------------|-------------------|
| 1 | Yes | None | None |
| 2 | Yes | None | None |
| 3 | Yes | None | None |
| 4 | Partial | Groups 1-3 results enhance testing | None (uses own test data) |

## Resource Requirements

### Per Group:
- CPU: 2-4 cores
- Memory: 2-4 GB
- Disk: 500 MB for test data and results
- Network: API calls to external services (CTS, UniProt)

### Total System:
- CPU: 8-16 cores recommended
- Memory: 8-16 GB recommended
- Disk: 2 GB for all test data and results
- Network: Moderate bandwidth for external API calls

## Expected Outcomes

### Success Criteria:
1. All strategies execute without fatal errors
2. Mapping rates > 60% for most strategies
3. Output files generated for each strategy
4. Statistical reports available

### Key Metrics to Track:
- Execution time per strategy
- Mapping success rates
- Memory peak usage
- API call failures/retries
- Output file sizes

## Coordination Points

### Before Starting:
1. Verify all Claude instances have access to the codebase
2. Confirm no existing processes on ports 8000-8003
3. Ensure test data directories are clean

### During Execution:
1. Monitor system resources (CPU, memory, disk)
2. Check for API rate limiting issues
3. Watch for any cross-group interference

### After Completion:
1. Collect all FINAL_REPORT.json files
2. Archive test results with timestamps
3. Stop all API servers
4. Document any issues encountered

## Aggregation Script

After all groups complete, run this aggregation:

```bash
# Aggregate all results
cat > /tmp/aggregate_results.py << 'EOF'
import json
from pathlib import Path
from datetime import datetime

aggregate_report = {
    "test_date": datetime.now().isoformat(),
    "total_strategies": 26,
    "groups": {}
}

# Collect results from each group
result_dirs = [
    "/tmp/protein_test_results",
    "/tmp/metabolite_test_results", 
    "/tmp/chemistry_test_results",
    "/tmp/multi_entity_test_results"
]

total_successful = 0
total_failed = 0

for dir_path in result_dirs:
    dir_obj = Path(dir_path)
    if dir_obj.exists():
        report_file = dir_obj / "FINAL_REPORT.json"
        if report_file.exists():
            with open(report_file) as f:
                group_data = json.load(f)
                group_name = group_data.get("test_group", dir_obj.name)
                aggregate_report["groups"][group_name] = group_data.get("summary", {})
                total_successful += group_data.get("summary", {}).get("successful", 0)
                total_failed += group_data.get("summary", {}).get("failed", 0)

aggregate_report["overall_summary"] = {
    "total_executed": total_successful + total_failed,
    "total_successful": total_successful,
    "total_failed": total_failed,
    "overall_success_rate": round(total_successful / 26 * 100, 2)
}

print(json.dumps(aggregate_report, indent=2))

# Save aggregate report
with open("/tmp/AGGREGATE_TEST_REPORT.json", "w") as f:
    json.dump(aggregate_report, f, indent=2)
EOF

python /tmp/aggregate_results.py
```

## Troubleshooting Guide

### Common Issues:

1. **Port Already in Use**
   - Solution: Change port in the test group file
   - Alternative: Kill existing process: `lsof -ti:PORT | xargs kill`

2. **Memory Exhaustion**
   - Solution: Run groups sequentially instead of parallel
   - Alternative: Reduce test data size

3. **API Rate Limiting**
   - Solution: Add delays between API calls
   - Alternative: Use cached/mocked responses

4. **Missing Actions**
   - Solution: Verify action registration in ACTION_REGISTRY
   - Alternative: Skip affected strategies

5. **File Permission Issues**
   - Solution: Ensure write permissions on /tmp directories
   - Alternative: Use home directory for outputs

## Final Checklist

- [ ] All 4 test group markdown files created
- [ ] Each Claude instance assigned to a group
- [ ] API ports confirmed available
- [ ] Test data directories created
- [ ] Poetry environment activated in each instance
- [ ] System resources monitored
- [ ] Results collection plan ready
- [ ] Backup/archive strategy defined

## Notes
- Groups can run fully in parallel with no dependencies
- Each group is self-contained with its own test data generation
- Results are independent but can be aggregated for overall assessment
- Consider running Group 4 (multi-entity) last for best results, as it benefits from seeing how other integrations perform