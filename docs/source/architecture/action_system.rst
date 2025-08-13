Action System Architecture
==========================

The action system provides the core functionality for biological data processing in BioMapper through a self-registering, type-safe architecture.

Core Data Operations
--------------------

Fundamental actions for data loading and analysis:

**LOAD_DATASET_IDENTIFIERS**
  Generic data loader supporting CSV/TSV files with flexible column mapping and automatic format detection.

**MERGE_DATASETS**
  Combine multiple datasets with intelligent deduplication and conflict resolution.

**FILTER_DATASET**
  Apply complex filtering criteria using Python expressions.

**EXPORT_DATASET_V2**
  Export results to CSV, TSV, or JSON formats with metadata preservation.

**CUSTOM_TRANSFORM_EXPRESSION**
  Apply Python expressions to transform data columns dynamically.

Action Registry System
----------------------

Actions self-register at import time using the ``@register_action`` decorator:

.. code-block:: python

    from biomapper.core.strategy_actions.registry import register_action
    from biomapper.core.strategy_actions.typed_base import TypedStrategyAction
    
    @register_action("ACTION_NAME")
    class MyAction(TypedStrategyAction[ParamsModel, ResultModel]):
        pass

The registry (``ACTION_REGISTRY``) is a global dictionary that enables dynamic action lookup based on YAML strategy configurations. No manual registration is required.

Type Safety
-----------

**Pydantic Models**
  All action parameters and results use Pydantic models for validation.

**TypedStrategyAction Base**
  New base class provides type-safe parameter handling.

**Backward Compatibility**
  Legacy dict-based interface maintained during migration.

Execution Context
-----------------

**Shared Dictionary**
  Actions communicate through a shared context object.

**Data Storage**
  Results stored with descriptive keys like "ukbb_proteins".

**Metadata Tracking**
  Automatic collection of execution statistics and timing.

**Error Handling**
  Comprehensive error reporting with context preservation.

Action Development Pattern
--------------------------

Follow Test-Driven Development (TDD) when creating new actions:

.. code-block:: python

    from pydantic import BaseModel, Field
    from biomapper.core.strategy_actions.typed_base import TypedStrategyAction
    from biomapper.core.strategy_actions.registry import register_action
    
    class MyActionParams(BaseModel):
        input_key: str = Field(..., description="Input dataset key")
        threshold: float = Field(0.8, ge=0.0, le=1.0, description="Processing threshold")
        output_key: str = Field(..., description="Output dataset key")
    
    @register_action("MY_ACTION")  
    class MyAction(TypedStrategyAction[MyActionParams, ActionResult]):
        """Process biological data with threshold filtering."""
        
        def get_params_model(self) -> type[MyActionParams]:
            return MyActionParams
        
        async def execute_typed(
            self, 
            params: MyActionParams, 
            context: Dict[str, Any],
            source_endpoint=None,
            target_endpoint=None
        ) -> ActionResult:
            # Access input data
            input_data = context["datasets"].get(params.input_key, [])
            
            # Process data
            processed = self._process_data(input_data, params.threshold)
            
            # Store results
            context["datasets"][params.output_key] = processed
            
            return ActionResult(
                success=True,
                message=f"Processed {len(processed)} items",
                data={"filtered_count": len(input_data) - len(processed)}
            )

Entity-Specific Actions
-----------------------

Actions are organized by biological entity type:

**Protein Actions** (``entities/proteins/``)
  * ``PROTEIN_EXTRACT_UNIPROT_FROM_XREFS`` - Extract UniProt IDs from compound fields
  * ``PROTEIN_NORMALIZE_ACCESSIONS`` - Standardize protein identifier formats
  * ``PROTEIN_MULTI_BRIDGE`` - Multi-source protein resolution
  * ``MERGE_WITH_UNIPROT_RESOLUTION`` - Historical UniProt ID mapping

**Metabolite Actions** (``entities/metabolites/``)
  * ``METABOLITE_CTS_BRIDGE`` - Chemical Translation Service integration
  * ``METABOLITE_EXTRACT_IDENTIFIERS`` - Extract metabolite IDs from text
  * ``METABOLITE_NORMALIZE_HMDB`` - Standardize HMDB formats
  * ``SEMANTIC_METABOLITE_MATCH`` - AI-powered semantic matching
  * ``VECTOR_ENHANCED_MATCH`` - Vector embedding similarity

**Chemistry Actions** (``entities/chemistry/``)
  * ``CHEMISTRY_EXTRACT_LOINC`` - Extract LOINC codes
  * ``CHEMISTRY_FUZZY_TEST_MATCH`` - Fuzzy clinical test matching
  * ``CHEMISTRY_VENDOR_HARMONIZATION`` - Harmonize vendor codes

**Analysis Actions** (``algorithms/``)
  * ``CALCULATE_SET_OVERLAP`` - Jaccard similarity with Venn diagrams
  * ``CALCULATE_THREE_WAY_OVERLAP`` - Three-dataset comparison
  * ``CALCULATE_MAPPING_QUALITY`` - Quality metrics assessment

Benefits
--------

* **Modularity**: Each action is self-contained and independently testable
* **Reusability**: Actions work in any strategy combination
* **Type Safety**: Compile-time validation with Pydantic models
* **Extensibility**: Simple to add new action types without modifying core
* **Discoverability**: Entity-based organization improves navigation
* **Error Handling**: Comprehensive validation and error reporting

---

Verification Sources
--------------------
*Last verified: 2025-08-13*

This documentation was verified against the following project resources:

* ``biomapper/core/strategy_actions/registry.py`` (Registry implementation)
* ``biomapper/core/strategy_actions/typed_base.py`` (TypedStrategyAction base)
* ``biomapper/core/strategy_actions/entities/`` (Entity-specific actions)
* ``biomapper/core/strategy_actions/io/load_dataset_identifiers.py`` (Data loader)
* ``biomapper/core/strategy_actions/data_operations/`` (Core data operations)
* ``README.md`` (Available actions list)
* ``CLAUDE.md`` (Action development patterns)