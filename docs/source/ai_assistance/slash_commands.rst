Slash Commands Reference
=========================

The BioMapper Framework Triad provides slash commands for manual framework activation when automatic detection isn't sufficient or when you want explicit control. These commands are integrated with the ``UnifiedBiomapperAgent`` for seamless operation.

.. note::
   Slash commands are primarily for Claude Code integration. In most cases, automatic detection from natural language is preferred.

Available Commands
------------------

``/biomapper-surgical``
~~~~~~~~~~~~~~~~~~~~~~~

**Purpose:** Activate Surgical Framework for internal action logic fixes

**Syntax:** ``/biomapper-surgical [ACTION_NAME]``

**Parameters:**
   - ``ACTION_NAME`` (optional) - Target action to modify
   - If omitted, uses ``auto_detect`` mode

**Example Usage:**

.. code-block:: bash

   # Specific action
   /biomapper-surgical GENERATE_MAPPING_VISUALIZATIONS
   
   # Auto-detect from context
   /biomapper-surgical

**Output Example:**

.. code-block:: text

   🔒 SURGICAL MODE: Action Logic Isolation Active
   🎯 Target: GENERATE_MAPPING_VISUALIZATIONS
   ============================================================
   
   📊 Action Analysis:
     Internal methods: 8
     External interfaces: 3
     Pipeline integrations: 2
   
   🔍 Detected Issues:
     • Counting logic using len(df) instead of df['id'].nunique()
     • Statistics aggregation including duplicates
   
   ✅ Surgical Modifications Applied:
     • Fixed counting to use unique entities
     • Preserved all external interfaces
     • Pipeline integration unchanged

**When to Use:**
   - Fixing bugs in action logic
   - Correcting calculations or statistics
   - Updating internal algorithms
   - Refactoring without interface changes

``/biomapper-circuitous``
~~~~~~~~~~~~~~~~~~~~~~~~~

**Purpose:** Diagnose and repair pipeline orchestration issues

**Syntax:** ``/biomapper-circuitous [STRATEGY_NAME]``

**Parameters:**
   - ``STRATEGY_NAME`` (optional) - Strategy file to analyze (without .yaml)
   - If omitted, uses ``auto_detect`` mode

**Example Usage:**

.. code-block:: bash

   # Specific strategy
   /biomapper-circuitous prot_arv_to_kg2c_uniprot_v3.0
   
   # Auto-detect
   /biomapper-circuitous

**Output Example:**

.. code-block:: text

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
     • Ensure key 'stage1_results' is written by previous step

**When to Use:**
   - Parameter substitution failures
   - Context not passing between steps
   - Step sequencing problems
   - YAML strategy debugging

``/biomapper-interstitial``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Purpose:** Ensure backward compatibility during interface evolution

**Syntax:** ``/biomapper-interstitial [ACTION_TYPE]``

**Parameters:**
   - ``ACTION_TYPE`` (optional) - Action to analyze for compatibility
   - If omitted, uses ``auto_detect`` mode

**Example Usage:**

.. code-block:: bash

   # Specific action
   /biomapper-interstitial EXPORT_DATASET
   
   # Auto-detect
   /biomapper-interstitial

**Output Example:**

.. code-block:: text

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

**When to Use:**
   - Renaming parameters
   - Changing action interfaces
   - Evolving API contracts
   - Ensuring strategy compatibility

Command Implementation
----------------------

The slash commands are integrated with the unified framework architecture and route through the ``UnifiedBiomapperAgent``:

**Integration Architecture:**

.. code-block:: text

   Claude Code → Slash Command → UnifiedBiomapperAgent → Specific Framework
   
   Available commands:
   ├── /biomapper-surgical → SurgicalModeAgent
   ├── /biomapper-circuitous → CircuitousFramework  
   └── /biomapper-interstitial → InterstitialFramework

**Script Pattern:**

Each command follows this pattern:

.. code-block:: python

   # Conceptual implementation - integrated with UnifiedBiomapperAgent
   from src.core.safety.unified_agent import unified_agent
   
   # Parse command and arguments
   command = "surgical"  # or "circuitous", "interstitial"
   target = "${ARGUMENT_1:-auto_detect}"
   
   # Route through unified agent
   if target != "auto_detect":
       # Direct target specification
       context = unified_agent.process_user_message(f"{command} {target}")
       result = unified_agent.execute_framework_operation("analyze")
   else:
       # Auto-detect from context
       context = unified_agent.process_user_message(f"activate {command} mode")
       result = unified_agent.execute_framework_operation("analyze")

Integration with Claude Code
----------------------------

**Automatic Invocation:**

Claude Code can invoke these commands automatically when detecting issues:

.. code-block:: python

   # Agent detects counting issue
   User: "The statistics are wrong"
   Agent: [Runs /biomapper-surgical automatically]

**Manual Invocation:**

Users can explicitly request framework activation:

.. code-block:: text

   User: "/biomapper-surgical GENERATE_MAPPING_VISUALIZATIONS"
   Agent: [Activates surgical framework for specified action]

**Context Preservation:**

Commands maintain context between invocations:

.. code-block:: python

   # Framework remembers previous analysis
   /biomapper-circuitous strategy_v1
   # ... make fixes ...
   /biomapper-circuitous  # Re-analyzes same strategy

Advanced Features
-----------------

**Verbose Mode:**

Add ``--verbose`` for detailed output:

.. code-block:: bash

   /biomapper-surgical EXPORT_DATASET --verbose

**Dry Run Mode:**

Preview changes without applying:

.. code-block:: bash

   /biomapper-interstitial --dry-run

**Export Analysis:**

Save analysis results:

.. code-block:: bash

   /biomapper-circuitous strategy_v1 --export analysis.json

Best Practices
--------------

1. **Use Auto-Detection First**
   - Let natural language trigger frameworks
   - Use commands only when needed

2. **Provide Specific Targets**
   - Include action/strategy names
   - Helps framework focus analysis

3. **Review Before Applying**
   - Check suggested changes
   - Ensure compatibility maintained

4. **Chain Commands When Needed**
   - Surgical → Interstitial for safe changes
   - Circuitous → Surgical for root causes

Common Workflows
----------------

**Workflow 1: Safe Action Update**

.. code-block:: bash

   # 1. Fix the logic
   /biomapper-surgical MY_ACTION
   
   # 2. Ensure compatibility
   /biomapper-interstitial MY_ACTION
   
   # 3. Verify pipeline
   /biomapper-circuitous my_strategy

**Workflow 2: Debug Pipeline Issue**

.. code-block:: bash

   # 1. Diagnose flow
   /biomapper-circuitous failing_strategy
   
   # 2. Fix identified action
   /biomapper-surgical PROBLEMATIC_ACTION
   
   # 3. Re-verify flow
   /biomapper-circuitous failing_strategy

**Workflow 3: API Evolution**

.. code-block:: bash

   # 1. Check current interface
   /biomapper-interstitial OLD_ACTION
   
   # 2. Apply evolution
   # ... make changes ...
   
   # 3. Ensure compatibility
   /biomapper-interstitial OLD_ACTION

Error Handling
--------------

**Common Errors:**

.. list-table:: Error Resolution
   :header-rows: 1
   :widths: 30 70

   * - Error
     - Resolution
   * - "Action not found"
     - Check ACTION_REGISTRY for valid names
   * - "Strategy file missing"
     - Verify path: src/configs/strategies/experimental/
   * - "No compatibility issues"
     - Framework working correctly - no action needed
   * - "Context missing"
     - Run in directory with biomapper source

**Debug Mode:**

Enable debug output for troubleshooting:

.. code-block:: bash

   export BIOMAPPER_DEBUG=1
   /biomapper-surgical MY_ACTION

See Also
--------

* :doc:`framework_triad` - Complete framework documentation
* :doc:`framework_triggering` - Automatic detection mechanics
* :doc:`examples` - Real-world usage scenarios
* ``src/core/safety/`` - Framework implementations

---

## Verification Sources

*Last verified: 2025-01-22*

This documentation was verified against the following project resources:

- ``/biomapper/src/core/safety/unified_agent.py`` (unified_agent global instance and command routing)
- ``/biomapper/src/core/safety/surgical_agent.py`` (SurgicalModeAgent with activate_surgical_mode)
- ``/biomapper/src/core/safety/circuitous_framework.py`` (CircuitousFramework integration)
- ``/biomapper/src/core/safety/interstitial_framework.py`` (InterstitialFramework integration)
- ``/biomapper/CLAUDE.md`` (Slash command usage patterns and integration)
- ``/biomapper/README.md`` (AI-native developer experience including commands)