Action System Architecture
=========================

The action system provides the core functionality for biological data processing in Biomapper.

MVP Actions
-----------

Three action types handle the majority of biological data mapping scenarios:

**LOAD_DATASET_IDENTIFIERS**
  Generic data loader supporting CSV/TSV files with flexible column mapping.

**MERGE_WITH_UNIPROT_RESOLUTION**
  Intelligent merging with historical UniProt identifier resolution.

**CALCULATE_SET_OVERLAP** 
  Comprehensive overlap analysis with Venn diagram generation.

Action Registry
---------------

Actions are automatically registered using decorators:

.. code-block:: python

    @register_action("ACTION_NAME")
    class MyAction(TypedStrategyAction):
        pass

The registry enables dynamic action loading based on YAML configuration.

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

Action Development
------------------

Creating new actions follows this pattern:

.. code-block:: python

    class MyActionParams(BaseModel):
        input_key: str
        output_key: str
        # ... other parameters
    
    @register_action("MY_ACTION")  
    class MyAction(TypedStrategyAction[MyActionParams, ActionResult]):
        
        def get_params_model(self) -> type[MyActionParams]:
            return MyActionParams
        
        async def execute_typed(
            self, 
            params: MyActionParams, 
            context: Dict[str, Any],
            source_endpoint=None,
            target_endpoint=None
        ) -> ActionResult:
            # Implementation here
            pass

Benefits
--------

* **Modularity**: Each action is self-contained
* **Reusability**: Actions work in any strategy combination  
* **Testability**: Easy to unit test individual actions
* **Extensibility**: Simple to add new action types
* **Type Safety**: Compile-time parameter validation