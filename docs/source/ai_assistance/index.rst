AI-Assisted Development
========================

BioMapper features a comprehensive AI-native developer experience through the **BioMapper Framework Triad** - three specialized isolation frameworks that automatically activate based on natural language descriptions of development tasks. This system is implemented in the ``src/core/safety/`` module and provides seamless, transparent framework selection and execution.

This section documents how these frameworks work, how they're triggered, and how to use them effectively with AI agents like Claude Code.

.. note::
   The frameworks can be activated in two ways:
   
   1. **Direct activation** - Use the framework name ("surgical", "circuitous", "interstitial") anywhere in your message
   2. **Automatic detection** - Describe the problem naturally and the UnifiedBiomapperAgent will select the appropriate framework using pattern matching and confidence scoring
   
   Both methods work equally well. The unified agent uses a confidence threshold of 40% for activation.

Framework Overview
------------------

The BioMapper Framework Triad consists of three specialized frameworks:

.. list-table:: Framework Quick Reference
   :header-rows: 1
   :widths: 20 30 50

   * - Framework
     - Purpose
     - Example Trigger
   * - **🔒 Surgical**
     - Fix internal action logic
     - "The statistics are counting duplicates"
   * - **🔄 Circuitous**
     - Repair pipeline flow
     - "Parameters not passing between steps"
   * - **🔗 Interstitial**
     - Ensure compatibility
     - "New parameter broke existing strategies"

Key Concepts
------------

**Automatic Activation**
   The ``UnifiedBiomapperAgent`` detects intent from natural language using pre-compiled regex patterns and confidence scoring with keyword boosting. No explicit framework names needed.

**User-Transparent Operation**
   The frameworks operate invisibly through the ``FrameworkRouter`` - you describe problems naturally and the appropriate framework activates automatically with confidence threshold of 40%.

**100% Backward Compatibility**
   The Interstitial Framework guarantees that all interface changes maintain complete backward compatibility using automatic compatibility layers and alias mapping.

**Generic Application**
   All frameworks work with ANY action type through the ``ACTION_REGISTRY`` - they're not limited to specific biological entities or operations.

How It Works
------------

The ``UnifiedBiomapperAgent`` uses a sophisticated routing pipeline:

1. **You describe a problem** in natural language
2. **Pattern matching** - Pre-compiled regex patterns check for framework-specific triggers
3. **Confidence scoring** - Calculates match confidence with base score + keyword bonuses
4. **Ambiguity resolution** - Uses priority order: Surgical → Interstitial → Circuitous
5. **Framework activates** automatically if confidence ≥ 40%
6. **Target extraction** - Identifies specific actions/strategies from the message
7. **Fix is applied** with appropriate isolation guarantees

Example Workflow
----------------

.. code-block:: text

   User: "The protein mapping shows 3675 proteins but there are only 1172 unique ones"
   
   Agent: [FrameworkRouter detects pattern match → Confidence: 85% → Activates Surgical Framework]
          🔒 Surgical mode activated
          🎯 Target: GENERATE_MAPPING_VISUALIZATIONS (detected from ACTION_REGISTRY)
          ✅ Fixed: Now counting unique entities via df['uniprot'].nunique()
   
   User: "Make sure this doesn't break the pipeline"
   
   Agent: [Pattern matches pipeline concern → Confidence: 75% → Activates Circuitous Framework]
          🔄 Circuitous mode activated
          📋 Strategy: auto-detected from context
          ✅ Pipeline integrity validated - all interfaces preserved

Contents
--------

.. toctree::
   :maxdepth: 2
   
   framework_triad
   framework_triggering
   slash_commands
   examples

Quick Links
-----------

* :doc:`framework_triad` - Complete framework documentation
* :doc:`framework_triggering` - How automatic detection works
* :doc:`slash_commands` - Manual framework activation
* :doc:`examples` - Real-world usage scenarios

Integration with Claude Code
----------------------------

When using Claude Code with BiOMapper:

1. **Describe problems naturally** - Don't worry about framework names
2. **Trust automatic detection** - The agent will choose the right framework
3. **Provide context** - Include action/strategy names when known
4. **Review the approach** - The agent will explain which framework is active

Best Practices
--------------

* **Be specific** about the problem you're experiencing
* **Include examples** of incorrect behavior when possible
* **Mention action/strategy names** to help with targeting
* **Don't force frameworks** - let automatic detection work
* **Report misdetections** to improve pattern matching

See Also
--------

* :doc:`../architecture/overview` - System architecture
* ``src/actions/`` - Action development patterns  
* ``tests/`` - Comprehensive testing strategies
* ``src/core/safety/`` - Framework implementation
* ``CLAUDE.md`` - Development instructions

---

## Verification Sources

*Last verified: 2025-01-22*

This documentation was verified against the following project resources:

- ``/biomapper/src/core/safety/unified_agent.py`` (UnifiedBiomapperAgent implementation with FrameworkRouter)
- ``/biomapper/src/core/safety/surgical_agent.py`` (SurgicalModeAgent and AutoSurgicalFramework classes)
- ``/biomapper/src/actions/registry.py`` (ACTION_REGISTRY for target extraction)
- ``/biomapper/README.md`` (AI-native developer experience overview)
- ``/biomapper/CLAUDE.md`` (Framework triad documentation and usage patterns)
- ``/biomapper/pyproject.toml`` (Project dependencies and configuration)