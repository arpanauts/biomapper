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
    from biomapper.core.strategy_actions.models import ActionResult
    
    @register_action("ACTION_NAME")
    class MyAction(TypedStrategyAction[ParamsModel, ActionResult]):
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
    from biomapper.core.strategy_actions.models import ActionResult
    from typing import Dict, Any
    
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
            context: Dict[str, Any]
        ) -> ActionResult:
            # Access input data
            input_data = context["datasets"].get(params.input_key, [])
            
            # Process data  
            processed = [item for item in input_data 
                        if item.get("score", 0) >= params.threshold]
            
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
  * ``METABOLITE_MULTI_BRIDGE`` - Multi-database metabolite resolution
  * ``NIGHTINGALE_NMR_MATCH`` - Nightingale NMR platform matching
  * ``SEMANTIC_METABOLITE_MATCH`` - AI-powered semantic matching
  * ``VECTOR_ENHANCED_MATCH`` - Vector embedding similarity
  * ``METABOLITE_API_ENRICHMENT`` - External API enrichment
  * ``COMBINE_METABOLITE_MATCHES`` - Merge multiple matching strategies

**Chemistry Actions** (``entities/chemistry/``)
  * ``CHEMISTRY_EXTRACT_LOINC`` - Extract LOINC codes from clinical data
  * ``CHEMISTRY_FUZZY_TEST_MATCH`` - Fuzzy matching for clinical tests
  * ``CHEMISTRY_VENDOR_HARMONIZATION`` - Harmonize vendor-specific codes
  * ``CHEMISTRY_TO_PHENOTYPE_BRIDGE`` - Link chemistry to phenotypes

**Analysis Actions** (``algorithms/``)
  * ``CALCULATE_SET_OVERLAP`` - Jaccard similarity with Venn diagrams
  * ``CALCULATE_THREE_WAY_OVERLAP`` - Three-dataset comparison
  * ``CALCULATE_MAPPING_QUALITY`` - Quality metrics assessment
  * ``GENERATE_METABOLOMICS_REPORT`` - Comprehensive metabolomics reports
  * ``GENERATE_ENHANCEMENT_REPORT`` - Validation and enhancement reports

Benefits
--------

* **Modularity**: Each action is self-contained and independently testable
* **Reusability**: Actions work in any strategy combination
* **Type Safety**: Compile-time validation with Pydantic models
* **Extensibility**: Simple to add new action types without modifying core
* **Discoverability**: Entity-based organization improves navigation
* **Error Handling**: Comprehensive validation and error reporting

**Infrastructure Actions** (``io/`` and ``utils/``)
  * ``SYNC_TO_GOOGLE_DRIVE_V2`` - Upload results to Google Drive with chunked transfer
  * ``CHUNK_PROCESSOR`` - Process large datasets in configurable chunks
  * ``BASELINE_FUZZY_MATCH`` - Fuzzy string matching utilities

---

Verification Sources
--------------------
*Last verified: 2025-08-14*

This documentation was verified against the following project resources:

- ``/biomapper/biomapper/core/strategy_actions/registry.py`` (Global ACTION_REGISTRY and register_action decorator)
- ``/biomapper/biomapper/core/strategy_actions/typed_base.py`` (TypedStrategyAction generic base class)
- ``/biomapper/biomapper/core/strategy_actions/models.py`` (ActionResult model definition)
- ``/biomapper/biomapper/core/strategy_actions/entities/`` (37 self-registering entity-specific actions)
- ``/biomapper/biomapper/core/strategy_actions/io/load_dataset_identifiers.py`` (Generic CSV/TSV data loader)
- ``/biomapper/biomapper/core/strategy_actions/data_operations/`` (Core data operations like merge and filter)
- ``/biomapper/README.md`` (Complete list of available actions)
- ``/biomapper/CLAUDE.md`` (Action development patterns and TDD approach)