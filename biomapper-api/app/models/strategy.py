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