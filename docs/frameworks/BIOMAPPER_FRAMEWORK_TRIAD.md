# BiOMapper Framework Triad: Complete Isolation Architecture

## Overview

The BiOMapper Framework Triad provides three complementary isolation mechanisms for safe, transparent development and maintenance of the biomapper system. Each framework operates automatically based on intent detection from natural language, requiring no user training or explicit activation.

## The Three Frameworks

### 1. 🔒 Surgical Framework - Internal Action Logic
**Purpose**: Modify internal action logic while preserving external interfaces and pipeline integration.

**Automatic Activation Triggers**:
- "Statistics showing wrong count"
- "Internal logic broken" 
- "Fix counting/calculation"
- "Action logic issue"

**Key Features**:
- Context snapshot preservation
- Surgical validation of changes
- Zero pipeline disruption
- Automatic rollback on failure

**Example Use Case**:
```
User: "The statistics show 3675 proteins but should count unique entities"
Agent: [Automatically activates Surgical Framework]
       🔒 Surgical mode activated
       🎯 Target: GENERATE_MAPPING_VISUALIZATIONS
       ✅ Fixed: Now counting unique entities (1172) instead of records
```

### 2. 🔄 Circuitous Framework - Pipeline Orchestration
**Purpose**: Diagnose and repair parameter flow issues in YAML strategy pipelines.

**Automatic Activation Triggers**:
- "Parameters not flowing between steps"
- "Pipeline orchestration broken"
- "Strategy sequence wrong"
- "Parameter substitution failing"

**Key Features**:
- Flow graph analysis
- Parameter tracing
- Dependency mapping
- Breakpoint detection
- Automated repair suggestions

**Example Use Case**:
```
User: "The metabolomics strategy isn't passing context between actions"
Agent: [Automatically activates Circuitous Framework]
       🔄 Circuitous mode activated
       📋 Strategy: metabolomics_progressive_v4.0
       ⚠️ Issues Found: 2
       🔧 Applying repairs to parameter flow
```

### 3. 🔗 Interstitial Framework - Interface Compatibility
**Purpose**: Ensure 100% backward compatibility during interface evolution.

**Automatic Activation Triggers**:
- "Interface between actions broken"
- "Backward compatibility issue"
- "New parameter broke existing strategies"
- "API evolution breaking changes"

**Key Features**:
- Contract extraction and analysis
- Compatibility validation
- Automatic compatibility layer generation
- Migration path creation
- Alias maintenance

**Core Principle**: **100% Backward Compatibility**
- Never break existing strategies
- Always provide migration paths
- Maintain all parameter aliases indefinitely
- Generate compatibility wrappers automatically

**Example Use Case**:
```
User: "The new output_key parameter broke old strategies using dataset_key"
Agent: [Automatically activates Interstitial Framework]
       🔗 Interstitial mode activated
       🛡️ Compatibility: 100% guaranteed
       🔧 Creating compatibility layer: dataset_key → output_key alias
```

## Unified Agent Architecture

The `UnifiedBiomapperAgent` orchestrates all three frameworks through intelligent routing:

```python
from src.core.safety import unified_agent

# Agent automatically detects intent and routes to appropriate framework
context = unified_agent.process_user_message(user_message)
```

### Intent Detection & Routing

1. **Pattern Matching**: Each framework has specific patterns
2. **Confidence Scoring**: Weighted scoring based on pattern matches
3. **Priority Resolution**: Handles ambiguous cases using priority order:
   - Surgical (most specific)
   - Interstitial (interface-specific)
   - Circuitous (pipeline-wide)
4. **Threshold Activation**: Minimum 40% confidence for activation

### Confidence Scoring Algorithm
```python
# Pattern specificity weighting
pattern_weight = len(pattern.pattern) / 100.0
score = min(1.0, 0.3 + pattern_weight)

# Keyword boosting
if framework_keywords in message:
    score += 0.1 per keyword

# Ambiguity resolution
if confidence_difference < 0.15:
    use_priority_order()
```

## Framework Interactions

### Surgical → Interstitial
When surgical changes modify output format, Interstitial ensures compatibility:
```
Surgical: Changes internal calculation
    ↓
Interstitial: Validates output contract unchanged
    ↓
Result: Internal fix with guaranteed compatibility
```

### Circuitous → Surgical
When pipeline issues stem from action logic:
```
Circuitous: Detects parameter not propagating
    ↓
Surgical: Fixes action's context handling
    ↓
Result: Pipeline flow restored
```

### Interstitial → Circuitous
When interface changes affect pipeline flow:
```
Interstitial: Creates compatibility layer
    ↓
Circuitous: Validates pipeline still works
    ↓
Result: Evolution without disruption
```

## Slash Commands

### `/biomapper-surgical [ACTION_NAME]`
Activate surgical mode for specific action or auto-detect from context.

### `/biomapper-circuitous [STRATEGY_NAME]`
Diagnose pipeline orchestration issues in a strategy.

### `/biomapper-interstitial [ACTION_TYPE]`
Analyze interface compatibility and ensure backward compatibility.

## Implementation Details

### Directory Structure
```
src/core/safety/
├── __init__.py                    # Framework exports
├── action_surgeon.py               # Surgical: Core surgery logic
├── surgical_agent.py               # Surgical: Agent behavior
├── circuitous_framework.py        # Circuitous: Pipeline analysis
├── interstitial_framework.py      # Interstitial: Compatibility
└── unified_agent.py               # Unified routing and orchestration
```

### Key Classes

**Surgical Framework**:
- `ActionSurgeon`: Performs surgical modifications
- `SurgicalValidator`: Validates changes
- `ContextTracker`: Tracks context flow

**Circuitous Framework**:
- `CircuitousFramework`: Main orchestrator
- `StrategyFlowAnalyzer`: Analyzes parameter flow
- `FlowNode`: Represents pipeline steps
- `FlowBreakpoint`: Identifies issues

**Interstitial Framework**:
- `InterstitialFramework`: Main orchestrator
- `ContractAnalyzer`: Extracts action contracts
- `CompatibilityLayer`: Generates adapters
- `ActionContract`: Interface specification

**Unified Agent**:
- `UnifiedBiomapperAgent`: Main agent
- `FrameworkRouter`: Intent routing
- `IntentScore`: Confidence scoring

## Usage Examples

### Natural Language Activation

```python
# User describes issue naturally
message = "The protein statistics are counting duplicates"
# Agent automatically activates Surgical Framework

message = "Parameters aren't passing between pipeline steps"
# Agent automatically activates Circuitous Framework

message = "The new parameter names broke backward compatibility"
# Agent automatically activates Interstitial Framework
```

### Programmatic Access

```python
from src.core.safety import unified_agent

# Process any user message
result = unified_agent.process_user_message(
    "Fix the metabolite matching that's overcounting"
)

# Execute framework operations
if result['framework'] == 'surgical':
    unified_agent.execute_framework_operation('validate')
    unified_agent.execute_framework_operation('apply')
```

## Compatibility Guarantees

### Never Break
- ❌ Required parameters cannot be removed
- ❌ Parameter types must remain compatible
- ❌ Output structure must remain accessible
- ❌ Context keys must remain available

### Always Provide
- ✅ Migration path for deprecated features
- ✅ Default values for new required parameters
- ✅ Type adapters for changed parameters
- ✅ Compatibility wrappers when needed

### Preserve
- 🛡️ All existing strategies must continue working
- 🛡️ All parameter aliases must be maintained
- 🛡️ All output formats must be readable
- 🛡️ All context patterns must be supported

## Performance Characteristics

- **Pattern Matching**: Pre-compiled regex, O(n) where n = message length
- **Confidence Scoring**: O(p) where p = number of patterns (~10-20)
- **Framework Activation**: < 10ms for typical messages
- **Memory Overhead**: ~5MB for pattern cache and framework instances

## Testing Strategy

### Unit Tests
```bash
# Test individual frameworks
pytest tests/unit/core/safety/test_surgical.py
pytest tests/unit/core/safety/test_circuitous.py
pytest tests/unit/core/safety/test_interstitial.py
```

### Integration Tests
```bash
# Test unified agent routing
pytest tests/integration/test_unified_agent.py

# Test framework interactions
pytest tests/integration/test_framework_interactions.py
```

### Confidence Calibration
```python
# Test pattern matching accuracy
test_messages = [
    ("stats showing wrong count", FrameworkType.SURGICAL, 0.7),
    ("pipeline parameter flow broken", FrameworkType.CIRCUITOUS, 0.8),
    ("backward compatibility issue", FrameworkType.INTERSTITIAL, 0.9),
]
```

## Best Practices

1. **Let the Agent Decide**: Don't force framework selection, describe the problem naturally
2. **Provide Context**: Include action/strategy names when known
3. **Trust Automatic Detection**: The agent learns from patterns
4. **Report Issues**: If wrong framework activates, report for pattern tuning

## Troubleshooting

### Framework Not Activating
- Check confidence threshold (minimum 40%)
- Verify patterns match your description
- Try more specific keywords

### Wrong Framework Activated
- Priority order may override in ambiguous cases
- Add more specific context to message
- Use slash command for explicit activation

### Compatibility Issues
- Interstitial Framework logs all compatibility decisions
- Check `~/.biomapper/compatibility.log` for details
- All aliases are permanent once created

## Future Enhancements

1. **Pattern Learning**: ML-based pattern refinement from usage
2. **Cross-Framework Orchestration**: Automatic chaining of frameworks
3. **Rollback History**: Complete undo/redo for all framework operations
4. **Visual Flow Diagrams**: Graphical pipeline analysis
5. **Compatibility Database**: Centralized alias and migration tracking

## Conclusion

The BiOMapper Framework Triad provides comprehensive, automatic isolation for all aspects of biomapper development:

- **Surgical**: Fix internals without breaking integration
- **Circuitous**: Repair pipeline flow without touching actions
- **Interstitial**: Evolve interfaces with 100% backward compatibility

Together, they enable confident, rapid development while maintaining system stability and user trust.