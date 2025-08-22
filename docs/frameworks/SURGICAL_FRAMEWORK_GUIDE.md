# BiOMapper Surgical Framework Guide

## Overview

The Surgical Framework enables safe, isolated modifications to BiOMapper action internals without affecting pipeline integration or output structures. It's designed to be **automatically activated by agents** when detecting the need for careful action refinement.

## Key Features

- 🔒 **Automatic Detection**: Agent detects surgical intent from natural language
- 🛡️ **Isolation**: Changes tested in sandbox before integration
- ✅ **Validation**: Ensures no structural or interface changes
- 🎯 **Generic**: Works with any BiOMapper action type
- 👤 **Transparent**: Users never see framework complexity

## How It Works

### 1. Automatic Activation

When a user describes an issue that requires internal action changes:

```
User: "The statistics show 3675 proteins but should show unique entities"
Agent: [Automatically activates surgical mode]
       "I see the issue with incorrect counting logic. Let me fix that 
        while ensuring all output formats remain unchanged..."
```

### 2. Detection Patterns

The framework detects surgical need from patterns like:
- "Fix counting/statistics/logic in action"
- "Update without breaking pipeline"  
- "Should show unique entities"
- "3675 but should be 1200"
- "Counting expanded records instead of unique"

### 3. Safety Guarantees

Every surgical modification is validated for:
- **Context Interface**: Same keys read/written
- **Output Structure**: File formats unchanged
- **Data Types**: Type consistency maintained
- **Pipeline Integration**: No breaking changes

## Agent Integration

### Automatic Usage

```python
from core.safety import surgical_framework

# In agent's message processing
def process_user_message(message):
    # Automatically check for surgical need
    surgical_context = surgical_framework.process_user_message(message)
    
    if surgical_context:
        # Enter surgical mode transparently
        handle_surgical_modification(surgical_context)
    else:
        # Normal processing
        handle_standard_request(message)
```

### What Users See

Users interact naturally without knowing about surgical mode:

```
User: "The entity counting is wrong, it's counting all records"

Agent: I see the issue - the statistics are counting expanded records 
       instead of unique entities. Let me fix that while preserving 
       all your output formats...
       
       ✅ Fixed! Statistics now correctly show unique entity counts.
       The output files maintain the same structure.
```

## Supported Action Types

The framework works generically with any action:

- `GENERATE_MAPPING_VISUALIZATIONS` - Statistics fixes
- `EXPORT_DATASET` - Format preservation issues
- `METABOLITE_CTS_BRIDGE` - API logic refinement
- `PROTEIN_NORMALIZE_ACCESSIONS` - Parsing updates
- Any future action needing surgical changes

## Architecture

### Core Components

1. **ActionSurgeon**: Main surgical executor
   - Captures baseline behavior
   - Validates changes are safe
   - Ensures no side effects

2. **SurgicalModeAgent**: Agent integration
   - Detects surgical intent
   - Manages activation/deactivation
   - Provides user responses

3. **SurgicalValidator**: Safety checks
   - Validates context interface
   - Checks output structures
   - Ensures type consistency

4. **ContextTracker**: Monitors access
   - Tracks context reads/writes
   - Detects interface changes
   - Records access patterns

## Example: Statistics Fix

### Problem
Visualization shows 3,675 proteins (expanded records) instead of ~1,200 unique entities.

### Surgical Solution

1. **Detection**: Framework detects "counting expanded records" pattern
2. **Isolation**: Creates sandbox with real pipeline data
3. **Baseline**: Captures current behavior
4. **Modification**: Updates counting logic internally
5. **Validation**: Verifies output structure unchanged
6. **Integration**: Applies validated changes

### Result
Statistics now show correct unique counts while maintaining exact same output file structure.

## Safety Validation Process

```
📸 Baseline Capture
  ↓
🔧 Apply Changes in Isolation
  ↓
🔍 Validation Checks:
  • Context interface preserved? ✅
  • Output structure unchanged? ✅
  • Data types consistent? ✅
  ↓
✅ Safe to Integrate
```

## Developer Usage

### Testing Surgical Changes

```python
from core.safety import SurgicalMode

# Use context manager for surgical operations
with SurgicalMode('GENERATE_MAPPING_VISUALIZATIONS') as surgeon:
    # Baseline automatically captured
    
    # Make your changes
    modified_action = apply_statistics_fix()
    
    # Validate automatically
    is_safe, messages = surgeon.validate_surgical_changes(modified_action)
    
    if is_safe:
        # Apply changes
        deploy_fix(modified_action)
```

### Adding New Detection Patterns

Edit patterns in `ActionSurgeon.SURGICAL_PATTERNS`:

```python
SURGICAL_PATTERNS = [
    r"your.*pattern.*here",
    # Existing patterns...
]
```

## Command Reference

While users never see these, agents can use:

- `/biomapper-surgical [ACTION] [ISSUE]` - Activate surgical mode
- Detection is automatic based on message patterns
- Validation happens transparently
- User only sees natural language responses

## Best Practices

1. **Let Detection Work**: Trust automatic pattern detection
2. **Preserve Everything**: Never change interfaces or structures
3. **Test in Isolation**: Always validate before integration
4. **User Transparency**: Hide framework complexity from users
5. **Document Changes**: Log what was modified internally

## Troubleshooting

### Detection Not Triggering
- Check if message matches patterns in `SURGICAL_PATTERNS`
- Verify action type is in registry
- Look for explicit action name mentions

### Validation Failures
- Context interface changed: Check read/write patterns
- Output structure changed: Verify file format preservation
- Type changes: Ensure data type consistency

### Integration Issues
- Test with real pipeline data
- Verify all output files generated
- Check context state after execution

## Future Enhancements

- [ ] Machine learning for pattern detection
- [ ] Automatic rollback on failure
- [ ] Performance impact analysis
- [ ] Change history tracking
- [ ] Team collaboration features

## Summary

The Surgical Framework enables safe action refinement through:
- **Automatic activation** from natural language
- **Transparent operation** hidden from users
- **Comprehensive validation** of all changes
- **Generic support** for any action type
- **Safety guarantees** for pipeline stability

This allows fixing internal logic issues while maintaining 100% compatibility with existing pipelines and integrations.