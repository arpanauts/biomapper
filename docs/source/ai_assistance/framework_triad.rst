BioMapper Framework Triad
==========================

The BioMapper Framework Triad provides three complementary isolation mechanisms for safe, transparent development and maintenance of the BioMapper system. These frameworks are implemented in ``src/core/safety/`` and orchestrated by the ``UnifiedBiomapperAgent``.

.. important::
   All frameworks can be activated two ways:
   
   - **By name**: Simply say "surgical", "circuitous", or "interstitial" to directly activate the framework
   - **By description**: Describe the problem naturally and the appropriate framework activates automatically
   
   No user training required - both methods work seamlessly.

Framework Overview
------------------

.. list-table:: The Three Frameworks
   :header-rows: 1
   :widths: 15 25 30 30

   * - Framework
     - Purpose
     - Isolation Guarantee
     - Example Use Case
   * - **🔒 Surgical**
     - Fix internal action logic
     - Preserves all external interfaces
     - "Statistics counting wrong"
   * - **🔄 Circuitous**
     - Repair pipeline orchestration
     - Maintains action boundaries
     - "Parameters not flowing"
   * - **🔗 Interstitial**
     - Ensure interface compatibility
     - 100% backward compatibility
     - "New parameter broke strategies"

Surgical Framework
------------------

**Purpose:** Enable safe modifications to action internals without affecting pipeline integration

**Key Features:**

- **Context Snapshot Preservation** - Captures before/after state
- **Surgical Validation** - Ensures changes are internal only
- **Automatic Rollback** - Reverts if validation fails
- **Zero Pipeline Disruption** - Guarantees interface stability

**Architecture:**

.. code-block:: text

   Action Boundary
   ┌─────────────────────────────┐
   │   External Interface        │ ← Preserved
   ├─────────────────────────────┤
   │   ┌───────────────────┐     │
   │   │  Internal Logic   │     │ ← Modified
   │   │  (Surgical Zone)  │     │
   │   └───────────────────┘     │
   ├─────────────────────────────┤
   │   Output Interface          │ ← Preserved
   └─────────────────────────────┘

**Implementation Classes:**

- ``ActionSurgeon`` - Performs surgical modifications with safety validation
- ``SurgicalModeAgent`` - Agent-side surgical mode manager with auto-detection
- ``AutoSurgicalFramework`` - Top-level framework orchestrator
- ``ContextTracker`` - Monitors context access patterns (referenced in surgical_agent.py)

**Validation Rules:**

1. Output structure must remain identical
2. Context keys read/written must not change
3. Parameter interface must be preserved
4. File outputs must maintain format

**Example Application:**

.. code-block:: python

   # Original (incorrect)
   def calculate_statistics(self, df):
       total = len(df)  # Counts all rows
       return {"total_proteins": total}
   
   # After Surgical Fix
   def calculate_statistics(self, df):
       total = df['uniprot'].nunique()  # Counts unique
       return {"total_proteins": total}  # Same structure

Circuitous Framework
--------------------

**Purpose:** Diagnose and repair parameter flow issues in YAML strategy pipelines

**Key Features:**

- **Flow Graph Analysis** - Builds step dependency graph
- **Parameter Tracing** - Tracks parameter substitution
- **Breakpoint Detection** - Identifies flow interruptions
- **Automated Repairs** - Suggests or applies fixes

**Architecture:**

.. code-block:: text

   Strategy Pipeline Flow
   ┌──────────┐    params    ┌──────────┐    context    ┌──────────┐
   │  Step 1  │──────────────►│  Step 2  │──────────────►│  Step 3  │
   └──────────┘               └──────────┘               └──────────┘
        │                           │                           │
        └───────────┬───────────────┴───────────────────────────┘
                    │
              Flow Analysis
              - Parameter resolution
              - Context propagation
              - Dependency validation

**Implementation Classes:**

- ``CircuitousFramework`` - Main orchestrator for pipeline flow analysis
- ``CircuitousMode`` - Framework operation modes and configuration
- Strategy analysis components (integrated into unified agent framework)

**Common Issues Detected:**

1. **Undefined Parameters** - ``${parameters.missing}``
2. **Context Key Missing** - Step expects key not provided
3. **Circular Dependencies** - Steps depend on each other
4. **Parameter Type Mismatch** - String where list expected
5. **Output Not Available** - Previous step didn't create expected output

**Repair Strategies:**

.. code-block:: yaml

   # Issue: Parameter not defined
   parameters:
     input_file: "/data/proteins.csv"
   steps:
     - params:
         file: "${parameters.source_file}"  # WRONG
   
   # Fix: Add missing parameter or correct reference
   parameters:
     input_file: "/data/proteins.csv"
     source_file: "/data/proteins.csv"  # Added
   # OR
     - params:
         file: "${parameters.input_file}"  # Corrected

Interstitial Framework
----------------------

**Purpose:** Ensure 100% backward compatibility during interface evolution

**Core Principle:** **Never Break Existing Code**

**Key Features:**

- **Contract Extraction** - Analyzes action interfaces
- **Compatibility Validation** - Checks for breaking changes
- **Automatic Adapters** - Generates compatibility layers
- **Permanent Aliases** - Maintains all historical names

**Architecture:**

.. code-block:: text

   Interface Evolution with Compatibility
   
   Old Interface          Compatibility Layer         New Interface
   ┌─────────────┐       ┌──────────────────┐       ┌─────────────┐
   │ dataset_key │──────►│  Alias Mapping   │──────►│  input_key  │
   └─────────────┘       │  Type Adapters   │       └─────────────┘
                         │  Default Values  │
                         └──────────────────┘

**Implementation Classes:**

- ``InterstitialFramework`` - Main orchestrator for interface compatibility
- ``InterstitialMode`` - Framework operation modes and configuration
- Compatibility layer generation (integrated into unified framework architecture)

**Compatibility Rules:**

**NEVER BREAK:**
   - ❌ Required parameters cannot be removed
   - ❌ Parameter types must remain compatible
   - ❌ Output structure must remain accessible
   - ❌ Context keys must remain available

**ALWAYS PROVIDE:**
   - ✅ Migration path for deprecated features
   - ✅ Default values for new required parameters
   - ✅ Type adapters for changed parameters
   - ✅ Compatibility wrappers when needed

**PRESERVE:**
   - 🛡️ All existing strategies must continue working
   - 🛡️ All parameter aliases must be maintained
   - 🛡️ All output formats must be readable
   - 🛡️ All context patterns must be supported

**Example Compatibility Layer:**

.. code-block:: python

   class ActionParams(BaseModel):
       # New parameter name
       input_key: str
       
       # Compatibility configuration
       class Config:
           # Accept extra fields
           extra = "allow"
           # Permanent alias
           fields = {
               'input_key': {'alias': 'dataset_key'}
           }
       
       @validator('input_key', pre=True)
       def handle_legacy(cls, v, values):
           # Support multiple legacy names
           for old_name in ['dataset_key', 'data_key', 'input']:
               if old_name in values:
                   return values[old_name]
           return v

Unified Agent Architecture
--------------------------

The ``UnifiedBiomapperAgent`` orchestrates all three frameworks:

**Components:**

- **FrameworkRouter** - Intelligent intent routing with pre-compiled patterns
- **IntentScore** - Confidence scoring system with threshold validation
- **Pattern Cache** - Pre-compiled regex patterns for performance
- **Priority Resolver** - Handles ambiguous cases using framework priority order

**Routing Pipeline:**

.. code-block:: text

   User Message
        │
        ▼
   Pattern Matching ──────► No Match ──► No Framework
        │
        ▼
   Confidence Scoring
        │
        ▼
   Threshold Check (≥40%)
        │
        ▼
   Ambiguity Resolution
        │
        ▼
   Framework Activation

**Confidence Algorithm:**

.. code-block:: python

   confidence = base_pattern_score + keyword_bonuses
   
   # Pattern scoring
   pattern_weight = len(pattern) / 100  # Specificity
   base_score = 0.3 + pattern_weight    # 0.3 base + bonus
   
   # Keyword bonuses
   for keyword in framework_keywords:
       if keyword in message:
           confidence += 0.1
   
   # Cap at 1.0
   confidence = min(1.0, confidence)

Framework Interactions
----------------------

The frameworks can work together:

**Surgical → Interstitial:**

.. code-block:: text

   1. Surgical fixes internal logic
   2. Interstitial validates interface unchanged
   3. Result: Safe internal fix

**Circuitous → Surgical:**

.. code-block:: text

   1. Circuitous detects flow issue
   2. Root cause in action logic
   3. Surgical fixes action
   4. Circuitous validates flow restored

**Interstitial → Circuitous:**

.. code-block:: text

   1. Interstitial creates compatibility layer
   2. Circuitous validates strategies still work
   3. Result: Safe evolution

Performance Characteristics
---------------------------

.. list-table:: Performance Metrics
   :header-rows: 1
   :widths: 30 70

   * - Metric
     - Value
   * - Pattern Compilation
     - ~5ms on initialization
   * - Message Processing
     - <10ms typical
   * - Memory Usage
     - ~5MB pattern cache
   * - Framework Activation
     - <50ms including analysis
   * - Scaling
     - O(n*p) where n=message length, p=patterns

Best Practices
--------------

**For Users:**

1. Describe problems naturally - don't worry about frameworks
2. Include specific details and examples
3. Trust automatic detection
4. Use slash commands only when needed

**For Developers:**

1. Let frameworks handle isolation
2. Write comprehensive tests
3. Document interface changes
4. Maintain backward compatibility

**For AI Agents:**

1. Process natural language first
2. Apply appropriate framework
3. Validate changes thoroughly
4. Ensure compatibility always

Testing Strategy
----------------

Each framework includes comprehensive tests:

**Unit Tests:**
   - Pattern matching accuracy
   - Confidence scoring
   - Individual component validation

**Integration Tests:**
   - Framework routing
   - Cross-framework workflows
   - Real-world scenarios

**Confidence Calibration:**
   - Pattern effectiveness
   - Threshold tuning
   - Ambiguity resolution

Future Enhancements
-------------------

**Planned Features:**

1. **Machine Learning** - Pattern learning from usage
2. **Visual Diagnostics** - Pipeline flow diagrams
3. **Automated Repairs** - One-click fixes
4. **Rollback History** - Complete undo/redo
5. **Multi-Agent Support** - Coordinate multiple AI agents

**Research Areas:**

- Cross-framework orchestration
- Predictive issue detection
- Performance optimization
- Compatibility prediction

See Also
--------

* :doc:`framework_triggering` - Detection mechanics
* :doc:`slash_commands` - Manual activation
* :doc:`examples` - Real-world scenarios
* ``src/core/safety/`` - Framework implementation directory

---

## Verification Sources

*Last verified: 2025-01-22*

This documentation was verified against the following project resources:

- ``/biomapper/src/core/safety/unified_agent.py`` (UnifiedBiomapperAgent with FrameworkRouter and IntentScore classes)
- ``/biomapper/src/core/safety/surgical_agent.py`` (SurgicalModeAgent, AutoSurgicalFramework classes)
- ``/biomapper/src/core/safety/action_surgeon.py`` (ActionSurgeon, SurgicalMode implementation)
- ``/biomapper/src/core/safety/circuitous_framework.py`` (CircuitousFramework, CircuitousMode classes)
- ``/biomapper/src/core/safety/interstitial_framework.py`` (InterstitialFramework, InterstitialMode classes)
- ``/biomapper/src/actions/registry.py`` (ACTION_REGISTRY for target extraction)
- ``/biomapper/CLAUDE.md`` (Framework triad specifications and pattern documentation)