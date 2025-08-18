"""Tests for client models."""

import pytest
from datetime import datetime
from pathlib import Path

from pydantic import ValidationError as PydanticValidationError

from src.client.models import (
    # Enums
    JobStatusEnum,
    LogLevel,
    CheckpointInterval,
    ProgressEventType,
    
    # Request Models
    ExecutionOptions,
    StrategyExecutionRequest,
    Job,
    JobStatus,
    StrategyResult,
    ProgressEvent,
    ValidationResult,
    FileUploadResponse,
    ExecutionContext,
)


class TestEnums:
    """Test enumeration classes."""

    def test_job_status_enum_values(self):
        """Test JobStatusEnum has correct values."""
        assert JobStatusEnum.PENDING == "pending"
        assert JobStatusEnum.RUNNING == "running"
        assert JobStatusEnum.PAUSED == "paused"
        assert JobStatusEnum.COMPLETED == "completed"
        assert JobStatusEnum.FAILED == "failed"
        assert JobStatusEnum.CANCELLED == "cancelled"

    def test_job_status_enum_membership(self):
        """Test JobStatusEnum membership."""
        valid_statuses = ["pending", "running", "paused", "completed", "failed", "cancelled"]
        
        for status in valid_statuses:
            assert status in JobStatusEnum._value2member_map_
        
        assert "invalid_status" not in JobStatusEnum._value2member_map_

    def test_log_level_enum_values(self):
        """Test LogLevel has correct values."""
        assert LogLevel.DEBUG == "DEBUG"
        assert LogLevel.INFO == "INFO"
        assert LogLevel.WARNING == "WARNING"
        assert LogLevel.ERROR == "ERROR"
        assert LogLevel.CRITICAL == "CRITICAL"

    def test_checkpoint_interval_enum_values(self):
        """Test CheckpointInterval has correct values."""
        assert CheckpointInterval.NEVER == "never"
        assert CheckpointInterval.AFTER_EACH_STEP == "after_each_step"
        assert CheckpointInterval.AFTER_EACH_ACTION == "after_each_action"
        assert CheckpointInterval.ON_ERROR == "on_error"

    def test_progress_event_type_enum_values(self):
        """Test ProgressEventType has correct values."""
        assert ProgressEventType.PROGRESS == "progress"
        assert ProgressEventType.LOG == "log"
        assert ProgressEventType.STATUS_CHANGE == "status_change"
        assert ProgressEventType.ERROR == "error"
        assert ProgressEventType.WARNING == "warning"


class TestExecutionOptions:
    """Test ExecutionOptions model."""

    def test_execution_options_defaults(self):
        """Test ExecutionOptions default values."""
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

    def test_execution_options_custom_values(self):
        """Test ExecutionOptions with custom values."""
        options = ExecutionOptions(
            checkpoint_enabled=True,
            checkpoint_interval=CheckpointInterval.AFTER_EACH_ACTION,
            timeout_seconds=600,
            max_retries=5,
            retry_delay_seconds=10,
            parallel_actions=False,
            debug_mode=True,
            output_dir="/tmp/output",
            preserve_intermediate=True
        )
        
        assert options.checkpoint_enabled is True
        assert options.checkpoint_interval == CheckpointInterval.AFTER_EACH_ACTION
        assert options.timeout_seconds == 600
        assert options.max_retries == 5
        assert options.retry_delay_seconds == 10
        assert options.parallel_actions is False
        assert options.debug_mode is True
        assert options.output_dir == "/tmp/output"
        assert options.preserve_intermediate is True

    def test_execution_options_serialization(self):
        """Test ExecutionOptions serialization."""
        options = ExecutionOptions(
            checkpoint_enabled=True,
            timeout_seconds=300,
            debug_mode=True
        )
        
        data = options.dict()
        
        assert data["checkpoint_enabled"] is True
        assert data["timeout_seconds"] == 300
        assert data["debug_mode"] is True
        assert data["checkpoint_interval"] == "after_each_step"

    def test_execution_options_deserialization(self):
        """Test ExecutionOptions deserialization."""
        data = {
            "checkpoint_enabled": True,
            "checkpoint_interval": "after_each_action",
            "timeout_seconds": 600,
            "debug_mode": True
        }
        
        options = ExecutionOptions(**data)
        
        assert options.checkpoint_enabled is True
        assert options.checkpoint_interval == CheckpointInterval.AFTER_EACH_ACTION
        assert options.timeout_seconds == 600
        assert options.debug_mode is True


class TestStrategyExecutionRequest:
    """Test StrategyExecutionRequest model."""

    def test_strategy_execution_request_defaults(self):
        """Test StrategyExecutionRequest default values."""
        request = StrategyExecutionRequest()
        
        assert request.strategy_name is None
        assert request.strategy_yaml is None
        assert request.parameters == {}
        assert isinstance(request.options, ExecutionOptions)
        assert request.context == {}

    def test_strategy_execution_request_with_name(self):
        """Test StrategyExecutionRequest with strategy name."""
        request = StrategyExecutionRequest(
            strategy_name="test_strategy",
            parameters={"param1": "value1"},
            context={"key": "value"}
        )
        
        assert request.strategy_name == "test_strategy"
        assert request.strategy_yaml is None
        assert request.parameters == {"param1": "value1"}
        assert request.context == {"key": "value"}

    def test_strategy_execution_request_with_yaml(self):
        """Test StrategyExecutionRequest with strategy YAML."""
        strategy_yaml = {
            "name": "test_strategy",
            "steps": [{"action": {"type": "LOAD_DATA"}}]
        }
        
        request = StrategyExecutionRequest(
            strategy_yaml=strategy_yaml,
            parameters={"threshold": 0.8}
        )
        
        assert request.strategy_name is None
        assert request.strategy_yaml == strategy_yaml
        assert request.parameters == {"threshold": 0.8}

    def test_strategy_execution_request_serialization(self):
        """Test StrategyExecutionRequest serialization."""
        request = StrategyExecutionRequest(
            strategy_name="test_strategy",
            parameters={"param": "value"},
            options=ExecutionOptions(debug_mode=True)
        )
        
        data = request.dict()
        
        assert data["strategy_name"] == "test_strategy"
        assert data["parameters"] == {"param": "value"}
        assert data["options"]["debug_mode"] is True


class TestJob:
    """Test Job model."""

    def test_job_creation(self):
        """Test Job model creation."""
        created_at = datetime.utcnow()
        updated_at = datetime.utcnow()
        
        job = Job(
            id="job-123",
            status=JobStatusEnum.RUNNING,
            strategy_name="test_strategy",
            created_at=created_at,
            updated_at=updated_at
        )
        
        assert job.id == "job-123"
        assert job.status == JobStatusEnum.RUNNING
        assert job.strategy_name == "test_strategy"
        assert job.created_at == created_at
        assert job.updated_at == updated_at
        assert job.progress_percentage == 0.0
        assert job.current_step is None

    def test_job_with_optional_fields(self):
        """Test Job model with optional fields."""
        job = Job(
            id="job-456",
            status=JobStatusEnum.COMPLETED,
            strategy_name="metabolomics_pipeline",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            progress_percentage=100.0,
            current_step="EXPORT_RESULTS",
            total_steps=5,
            result_id="result-789"
        )
        
        assert job.progress_percentage == 100.0
        assert job.current_step == "EXPORT_RESULTS"
        assert job.total_steps == 5
        assert job.result_id == "result-789"

    def test_job_serialization(self):
        """Test Job serialization."""
        job = Job(
            id="job-123",
            status=JobStatusEnum.FAILED,
            strategy_name="test_strategy",
            created_at=datetime(2023, 1, 1, 12, 0, 0),
            updated_at=datetime(2023, 1, 1, 12, 5, 0),
            error_message="Processing failed"
        )
        
        data = job.dict()
        
        assert data["id"] == "job-123"
        assert data["status"] == "failed"
        assert data["strategy_name"] == "test_strategy"
        assert data["error_message"] == "Processing failed"

    def test_job_deserialization(self):
        """Test Job deserialization."""
        data = {
            "id": "job-789",
            "status": "completed",
            "strategy_name": "protein_mapping",
            "created_at": "2023-01-01T12:00:00",
            "updated_at": "2023-01-01T12:10:00",
            "progress_percentage": 100.0
        }
        
        job = Job(**data)
        
        assert job.id == "job-789"
        assert job.status == JobStatusEnum.COMPLETED
        assert job.progress_percentage == 100.0


class TestJobStatus:
    """Test JobStatus model."""

    def test_job_status_creation(self):
        """Test JobStatus model creation."""
        updated_at = datetime.utcnow()
        
        status = JobStatus(
            job_id="job-123",
            status=JobStatusEnum.RUNNING,
            progress=50.0,
            current_action="PROCESS_DATA",
            message="Processing data...",
            updated_at=updated_at
        )
        
        assert status.job_id == "job-123"
        assert status.status == JobStatusEnum.RUNNING
        assert status.progress == 50.0
        assert status.current_action == "PROCESS_DATA"
        assert status.message == "Processing data..."
        assert status.updated_at == updated_at

    def test_job_status_optional_fields(self):
        """Test JobStatus with optional fields."""
        status = JobStatus(
            job_id="job-456",
            status=JobStatusEnum.COMPLETED,
            progress=100.0,
            updated_at=datetime.utcnow()
        )
        
        assert status.current_action is None
        assert status.message is None

    def test_job_status_progress_validation(self):
        """Test JobStatus progress value validation."""
        # Valid progress values
        valid_progress_values = [0.0, 25.5, 50.0, 75.25, 100.0]
        
        for progress in valid_progress_values:
            status = JobStatus(
                job_id="job-test",
                status=JobStatusEnum.RUNNING,
                progress=progress,
                updated_at=datetime.utcnow()
            )
            assert status.progress == progress


class TestStrategyResult:
    """Test StrategyResult model."""

    def test_strategy_result_success(self):
        """Test successful StrategyResult."""
        result = StrategyResult(
            success=True,
            job_id="job-123",
            execution_time_seconds=125.5,
            result_data={"mapped_count": 100, "unmapped_count": 5},
            output_files=["/tmp/results.csv", "/tmp/summary.txt"],
            statistics={"total_records": 105, "mapping_rate": 0.95}
        )
        
        assert result.success is True
        assert result.job_id == "job-123"
        assert result.execution_time_seconds == 125.5
        assert result.result_data["mapped_count"] == 100
        assert len(result.output_files) == 2
        assert result.statistics["mapping_rate"] == 0.95
        assert result.error is None

    def test_strategy_result_failure(self):
        """Test failed StrategyResult."""
        result = StrategyResult(
            success=False,
            job_id="job-456",
            execution_time_seconds=30.0,
            error="File not found: /path/to/data.csv",
            warnings=["Column 'id' has missing values"]
        )
        
        assert result.success is False
        assert result.job_id == "job-456"
        assert result.error == "File not found: /path/to/data.csv"
        assert len(result.warnings) == 1
        assert result.result_data is None

    def test_strategy_result_defaults(self):
        """Test StrategyResult default values."""
        result = StrategyResult(
            success=True,
            job_id="job-789",
            execution_time_seconds=60.0
        )
        
        assert result.result_data is None
        assert result.output_files == []
        assert result.statistics is None
        assert result.error is None
        assert result.warnings == []
        assert result.checkpoints == []


class TestProgressEvent:
    """Test ProgressEvent model."""

    def test_progress_event_creation(self):
        """Test ProgressEvent creation."""
        timestamp = datetime.utcnow()
        
        event = ProgressEvent(
            type=ProgressEventType.PROGRESS,
            timestamp=timestamp,
            job_id="job-123",
            step=3,
            total=10,
            percentage=30.0,
            message="Processing step 3 of 10"
        )
        
        assert event.type == ProgressEventType.PROGRESS
        assert event.timestamp == timestamp
        assert event.job_id == "job-123"
        assert event.step == 3
        assert event.total == 10
        assert event.percentage == 30.0
        assert event.message == "Processing step 3 of 10"

    def test_progress_event_optional_fields(self):
        """Test ProgressEvent with optional fields."""
        event = ProgressEvent(
            type=ProgressEventType.LOG,
            timestamp=datetime.utcnow(),
            job_id="job-456",
            message="Log message"
        )
        
        assert event.step is None
        assert event.total is None
        assert event.percentage == 0.0
        assert event.details is None

    def test_progress_event_with_details(self):
        """Test ProgressEvent with details."""
        details = {
            "action": "LOAD_DATA",
            "file_path": "/path/to/data.csv",
            "records_processed": 1000
        }
        
        event = ProgressEvent(
            type=ProgressEventType.STATUS_CHANGE,
            timestamp=datetime.utcnow(),
            job_id="job-789",
            message="Status changed",
            details=details
        )
        
        assert event.details == details
        assert event.details["action"] == "LOAD_DATA"


class TestFileUploadResponse:
    """Test FileUploadResponse model."""

    def test_file_upload_response_creation(self):
        """Test FileUploadResponse creation."""
        response = FileUploadResponse(
            session_id="session-123",
            filename="data.csv",
            file_size=1024,
            columns=["id", "name", "value"],
            row_count=100,
            preview=[{"id": 1, "name": "test", "value": 42}]
        )
        
        assert response.session_id == "session-123"
        assert response.filename == "data.csv"
        assert response.file_size == 1024
        assert response.columns == ["id", "name", "value"]
        assert response.row_count == 100
        assert len(response.preview) == 1

    def test_file_upload_response_optional_fields(self):
        """Test FileUploadResponse with optional fields."""
        response = FileUploadResponse(
            session_id="session-456",
            filename="data.tsv",
            file_size=2048
        )
        
        assert response.columns is None
        assert response.row_count is None
        assert response.preview is None


class TestValidationResult:
    """Test ValidationResult model."""

    def test_validation_result_valid(self):
        """Test valid ValidationResult."""
        result = ValidationResult(
            is_valid=True,
            schema_version="1.0.0"
        )
        
        assert result.is_valid is True
        assert result.errors == []
        assert result.warnings == []
        assert result.suggestions == []
        assert result.schema_version == "1.0.0"

    def test_validation_result_invalid(self):
        """Test invalid ValidationResult."""
        result = ValidationResult(
            is_valid=False,
            errors=["Missing required field: strategy_name"],
            warnings=["Deprecated parameter: old_param"],
            suggestions=["Consider using new_param instead of old_param"]
        )
        
        assert result.is_valid is False
        assert len(result.errors) == 1
        assert len(result.warnings) == 1
        assert len(result.suggestions) == 1

    def test_validation_result_serialization(self):
        """Test ValidationResult serialization."""
        result = ValidationResult(
            is_valid=False,
            errors=["Error 1", "Error 2"],
            warnings=["Warning 1"]
        )
        
        data = result.dict()
        
        assert data["is_valid"] is False
        assert data["errors"] == ["Error 1", "Error 2"]
        assert data["warnings"] == ["Warning 1"]


class TestExecutionContext:
    """Test ExecutionContext helper model."""

    def test_execution_context_defaults(self):
        """Test ExecutionContext default values."""
        context = ExecutionContext()
        
        assert context.parameters == {}
        assert context.files == {}
        assert isinstance(context.options, ExecutionOptions)
        assert context.metadata == {}

    def test_execution_context_add_parameter(self):
        """Test adding parameters to ExecutionContext."""
        context = ExecutionContext()
        
        result = context.add_parameter("threshold", 0.8)
        
        assert result is context  # Method chaining
        assert context.parameters["threshold"] == 0.8

    def test_execution_context_add_file(self):
        """Test adding files to ExecutionContext."""
        context = ExecutionContext()
        
        result = context.add_file("input_data", "/path/to/data.csv")
        
        assert result is context  # Method chaining
        assert context.files["input_data"] == "/path/to/data.csv"

    def test_execution_context_add_file_pathlib(self):
        """Test adding files with pathlib.Path."""
        context = ExecutionContext()
        path = Path("/path/to/data.csv")
        
        context.add_file("input_data", path)
        
        assert context.files["input_data"] == "/path/to/data.csv"

    def test_execution_context_set_output_dir(self):
        """Test setting output directory."""
        context = ExecutionContext()
        
        result = context.set_output_dir("/tmp/output")
        
        assert result is context  # Method chaining
        assert context.options.output_dir == "/tmp/output"

    def test_execution_context_enable_checkpoints(self):
        """Test enabling checkpoints."""
        context = ExecutionContext()
        
        result = context.enable_checkpoints(CheckpointInterval.AFTER_EACH_ACTION)
        
        assert result is context  # Method chaining
        assert context.options.checkpoint_enabled is True
        assert context.options.checkpoint_interval == CheckpointInterval.AFTER_EACH_ACTION

    def test_execution_context_enable_debug(self):
        """Test enabling debug mode."""
        context = ExecutionContext()
        
        result = context.enable_debug()
        
        assert result is context  # Method chaining
        assert context.options.debug_mode is True

    def test_execution_context_set_timeout(self):
        """Test setting timeout."""
        context = ExecutionContext()
        
        result = context.set_timeout(600)
        
        assert result is context  # Method chaining
        assert context.options.timeout_seconds == 600

    def test_execution_context_to_request(self):
        """Test converting ExecutionContext to StrategyExecutionRequest."""
        context = ExecutionContext()
        context.add_parameter("param1", "value1")
        context.add_file("data", "/path/to/data.csv")
        context.enable_debug()
        context.metadata["version"] = "1.0"
        
        request = context.to_request("test_strategy")
        
        assert request.strategy_name == "test_strategy"
        assert request.parameters == {"param1": "value1"}
        assert request.options.debug_mode is True
        assert request.context["files"] == {"data": "/path/to/data.csv"}
        assert request.context["metadata"] == {"version": "1.0"}

    def test_execution_context_method_chaining(self):
        """Test ExecutionContext method chaining."""
        context = (ExecutionContext()
                  .add_parameter("threshold", 0.8)
                  .add_parameter("output_format", "csv")
                  .add_file("input", "/data/input.csv")
                  .set_output_dir("/tmp/output")
                  .enable_checkpoints()
                  .enable_debug()
                  .set_timeout(300))
        
        assert context.parameters["threshold"] == 0.8
        assert context.parameters["output_format"] == "csv"
        assert context.files["input"] == "/data/input.csv"
        assert context.options.output_dir == "/tmp/output"
        assert context.options.checkpoint_enabled is True
        assert context.options.debug_mode is True
        assert context.options.timeout_seconds == 300


class TestModelSerialization:
    """Test model serialization and deserialization."""

    def test_json_serialization_roundtrip(self):
        """Test JSON serialization round-trip."""
        original = StrategyExecutionRequest(
            strategy_name="test_strategy",
            parameters={"param": "value"},
            options=ExecutionOptions(debug_mode=True, timeout_seconds=300)
        )
        
        # Serialize to JSON
        json_data = original.json()
        
        # Deserialize from JSON
        restored = StrategyExecutionRequest.parse_raw(json_data)
        
        assert restored.strategy_name == original.strategy_name
        assert restored.parameters == original.parameters
        assert restored.options.debug_mode == original.options.debug_mode
        assert restored.options.timeout_seconds == original.options.timeout_seconds

    def test_dict_serialization_roundtrip(self):
        """Test dict serialization round-trip."""
        original = Job(
            id="job-123",
            status=JobStatusEnum.COMPLETED,
            strategy_name="test_strategy",
            created_at=datetime(2023, 1, 1, 12, 0, 0),
            updated_at=datetime(2023, 1, 1, 12, 5, 0),
            progress_percentage=100.0
        )
        
        # Serialize to dict
        data = original.dict()
        
        # Deserialize from dict
        restored = Job(**data)
        
        assert restored.id == original.id
        assert restored.status == original.status
        assert restored.strategy_name == original.strategy_name
        assert restored.progress_percentage == original.progress_percentage

    def test_nested_model_serialization(self):
        """Test serialization of models with nested models."""
        execution_options = ExecutionOptions(
            checkpoint_enabled=True,
            debug_mode=True
        )
        
        request = StrategyExecutionRequest(
            strategy_name="nested_test",
            options=execution_options
        )
        
        data = request.dict()
        
        assert data["strategy_name"] == "nested_test"
        assert data["options"]["checkpoint_enabled"] is True
        assert data["options"]["debug_mode"] is True

    def test_datetime_serialization(self):
        """Test datetime field serialization."""
        timestamp = datetime(2023, 1, 1, 12, 0, 0)
        
        event = ProgressEvent(
            type=ProgressEventType.PROGRESS,
            timestamp=timestamp,
            job_id="job-123",
            message="Test message"
        )
        
        data = event.dict()
        
        # Datetime should be serialized as ISO format string
        assert isinstance(data["timestamp"], datetime)
        
        # JSON serialization should handle datetime
        json_data = event.json()
        assert "2023-01-01T12:00:00" in json_data


class TestModelValidation:
    """Test model field validation."""

    def test_required_field_validation(self):
        """Test validation of required fields."""
        # Missing required fields should raise ValidationError
        with pytest.raises(PydanticValidationError) as exc_info:
            Job()  # Missing required fields
        
        error = exc_info.value
        field_errors = {err["loc"][0] for err in error.errors()}
        
        # Check that required fields are in the error
        required_fields = {"id", "status", "strategy_name", "created_at", "updated_at"}
        assert required_fields.issubset(field_errors)

    def test_enum_field_validation(self):
        """Test enum field validation."""
        # Valid enum value
        job = Job(
            id="job-123",
            status=JobStatusEnum.RUNNING,
            strategy_name="test",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        assert job.status == JobStatusEnum.RUNNING
        
        # Valid string enum value
        job_data = {
            "id": "job-456",
            "status": "completed",  # String value that maps to enum
            "strategy_name": "test",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        job = Job(**job_data)
        assert job.status == JobStatusEnum.COMPLETED
        
        # Invalid enum value should raise ValidationError
        with pytest.raises(PydanticValidationError):
            Job(
                id="job-789",
                status="invalid_status",
                strategy_name="test",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )

    def test_type_validation(self):
        """Test field type validation."""
        # Valid types
        options = ExecutionOptions(
            timeout_seconds=300,  # int
            debug_mode=True,      # bool
            output_dir="/tmp"     # str
        )
        
        assert options.timeout_seconds == 300
        assert options.debug_mode is True
        assert options.output_dir == "/tmp"
        
        # Invalid types should be coerced or raise ValidationError
        with pytest.raises(PydanticValidationError):
            ExecutionOptions(debug_mode="not_a_boolean")

    def test_optional_field_validation(self):
        """Test optional field handling."""
        # Optional fields can be None
        result = StrategyResult(
            success=True,
            job_id="job-123",
            execution_time_seconds=60.0,
            result_data=None,  # Optional
            error=None         # Optional
        )
        
        assert result.result_data is None
        assert result.error is None

    def test_list_field_validation(self):
        """Test list field validation."""
        # Valid list
        result = StrategyResult(
            success=True,
            job_id="job-123",
            execution_time_seconds=60.0,
            output_files=["file1.csv", "file2.txt"],
            warnings=["Warning 1", "Warning 2"]
        )
        
        assert len(result.output_files) == 2
        assert len(result.warnings) == 2
        
        # Empty list is valid
        result = StrategyResult(
            success=True,
            job_id="job-456",
            execution_time_seconds=30.0,
            output_files=[],
            warnings=[]
        )
        
        assert result.output_files == []
        assert result.warnings == []

    def test_dict_field_validation(self):
        """Test dictionary field validation."""
        # Valid dict
        request = StrategyExecutionRequest(
            strategy_name="test",
            parameters={"key1": "value1", "key2": 42},
            context={"metadata": {"version": "1.0"}}
        )
        
        assert request.parameters["key1"] == "value1"
        assert request.parameters["key2"] == 42
        assert request.context["metadata"]["version"] == "1.0"
        
        # Empty dict is valid
        request = StrategyExecutionRequest(
            parameters={},
            context={}
        )
        
        assert request.parameters == {}
        assert request.context == {}


class TestModelEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_very_long_string_fields(self):
        """Test handling of very long string values."""
        long_message = "A" * 10000  # 10k character string
        
        error_result = StrategyResult(
            success=False,
            job_id="job-123",
            execution_time_seconds=30.0,
            error=long_message
        )
        
        assert len(error_result.error) == 10000
        assert error_result.error == long_message

    def test_unicode_string_handling(self):
        """Test handling of Unicode characters."""
        unicode_message = "Test with unicode: 你好 🌟 café"
        
        event = ProgressEvent(
            type=ProgressEventType.LOG,
            timestamp=datetime.utcnow(),
            job_id="job-123",
            message=unicode_message
        )
        
        assert event.message == unicode_message

    def test_large_dict_handling(self):
        """Test handling of large dictionaries."""
        large_params = {f"param_{i}": f"value_{i}" for i in range(1000)}
        
        request = StrategyExecutionRequest(
            strategy_name="test",
            parameters=large_params
        )
        
        assert len(request.parameters) == 1000
        assert request.parameters["param_500"] == "value_500"

    def test_nested_dict_handling(self):
        """Test handling of deeply nested dictionaries."""
        nested_context = {
            "level1": {
                "level2": {
                    "level3": {
                        "level4": "deep_value"
                    }
                }
            }
        }
        
        request = StrategyExecutionRequest(
            strategy_name="test",
            context=nested_context
        )
        
        assert request.context["level1"]["level2"]["level3"]["level4"] == "deep_value"

    def test_empty_collections_handling(self):
        """Test handling of empty collections."""
        result = StrategyResult(
            success=True,
            job_id="job-123",
            execution_time_seconds=60.0,
            output_files=[],
            warnings=[],
            checkpoints=[]
        )
        
        assert result.output_files == []
        assert result.warnings == []
        assert result.checkpoints == []
        
        # Serialization should preserve empty collections
        data = result.dict()
        assert data["output_files"] == []
        assert data["warnings"] == []
        assert data["checkpoints"] == []


class TestModelCopy:
    """Test model copying and mutation."""

    def test_model_copy(self):
        """Test model copy functionality."""
        original = ExecutionOptions(
            debug_mode=True,
            timeout_seconds=300
        )
        
        copied = original.copy()
        
        assert copied.debug_mode == original.debug_mode
        assert copied.timeout_seconds == original.timeout_seconds
        assert copied is not original  # Different instances

    def test_model_copy_with_update(self):
        """Test model copy with field updates."""
        original = ExecutionOptions(
            debug_mode=False,
            timeout_seconds=300,
            max_retries=3
        )
        
        updated = original.copy(update={"debug_mode": True, "max_retries": 5})
        
        assert updated.debug_mode is True  # Updated
        assert updated.max_retries == 5    # Updated
        assert updated.timeout_seconds == 300  # Preserved
        
        # Original should be unchanged
        assert original.debug_mode is False
        assert original.max_retries == 3

    def test_deep_copy_behavior(self):
        """Test deep copy behavior with nested objects."""
        original = StrategyExecutionRequest(
            strategy_name="test",
            parameters={"nested": {"key": "value"}},
            options=ExecutionOptions(debug_mode=True)
        )
        
        copied = original.copy(deep=True)
        
        # Modify nested dict in copy
        copied.parameters["nested"]["key"] = "modified"
        
        # Original should be unchanged (deep copy)
        assert original.parameters["nested"]["key"] == "value"
        assert copied.parameters["nested"]["key"] == "modified"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])