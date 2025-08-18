"""Tests for client exceptions."""

import pytest

from src.client.exceptions import (
    ApiError,
    AuthenticationError,
    BiomapperClientError,
    CheckpointError,
    ConnectionError,
    ExecutionError,
    FileUploadError,
    JobNotFoundError,
    NetworkError,
    StrategyNotFoundError,
    TimeoutError,
    ValidationError,
)


class TestBiomapperClientError:
    """Test base BiomapperClientError exception."""

    def test_base_exception_instantiation(self):
        """Test base exception can be instantiated."""
        error = BiomapperClientError("Test error message")
        
        assert str(error) == "Test error message"
        assert isinstance(error, Exception)

    def test_base_exception_inheritance(self):
        """Test that all client exceptions inherit from BiomapperClientError."""
        exceptions_to_test = [
            ConnectionError,
            AuthenticationError,
            StrategyNotFoundError,
            JobNotFoundError,
            ValidationError,
            TimeoutError,
            ExecutionError,
            ApiError,
            NetworkError,
            CheckpointError,
            FileUploadError,
        ]
        
        for exception_class in exceptions_to_test:
            if exception_class == ApiError:
                error = exception_class(500, "Test message")
            else:
                error = exception_class("Test message")
            assert isinstance(error, BiomapperClientError)
            assert isinstance(error, Exception)

    def test_base_exception_message_handling(self):
        """Test base exception message handling."""
        message = "This is a test error message"
        error = BiomapperClientError(message)
        
        assert str(error) == message
        assert error.args[0] == message


class TestConnectionError:
    """Test ConnectionError exception."""

    def test_connection_error_instantiation(self):
        """Test ConnectionError instantiation."""
        error = ConnectionError("Cannot connect to API")
        
        assert str(error) == "Cannot connect to API"
        assert isinstance(error, BiomapperClientError)

    def test_connection_error_empty_message(self):
        """Test ConnectionError with empty message."""
        error = ConnectionError("")
        
        assert str(error) == ""

    def test_connection_error_inheritance_chain(self):
        """Test ConnectionError inheritance chain."""
        error = ConnectionError("Connection failed")
        
        assert isinstance(error, ConnectionError)
        assert isinstance(error, BiomapperClientError)
        assert isinstance(error, Exception)


class TestAuthenticationError:
    """Test AuthenticationError exception."""

    def test_authentication_error_instantiation(self):
        """Test AuthenticationError instantiation."""
        error = AuthenticationError("Invalid API key")
        
        assert str(error) == "Invalid API key"
        assert isinstance(error, BiomapperClientError)

    def test_authentication_error_scenarios(self):
        """Test common authentication error scenarios."""
        scenarios = [
            "Invalid API key",
            "Token expired",
            "Authentication required",
            "Access denied",
        ]
        
        for scenario in scenarios:
            error = AuthenticationError(scenario)
            assert str(error) == scenario
            assert isinstance(error, BiomapperClientError)


class TestStrategyNotFoundError:
    """Test StrategyNotFoundError exception."""

    def test_strategy_not_found_error_instantiation(self):
        """Test StrategyNotFoundError instantiation."""
        strategy_name = "nonexistent_strategy"
        error = StrategyNotFoundError(f"Strategy not found: {strategy_name}")
        
        assert "Strategy not found: nonexistent_strategy" in str(error)
        assert isinstance(error, BiomapperClientError)

    def test_strategy_not_found_error_with_strategy_name(self):
        """Test StrategyNotFoundError with various strategy names."""
        strategy_names = [
            "metabolomics_baseline",
            "protein_mapping",
            "custom_strategy_123",
            "strategy-with-dashes",
        ]
        
        for name in strategy_names:
            error = StrategyNotFoundError(f"Strategy '{name}' not found")
            assert name in str(error)
            assert isinstance(error, BiomapperClientError)


class TestJobNotFoundError:
    """Test JobNotFoundError exception."""

    def test_job_not_found_error_instantiation(self):
        """Test JobNotFoundError instantiation."""
        job_id = "job-123-456"
        error = JobNotFoundError(f"Job not found: {job_id}")
        
        assert "Job not found: job-123-456" in str(error)
        assert isinstance(error, BiomapperClientError)

    def test_job_not_found_error_with_various_ids(self):
        """Test JobNotFoundError with various job ID formats."""
        job_ids = [
            "job-123",
            "uuid-4a2b8c9d-1234-5678-9abc-def123456789",
            "short_id",
            "job_with_underscores_123",
        ]
        
        for job_id in job_ids:
            error = JobNotFoundError(f"Job '{job_id}' does not exist")
            assert job_id in str(error)
            assert isinstance(error, BiomapperClientError)


class TestValidationError:
    """Test ValidationError exception."""

    def test_validation_error_instantiation(self):
        """Test ValidationError instantiation."""
        error = ValidationError("Invalid parameter format")
        
        assert str(error) == "Invalid parameter format"
        assert isinstance(error, BiomapperClientError)

    def test_validation_error_scenarios(self):
        """Test common validation error scenarios."""
        scenarios = [
            "Missing required parameter: strategy_name",
            "Invalid parameter type: expected str, got int",
            "Parameter value out of range: threshold must be between 0 and 1",
            "Invalid file format: expected CSV or TSV",
            "Empty required field: identifier_column",
        ]
        
        for scenario in scenarios:
            error = ValidationError(scenario)
            assert str(error) == scenario
            assert isinstance(error, BiomapperClientError)


class TestTimeoutError:
    """Test TimeoutError exception."""

    def test_timeout_error_instantiation(self):
        """Test TimeoutError instantiation."""
        error = TimeoutError("Operation timed out after 300 seconds")
        
        assert "Operation timed out after 300 seconds" in str(error)
        assert isinstance(error, BiomapperClientError)

    def test_timeout_error_with_duration(self):
        """Test TimeoutError with various timeout durations."""
        durations = [30, 60, 300, 600, 1800]
        
        for duration in durations:
            error = TimeoutError(f"Request timed out after {duration} seconds")
            assert str(duration) in str(error)
            assert "timed out" in str(error)
            assert isinstance(error, BiomapperClientError)

    def test_timeout_error_custom_messages(self):
        """Test TimeoutError with custom timeout messages."""
        messages = [
            "Connection timeout",
            "Read timeout",
            "Strategy execution timeout",
            "Job polling timeout",
        ]
        
        for message in messages:
            error = TimeoutError(message)
            assert str(error) == message
            assert isinstance(error, BiomapperClientError)


class TestExecutionError:
    """Test ExecutionError exception."""

    def test_execution_error_instantiation(self):
        """Test ExecutionError instantiation without details."""
        error = ExecutionError("Strategy execution failed")
        
        assert str(error) == "Strategy execution failed"
        assert error.details == {}
        assert isinstance(error, BiomapperClientError)

    def test_execution_error_with_details(self):
        """Test ExecutionError instantiation with details."""
        details = {
            "step": "LOAD_DATA",
            "action": "load_dataset_identifiers",
            "error_code": "E001",
            "file_path": "/path/to/data.csv"
        }
        
        error = ExecutionError("Data loading failed", details=details)
        
        assert str(error) == "Data loading failed"
        assert error.details == details
        assert error.details["step"] == "LOAD_DATA"
        assert error.details["error_code"] == "E001"

    def test_execution_error_details_default(self):
        """Test ExecutionError details default to empty dict."""
        error = ExecutionError("Execution failed")
        
        assert isinstance(error.details, dict)
        assert len(error.details) == 0

    def test_execution_error_details_none_handling(self):
        """Test ExecutionError handles None details gracefully."""
        error = ExecutionError("Execution failed", details=None)
        
        assert error.details == {}
        assert isinstance(error.details, dict)

    def test_execution_error_complex_details(self):
        """Test ExecutionError with complex details structure."""
        details = {
            "execution_context": {
                "strategy_name": "metabolomics_pipeline",
                "step_index": 3,
                "total_steps": 10,
            },
            "error_info": {
                "exception_type": "FileNotFoundError",
                "traceback": ["line 1", "line 2", "line 3"],
            },
            "input_data": {
                "file_count": 5,
                "total_records": 1000,
            }
        }
        
        error = ExecutionError("Complex execution failure", details=details)
        
        assert error.details["execution_context"]["strategy_name"] == "metabolomics_pipeline"
        assert error.details["error_info"]["exception_type"] == "FileNotFoundError"
        assert error.details["input_data"]["total_records"] == 1000


class TestApiError:
    """Test ApiError exception."""

    def test_api_error_instantiation(self):
        """Test ApiError instantiation."""
        error = ApiError(500, "Internal server error")
        
        assert error.status_code == 500
        assert error.message == "Internal server error"
        assert error.details == {}
        assert "API Error (500): Internal server error" in str(error)

    def test_api_error_with_details(self):
        """Test ApiError with details."""
        details = {
            "request_id": "req-123",
            "timestamp": "2023-01-01T00:00:00Z",
            "endpoint": "/api/strategies/execute"
        }
        
        error = ApiError(400, "Bad request", details=details)
        
        assert error.status_code == 400
        assert error.message == "Bad request"
        assert error.details == details
        assert error.details["request_id"] == "req-123"

    def test_api_error_various_status_codes(self):
        """Test ApiError with various HTTP status codes."""
        status_codes = [400, 401, 403, 404, 429, 500, 502, 503, 504]
        
        for status_code in status_codes:
            error = ApiError(status_code, f"HTTP {status_code} error")
            
            assert error.status_code == status_code
            assert str(status_code) in str(error)
            assert f"HTTP {status_code} error" in str(error)

    def test_api_error_details_default(self):
        """Test ApiError details default to empty dict."""
        error = ApiError(500, "Server error")
        
        assert isinstance(error.details, dict)
        assert len(error.details) == 0

    def test_api_error_details_none_handling(self):
        """Test ApiError handles None details gracefully."""
        error = ApiError(400, "Bad request", details=None)
        
        assert error.details == {}
        assert isinstance(error.details, dict)

    def test_api_error_string_representation(self):
        """Test ApiError string representation format."""
        error = ApiError(404, "Resource not found")
        
        expected = "API Error (404): Resource not found"
        assert str(error) == expected

    def test_api_error_attribute_access(self):
        """Test ApiError attribute access."""
        error = ApiError(422, "Validation failed", {"field": "value"})
        
        assert hasattr(error, "status_code")
        assert hasattr(error, "message")
        assert hasattr(error, "details")
        
        assert error.status_code == 422
        assert error.message == "Validation failed"
        assert error.details["field"] == "value"


class TestNetworkError:
    """Test NetworkError exception."""

    def test_network_error_instantiation(self):
        """Test NetworkError instantiation."""
        error = NetworkError("Connection refused")
        
        assert str(error) == "Connection refused"
        assert isinstance(error, BiomapperClientError)

    def test_network_error_scenarios(self):
        """Test common network error scenarios."""
        scenarios = [
            "Connection timeout",
            "DNS resolution failed",
            "Connection refused",
            "Network unreachable",
            "SSL certificate verification failed",
            "Proxy connection failed",
        ]
        
        for scenario in scenarios:
            error = NetworkError(scenario)
            assert str(error) == scenario
            assert isinstance(error, BiomapperClientError)


class TestCheckpointError:
    """Test CheckpointError exception."""

    def test_checkpoint_error_instantiation(self):
        """Test CheckpointError instantiation."""
        error = CheckpointError("Failed to save checkpoint")
        
        assert str(error) == "Failed to save checkpoint"
        assert isinstance(error, BiomapperClientError)

    def test_checkpoint_error_scenarios(self):
        """Test common checkpoint error scenarios."""
        scenarios = [
            "Checkpoint file not found",
            "Failed to save checkpoint",
            "Failed to restore from checkpoint",
            "Checkpoint data corrupted",
            "Invalid checkpoint format",
        ]
        
        for scenario in scenarios:
            error = CheckpointError(scenario)
            assert str(error) == scenario
            assert isinstance(error, BiomapperClientError)


class TestFileUploadError:
    """Test FileUploadError exception."""

    def test_file_upload_error_instantiation(self):
        """Test FileUploadError instantiation."""
        error = FileUploadError("File upload failed")
        
        assert str(error) == "File upload failed"
        assert isinstance(error, BiomapperClientError)

    def test_file_upload_error_scenarios(self):
        """Test common file upload error scenarios."""
        scenarios = [
            "File not found: /path/to/file.csv",
            "File too large: maximum size is 100MB",
            "Invalid file format: expected CSV or TSV",
            "Upload interrupted: network connection lost",
            "Permission denied: cannot read file",
        ]
        
        for scenario in scenarios:
            error = FileUploadError(scenario)
            assert str(error) == scenario
            assert isinstance(error, BiomapperClientError)


class TestExceptionChaining:
    """Test exception chaining and context preservation."""

    def test_exception_chaining_with_cause(self):
        """Test exception chaining with __cause__."""
        original_error = ValueError("Original error")
        
        try:
            raise original_error
        except ValueError as e:
            client_error = BiomapperClientError("Client error")
            client_error.__cause__ = e
            
            assert client_error.__cause__ is original_error
            assert str(client_error) == "Client error"

    def test_exception_chaining_with_context(self):
        """Test exception chaining with __context__."""
        client_error = None
        try:
            raise ValueError("First error")
        except ValueError:
            try:
                raise KeyError("Second error")
            except KeyError:
                client_error = BiomapperClientError("Final error")
        
        # For this test, we just verify the error was created properly
        assert client_error is not None
        assert str(client_error) == "Final error"

    def test_nested_exception_handling(self):
        """Test handling of nested exceptions."""
        def raise_api_error():
            try:
                raise ConnectionError("Network failed")
            except ConnectionError as e:
                raise ApiError(500, "Server error") from e
        
        with pytest.raises(ApiError) as exc_info:
            raise_api_error()
        
        api_error = exc_info.value
        assert api_error.status_code == 500
        assert isinstance(api_error.__cause__, ConnectionError)


class TestExceptionSerialization:
    """Test exception serialization and representation."""

    def test_exception_representation(self):
        """Test exception string representation."""
        exceptions_and_messages = [
            (BiomapperClientError("Base error"), "Base error"),
            (ConnectionError("Connection failed"), "Connection failed"),
            (ApiError(404, "Not found"), "API Error (404): Not found"),
            (ExecutionError("Exec failed", {"key": "value"}), "Exec failed"),
        ]
        
        for exception, expected_message in exceptions_and_messages:
            assert expected_message in str(exception)

    def test_exception_args_preservation(self):
        """Test that exception args are preserved."""
        message = "Test error message"
        error = BiomapperClientError(message)
        
        assert error.args == (message,)
        assert error.args[0] == message

    def test_exception_with_multiple_args(self):
        """Test exception with multiple arguments."""
        args = ("Error message", 123, {"key": "value"})
        error = BiomapperClientError(*args)
        
        assert error.args == args
        assert len(error.args) == 3

    def test_complex_exception_details_access(self):
        """Test accessing complex exception details."""
        details = {
            "nested": {
                "level1": {
                    "level2": "deep_value"
                }
            },
            "list": [1, 2, 3],
            "mixed": {"string": "value", "number": 42}
        }
        
        error = ExecutionError("Complex error", details=details)
        
        assert error.details["nested"]["level1"]["level2"] == "deep_value"
        assert error.details["list"] == [1, 2, 3]
        assert error.details["mixed"]["number"] == 42


class TestExceptionEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_message_handling(self):
        """Test handling of empty error messages."""
        error = BiomapperClientError("")
        
        assert str(error) == ""
        assert error.args == ("",)

    def test_none_message_handling(self):
        """Test handling of None as message."""
        # Most exception classes accept None as message
        error = BiomapperClientError(None)
        assert str(error) == "None"

    def test_unicode_message_handling(self):
        """Test handling of Unicode characters in messages."""
        unicode_message = "Error with unicode: 你好 🌟 café"
        error = BiomapperClientError(unicode_message)
        
        assert str(error) == unicode_message
        assert unicode_message in str(error)

    def test_very_long_message_handling(self):
        """Test handling of very long error messages."""
        long_message = "A" * 10000  # 10k character message
        error = BiomapperClientError(long_message)
        
        assert str(error) == long_message
        assert len(str(error)) == 10000

    def test_api_error_edge_cases(self):
        """Test ApiError edge cases."""
        # Test with zero status code
        error = ApiError(0, "Zero status")
        assert error.status_code == 0
        
        # Test with negative status code
        error = ApiError(-1, "Negative status")
        assert error.status_code == -1
        
        # Test with very high status code
        error = ApiError(9999, "High status")
        assert error.status_code == 9999

    def test_execution_error_empty_details(self):
        """Test ExecutionError with explicitly empty details."""
        error = ExecutionError("Error", details={})
        
        assert error.details == {}
        assert isinstance(error.details, dict)


class TestExceptionComparison:
    """Test exception equality and comparison."""

    def test_exception_equality(self):
        """Test exception equality comparison."""
        error1 = BiomapperClientError("Same message")
        error2 = BiomapperClientError("Same message")
        error3 = BiomapperClientError("Different message")
        
        # Note: Exception equality is based on identity, not message
        assert error1 is not error2
        assert error1 is not error3

    def test_exception_type_checking(self):
        """Test exception type checking with isinstance."""
        connection_error = ConnectionError("Connection failed")
        api_error = ApiError(500, "Server error")
        
        assert isinstance(connection_error, BiomapperClientError)
        assert isinstance(api_error, BiomapperClientError)
        assert isinstance(connection_error, ConnectionError)
        assert isinstance(api_error, ApiError)
        
        assert not isinstance(connection_error, ApiError)
        assert not isinstance(api_error, ConnectionError)

    def test_exception_inheritance_check(self):
        """Test exception inheritance checking."""
        error = ExecutionError("Execution failed")
        
        assert issubclass(ExecutionError, BiomapperClientError)
        assert issubclass(ExecutionError, Exception)
        assert issubclass(BiomapperClientError, Exception)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])