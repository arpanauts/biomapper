Creating New Actions
====================

This guide walks through creating new actions for BioMapper using Test-Driven Development (TDD).

Overview
--------

BioMapper actions are self-registering components that process biological data. Each action:

* Inherits from ``TypedStrategyAction``
* Uses Pydantic models for parameters
* Self-registers via ``@register_action`` decorator
* Modifies a shared execution context

Step 1: Write Tests First (TDD)
--------------------------------

Always start by writing tests:

.. code-block:: python

   # tests/unit/core/strategy_actions/test_my_action.py
   import pytest
   from biomapper.core.strategy_actions.my_action import (
       MyAction, 
       MyActionParams
   )
   
   @pytest.mark.asyncio
   async def test_my_action_basic():
       """Test basic functionality."""
       # Arrange
       params = MyActionParams(
           input_key="test_data",
           threshold=0.8,
           output_key="filtered"
       )
       
       context = {
           "datasets": {
               "test_data": [
                   {"id": "1", "score": 0.9},
                   {"id": "2", "score": 0.7},
                   {"id": "3", "score": 0.85}
               ]
           }
       }
       
       # Act
       action = MyAction()
       result = await action.execute_typed(params, context)
       
       # Assert
       assert result.success
       assert "filtered" in context["datasets"]
       assert len(context["datasets"]["filtered"]) == 2
       
   @pytest.mark.asyncio
   async def test_my_action_validation():
       """Test parameter validation."""
       with pytest.raises(ValidationError):
           MyActionParams(
               input_key="",  # Empty key should fail
               threshold=1.5  # Out of range
           )

Step 2: Define Parameters
-------------------------

Create Pydantic models for type-safe parameters:

.. code-block:: python

   # biomapper/core/strategy_actions/my_action.py
   from pydantic import BaseModel, Field, field_validator
   from typing import Optional, List, Dict, Any
   
   class MyActionParams(BaseModel):
       """Parameters for MyAction."""
       
       input_key: str = Field(
           ...,
           description="Key to input dataset in context"
       )
       
       threshold: float = Field(
           0.8,
           ge=0.0,
           le=1.0,
           description="Score threshold for filtering"
       )
       
       output_key: str = Field(
           "filtered_output",
           description="Key for output dataset"
       )
       
       include_metadata: bool = Field(
           True,
           description="Include metadata in output"
       )
       
       @field_validator("input_key")
       @classmethod
       def validate_input_key(cls, v: str) -> str:
           if not v or not v.strip():
               raise ValueError("Input key cannot be empty")
           return v.strip()

Step 3: Implement the Action
-----------------------------

.. code-block:: python

   from biomapper.core.strategy_actions.typed_base import (
       TypedStrategyAction,
       StandardActionResult
   )
   from biomapper.core.strategy_actions.registry import register_action
   from typing import Dict, Any, List
   import logging
   
   logger = logging.getLogger(__name__)
   
   @register_action("MY_ACTION")
   class MyAction(TypedStrategyAction[MyActionParams, StandardActionResult]):
       """
       Filter biological data based on score threshold.
       
       This action filters items from an input dataset based on a 
       configurable score threshold and stores results in the context.
       
       Example:
           Input: [{"id": "A", "score": 0.9}, {"id": "B", "score": 0.6}]
           Threshold: 0.8
           Output: [{"id": "A", "score": 0.9}]
       """
       
       def get_params_model(self) -> type[MyActionParams]:
           """Return the parameters model class."""
           return MyActionParams
       
       async def execute_typed(
           self, 
           params: MyActionParams, 
           context: Dict[str, Any]
       ) -> StandardActionResult:
           """Execute the filtering action."""
           try:
               # Get input data
               if params.input_key not in context.get("datasets", {}):
                   return StandardActionResult(
                       success=False,
                       message=f"Input key '{params.input_key}' not found"
                   )
               
               input_data = context["datasets"][params.input_key]
               logger.info(f"Processing {len(input_data)} items")
               
               # Apply filtering
               filtered = [
                   item for item in input_data
                   if item.get("score", 0) >= params.threshold
               ]
               
               # Add metadata if requested
               if params.include_metadata:
                   for item in filtered:
                       item["_metadata"] = {
                           "filtered_by": "score",
                           "threshold": params.threshold
                       }
               
               # Store results
               if "datasets" not in context:
                   context["datasets"] = {}
               context["datasets"][params.output_key] = filtered
               
               # Update statistics
               if "statistics" not in context:
                   context["statistics"] = {}
               context["statistics"][params.output_key] = {
                   "total_input": len(input_data),
                   "total_output": len(filtered),
                   "filter_rate": len(filtered) / len(input_data)
               }
               
               logger.info(f"Filtered {len(input_data)} to {len(filtered)} items")
               
               return StandardActionResult(
                   success=True,
                   message=f"Filtered {len(filtered)} items with threshold {params.threshold}",
                   data={
                       "input_count": len(input_data),
                       "output_count": len(filtered),
                       "removed_count": len(input_data) - len(filtered)
                   }
               )
               
           except Exception as e:
               logger.error(f"Error in MyAction: {str(e)}")
               return StandardActionResult(
                   success=False,
                   message=f"Action failed: {str(e)}"
               )

Step 4: Choose Action Location
-------------------------------

Place your action in the appropriate directory:

.. code-block:: text

   strategy_actions/
   ├── entities/           # Entity-specific actions
   │   ├── proteins/      # Protein processing
   │   ├── metabolites/   # Metabolite processing
   │   └── chemistry/     # Clinical chemistry
   ├── utils/             # General utilities
   │   └── data_processing/
   ├── io/                # Input/output actions
   └── algorithms/        # Reusable algorithms

Step 5: Register the Action
----------------------------

The ``@register_action`` decorator automatically registers your action. No manual registration needed!

Step 6: Use in YAML Strategy
-----------------------------

.. code-block:: yaml

   name: filter_example
   description: Example using custom filter action
   
   parameters:
     input_file: "/data/scores.csv"
     score_threshold: 0.75
   
   steps:
     - name: load_data
       action:
         type: LOAD_DATASET_IDENTIFIERS
         params:
           file_path: "${parameters.input_file}"
           output_key: "raw_data"
     
     - name: filter_high_scores
       action:
         type: MY_ACTION
         params:
           input_key: "raw_data"
           threshold: "${parameters.score_threshold}"
           output_key: "high_scores"
           include_metadata: true
     
     - name: export_results
       action:
         type: EXPORT_DATASET_V2
         params:
           input_key: "high_scores"
           output_file: "/results/filtered.csv"

Best Practices
--------------

**1. Always Use TDD**
   - Write tests first
   - Test edge cases
   - Test error conditions

**2. Parameter Validation**
   - Use Pydantic Field constraints
   - Add custom validators for complex logic
   - Provide clear descriptions

**3. Error Handling**
   - Return ActionResult with success=False on errors
   - Log errors with context
   - Don't raise exceptions

**4. Documentation**
   - Add docstrings with examples
   - Document parameters clearly
   - Include usage in docstring

**5. Performance**
   - Process large datasets in chunks
   - Use efficient data structures
   - Consider memory usage

**6. Testing Checklist**
   - ✅ Unit tests pass
   - ✅ Parameter validation tested
   - ✅ Error cases handled
   - ✅ Integration with context tested
   - ✅ Performance acceptable

Common Patterns
---------------

**Reading from Context:**

.. code-block:: python

   # Safe context access
   datasets = context.get("datasets", {})
   input_data = datasets.get(params.input_key, [])

**Writing to Context:**

.. code-block:: python

   # Ensure datasets exists
   if "datasets" not in context:
       context["datasets"] = {}
   context["datasets"][params.output_key] = result

**Updating Statistics:**

.. code-block:: python

   # Track metrics
   if "statistics" not in context:
       context["statistics"] = {}
   context["statistics"][self.__class__.__name__] = {
       "processed": len(data),
       "runtime": elapsed_time
   }

**Chunked Processing:**

.. code-block:: python

   from biomapper.core.utils import chunk_list
   
   CHUNK_SIZE = 10000
   results = []
   
   for chunk in chunk_list(input_data, CHUNK_SIZE):
       chunk_result = process_chunk(chunk)
       results.extend(chunk_result)

Debugging Tips
--------------

1. **Enable Debug Logging:**

   .. code-block:: python
   
      import logging
      logging.basicConfig(level=logging.DEBUG)

2. **Test Locally First:**

   .. code-block:: bash
   
      poetry run pytest tests/unit/core/strategy_actions/test_my_action.py -xvs

3. **Use Print Debugging in Tests:**

   .. code-block:: python
   
      print(f"Context after action: {context}")
      assert result.success

4. **Check Action Registration:**

   .. code-block:: python
   
      from biomapper.core.strategy_actions.registry import ACTION_REGISTRY
      print(ACTION_REGISTRY.keys())

Need Help?
----------

* Check existing actions in ``biomapper/core/strategy_actions/``
* Review tests in ``tests/unit/core/strategy_actions/``
* See ``CLAUDE.md`` for AI assistance with development

---

Verification Sources
--------------------

*Last verified: 2025-08-13*

This documentation was verified against the following project resources:

- ``/home/ubuntu/biomapper/biomapper/core/strategy_actions/typed_base.py`` (TypedStrategyAction base class)
- ``/home/ubuntu/biomapper/biomapper/core/strategy_actions/registry.py`` (action registration system)
- ``/home/ubuntu/biomapper/biomapper/core/strategy_actions/load_dataset_identifiers.py`` (example action implementation)
- ``/home/ubuntu/biomapper/biomapper/core/models/action_results.py`` (result models)
- ``/home/ubuntu/biomapper/CLAUDE.md`` (creating actions guide)