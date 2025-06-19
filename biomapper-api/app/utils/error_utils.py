"""
Utilities for error handling.
"""
from typing import Optional, Dict, Any

from fastapi import status


class APIError(Exception):
    """Base API error class."""

    def __init__(
        self,
        status_code: int,
        detail: str,
        error_code: Optional[str] = None,
        headers: Optional[Dict[str, Any]] = None,
    ):
        self.status_code = status_code
        self.detail = detail
        self.error_code = error_code
        self.headers = headers
        super().__init__(self.detail)


class NotFoundError(APIError):
    """Resource not found error."""

    def __init__(
        self,
        detail: str,
        error_code: Optional[str] = None,
        headers: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
            error_code=error_code or "NOT_FOUND",
            headers=headers,
        )


class ValidationError(APIError):
    """Input validation error."""

    def __init__(
        self,
        detail: str,
        error_code: Optional[str] = None,
        headers: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
            error_code=error_code or "VALIDATION_ERROR",
            headers=headers,
        )


class MappingError(APIError):
    """Error during mapping operation."""

    def __init__(
        self,
        detail: str,
        error_code: Optional[str] = None,
        headers: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
            error_code=error_code or "MAPPING_ERROR",
            headers=headers,
        )
