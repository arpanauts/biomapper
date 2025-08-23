"""Simple v2 strategy execution routes without database dependencies."""

import logging
import uuid
from pathlib import Path
from typing import Any, Dict, Optional, Union

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field

from src.core.minimal_strategy_service import MinimalStrategyService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/strategies/v2", tags=["Strategy Execution V2"])
# Module-level logging moved to avoid initialization issues
# logger.info("strategies_v2_simple module loaded - v2 routes registered at /api/strategies/v2")


class V2ExecutionOptions(BaseModel):
    """Options for strategy execution."""

    checkpoint_enabled: bool = False
    timeout_seconds: Optional[int] = None
    max_retries: int = 3
    validate_prerequisites: bool = False


class V2StrategyExecutionRequest(BaseModel):
    """Request to execute a strategy."""

    strategy: Union[str, Dict[str, Any]] = Field(
        ..., description="Strategy name or inline strategy definition"
    )
    parameters: Dict[str, Any] = Field(
        default_factory=dict, description="Parameters to pass to the strategy"
    )
    options: V2ExecutionOptions = Field(
        default_factory=V2ExecutionOptions, description="Execution options"
    )


class V2StrategyExecutionResponse(BaseModel):
    """Response from strategy execution request."""

    job_id: str = Field(..., description="Unique job identifier")
    status: str = Field(..., description="Job status")
    message: str = Field(..., description="Status message")


# Global job storage (simple in-memory for now)
jobs: Dict[str, Dict[str, Any]] = {}


async def run_strategy_async(
    job_id: str, strategy_name: str, parameters: Dict[str, Any]
):
    """Run strategy asynchronously."""
    try:
        # Update job status
        jobs[job_id]["status"] = "running"
        logger.info(f"Starting async execution of strategy '{strategy_name}' (job_id: {job_id})")
        logger.debug(f"Parameters received: {parameters}")

        # Execute strategy
        strategies_dir = Path(__file__).parent.parent.parent / "configs" / "strategies"
        service = MinimalStrategyService(str(strategies_dir))
        
        # Properly format context with parameters
        context = {"parameters": parameters} if parameters else None
        logger.debug(f"Calling execute_strategy with context: {context}")
        
        result = await service.execute_strategy(
            strategy_name=strategy_name, context=context
        )
        
        logger.info(f"Strategy '{strategy_name}' execution completed (job_id: {job_id})")
        logger.debug(f"Result keys: {list(result.keys()) if result else 'None'}")

        # Update job with results
        jobs[job_id]["status"] = "completed"
        jobs[job_id]["result"] = result

    except Exception as e:
        logger.error(f"Strategy execution failed for job {job_id}: {e}", exc_info=True)
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)


@router.post("/execute", response_model=V2StrategyExecutionResponse)
async def execute_strategy(
    request: V2StrategyExecutionRequest, background_tasks: BackgroundTasks
) -> V2StrategyExecutionResponse:
    """
    Execute a strategy using MinimalStrategyService.

    This is a simplified v2 endpoint that works with modern YAML strategies.
    """
    try:
        logger.info(
            f"V2 endpoint hit! Request: strategy={request.strategy}, params={request.parameters}"
        )
        # Generate job ID
        job_id = str(uuid.uuid4())

        # Get strategy name
        if isinstance(request.strategy, str):
            strategy_name = request.strategy
        else:
            # For inline strategies, use a generic name
            strategy_name = request.strategy.get("name", "inline_strategy")

        # Initialize job
        jobs[job_id] = {
            "id": job_id,
            "status": "pending",
            "strategy_name": strategy_name,
            "parameters": request.parameters,
        }

        # Check if strategy exists
        strategies_dir = Path(__file__).parent.parent.parent / "configs" / "strategies"
        logger.info(f"Loading strategies from: {strategies_dir}")
        service = MinimalStrategyService(str(strategies_dir))
        logger.info(f"Loaded strategies: {list(service.strategies.keys())}")

        if strategy_name not in service.strategies:
            # Try without checking - it might be in a different location
            logger.warning(
                f"Strategy '{strategy_name}' not in loaded strategies, attempting execution anyway"
            )
        else:
            logger.info(f"Found strategy '{strategy_name}' in loaded strategies")

        # Execute in background
        background_tasks.add_task(
            run_strategy_async, job_id, strategy_name, request.parameters
        )

        return V2StrategyExecutionResponse(
            job_id=job_id,
            status="running",
            message=f"Strategy '{strategy_name}' execution started",
        )

    except Exception as e:
        logger.error(f"Failed to start strategy execution: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs/{job_id}/status")
async def get_job_status(job_id: str):
    """Get the status of a job."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    job = jobs[job_id]
    return {
        "job_id": job_id,
        "status": job["status"],
        "strategy_name": job.get("strategy_name"),
        "error": job.get("error"),
    }


@router.get("/jobs/{job_id}/results")
async def get_job_results(job_id: str):
    """Get the results of a completed job."""
    try:
        if job_id not in jobs:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

        job = jobs[job_id]
        if job["status"] != "completed":
            raise HTTPException(
                status_code=400,
                detail=f"Job {job_id} is not completed. Status: {job['status']}",
            )

        # Convert result to JSON-serializable format
        result = job.get("result", {})
        
        # Convert datasets to simple summaries (DataFrames aren't JSON serializable)
        if "datasets" in result:
            datasets_summary = {}
            for key, value in result["datasets"].items():
                if hasattr(value, "to_dict"):
                    # For DataFrames, just return row count
                    datasets_summary[key] = {"_row_count": len(value)}
                elif isinstance(value, list):
                    datasets_summary[key] = value[:100] if len(value) > 100 else value  # Limit large lists
                else:
                    datasets_summary[key] = value
            result["datasets"] = datasets_summary
        
        return result
    except Exception as e:
        # Log the error without extra kwargs that might cause issues
        import traceback
        logger.error(f"Error in get_job_results: {str(e)}")
        logger.debug(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error retrieving results: {str(e)}")
