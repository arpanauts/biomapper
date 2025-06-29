# Prompt: Refactor Strategy Execution API for Full Integration

**Objective:**

Your task is to refactor the strategy execution API to fully integrate the `biomapper-api` with the core `biomapper` engine. This involves updating the API's request model, route, and service to correctly handle and pass the required parameters for executing a YAML-based strategy.

**Context:**

The API is now connected to the real `biomapper` engine, but the `execute_strategy` method in `mapper_service.py` contains a temporary implementation that returns mock data. This is because the underlying `YamlStrategyExecutionService` requires specific parameters (`source_endpoint_name`, `target_endpoint_name`, `input_identifiers`) that are not being passed through the API stack.

We will now refactor the API to properly handle these parameters, enabling a true end-to-end execution of the mapping pipeline.

--- 

### **Step 1: Update the API Request Model**

Modify the Pydantic model to include specific fields for strategy execution.

**File to Modify:** `/home/ubuntu/biomapper/biomapper-api/app/models/strategy.py`

**Instructions:**

Replace the generic `StrategyExecutionRequest` with a more specific model that includes the required parameters.

**New Code:**
```python
"""Pydantic models for strategy execution."""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel


class StrategyExecutionRequest(BaseModel):
    """Request model for strategy execution.
    
    Attributes:
        source_endpoint_name: The name of the source data endpoint.
        target_endpoint_name: The name of the target data endpoint.
        input_identifiers: A list of identifiers to be mapped.
        options: An optional dictionary for additional context and parameters.
    """
    source_endpoint_name: str
    target_endpoint_name: str
    input_identifiers: List[str]
    options: Optional[Dict[str, Any]] = None


class StrategyExecutionResponse(BaseModel):
    """Response model for strategy execution.
    
    Attributes:
        results: Dictionary containing the results from the strategy execution.
    """
    results: Dict[str, Any]
```

---

### **Step 2: Update the API Route**

Modify the API route to use the new request model and pass the parameters to the service layer.

**File to Modify:** `/home/ubuntu/biomapper/biomapper-api/app/api/routes/strategies.py`

**Instructions:**

Update the `execute_strategy` endpoint to unpack the new request model and pass the individual arguments to the `mapper_service`.

**New Code:**
```python
"""
Strategy execution API routes.
"""
from fastapi import APIRouter, Depends, HTTPException
from app.api.deps import get_mapper_service
from app.models.strategy import StrategyExecutionRequest, StrategyExecutionResponse
from app.services.mapper_service import MapperService


router = APIRouter(prefix="/api/strategies", tags=["strategies"])


@router.post("/{strategy_name}/execute", response_model=StrategyExecutionResponse)
async def execute_strategy(
    strategy_name: str,
    request: StrategyExecutionRequest,
    mapper_service: MapperService = Depends(get_mapper_service)
) -> StrategyExecutionResponse:
    """Execute a mapping strategy by name."""
    try:
        results = await mapper_service.execute_strategy(
            strategy_name=strategy_name,
            source_endpoint_name=request.source_endpoint_name,
            target_endpoint_name=request.target_endpoint_name,
            input_identifiers=request.input_identifiers,
            context=request.options
        )
        return StrategyExecutionResponse(results=results)
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail=f"Strategy '{strategy_name}' not found"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Strategy execution failed: {str(e)}"
        )
```

---

### **Step 3: Update the Mapper Service**

Modify the `MapperService` to accept the new parameters and call the real `biomapper` engine.

**File to Modify:** `/home/ubuntu/biomapper/biomapper-api/app/services/mapper_service.py`

**Instructions:**

1.  Remove the temporary `execute_yaml_strategy_direct` method.
2.  Update the `execute_strategy` method signature to accept the new parameters.
3.  Implement the call to the real `self.executor.strategy_coordinator.yaml_strategy_execution_service.execute`.

**New `execute_strategy` method:**
```python
    async def execute_strategy(
        self, 
        strategy_name: str, 
        source_endpoint_name: str,
        target_endpoint_name: str,
        input_identifiers: List[str],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Executes a named strategy with the given context using the real MappingExecutor.
        """
        await self.ensure_executor_initialized()

        if not self.strategies.get(strategy_name):
            raise HTTPException(
                status_code=404,
                detail=f"Strategy '{strategy_name}' not found."
            )

        try:
            logger.info(f"Executing strategy '{strategy_name}' with real executor...")
            
            # Execute the strategy using the appropriate service from the executor
            final_context = await self.executor.strategy_coordinator.yaml_strategy_execution_service.execute(
                strategy_name=strategy_name,
                source_endpoint_name=source_endpoint_name,
                target_endpoint_name=target_endpoint_name,
                input_identifiers=input_identifiers,
                initial_context=context
            )
            
            logger.info(f"Successfully executed strategy '{strategy_name}'.")
            return final_context

        except Exception as e:
            logger.exception(f"An error occurred during execution of strategy '{strategy_name}': {e}")
            raise HTTPException(
                status_code=500,
                detail=f"An internal error occurred while executing the strategy: {e}",
            )
```

**IMPORTANT:** Make sure to delete the now-unused `execute_yaml_strategy_direct` method from the file entirely.

---

### **Step 4: Update the Client Script**

Modify the client script to send the request payload in the new, structured format.

**File to Modify:** `/home/ubuntu/biomapper/scripts/main_pipelines/run_full_ukbb_hpa_mapping.py`

**Instructions:**

Update the `main` function to construct the JSON payload according to the new `StrategyExecutionRequest` model.

**New `json_payload` in `main` function:**
```python
    # Construct the request payload
    json_payload = {
        "source_endpoint_name": "UKBB_PROTEIN_ASSAY_ID",
        "target_endpoint_name": "HPA_GENE_NAME",
        "input_identifiers": identifiers,
        "options": {
            "some_option": "value"
        }
    }
```

---

**Verification:**

After applying all changes, run the client script:

```bash
python3 /home/ubuntu/biomapper/scripts/main_pipelines/run_full_ukbb_hpa_mapping.py
```

The output should now show the actual, complete results from the `biomapper` engine, including mapping statistics and provenance, confirming a successful end-to-end execution.
