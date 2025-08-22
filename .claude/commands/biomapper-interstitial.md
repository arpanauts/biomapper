# BiOMapper Interstitial Mode - Interface Compatibility

Ensure 100% backward compatibility during interface evolution.

USAGE: `/biomapper-interstitial [ACTION_TYPE]`

## Automatic Activation

```python
#!/usr/bin/env python3
"""
Interstitial mode for BiOMapper interface compatibility.
Automatically activated when agent detects compatibility needs.
CORE PRINCIPLE: Maintain 100% backward compatibility.
"""

import sys
import os
sys.path.insert(0, '/home/ubuntu/biomapper/src')
os.chdir('/home/ubuntu/biomapper')

from core.safety import InterstitialFramework

# Parse arguments
action = "${ARGUMENT_1:-auto_detect}"

print(f"🔗 INTERSTITIAL MODE: Interface Compatibility Management")
print(f"🛡️ GUARANTEE: 100% Backward Compatibility")
print(f"🎯 Action: {action}")
print("=" * 60)

framework = InterstitialFramework()

if action != "auto_detect":
    # Analyze interface evolution
    print(f"\n📊 Analyzing interface evolution for {action}...")
    
    evolution = framework.analyze_interface_evolution(action)
    
    print(f"\n📋 Current Interface:")
    print(f"  Parameters: {len(evolution['current_interface']['input_params'])}")
    print(f"  Context reads: {evolution['current_interface']['context_reads']}")
    print(f"  Context writes: {evolution['current_interface']['context_writes']}")
    
    if evolution['compatibility_issues']:
        print(f"\n⚠️ Compatibility Issues: {len(evolution['compatibility_issues'])}")
        print(f"  Breaking changes: {evolution['breaking_changes']}")
        print(f"  Warnings: {evolution['warnings']}")
        
        # Ensure compatibility
        print(f"\n🛡️ Ensuring Backward Compatibility...")
        result = framework.ensure_backward_compatibility(action)
        
        if result['compatibility_assured']:
            print("✅ Backward compatibility guaranteed!")
        else:
            print("🔧 Applying compatibility solutions:")
            for solution in result['solutions_applied']:
                print(f"  • {solution['action']}")
    else:
        print("\n✅ No compatibility issues detected")
        
    # Show compatibility rules
    print(f"\n📜 Compatibility Rules Enforced:")
    for rule_type, rules in framework.COMPATIBILITY_RULES.items():
        print(f"\n{rule_type}:")
        for rule in rules[:2]:  # Show first 2 rules
            print(f"  • {rule}")
else:
    print("ℹ️ Specify an action type to analyze")
```

## What This Does

1. **Contract Analysis**: Extracts action input/output interfaces
2. **Evolution Tracking**: Detects interface changes
3. **Compatibility Validation**: Ensures backward compatibility
4. **Auto-Remediation**: Creates compatibility layers

## When Agent Uses This

The agent automatically activates interstitial mode when detecting:
- "Interface between actions broken"
- "Backward compatibility issue"
- "New parameter broke existing strategies"
- "Action boundary needs modification"
- "API evolution breaking changes"

## Compatibility Guarantees

### NEVER BREAK
- ❌ Required parameters cannot be removed
- ❌ Parameter types must remain compatible
- ❌ Output structure must remain accessible
- ❌ Context keys must remain available

### ALWAYS PROVIDE
- ✅ Migration path for deprecated features
- ✅ Default values for new required parameters
- ✅ Type adapters for changed parameters
- ✅ Compatibility wrappers when needed

### PRESERVE
- 🛡️ All existing strategies must continue working
- 🛡️ All parameter aliases must be maintained
- 🛡️ All output formats must be readable
- 🛡️ All context patterns must be supported

## Example Usage

```bash
# Agent detects compatibility issue and runs:
/biomapper-interstitial EXPORT_DATASET

# Manual compatibility check:
/biomapper-interstitial GENERATE_MAPPING_VISUALIZATIONS
```

## Compatibility Report

```
🔗 INTERSTITIAL MODE: Interface Compatibility Management
🛡️ GUARANTEE: 100% Backward Compatibility
🎯 Action: EXPORT_DATASET
============================================================

📋 Current Interface:
  Parameters: 5
  Context reads: ['datasets']
  Context writes: ['output_files']

⚠️ Compatibility Issues: 2
  Breaking changes: 0
  Warnings: 2

🛡️ Ensuring Backward Compatibility...
🔧 Applying compatibility solutions:
  • Maintain alias 'dataset_key' → 'input_key' indefinitely
  • Maintain alias 'output_dir' → 'directory_path' indefinitely

✅ Backward compatibility guaranteed!
```

**NOTE**: The framework guarantees that ALL existing strategies continue working after interface changes through automatic compatibility layer generation.