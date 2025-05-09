from typing import Optional, Dict, Any
import enum


class ErrorCode(enum.Enum):
    """Standardized error codes for Biomapper."""

    # General errors (1-99)
    UNKNOWN_ERROR = 1
    CONFIGURATION_ERROR = 2
    NOT_IMPLEMENTED = 3

    # Client errors (100-199)
    CLIENT_INITIALIZATION_ERROR = 100
    CLIENT_EXECUTION_ERROR = 101
    CLIENT_TIMEOUT_ERROR = 102

    # Database errors (200-299)
    DATABASE_CONNECTION_ERROR = 200
    DATABASE_QUERY_ERROR = 201
    DATABASE_TRANSACTION_ERROR = 202
    DATABASE_INITIALIZATION_ERROR = 203

    # Cache errors (300-399)
    CACHE_RETRIEVAL_ERROR = 300
    CACHE_STORAGE_ERROR = 301
    CACHE_TRANSACTION_ERROR = 302

    # Mapping errors (400-499)
    NO_PATH_FOUND_ERROR = 400
    MAPPING_EXECUTION_ERROR = 401
    INVALID_INPUT_ERROR = 402

    # API errors (500-599)
    API_VALIDATION_ERROR = 500
    API_AUTHENTICATION_ERROR = 501
    API_AUTHORIZATION_ERROR = 502


class BiomapperError(Exception):
    """Base exception class for biomapper-specific errors."""

    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.UNKNOWN_ERROR,
        details: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize base error with standard fields.

        Args:
            message: Human-readable error message
            error_code: Standardized error code
            details: Additional context for debugging
        """
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)

    def __str__(self) -> str:
        """Format the error as a string."""
        result = f"[{self.error_code.name}] {self.message}"
        if self.details:
            details_str = ", ".join(f"{k}={v}" for k, v in self.details.items())
            result += f" ({details_str})"
        return result


class NoPathFoundError(BiomapperError):
    """Raised when no valid mapping path can be found between endpoints."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message, error_code=ErrorCode.NO_PATH_FOUND_ERROR, details=details
        )


class MappingExecutionError(BiomapperError):
    """Raised for errors in the mapping execution process itself, outside of client, cache, or pathfinding issues."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message, error_code=ErrorCode.MAPPING_EXECUTION_ERROR, details=details
        )


class ClientError(BiomapperError):
    """Base class for client-related errors."""

    def __init__(
        self,
        message: str,
        error_code: ErrorCode,
        client_name: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        # Ensure details is a dictionary before passing up
        _details = details if isinstance(details, dict) else {}
        if details and not isinstance(details, dict):
            _details["original_details"] = str(details)  # Store original if not dict

        super().__init__(message, error_code=error_code, details=_details)
        self.client_name = client_name

        # Add client_name to details if provided
        if client_name:
            # self.details is guaranteed to be a dict by BiomapperError's init
            self.details["client_name"] = client_name


class ClientExecutionError(ClientError):
    """Raised specifically when an error occurs during the execution phase of a client method (e.g., map_identifiers)."""

    def __init__(
        self,
        message: str,
        client_name: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message,
            error_code=ErrorCode.CLIENT_EXECUTION_ERROR,
            client_name=client_name,
            details=details,
        )


class ClientInitializationError(ClientError):
    """Raised when an error occurs during client initialization."""

    def __init__(
        self,
        message: str,
        client_name: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message,
            error_code=ErrorCode.CLIENT_INITIALIZATION_ERROR,
            client_name=client_name,
            details=details,
        )


class ConfigurationError(BiomapperError):
    """Raised for configuration-related issues (e.g., missing endpoints, invalid settings)."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message, error_code=ErrorCode.CONFIGURATION_ERROR, details=details
        )


class CacheError(BiomapperError):
    """Base class for cache-related errors."""

    def __init__(
        self,
        message: str,
        error_code: ErrorCode,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, error_code=error_code, details=details)


class CacheTransactionError(CacheError):
    """Raised specifically for errors during cache database transactions (commit, rollback)."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message, error_code=ErrorCode.CACHE_TRANSACTION_ERROR, details=details
        )


class CacheRetrievalError(CacheError):
    """Raised when there's an error retrieving data from the cache."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message, error_code=ErrorCode.CACHE_RETRIEVAL_ERROR, details=details
        )


class CacheStorageError(CacheError):
    """Raised when there's an error storing data in the cache."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message, error_code=ErrorCode.CACHE_STORAGE_ERROR, details=details
        )


class DatabaseError(BiomapperError):
    """Base class for metamapper database-related errors."""

    def __init__(
        self,
        message: str,
        error_code: ErrorCode,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, error_code=error_code, details=details)


class DatabaseConnectionError(DatabaseError):
    """Raised for errors connecting to the metamapper database."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message, error_code=ErrorCode.DATABASE_CONNECTION_ERROR, details=details
        )


class DatabaseQueryError(DatabaseError):
    """Raised for errors during metamapper database queries."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message, error_code=ErrorCode.DATABASE_QUERY_ERROR, details=details
        )


class DatabaseTransactionError(DatabaseError):
    """Raised for errors during metamapper database transactions."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message, error_code=ErrorCode.DATABASE_TRANSACTION_ERROR, details=details
        )


# Placeholder for future API errors if needed
# class APIError(BiomapperError): ...
