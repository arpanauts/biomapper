# BiOMapper Surgical Mode - Agent Command

Automatically activate surgical mode for safe action refinement.

USAGE: `/biomapper-surgical [ACTION_TYPE] [ISSUE_DESCRIPTION]`

## Automatic Activation

```python
#!/usr/bin/env python3
"""
Surgical mode for BiOMapper action refinement.
Automatically activated when agent detects surgical intent.
"""

import sys
import os
sys.path.insert(0, '/home/ubuntu/biomapper/src')
os.chdir('/home/ubuntu/biomapper')

from core.safety import surgical_framework

# Parse arguments
action_type = "${ARGUMENT_1:-GENERATE_MAPPING_VISUALIZATIONS}"
issue = "${ARGUMENT_2:-Fix entity counting logic}"

print(f"🔒 SURGICAL MODE: {action_type}")
print(f"📝 Issue: {issue}")
print("=" * 60)

# Check if surgical mode appropriate
surgical_context = surgical_framework.process_user_message(issue)

if surgical_context:
    print(surgical_context['initial_response'])
    print("\n✅ Surgical mode activated")
    print("🛡️ Safety checks enabled")
    print("📊 Baseline captured")
else:
    print("ℹ️ Surgical mode not needed for this request")
```

## What This Does

1. **Automatic Detection**: Identifies when surgical changes needed
2. **Isolation**: Creates safe sandbox for modifications  
3. **Validation**: Ensures no structural changes
4. **Integration**: Safely applies validated changes

## When Agent Uses This

The agent automatically activates surgical mode when detecting:
- "Fix counting/statistics/logic in action"
- "Update without breaking pipeline"
- "Internal change only"
- "Preserve output structure while fixing"

## Safety Guarantees

- ✅ Context interface preserved
- ✅ Output structure unchanged
- ✅ Data types maintained
- ✅ Pipeline integration intact

## Example Usage

```bash
# Agent detects need and runs automatically:
/biomapper-surgical GENERATE_MAPPING_VISUALIZATIONS "Fix entity counting"

# Or explicit activation:
/biomapper-surgical EXPORT_DATASET "Preserve list format"
```

## Validation Output

```
🔒 SURGICAL MODE: GENERATE_MAPPING_VISUALIZATIONS
📝 Issue: Fix entity counting logic
============================================================
I see the issue with incorrect counting logic. Let me fix that 
while ensuring all output formats and pipeline integration remain unchanged...

✅ Surgical mode activated
🛡️ Safety checks enabled
📊 Baseline captured
```

**NOTE**: Users never see or use this command directly - it's automatically activated by the agent based on natural language intent.