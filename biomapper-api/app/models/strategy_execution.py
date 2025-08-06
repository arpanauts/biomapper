"""Models for enhanced strategy execution with job management."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    """Status of a strategy execution job."""
    
    PENDING = "pending"
    VALIDATING = "validating"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ExecutionOptions(BaseModel):
    """Options for strategy execution."""
    
    checkpoint_enabled: bool = Field(
        default=True, 
        description="Enable checkpointing for recovery"
    )
    checkpoint_interval: str = Field(
        default="after_each_step",
        description="When to create checkpoints: after_each_step, after_actions, manual"
    )
    progress_callback_url: Optional[str] = Field(
        default=None,
        description="URL to POST progress updates"
    )
    timeout_seconds: int = Field(
        default=3600,
        description="Maximum execution time in seconds"
    )
    retry_failed_steps: bool = Field(
        default=True,
        description="Automatically retry failed steps"
    )
    max_retries: int = Field(
        default=3,
        description="Maximum number of retries per step"
    )
    parallel_actions: bool = Field(
        default=False,
        description="Execute independent actions in parallel"
    )
    validate_prerequisites: bool = Field(
        default=True,
        description="Check prerequisites before execution"
    )


class StrategyExecutionRequest(BaseModel):
    """Request to execute a strategy."""
    
    strategy: Union[str, Dict[str, Any]] = Field(
        ...,
        description="Path to YAML file or inline strategy definition"
    )
    parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Parameters to pass to the strategy"
    )
    options: ExecutionOptions = Field(
        default_factory=ExecutionOptions,
        description="Execution options"
    )
    tags: List[str] = Field(
        default_factory=list,
        description="Tags for job organization and filtering"
    )
    description: Optional[str] = Field(
        default=None,
        description="Optional job description"
    )


class StrategyExecutionResponse(BaseModel):
    """Response from strategy execution request."""
    
    job_id: str = Field(..., description="Unique job identifier")
    status: JobStatus = Field(..., description="Initial job status")
    created_at: datetime = Field(..., description="Job creation timestamp")
    strategy_name: Optional[str] = Field(
        default=None,
        description="Name of the strategy being executed"
    )
    message: str = Field(..., description="Status message")
    estimated_duration: Optional[int] = Field(
        default=None,
        description="Estimated execution time in seconds"
    )
    websocket_url: Optional[str] = Field(
        default=None,
        description="WebSocket URL for real-time updates"
    )
    sse_url: Optional[str] = Field(
        default=None,
        description="Server-Sent Events URL for updates"
    )


class StepInfo(BaseModel):
    """Information about a strategy execution step."""
    
    name: str = Field(..., description="Step name")
    action_type: str = Field(..., description="Type of action")
    status: JobStatus = Field(..., description="Step status")
    started_at: Optional[datetime] = Field(default=None)
    completed_at: Optional[datetime] = Field(default=None)
    duration_ms: Optional[int] = Field(default=None)
    error_message: Optional[str] = Field(default=None)
    retry_count: int = Field(default=0)
    output_summary: Optional[Dict[str, Any]] = Field(default=None)


class ProgressInfo(BaseModel):
    """Progress information for a running job."""
    
    job_id: str
    status: JobStatus
    current_step: Optional[str] = Field(default=None)
    current_step_index: int = Field(default=0)
    total_steps: int = Field(default=0)
    progress_percentage: float = Field(default=0.0)
    steps: List[StepInfo] = Field(default_factory=list)
    elapsed_seconds: int = Field(default=0)
    estimated_remaining_seconds: Optional[int] = Field(default=None)
    messages: List[str] = Field(default_factory=list)
    last_updated: datetime = Field(default_factory=datetime.utcnow)


class LogEntry(BaseModel):
    """Log entry for job execution."""
    
    timestamp: datetime
    level: str  # DEBUG, INFO, WARNING, ERROR
    step_name: Optional[str] = Field(default=None)
    message: str
    details: Optional[Dict[str, Any]] = Field(default=None)


class JobResults(BaseModel):
    """Complete results from a job execution."""
    
    job_id: str
    status: JobStatus
    created_at: datetime
    started_at: Optional[datetime] = Field(default=None)
    completed_at: Optional[datetime] = Field(default=None)
    duration_seconds: Optional[float] = Field(default=None)
    strategy_name: Optional[str] = Field(default=None)
    parameters: Dict[str, Any] = Field(default_factory=dict)
    steps: List[StepInfo] = Field(default_factory=list)
    final_context: Dict[str, Any] = Field(default_factory=dict)
    output_files: List[str] = Field(default_factory=list)
    error_message: Optional[str] = Field(default=None)
    error_details: Optional[Dict[str, Any]] = Field(default=None)
    metrics: Dict[str, Any] = Field(default_factory=dict)


class StepResults(BaseModel):
    """Results from a specific step."""
    
    job_id: str
    step_name: str
    action_type: str
    status: JobStatus
    input_data: Optional[Dict[str, Any]] = Field(default=None)
    output_data: Optional[Dict[str, Any]] = Field(default=None)
    error_message: Optional[str] = Field(default=None)
    logs: List[LogEntry] = Field(default_factory=list)
    metrics: Dict[str, Any] = Field(default_factory=dict)


class Checkpoint(BaseModel):
    """Checkpoint information."""
    
    id: str = Field(..., description="Unique checkpoint identifier")
    job_id: str = Field(..., description="Associated job ID")
    step_name: str = Field(..., description="Step where checkpoint was created")
    created_at: datetime = Field(..., description="Checkpoint creation time")
    context_snapshot: Dict[str, Any] = Field(
        default_factory=dict,
        description="Snapshot of execution context"
    )
    can_resume: bool = Field(
        default=True,
        description="Whether execution can resume from this checkpoint"
    )
    size_bytes: int = Field(default=0, description="Size of checkpoint data")
    description: Optional[str] = Field(default=None)


class RestoreResponse(BaseModel):
    """Response from checkpoint restore operation."""
    
    job_id: str
    original_job_id: str
    checkpoint_id: str
    status: JobStatus
    message: str
    resumed_at_step: str
    remaining_steps: int


class CancelResponse(BaseModel):
    """Response from job cancellation."""
    
    job_id: str
    status: JobStatus
    message: str
    cancelled_at: datetime
    cleanup_performed: bool = Field(
        default=False,
        description="Whether cleanup operations were performed"
    )


class PauseResponse(BaseModel):
    """Response from job pause operation."""
    
    job_id: str
    status: JobStatus
    message: str
    paused_at: datetime
    current_step: Optional[str] = Field(default=None)
    checkpoint_created: bool = Field(default=False)
    checkpoint_id: Optional[str] = Field(default=None)


class ResumeResponse(BaseModel):
    """Response from job resume operation."""
    
    job_id: str
    status: JobStatus
    message: str
    resumed_at: datetime
    resuming_from_step: Optional[str] = Field(default=None)


class PrerequisiteCheck(BaseModel):
    """Result of a prerequisite check."""
    
    name: str = Field(..., description="Name of the check")
    category: str = Field(..., description="Category: file, directory, service, credential")
    passed: bool = Field(..., description="Whether the check passed")
    message: str = Field(..., description="Check result message")
    details: Optional[Dict[str, Any]] = Field(default=None)
    required: bool = Field(
        default=True,
        description="Whether this is a required prerequisite"
    )


class PrerequisiteReport(BaseModel):
    """Complete prerequisite check report."""
    
    all_passed: bool = Field(..., description="Whether all required checks passed")
    total_checks: int = Field(default=0)
    passed_checks: int = Field(default=0)
    failed_checks: int = Field(default=0)
    checks: List[PrerequisiteCheck] = Field(default_factory=list)
    can_proceed: bool = Field(
        default=False,
        description="Whether execution can proceed"
    )
    recommendations: List[str] = Field(
        default_factory=list,
        description="Recommendations for fixing failed checks"
    )


class JobEvent(BaseModel):
    """Event emitted during job execution."""
    
    job_id: str
    event_type: str  # progress, log, error, complete, checkpoint
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    step_name: Optional[str] = Field(default=None)
    data: Dict[str, Any] = Field(default_factory=dict)
    message: Optional[str] = Field(default=None)


class ActionInfo(BaseModel):
    """Information about an available action."""
    
    name: str = Field(..., description="Action type name")
    description: str = Field(..., description="What the action does")
    category: str = Field(..., description="Action category")
    parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Parameter schema"
    )
    required_context: List[str] = Field(
        default_factory=list,
        description="Required context keys"
    )
    produces_context: List[str] = Field(
        default_factory=list,
        description="Context keys produced"
    )
    supports_checkpoint: bool = Field(default=True)
    estimated_duration: Optional[str] = Field(default=None)
    examples: List[Dict[str, Any]] = Field(default_factory=list)