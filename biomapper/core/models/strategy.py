"""Pydantic models for YAML strategy definitions."""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel


class StepAction(BaseModel):
    """Represents the action part of a strategy step."""
    type: str
    params: Optional[Dict[str, Any]] = None


class StrategyStep(BaseModel):
    """Represents a single step in a strategy."""
    name: str
    action: StepAction


class Strategy(BaseModel):
    """Represents a complete strategy with name and steps."""
    name: str
    description: Optional[str] = None
    steps: List[StrategyStep]