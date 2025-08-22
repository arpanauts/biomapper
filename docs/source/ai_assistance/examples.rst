Real-World Usage Examples
==========================

This page demonstrates real-world scenarios where the BioMapper Framework Triad has been successfully applied, showing how natural language triggers automatic framework selection through the ``UnifiedBiomapperAgent`` and ``FrameworkRouter``.

Case Study 1: Protein Counting Fix
-----------------------------------

**Original Issue:** Visualization showing 3,675 proteins instead of 1,172 unique entities

**User Message:**

.. code-block:: text

   "The statistics show 3675 proteins but should show unique entities"

**Framework Detection:**

.. code-block:: text

   Pattern matches:
   - "statistics.*(show|display|count).*(wrong|incorrect|inflated|expanded)" ✓
   - "should.*show.*unique.*(entities|proteins|metabolites)" ✓
   
   Confidence: 0.85 (high)
   Framework: SURGICAL

**Solution Applied:**

.. code-block:: python

   # BEFORE (in GENERATE_MAPPING_VISUALIZATIONS action)
   total_proteins = len(df)  # Counts all rows including duplicates
   
   # AFTER (Surgical fix via SurgicalModeAgent)
   # Applied using surgical safety framework with interface preservation
   id_col = 'uniprot' if 'uniprot' in df.columns else df.columns[0]
   total_proteins = df[id_col].nunique()  # Counts unique entities only

**Result:** Statistics now correctly show 1,172 unique proteins

Case Study 2: Metabolomics Pipeline Flow
-----------------------------------------

**Original Issue:** Parameters not substituting in metabolomics strategy

**User Message:**

.. code-block:: text

   "The ${parameters.input_file} isn't being substituted in the metabolomics pipeline"

**Framework Detection:**

.. code-block:: text

   Pattern matches:
   - "\$\{.*\}.*not.*(resolv|work|substitut)" ✓
   - "parameter.*substitution.*(failing|broken|not.*work)" ✓
   
   Keywords: "parameter" (+0.1), "pipeline" (+0.1)
   Confidence: 0.75 (high)
   Framework: CIRCUITOUS

**Diagnosis:**

.. code-block:: yaml

   # Issue found in strategy YAML
   parameters:
     data_file: "/path/to/data.csv"  # Defined as 'data_file'
   
   steps:
     - name: load_data
       action:
         params:
           file_path: "${parameters.input_file}"  # Using wrong name!

**Solution:** Circuitous Framework corrected parameter reference to ``${parameters.data_file}`` via strategy flow analysis

Case Study 3: API Evolution with Compatibility
-----------------------------------------------

**Original Issue:** Need to rename parameters but maintain backward compatibility

**User Message:**

.. code-block:: text

   "We renamed dataset_key to input_key but old strategies are breaking"

**Framework Detection:**

.. code-block:: text

   Pattern matches:
   - "(new|added).*parameter.*broke.*existing" ✓
   - "backward.*compatibility.*(maintain|preserve|break)" ✓
   
   Keywords: "backward" (+0.1), "compatibility" (+0.1)
   Confidence: 0.80 (high)
   Framework: INTERSTITIAL

**Compatibility Layer Created:**

.. code-block:: python

   class ExportDatasetParams(BaseModel):
       input_key: str = Field(..., description="Input dataset key")
       
       # Compatibility layer (auto-generated)
       @validator('input_key', pre=True, always=True)
       def handle_legacy_names(cls, v, values, **kwargs):
           # Support old 'dataset_key' parameter
           if 'dataset_key' in values:
               return values['dataset_key']
           return v
       
       class Config:
           # Accept old parameter names
           extra = "allow"
           fields = {
               'input_key': {'alias': 'dataset_key'}  # Permanent alias
           }

**Result:** Both old and new strategies work without modification

Case Study 4: Complex Multi-Framework Scenario
-----------------------------------------------

**Scenario:** Complete pipeline debugging and fix

**Step 1 - User Reports Issue:**

.. code-block:: text

   User: "The protein harmonization is showing wrong coverage percentages"
   
   Agent: [Detects statistics issue]
   Framework: SURGICAL
   Action: Investigating CALCULATE_COVERAGE action

**Step 2 - Root Cause Found:**

.. code-block:: text

   Agent: "Found the issue - counting all records instead of unique proteins.
          Let me fix this surgically..."
   
   [Applies fix to counting logic]
   Result: Coverage now shows 89% (correct) instead of 245% (wrong)

**Step 3 - User Wants Verification:**

.. code-block:: text

   User: "Make sure this fix works with the full pipeline"
   
   Agent: [Detects pipeline concern]
   Framework: CIRCUITOUS
   Action: Analyzing prot_arv_to_kg2c_v3.0 strategy
   
   Result: ✅ Pipeline flow intact, all parameters passing correctly

**Step 4 - User Wants Safety:**

.. code-block:: text

   User: "Ensure this doesn't break existing integrations"
   
   Agent: [Detects compatibility concern]
   Framework: INTERSTITIAL
   Action: Validating interface compatibility
   
   Result: ✅ All interfaces preserved, 100% backward compatible

Example Conversations
---------------------

Natural Language Activation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Example 1: Surgical (Problem Description)**

.. code-block:: text

   User: "The merge is creating duplicates instead of combining unique records"
   
   Agent: I see the issue with the internal logic. Let me fix that while 
          ensuring all output formats and pipeline integration remain unchanged...
          
          🔒 Surgical mode activated
          🎯 Target: MERGE_DATASETS
          📊 Confidence: 75%

**Example 1b: Surgical (Direct Name)**

.. code-block:: text

   User: "Use surgical mode to fix the counting logic"
   
   Agent: Activating surgical framework as requested...
          
          🔒 Surgical mode activated
          🎯 Target: detected from context
          📊 Confidence: 100%

**Example 2: Circuitous (Problem Description)**

.. code-block:: text

   User: "My strategy fails at step 3 - the data from step 2 isn't available"
   
   Agent: I'll analyze the pipeline parameter flow and identify where the 
          orchestration breaks...
          
          🔄 Circuitous mode activated
          📋 Strategy: detected from context
          📊 Confidence: 82%

**Example 2b: Circuitous (Direct Name)**

.. code-block:: text

   User: "Apply circuitous analysis to the metabolomics pipeline"
   
   Agent: Activating circuitous framework for pipeline analysis...
          
          🔄 Circuitous mode activated
          📋 Strategy: metabolomics pipeline
          📊 Confidence: 100%

**Example 3: Interstitial (Problem Description)**

.. code-block:: text

   User: "We need to add a required parameter but can't break production"
   
   Agent: I'll ensure complete backward compatibility while handling the 
          interface evolution...
          
          🔗 Interstitial mode activated
          🛡️ Compatibility: 100% guaranteed
          📊 Confidence: 91%

**Example 3b: Interstitial (Direct Name)**

.. code-block:: text

   User: "Use interstitial framework to manage this API change"
   
   Agent: Activating interstitial framework for compatibility management...
          
          🔗 Interstitial mode activated
          🛡️ Compatibility: 100% guaranteed
          📊 Confidence: 100%

Edge Cases and Ambiguity
~~~~~~~~~~~~~~~~~~~~~~~~~

**Ambiguous Message:**

.. code-block:: text

   User: "Fix the parameter handling"
   
   Analysis:
   - Could be Surgical (internal parameter logic)
   - Could be Circuitous (parameter flow)
   - Could be Interstitial (parameter interface)
   
   Resolution: Priority order → SURGICAL selected
   Confidence: 0.45 (low, but above threshold)

**Too Vague:**

.. code-block:: text

   User: "Something is wrong"
   
   Analysis:
   - No patterns match
   - No keywords found
   - Confidence: 0.0
   
   Result: No framework activated
   Agent: "Could you describe what specific issue you're experiencing?"

**Multiple Issues:**

.. code-block:: text

   User: "The counting is wrong and parameters aren't flowing"
   
   Analysis:
   - Surgical patterns match (counting)
   - Circuitous patterns match (flow)
   
   Resolution: Address sequentially
   Agent: "I'll fix the counting issue first (Surgical), then verify 
          the parameter flow (Circuitous)"

Common Patterns by Domain
--------------------------

Protein Workflows
~~~~~~~~~~~~~~~~~

**Typical Surgical Triggers:**
   - "UniProt deduplication not working"
   - "Protein count inflated"
   - "Accession normalization incorrect"

**Typical Circuitous Triggers:**
   - "Protein IDs not passing to enrichment"
   - "Multi-step resolution failing"
   - "Context lost between stages"

**Typical Interstitial Triggers:**
   - "New UniProt format breaking parser"
   - "Legacy protein ID support needed"

Metabolomics Workflows
~~~~~~~~~~~~~~~~~~~~~~

**Typical Surgical Triggers:**
   - "HMDB matching logic wrong"
   - "Semantic similarity threshold issue"
   - "Vector matching overcounting"

**Typical Circuitous Triggers:**
   - "CTS enrichment not receiving IDs"
   - "Stage outputs not combining"
   - "Progressive matching broken"

**Typical Interstitial Triggers:**
   - "New metabolite ID format"
   - "API response structure changed"

Performance & Optimization
~~~~~~~~~~~~~~~~~~~~~~~~~~

**Typical Surgical Triggers:**
   - "Action taking too long"
   - "Memory usage excessive"
   - "Inefficient algorithm"

**Typical Circuitous Triggers:**
   - "Pipeline stalling at step X"
   - "Data not chunking properly"
   - "Parallel execution broken"

**Typical Interstitial Triggers:**
   - "New chunking parameter needed"
   - "Performance config evolution"

Tips for Effective Use
-----------------------

**Getting Best Results:**

1. **Be Specific About Problems**
   
   .. code-block:: text
   
      ❌ "It's broken"
      ✅ "The coverage shows 150% which is impossible"

2. **Include Context**
   
   .. code-block:: text
   
      ❌ "Fix the action"
      ✅ "Fix the counting in GENERATE_MAPPING_VISUALIZATIONS"

3. **Mention Observable Behavior**
   
   .. code-block:: text
   
      ❌ "Something seems wrong"
      ✅ "Shows 3675 but should be 1172"

4. **Describe Impact**
   
   .. code-block:: text
   
      ❌ "Parameter issue"
      ✅ "Parameter not substituting causing pipeline to fail"

**When Automatic Detection Fails:**

If the framework doesn't activate or wrong one selected:

1. Add more specific keywords
2. Describe the problem differently
3. Use slash commands for explicit control
4. Report the case for pattern improvement

See Also
--------

* :doc:`framework_triad` - Complete framework documentation
* :doc:`framework_triggering` - Detection mechanics
* :doc:`slash_commands` - Manual activation
* ``src/actions/`` - Action development patterns

---

## Verification Sources

*Last verified: 2025-01-22*

This documentation was verified against the following project resources:

- ``/biomapper/src/core/safety/unified_agent.py`` (UnifiedBiomapperAgent with framework routing examples)
- ``/biomapper/src/core/safety/surgical_agent.py`` (SurgicalModeAgent behavior patterns and responses)
- ``/biomapper/src/actions/entities/proteins/`` (Protein mapping actions like GENERATE_MAPPING_VISUALIZATIONS)
- ``/biomapper/src/configs/strategies/experimental/`` (YAML strategy patterns and parameter substitution)
- ``/biomapper/CLAUDE.md`` (Real-world usage patterns and case studies)
- ``/biomapper/README.md`` (Framework triad examples and natural language activation)