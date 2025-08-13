"""Exception classes for Biomapper client."""

from typing import Any, Dict, Optional


class BiomapperClientError(Exception):
    """Base exception for client errors."""


class ConnectionError(BiomapperClientError):
    """Cannot connect to API."""


class AuthenticationError(BiomapperClientError):
    """Authentication failed."""


class StrategyNotFoundError(BiomapperClientError):
    """Strategy not found."""


class JobNotFoundError(BiomapperClientError):
    """Job not found."""


class ValidationError(BiomapperClientError):
    """Validation error."""


class TimeoutError(BiomapperClientError):
    """Operation timed out."""


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


class CheckpointError(BiomapperClientError):
    """Checkpoint-related error."""


class FileUploadError(BiomapperClientError):
    """File upload error."""
