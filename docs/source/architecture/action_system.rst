Action System Architecture
==========================

The action system provides the core functionality for biological data processing in BioMapper through a self-registering, type-safe architecture.

Core Data Operations
--------------------

Fundamental actions for data loading and analysis:

**LOAD_DATASET_IDENTIFIERS**
  Generic data loader supporting CSV/TSV files with intelligent identifier handling, automatic format detection, prefix stripping, and regex-based filtering.

**MERGE_DATASETS**
  Combine multiple datasets with intelligent deduplication and conflict resolution strategies.

**FILTER_DATASET**
  Apply complex filtering criteria using Python expressions for data subsetting.

**EXPORT_DATASET**
  Export results to CSV, TSV, or JSON formats with comprehensive metadata preservation.

**CUSTOM_TRANSFORM_EXPRESSION**
  Apply Python expressions to transform data columns dynamically without code changes.

Action Registry System
----------------------

Actions self-register at import time using the ``@register_action`` decorator:

.. code-block:: python

    from actions.registry import register_action
    from actions.typed_base import TypedStrategyAction
    
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
    from actions.typed_base import TypedStrategyAction, StandardActionResult
    from actions.registry import register_action
    from typing import Dict, Any, List
    
    class MyActionParams(BaseModel):
        """Parameters for custom action with validation."""
        input_key: str = Field(..., description="Input dataset key")
        threshold: float = Field(0.8, ge=0.0, le=1.0, description="Processing threshold")
        output_key: str = Field(..., description="Output dataset key")
    
    @register_action("MY_ACTION")  
    class MyAction(TypedStrategyAction[MyActionParams, StandardActionResult]):
        """Process biological data with threshold filtering."""
        
        def get_params_model(self) -> type[MyActionParams]:
            return MyActionParams
        
        async def execute_typed(
            self, 
            params: MyActionParams, 
            context: Dict[str, Any]
        ) -> StandardActionResult:
            # Access input data from context datasets
            input_data = context.get("datasets", {}).get(params.input_key, pd.DataFrame())
            
            # Process data using pandas operations
            if not input_data.empty:
                processed = input_data[input_data["score"] >= params.threshold]
            else:
                processed = pd.DataFrame()
            
            # Store results in context
            if "datasets" not in context:
                context["datasets"] = {}
            context["datasets"][params.output_key] = processed
            
            return StandardActionResult(
                success=True,
                message=f"Processed {len(processed)} items from {len(input_data)} total",
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

**Report Actions** (``reports/``)
  * ``GENERATE_MAPPING_VISUALIZATIONS`` - Create visualization reports for mapping results
  * ``GENERATE_LLM_ANALYSIS`` - Generate AI-powered analysis reports using LLM providers

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
  * ``PARSE_COMPOSITE_IDENTIFIERS`` - Parse complex identifier formats from compound fields
  * ``CUSTOM_TRANSFORM`` - Apply custom Python expressions to transform data columns

---

## Verification Sources
*Last verified: 2025-01-18*

This documentation was verified against the following project resources:

- `/biomapper/src/actions/registry.py` (Global ACTION_REGISTRY dictionary with @register_action decorator)
- `/biomapper/src/actions/typed_base.py` (TypedStrategyAction base class with execute_typed method)
- `/biomapper/src/actions/load_dataset_identifiers.py` (LOAD_DATASET_IDENTIFIERS action implementation)
- `/biomapper/src/actions/merge_datasets.py` (MERGE_DATASETS action with deduplication logic)
- `/biomapper/src/actions/semantic_metabolite_match.py` (SEMANTIC_METABOLITE_MATCH AI-powered matching)
- `/biomapper/src/actions/reports/generate_mapping_visualizations.py` (GENERATE_MAPPING_VISUALIZATIONS action)
- `/biomapper/src/actions/reports/generate_llm_analysis.py` (GENERATE_LLM_ANALYSIS action)
- `/biomapper/src/actions/utils/data_processing/filter_dataset.py` (FILTER_DATASET action implementation)
- `/biomapper/src/actions/utils/data_processing/custom_transform_expression.py` (CUSTOM_TRANSFORM and CUSTOM_TRANSFORM_EXPRESSION actions)
- `/biomapper/src/actions/io/sync_to_google_drive_v2.py` (SYNC_TO_GOOGLE_DRIVE_V2 implementation)
- `/biomapper/CLAUDE.md` (2025 standardizations and TDD development patterns)