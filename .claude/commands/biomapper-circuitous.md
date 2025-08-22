# BiOMapper Circuitous Mode - Pipeline Orchestration

Automatically diagnose and repair pipeline parameter flow issues.

USAGE: `/biomapper-circuitous [STRATEGY_NAME]`

## Automatic Activation

```python
#!/usr/bin/env python3
"""
Circuitous mode for BiOMapper pipeline orchestration.
Automatically activated when agent detects flow issues.
"""

import sys
import os
sys.path.insert(0, '/home/ubuntu/biomapper/src')
os.chdir('/home/ubuntu/biomapper')

from core.safety import CircuitousFramework

# Parse arguments
strategy = "${ARGUMENT_1:-auto_detect}"

print(f"🔄 CIRCUITOUS MODE: Pipeline Orchestration Analysis")
print(f"📋 Strategy: {strategy}")
print("=" * 60)

framework = CircuitousFramework()

# Find strategy file
if strategy != "auto_detect":
    strategy_path = f"src/configs/strategies/experimental/{strategy}.yaml"
    
    # Diagnose pipeline flow
    diagnosis = framework.diagnose_strategy(strategy_path)
    
    print(f"\n📊 Flow Analysis:")
    print(f"  Total steps: {diagnosis['flow_analysis']['total_steps']}")
    print(f"  Dependencies: {diagnosis['flow_analysis']['dependencies_found']}")
    print(f"  Context keys: {diagnosis['flow_analysis']['context_keys_tracked']}")
    
    if diagnosis['issues_found'] > 0:
        print(f"\n⚠️ Issues Found: {diagnosis['issues_found']}")
        for issue in diagnosis['breakpoints']:
            print(f"  • {issue['type']}: {issue['description']}")
        
        print(f"\n🔧 Suggested Repairs:")
        for repair in diagnosis['suggested_repairs']:
            print(f"  • {repair['action']}")
    else:
        print("\n✅ No flow issues detected")
else:
    print("ℹ️ Specify a strategy name to diagnose")
```

## What This Does

1. **Flow Analysis**: Traces parameter flow through strategy steps
2. **Breakpoint Detection**: Identifies where data flow breaks
3. **Dependency Mapping**: Shows step interdependencies
4. **Repair Suggestions**: Provides fixes for flow issues

## When Agent Uses This

The agent automatically activates circuitous mode when detecting:
- "Parameters not flowing between steps"
- "Pipeline orchestration broken"
- "Step sequence wrong"
- "Parameter substitution failing"
- "Context not passing between actions"

## Flow Diagnostics

- ✅ Parameter resolution validation
- ✅ Context handoff verification
- ✅ Step sequencing analysis
- ✅ Dependency graph construction

## Example Usage

```bash
# Agent detects flow issue and runs:
/biomapper-circuitous prot_arv_to_kg2c_uniprot_v3.0

# Manual diagnosis:
/biomapper-circuitous met_arv_to_ukbb_progressive_v4.0
```

## Diagnostic Output

```
🔄 CIRCUITOUS MODE: Pipeline Orchestration Analysis
📋 Strategy: prot_arv_to_kg2c_uniprot_v3.0
============================================================

📊 Flow Analysis:
  Total steps: 8
  Dependencies: 5
  Context keys: 12

⚠️ Issues Found: 2
  • parameter: Undefined parameter: ${source_file}
  • context: Missing context key: stage1_results

🔧 Suggested Repairs:
  • Add missing parameter 'source_file' to parameters section
  • Ensure key 'stage1_results' is available in context
```

**NOTE**: Users describe pipeline issues naturally - the agent automatically activates circuitous mode based on intent detection.