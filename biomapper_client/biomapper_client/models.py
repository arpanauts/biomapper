"""Pydantic models for Biomapper client."""

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field


# Enums
class JobStatusEnum(str, Enum):
    """Job status enumeration."""

    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class LogLevel(str, Enum):
    """Log level enumeration."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class CheckpointInterval(str, Enum):
    """Checkpoint interval options."""

    NEVER = "never"
    AFTER_EACH_STEP = "after_each_step"
    AFTER_EACH_ACTION = "after_each_action"
    ON_ERROR = "on_error"


class ProgressEventType(str, Enum):
    """Progress event types."""

    PROGRESS = "progress"
    LOG = "log"
    STATUS_CHANGE = "status_change"
    ERROR = "error"
    WARNING = "warning"


# Request Models
class ExecutionOptions(BaseModel):
    """Options for strategy execution."""

    checkpoint_enabled: bool = False
    checkpoint_interval: CheckpointInterval = CheckpointInterval.AFTER_EACH_STEP
    timeout_seconds: Optional[int] = None
    max_retries: int = 3
    retry_delay_seconds: int = 5
    parallel_actions: bool = True
    debug_mode: bool = False
    output_dir: Optional[str] = None
    preserve_intermediate: bool = False


class StrategyExecutionRequest(BaseModel):
    """Strategy execution request."""

    strategy_name: Optional[str] = None
    strategy_yaml: Optional[Dict[str, Any]] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)
    options: ExecutionOptions = Field(default_factory=ExecutionOptions)
    context: Dict[str, Any] = Field(default_factory=dict)


class FileUploadRequest(BaseModel):
    """File upload request."""

    file_path: Optional[str] = None
    file_content: Optional[bytes] = None
    filename: str
    content_type: str = "text/csv"
    session_id: Optional[str] = None


class MappingJobRequest(BaseModel):
    """Mapping job request."""

    source_file: str
    source_column: str
    target_ontology: str
    mapping_strategy: Optional[str] = None
    options: Dict[str, Any] = Field(default_factory=dict)


# Response Models
class Job(BaseModel):
    """Job information."""

    id: str
    status: JobStatusEnum
    strategy_name: str
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress_percentage: float = 0.0
    current_step: Optional[str] = None
    total_steps: Optional[int] = None
    error_message: Optional[str] = None
    result_id: Optional[str] = None


class JobStatus(BaseModel):
    """Job status response."""

    job_id: str
    status: JobStatusEnum
    progress: float
    current_action: Optional[str] = None
    message: Optional[str] = None
    updated_at: datetime


class StrategyResult(BaseModel):
    """Strategy execution result."""

    success: bool
    job_id: str
    execution_time_seconds: float
    result_data: Optional[Dict[str, Any]] = None
    output_files: List[str] = Field(default_factory=list)
    statistics: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    warnings: List[str] = Field(default_factory=list)
    checkpoints: List[str] = Field(default_factory=list)


class StrategyExecutionResponse(BaseModel):
    """Strategy execution response from API."""

    job_id: str
    status: str
    message: str
    result: Optional[Dict[str, Any]] = None
    execution_time: Optional[float] = None
    error: Optional[str] = None


class LogEntry(BaseModel):
    """Log entry from job execution."""

    timestamp: datetime
    level: LogLevel
    message: str
    source: Optional[str] = None
    extra_data: Optional[Dict[str, Any]] = None


class Checkpoint(BaseModel):
    """Checkpoint information."""

    id: str
    job_id: str
    step_name: str
    created_at: datetime
    state_size_bytes: int
    is_restorable: bool = True
    metadata: Optional[Dict[str, Any]] = None


class ProgressEvent(BaseModel):
    """Progress event for streaming updates."""

    type: ProgressEventType
    timestamp: datetime
    job_id: str
    step: Optional[int] = None
    total: Optional[int] = None
    percentage: float = 0.0
    message: str
    details: Optional[Dict[str, Any]] = None


class ValidationResult(BaseModel):
    """Strategy validation result."""

    is_valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)
    schema_version: Optional[str] = None


class FileUploadResponse(BaseModel):
    """File upload response."""

    session_id: str
    filename: str
    file_size: int
    columns: Optional[List[str]] = None
    row_count: Optional[int] = None
    preview: Optional[List[Dict[str, Any]]] = None


class ColumnsResponse(BaseModel):
    """Column information response."""

    session_id: str
    columns: List[str]
    data_types: Optional[Dict[str, str]] = None
    sample_values: Optional[Dict[str, List[Any]]] = None


class CSVPreviewResponse(BaseModel):
    """CSV preview response."""

    session_id: str
    columns: List[str]
    data: List[Dict[str, Any]]
    total_rows: int
    preview_rows: int


class MappingJobResponse(BaseModel):
    """Mapping job creation response."""

    job_id: str
    status: str
    message: str
    estimated_time_seconds: Optional[float] = None


class MappingResults(BaseModel):
    """Mapping results."""

    job_id: str
    status: str
    total_records: int
    mapped_records: int
    unmapped_records: int
    mapping_rate: float
    results: List[Dict[str, Any]]
    statistics: Optional[Dict[str, Any]] = None
    output_file: Optional[str] = None


class RelationshipMappingResponse(BaseModel):
    """Relationship mapping response."""

    source_entities: List[str]
    target_entities: List[str]
    relationships: List[Dict[str, Any]]
    mapping_confidence: Dict[str, float]
    statistics: Dict[str, Any]


class EndpointResponse(BaseModel):
    """API endpoint information."""

    path: str
    method: str
    description: str
    parameters: List[Dict[str, Any]] = Field(default_factory=list)
    response_model: Optional[str] = None


class StrategyInfo(BaseModel):
    """Strategy information."""

    name: str
    description: str
    version: str
    parameters: Dict[str, Any]
    required_parameters: List[str]
    optional_parameters: List[str]
    actions: List[str]
    estimated_runtime_seconds: Optional[float] = None
    tags: List[str] = Field(default_factory=list)


# Helper Models for Client Usage
class ExecutionContext(BaseModel):
    """Helper for building execution contexts."""

    parameters: Dict[str, Any] = Field(default_factory=dict)
    files: Dict[str, str] = Field(default_factory=dict)
    options: ExecutionOptions = Field(default_factory=ExecutionOptions)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def add_parameter(self, key: str, value: Any) -> "ExecutionContext":
        """Add a parameter."""
        self.parameters[key] = value
        return self

    def add_file(self, key: str, path: Union[str, Path]) -> "ExecutionContext":
        """Add an input file."""
        self.files[key] = str(path)
        return self

    def set_output_dir(self, path: Union[str, Path]) -> "ExecutionContext":
        """Set output directory."""
        self.options.output_dir = str(path)
        return self

    def enable_checkpoints(
        self, interval: CheckpointInterval = CheckpointInterval.AFTER_EACH_STEP
    ) -> "ExecutionContext":
        """Enable checkpointing."""
        self.options.checkpoint_enabled = True
        self.options.checkpoint_interval = interval
        return self

    def enable_debug(self) -> "ExecutionContext":
        """Enable debug mode."""
        self.options.debug_mode = True
        return self

    def set_timeout(self, seconds: int) -> "ExecutionContext":
        """Set execution timeout."""
        self.options.timeout_seconds = seconds
        return self

    def to_request(self, strategy_name: str) -> StrategyExecutionRequest:
        """Convert to strategy execution request."""
        return StrategyExecutionRequest(
            strategy_name=strategy_name,
            parameters=self.parameters,
            options=self.options,
            context={
                "files": self.files,
                "metadata": self.metadata,
            },
        )
