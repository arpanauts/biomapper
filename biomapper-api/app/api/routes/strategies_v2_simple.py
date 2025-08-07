"""Simple v2 strategy execution routes without database dependencies."""

import logging
import uuid
from typing import Any, Dict, Optional, Union

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field

from biomapper.core.minimal_strategy_service import MinimalStrategyService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/strategies/v2", tags=["Strategy Execution V2"])
logger.info(
    "strategies_v2_simple module loaded - v2 routes registered at /api/strategies/v2"
)


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

        # Execute strategy
        strategies_dir = "/home/ubuntu/biomapper/configs/strategies"
        service = MinimalStrategyService(strategies_dir)
        result = await service.execute_strategy(
            strategy_name=strategy_name, context=parameters
        )

        # Update job with results
        jobs[job_id]["status"] = "completed"
        jobs[job_id]["result"] = result

    except Exception as e:
        logger.error(f"Strategy execution failed: {e}")
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
        strategies_dir = "/home/ubuntu/biomapper/configs/strategies"
        logger.info(f"Loading strategies from: {strategies_dir}")
        service = MinimalStrategyService(strategies_dir)
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
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    job = jobs[job_id]
    if job["status"] != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Job {job_id} is not completed. Status: {job['status']}",
        )

    return job.get("result", {})
