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