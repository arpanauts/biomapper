"""Control flow models for YAML strategy execution.

This module provides Pydantic models for control flow constructs in YAML strategies,
including conditions, loops, error handling, and DAG execution.
"""

from typing import Any, Dict, List, Optional, Union
from enum import Enum
from pydantic import BaseModel, Field, field_validator, model_validator


class ConditionType(str, Enum):
    """Type of condition evaluation."""
    SIMPLE = "simple"  # Single expression
    ALL = "all"  # AND logic - all conditions must be true
    ANY = "any"  # OR logic - any condition must be true


class ErrorAction(str, Enum):
    """Action to take on error."""
    STOP = "stop"  # Stop execution entirely
    CONTINUE = "continue"  # Continue to next step
    RETRY = "retry"  # Retry the failed step
    SKIP = "skip"  # Skip this step and continue


class BackoffStrategy(str, Enum):
    """Backoff strategy for retries."""
    LINEAR = "linear"  # Linear backoff (n * delay)
    EXPONENTIAL = "exponential"  # Exponential backoff (2^n * delay)


class ExecutionMode(str, Enum):
    """Execution mode for strategy steps."""
    SEQUENTIAL = "sequential"  # Execute steps in order
    DAG = "dag"  # Execute as directed acyclic graph


class CheckpointTiming(str, Enum):
    """When to create checkpoints."""
    BEFORE = "before"  # Create checkpoint before step
    AFTER = "after"  # Create checkpoint after step
    BOTH = "both"  # Create checkpoint before and after


class Condition(BaseModel):
    """Condition for step execution."""
    
    type: ConditionType = Field(
        default=ConditionType.SIMPLE,
        description="Type of condition evaluation"
    )
    expression: Optional[str] = Field(
        None,
        description="Expression for simple conditions (e.g., '${steps.baseline.score} > 0.8')"
    )
    all: Optional[List[Union[str, 'Condition']]] = Field(
        None,
        description="List of conditions that must all be true (AND logic)"
    )
    any: Optional[List[Union[str, 'Condition']]] = Field(
        None,
        description="List of conditions where any must be true (OR logic)"
    )
    
    @field_validator('expression')
    @classmethod
    def validate_expression(cls, v: Optional[str]) -> Optional[str]:
        """Validate expression syntax."""
        if v is None:
            return v
        
        # Check for basic ${...} pattern
        if not ('${' in v and '}' in v):
            raise ValueError(
                f"Expression must contain variable references using ${{...}} syntax: {v}"
            )
        
        # Check for dangerous patterns
        dangerous_patterns = ['import ', 'exec(', 'eval(', '__', 'os.', 'sys.']
        for pattern in dangerous_patterns:
            if pattern in v.lower():
                raise ValueError(f"Expression contains forbidden pattern '{pattern}'")
        
        return v
    
    @model_validator(mode='after')
    def validate_condition_structure(self) -> 'Condition':
        """Ensure condition has appropriate fields for its type."""
        if self.type == ConditionType.SIMPLE:
            if not self.expression:
                raise ValueError("Simple condition must have an expression")
            if self.all or self.any:
                raise ValueError("Simple condition cannot have 'all' or 'any' fields")
        elif self.type == ConditionType.ALL:
            if not self.all:
                raise ValueError("ALL condition must have 'all' field")
            if self.expression or self.any:
                raise ValueError("ALL condition cannot have 'expression' or 'any' fields")
        elif self.type == ConditionType.ANY:
            if not self.any:
                raise ValueError("ANY condition must have 'any' field")
            if self.expression or self.all:
                raise ValueError("ANY condition cannot have 'expression' or 'all' fields")
        return self


class ErrorHandling(BaseModel):
    """Error handling configuration for a step."""
    
    action: ErrorAction = Field(
        ...,
        description="Action to take when error occurs"
    )
    max_attempts: int = Field(
        3,
        ge=1,
        le=10,
        description="Maximum number of retry attempts"
    )
    backoff: BackoffStrategy = Field(
        BackoffStrategy.LINEAR,
        description="Backoff strategy for retries"
    )
    delay: int = Field(
        5,
        ge=1,
        le=300,
        description="Base delay in seconds between retries"
    )
    fallback: Optional[Dict[str, Any]] = Field(
        None,
        description="Fallback action if all retries fail"
    )
    message: Optional[str] = Field(
        None,
        description="Custom error message to log"
    )
    set_variable: Optional[str] = Field(
        None,
        description="Variable to set on error (e.g., 'step_failed=true')"
    )
    
    @field_validator('set_variable')
    @classmethod
    def validate_set_variable(cls, v: Optional[str]) -> Optional[str]:
        """Validate variable assignment syntax."""
        if v and '=' not in v:
            raise ValueError("set_variable must be in format 'variable_name=value'")
        return v


class LoopConfig(BaseModel):
    """Configuration for loops (for_each and repeat)."""
    
    # For for_each loops
    items: Optional[Union[str, List[Any]]] = Field(
        None,
        description="Items to iterate over (can be variable reference or literal list)"
    )
    as_variable: str = Field(
        "item",
        pattern="^[a-zA-Z_][a-zA-Z0-9_]*$",
        description="Variable name for current item"
    )
    
    # For repeat loops
    max_iterations: Optional[int] = Field(
        None,
        ge=1,
        le=1000,
        description="Maximum number of iterations"
    )
    while_condition: Optional[str] = Field(
        None,
        description="Condition to continue looping (e.g., '${metrics.score} < 0.95')"
    )
    
    @model_validator(mode='after')
    def validate_loop_type(self) -> 'LoopConfig':
        """Ensure loop has appropriate configuration."""
        if self.items is not None and (self.max_iterations or self.while_condition):
            raise ValueError("Cannot mix for_each (items) with repeat (max_iterations/while_condition)")
        if self.items is None and not (self.max_iterations or self.while_condition):
            raise ValueError("Loop must have either 'items' for for_each or 'max_iterations'/'while_condition' for repeat")
        return self


class ParallelConfig(BaseModel):
    """Configuration for parallel execution."""
    
    max_workers: int = Field(
        3,
        ge=1,
        le=10,
        description="Maximum number of parallel workers"
    )
    fail_fast: bool = Field(
        False,
        description="Stop all parallel tasks if one fails"
    )
    timeout: Optional[int] = Field(
        None,
        ge=1,
        le=3600,
        description="Timeout in seconds for parallel execution"
    )


class GlobalErrorHandling(BaseModel):
    """Global error handling configuration for entire strategy."""
    
    default: ErrorAction = Field(
        ErrorAction.STOP,
        description="Default error action for all steps"
    )
    max_retries: int = Field(
        3,
        ge=1,
        le=10,
        description="Default maximum retries for all steps"
    )
    retry_delay: int = Field(
        5,
        ge=1,
        le=300,
        description="Default retry delay in seconds"
    )
    continue_on_error: bool = Field(
        False,
        description="Whether to continue execution on unhandled errors"
    )
    error_log_level: str = Field(
        "error",
        pattern="^(debug|info|warning|error|critical)$",
        description="Logging level for errors"
    )


class CheckpointingConfig(BaseModel):
    """Checkpointing configuration for strategy execution."""
    
    enabled: bool = Field(
        False,
        description="Whether checkpointing is enabled"
    )
    strategy: str = Field(
        "after_critical_steps",
        pattern="^(after_each_step|after_critical_steps|manual)$",
        description="Checkpointing strategy"
    )
    storage: str = Field(
        "local",
        pattern="^(local|s3|database)$",
        description="Storage backend for checkpoints"
    )
    retention: str = Field(
        "7d",
        pattern="^\\d+[dhm]$",
        description="Checkpoint retention period (e.g., '7d', '24h', '30m')"
    )
    path: Optional[str] = Field(
        None,
        description="Path for checkpoint storage (local) or bucket (s3)"
    )


class ExecutionConfig(BaseModel):
    """Execution configuration for strategy."""
    
    mode: ExecutionMode = Field(
        ExecutionMode.SEQUENTIAL,
        description="Execution mode for steps"
    )
    parallel_default: Optional[ParallelConfig] = Field(
        None,
        description="Default parallel configuration when mode is DAG"
    )
    timeout: Optional[int] = Field(
        None,
        ge=1,
        le=86400,
        description="Overall timeout for strategy execution in seconds"
    )
    dry_run: bool = Field(
        False,
        description="Whether to run in dry-run mode (no actual execution)"
    )


class EnhancedStepDefinition(BaseModel):
    """Enhanced step definition with control flow support."""
    
    name: str = Field(
        ...,
        pattern="^[a-zA-Z_][a-zA-Z0-9_]*$",
        description="Unique step name"
    )
    description: Optional[str] = Field(
        None,
        description="Step description"
    )
    action: Dict[str, Any] = Field(
        ...,
        description="Action configuration with type and params"
    )
    
    # Control flow
    condition: Optional[Union[str, Condition]] = Field(
        None,
        description="Condition for step execution"
    )
    on_error: Optional[Union[ErrorAction, ErrorHandling]] = Field(
        None,
        description="Error handling for this step"
    )
    
    # Loops
    for_each: Optional[LoopConfig] = Field(
        None,
        description="For-each loop configuration"
    )
    repeat: Optional[LoopConfig] = Field(
        None,
        description="Repeat loop configuration"
    )
    
    # Parallelization
    parallel: Optional[ParallelConfig] = Field(
        None,
        description="Parallel execution configuration"
    )
    
    # Dependencies (for DAG mode)
    depends_on: Optional[List[str]] = Field(
        None,
        description="Step names this step depends on"
    )
    
    # Checkpointing
    checkpoint: Optional[CheckpointTiming] = Field(
        None,
        description="When to create checkpoint for this step"
    )
    
    # Variable manipulation
    set_variables: Optional[Dict[str, Any]] = Field(
        None,
        description="Variables to set after step execution"
    )
    
    # Step control
    is_critical: bool = Field(
        False,
        description="Whether this step is critical (failure stops execution)"
    )
    skip_if_exists: Optional[str] = Field(
        None,
        description="Skip step if this variable/file exists"
    )
    timeout: Optional[int] = Field(
        None,
        ge=1,
        le=3600,
        description="Timeout for this step in seconds"
    )
    
    @model_validator(mode='after')
    def validate_step_configuration(self) -> 'EnhancedStepDefinition':
        """Validate step configuration consistency."""
        # Cannot have both for_each and repeat
        if self.for_each and self.repeat:
            raise ValueError("Step cannot have both 'for_each' and 'repeat' configurations")
        
        # Parallel execution with loops requires special handling
        if self.parallel and (self.for_each or self.repeat):
            if self.for_each and not self.parallel.max_workers:
                raise ValueError("Parallel for_each requires max_workers configuration")
        
        # Validate action structure
        if 'type' not in self.action:
            raise ValueError("Action must have 'type' field")
        
        return self


# Update forward references
Condition.model_rebuild()