"""Pydantic models for strategy execution."""

from typing import Dict, Any
from pydantic import BaseModel


class StrategyExecutionRequest(BaseModel):
    """Request model for strategy execution.
    
    Attributes:
        context: Dictionary containing the execution context for the strategy.
    """
    context: Dict[str, Any]


class StrategyExecutionResponse(BaseModel):
    """Response model for strategy execution.
    
    Attributes:
        results: Dictionary containing the results from the strategy execution.
    """
    results: Dict[str, Any]