"""Exception classes for Biomapper client."""

from typing import Any, Dict, Optional


class BiomapperClientError(Exception):
    """Base exception for client errors."""

    pass


class ConnectionError(BiomapperClientError):
    """Cannot connect to API."""

    pass


class AuthenticationError(BiomapperClientError):
    """Authentication failed."""

    pass


class StrategyNotFoundError(BiomapperClientError):
    """Strategy not found."""

    pass


class JobNotFoundError(BiomapperClientError):
    """Job not found."""

    pass


class ValidationError(BiomapperClientError):
    """Validation error."""

    pass


class TimeoutError(BiomapperClientError):
    """Operation timed out."""

    pass


class ExecutionError(BiomapperClientError):
    """Strategy execution failed."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.details = details or {}


class ApiError(BiomapperClientError):
    """API returned an error."""

    def __init__(
        self, status_code: int, message: str, details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(f"API Error ({status_code}): {message}")
        self.status_code = status_code
        self.message = message
        self.details = details or {}


class NetworkError(BiomapperClientError):
    """Network-related error."""

    pass


class CheckpointError(BiomapperClientError):
    """Checkpoint-related error."""

    pass


class FileUploadError(BiomapperClientError):
    """File upload error."""

    pass
