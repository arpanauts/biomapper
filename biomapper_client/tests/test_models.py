"""Tests for Pydantic models."""

from datetime import datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from biomapper_client.models import (
    CheckpointInterval,
    ExecutionContext,
    ExecutionOptions,
    FileUploadRequest,
    FileUploadResponse,
    Job,
    JobStatus,
    JobStatusEnum,
    LogEntry,
    LogLevel,
    MappingJobRequest,
    ProgressEvent,
    ProgressEventType,
    StrategyExecutionRequest,
    StrategyExecutionResponse,
    StrategyInfo,
    StrategyResult,
    ValidationResult,
)


class TestEnums:
    """Test enum classes."""

    def test_job_status_enum(self):
        """Test JobStatusEnum values."""
        assert JobStatusEnum.PENDING == "pending"
        assert JobStatusEnum.RUNNING == "running"
        assert JobStatusEnum.COMPLETED == "completed"
        assert JobStatusEnum.FAILED == "failed"

    def test_log_level(self):
        """Test LogLevel values."""
        assert LogLevel.DEBUG == "DEBUG"
        assert LogLevel.INFO == "INFO"
        assert LogLevel.ERROR == "ERROR"

    def test_checkpoint_interval(self):
        """Test CheckpointInterval values."""
        assert CheckpointInterval.NEVER == "never"
        assert CheckpointInterval.AFTER_EACH_STEP == "after_each_step"

    def test_progress_event_type(self):
        """Test ProgressEventType values."""
        assert ProgressEventType.PROGRESS == "progress"
        assert ProgressEventType.LOG == "log"
        assert ProgressEventType.ERROR == "error"


class TestExecutionOptions:
    """Test ExecutionOptions model."""

    def test_default_values(self):
        """Test default values."""
        options = ExecutionOptions()

        assert options.checkpoint_enabled is False
        assert options.checkpoint_interval == CheckpointInterval.AFTER_EACH_STEP
        assert options.timeout_seconds is None
        assert options.max_retries == 3
        assert options.retry_delay_seconds == 5
        assert options.parallel_actions is True
        assert options.debug_mode is False
        assert options.output_dir is None
        assert options.preserve_intermediate is False

    def test_custom_values(self):
        """Test custom values."""
        options = ExecutionOptions(
            checkpoint_enabled=True,
            checkpoint_interval=CheckpointInterval.ON_ERROR,
            timeout_seconds=600,
            max_retries=5,
            debug_mode=True,
            output_dir="/output",
        )

        assert options.checkpoint_enabled is True
        assert options.checkpoint_interval == CheckpointInterval.ON_ERROR
        assert options.timeout_seconds == 600
        assert options.max_retries == 5
        assert options.debug_mode is True
        assert options.output_dir == "/output"


class TestStrategyExecutionRequest:
    """Test StrategyExecutionRequest model."""

    def test_minimal_request(self):
        """Test minimal request."""
        request = StrategyExecutionRequest()

        assert request.strategy_name is None
        assert request.strategy_yaml is None
        assert request.parameters == {}
        assert isinstance(request.options, ExecutionOptions)
        assert request.context == {}

    def test_with_strategy_name(self):
        """Test request with strategy name."""
        request = StrategyExecutionRequest(
            strategy_name="test_strategy",
            parameters={"param": "value"},
        )

        assert request.strategy_name == "test_strategy"
        assert request.parameters == {"param": "value"}

    def test_with_strategy_yaml(self):
        """Test request with strategy YAML."""
        strategy_yaml = {"name": "custom", "actions": []}
        request = StrategyExecutionRequest(strategy_yaml=strategy_yaml)

        assert request.strategy_yaml == strategy_yaml


class TestJob:
    """Test Job model."""

    def test_required_fields(self):
        """Test required fields."""
        job = Job(
            id="job-123",
            status=JobStatusEnum.RUNNING,
            strategy_name="test",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        assert job.id == "job-123"
        assert job.status == JobStatusEnum.RUNNING
        assert job.strategy_name == "test"
        assert job.progress_percentage == 0.0
        assert job.current_step is None
        assert job.error_message is None

    def test_optional_fields(self):
        """Test optional fields."""
        now = datetime.now()
        job = Job(
            id="job-123",
            status=JobStatusEnum.COMPLETED,
            strategy_name="test",
            created_at=now,
            updated_at=now,
            started_at=now,
            completed_at=now,
            progress_percentage=100.0,
            current_step="Final",
            total_steps=10,
            result_id="result-456",
        )

        assert job.progress_percentage == 100.0
        assert job.current_step == "Final"
        assert job.total_steps == 10
        assert job.result_id == "result-456"


class TestStrategyResult:
    """Test StrategyResult model."""

    def test_success_result(self):
        """Test successful result."""
        result = StrategyResult(
            success=True,
            job_id="job-123",
            execution_time_seconds=10.5,
            result_data={"key": "value"},
            output_files=["/path/to/output.csv"],
            statistics={"records": 100},
        )

        assert result.success is True
        assert result.job_id == "job-123"
        assert result.execution_time_seconds == 10.5
        assert result.result_data == {"key": "value"}
        assert result.output_files == ["/path/to/output.csv"]
        assert result.statistics == {"records": 100}
        assert result.error is None

    def test_failure_result(self):
        """Test failure result."""
        result = StrategyResult(
            success=False,
            job_id="job-123",
            execution_time_seconds=5.0,
            error="Something went wrong",
            warnings=["Warning 1", "Warning 2"],
        )

        assert result.success is False
        assert result.error == "Something went wrong"
        assert result.warnings == ["Warning 1", "Warning 2"]


class TestLogEntry:
    """Test LogEntry model."""

    def test_log_entry(self):
        """Test log entry creation."""
        now = datetime.now()
        entry = LogEntry(
            timestamp=now,
            level=LogLevel.INFO,
            message="Test message",
            source="test_module",
            extra_data={"key": "value"},
        )

        assert entry.timestamp == now
        assert entry.level == LogLevel.INFO
        assert entry.message == "Test message"
        assert entry.source == "test_module"
        assert entry.extra_data == {"key": "value"}


class TestProgressEvent:
    """Test ProgressEvent model."""

    def test_progress_event(self):
        """Test progress event creation."""
        now = datetime.now()
        event = ProgressEvent(
            type=ProgressEventType.PROGRESS,
            timestamp=now,
            job_id="job-123",
            step=5,
            total=10,
            percentage=50.0,
            message="Processing step 5",
            details={"current_file": "data.csv"},
        )

        assert event.type == ProgressEventType.PROGRESS
        assert event.job_id == "job-123"
        assert event.step == 5
        assert event.total == 10
        assert event.percentage == 50.0
        assert event.message == "Processing step 5"


class TestValidationResult:
    """Test ValidationResult model."""

    def test_valid_result(self):
        """Test valid validation result."""
        result = ValidationResult(is_valid=True)

        assert result.is_valid is True
        assert result.errors == []
        assert result.warnings == []
        assert result.suggestions == []

    def test_invalid_result(self):
        """Test invalid validation result."""
        result = ValidationResult(
            is_valid=False,
            errors=["Missing required field"],
            warnings=["Deprecated parameter used"],
            suggestions=["Consider using new format"],
            schema_version="1.0.0",
        )

        assert result.is_valid is False
        assert "Missing required field" in result.errors
        assert "Deprecated parameter used" in result.warnings
        assert "Consider using new format" in result.suggestions
        assert result.schema_version == "1.0.0"


class TestFileUploadResponse:
    """Test FileUploadResponse model."""

    def test_file_upload_response(self):
        """Test file upload response."""
        response = FileUploadResponse(
            session_id="sess-123",
            filename="data.csv",
            file_size=1024,
            columns=["col1", "col2"],
            row_count=100,
        )

        assert response.session_id == "sess-123"
        assert response.filename == "data.csv"
        assert response.file_size == 1024
        assert response.columns == ["col1", "col2"]
        assert response.row_count == 100


class TestExecutionContext:
    """Test ExecutionContext helper model."""

    def test_default_context(self):
        """Test default execution context."""
        context = ExecutionContext()

        assert context.parameters == {}
        assert context.files == {}
        assert isinstance(context.options, ExecutionOptions)
        assert context.metadata == {}

    def test_add_parameter(self):
        """Test adding parameters."""
        context = ExecutionContext()
        result = context.add_parameter("key", "value")

        assert result == context  # Check chaining
        assert context.parameters["key"] == "value"

    def test_add_file(self):
        """Test adding files."""
        context = ExecutionContext()

        # Test with string
        context.add_file("input1", "/path/to/file1")
        assert context.files["input1"] == "/path/to/file1"

        # Test with Path
        context.add_file("input2", Path("/path/to/file2"))
        assert context.files["input2"] == "/path/to/file2"

    def test_set_output_dir(self):
        """Test setting output directory."""
        context = ExecutionContext()

        # Test with string
        context.set_output_dir("/output")
        assert context.options.output_dir == "/output"

        # Test with Path
        context.set_output_dir(Path("/output2"))
        assert context.options.output_dir == "/output2"

    def test_enable_checkpoints(self):
        """Test enabling checkpoints."""
        context = ExecutionContext()

        # Default interval
        context.enable_checkpoints()
        assert context.options.checkpoint_enabled is True
        assert context.options.checkpoint_interval == CheckpointInterval.AFTER_EACH_STEP

        # Custom interval
        context.enable_checkpoints(CheckpointInterval.ON_ERROR)
        assert context.options.checkpoint_interval == CheckpointInterval.ON_ERROR

    def test_enable_debug(self):
        """Test enabling debug mode."""
        context = ExecutionContext()
        result = context.enable_debug()

        assert result == context  # Check chaining
        assert context.options.debug_mode is True

    def test_set_timeout(self):
        """Test setting timeout."""
        context = ExecutionContext()
        context.set_timeout(600)

        assert context.options.timeout_seconds == 600

    def test_to_request(self):
        """Test converting to request."""
        context = ExecutionContext()
        context.add_parameter("param1", "value1")
        context.add_file("input", "/file")
        context.metadata["key"] = "value"
        context.enable_checkpoints()

        request = context.to_request("test_strategy")

        assert isinstance(request, StrategyExecutionRequest)
        assert request.strategy_name == "test_strategy"
        assert request.parameters == {"param1": "value1"}
        assert request.options.checkpoint_enabled is True
        assert request.context["files"] == {"input": "/file"}
        assert request.context["metadata"] == {"key": "value"}

    def test_method_chaining(self):
        """Test that all methods support chaining."""
        context = (
            ExecutionContext()
            .add_parameter("p1", "v1")
            .add_parameter("p2", "v2")
            .add_file("f1", "/file1")
            .set_output_dir("/output")
            .enable_checkpoints()
            .enable_debug()
            .set_timeout(300)
        )

        assert context.parameters == {"p1": "v1", "p2": "v2"}
        assert context.files == {"f1": "/file1"}
        assert context.options.output_dir == "/output"
        assert context.options.checkpoint_enabled is True
        assert context.options.debug_mode is True
        assert context.options.timeout_seconds == 300


class TestStrategyInfo:
    """Test StrategyInfo model."""

    def test_strategy_info(self):
        """Test strategy info creation."""
        info = StrategyInfo(
            name="test_strategy",
            description="Test strategy description",
            version="1.0.0",
            parameters={"param1": {"type": "string", "required": True}},
            required_parameters=["param1"],
            optional_parameters=["param2"],
            actions=["LOAD_DATA", "PROCESS", "EXPORT"],
            estimated_runtime_seconds=60.0,
            tags=["metabolomics", "harmonization"],
        )

        assert info.name == "test_strategy"
        assert info.version == "1.0.0"
        assert info.required_parameters == ["param1"]
        assert info.optional_parameters == ["param2"]
        assert len(info.actions) == 3
        assert info.estimated_runtime_seconds == 60.0
        assert "metabolomics" in info.tags