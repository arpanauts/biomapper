"""Enhanced strategy schema with control flow support.

This module extends the basic strategy schema to support control flow constructs
while maintaining backward compatibility with existing strategies.
"""

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, field_validator, model_validator

from .control_flow import (
    EnhancedStepDefinition,
    GlobalErrorHandling,
    CheckpointingConfig,
    ExecutionConfig,
    Condition
)


class StrategyVariables(BaseModel):
    """Strategy-level variables that can be referenced in expressions."""
    
    class Config:
        extra = "allow"  # Allow arbitrary variables
    
    @field_validator('*')
    @classmethod
    def validate_variable_value(cls, v: Any) -> Any:
        """Ensure variable values are JSON-serializable."""
        import json
        try:
            json.dumps(v)
            return v
        except (TypeError, ValueError) as e:
            raise ValueError(f"Variable value must be JSON-serializable: {e}")


class StrategyParameters(BaseModel):
    """Strategy parameters that can be overridden at runtime."""
    
    class Config:
        extra = "allow"  # Allow arbitrary parameters
    
    @field_validator('*')
    @classmethod
    def validate_parameter_value(cls, v: Any) -> Any:
        """Ensure parameter values are JSON-serializable."""
        import json
        try:
            json.dumps(v)
            return v
        except (TypeError, ValueError) as e:
            raise ValueError(f"Parameter value must be JSON-serializable: {e}")


class EnhancedStrategy(BaseModel):
    """Enhanced strategy schema with control flow support."""
    
    # Basic metadata
    name: str = Field(
        ...,
        pattern="^[a-zA-Z_][a-zA-Z0-9_]*$",
        description="Strategy name"
    )
    description: Optional[str] = Field(
        None,
        description="Strategy description"
    )
    version: str = Field(
        "1.0",
        pattern="^\\d+\\.\\d+(\\.\\d+)?$",
        description="Strategy version"
    )
    tags: Optional[List[str]] = Field(
        None,
        description="Tags for categorizing strategies"
    )
    
    # Variables and parameters
    variables: Optional[Union[Dict[str, Any], StrategyVariables]] = Field(
        default_factory=dict,
        description="Strategy-level variables"
    )
    parameters: Optional[Union[Dict[str, Any], StrategyParameters]] = Field(
        default_factory=dict,
        description="Runtime parameters with defaults"
    )
    
    # Execution configuration
    execution: Optional[ExecutionConfig] = Field(
        default_factory=lambda: ExecutionConfig(mode="sequential"),
        description="Execution configuration"
    )
    error_handling: Optional[GlobalErrorHandling] = Field(
        default_factory=GlobalErrorHandling,
        description="Global error handling configuration"
    )
    checkpointing: Optional[CheckpointingConfig] = Field(
        None,
        description="Checkpointing configuration"
    )
    
    # Steps
    steps: List[Union[EnhancedStepDefinition, Dict[str, Any]]] = Field(
        ...,
        min_length=1,
        description="Strategy steps with control flow"
    )
    
    # Cleanup steps (always executed)
    finally_steps: Optional[List[EnhancedStepDefinition]] = Field(
        None,
        alias="finally",
        description="Steps to always execute at the end"
    )
    
    # Pre/post conditions
    pre_conditions: Optional[List[Union[str, Condition]]] = Field(
        None,
        description="Conditions that must be met before strategy execution"
    )
    post_conditions: Optional[List[Union[str, Condition]]] = Field(
        None,
        description="Conditions that should be met after strategy execution"
    )
    
    # Resource requirements
    requirements: Optional[Dict[str, Any]] = Field(
        None,
        description="Resource requirements (e.g., API keys, services)"
    )
    
    @field_validator('steps', mode='before')
    @classmethod
    def convert_legacy_steps(cls, v: List[Any]) -> List[Any]:
        """Convert legacy step format to enhanced format for backward compatibility."""
        converted_steps = []
        for step in v:
            if isinstance(step, dict):
                # Check if it's a legacy format (has 'action' but not new fields)
                if 'action' in step and not any(
                    key in step for key in ['condition', 'on_error', 'for_each', 'repeat']
                ):
                    # This might be a legacy step, but EnhancedStepDefinition
                    # should handle it fine
                    pass
                converted_steps.append(step)
            else:
                converted_steps.append(step)
        return converted_steps
    
    @model_validator(mode='after')
    def validate_strategy_consistency(self) -> 'EnhancedStrategy':
        """Validate overall strategy consistency."""
        # Validate step names are unique
        step_names = set()
        for step in self.steps:
            if isinstance(step, (EnhancedStepDefinition, dict)):
                name = step.name if isinstance(step, EnhancedStepDefinition) else step.get('name')
                if name:
                    if name in step_names:
                        raise ValueError(f"Duplicate step name: {name}")
                    step_names.add(name)
        
        # Validate dependencies in DAG mode
        if self.execution and self.execution.mode == "dag":
            for step in self.steps:
                if isinstance(step, EnhancedStepDefinition) and step.depends_on:
                    for dep in step.depends_on:
                        if dep not in step_names:
                            raise ValueError(f"Step '{step.name}' depends on unknown step '{dep}'")
        
        # Validate parameter references
        if self.parameters:
            param_names = set(self.parameters.keys()) if isinstance(self.parameters, dict) else set()
            # TODO: Validate that parameter references in steps are valid
        
        return self
    
    def is_control_flow_enabled(self) -> bool:
        """Check if this strategy uses any control flow features."""
        for step in self.steps:
            if isinstance(step, EnhancedStepDefinition):
                if any([
                    step.condition,
                    step.on_error,
                    step.for_each,
                    step.repeat,
                    step.parallel,
                    step.depends_on
                ]):
                    return True
            elif isinstance(step, dict):
                if any(key in step for key in [
                    'condition', 'on_error', 'for_each', 
                    'repeat', 'parallel', 'depends_on'
                ]):
                    return True
        return False
    
    def to_legacy_format(self) -> Dict[str, Any]:
        """Convert to legacy format for backward compatibility."""
        legacy = {
            "name": self.name,
            "description": self.description,
            "steps": []
        }
        
        for step in self.steps:
            if isinstance(step, EnhancedStepDefinition):
                # Convert to simple dict format
                legacy_step = {
                    "name": step.name,
                    "action": step.action
                }
                if step.description:
                    legacy_step["description"] = step.description
                legacy["steps"].append(legacy_step)
            else:
                # Already in dict format
                legacy["steps"].append({
                    "name": step.get("name"),
                    "action": step.get("action")
                })
        
        return legacy


class BackwardCompatibleStrategy(BaseModel):
    """
    A wrapper that can handle both legacy and enhanced strategy formats.
    This allows gradual migration of existing strategies.
    """
    
    # Raw strategy data
    raw_data: Dict[str, Any]
    
    # Parsed strategy (either legacy or enhanced)
    strategy: Optional[Union[EnhancedStrategy, Any]] = None
    
    @classmethod
    def from_yaml(cls, data: Dict[str, Any]) -> 'BackwardCompatibleStrategy':
        """Create strategy from YAML data, detecting format automatically."""
        instance = cls(raw_data=data)
        
        # Check if it has control flow features
        has_control_flow = False
        if 'steps' in data:
            for step in data['steps']:
                if any(key in step for key in [
                    'condition', 'on_error', 'for_each', 'repeat',
                    'parallel', 'depends_on', 'checkpoint', 'set_variables'
                ]):
                    has_control_flow = True
                    break
        
        # Also check for top-level control flow configuration
        if any(key in data for key in [
            'execution', 'error_handling', 'checkpointing',
            'variables', 'parameters', 'finally'
        ]):
            has_control_flow = True
        
        # Parse as appropriate type
        if has_control_flow:
            instance.strategy = EnhancedStrategy(**data)
        else:
            # Use legacy strategy model (assuming it exists)
            # For now, we'll just store the raw data
            instance.strategy = data
        
        return instance
    
    def is_enhanced(self) -> bool:
        """Check if this is an enhanced strategy with control flow."""
        return isinstance(self.strategy, EnhancedStrategy)
    
    def get_steps(self) -> List[Dict[str, Any]]:
        """Get steps in a uniform format."""
        if isinstance(self.strategy, EnhancedStrategy):
            return [
                step.model_dump() if isinstance(step, EnhancedStepDefinition) else step
                for step in self.strategy.steps
            ]
        elif isinstance(self.strategy, dict):
            return self.strategy.get('steps', [])
        else:
            return []