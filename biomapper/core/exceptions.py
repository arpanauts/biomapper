class BiomapperError(Exception):
    """Base exception class for biomapper-specific errors."""

    pass


class NoPathFoundError(BiomapperError):
    """Raised when no valid mapping path can be found between endpoints."""

    pass


class MappingExecutionError(BiomapperError):
    """Raised for errors in the mapping execution process itself, outside of client, cache, or pathfinding issues."""

    pass


class ClientError(BiomapperError):
    """Raised when an error occurs within a mapping client during execution."""

    def __init__(self, message, client_name=None, details=None):
        super().__init__(message)
        self.client_name = client_name
        self.details = details

    def __str__(self):
        base_message = super().__str__()
        if self.client_name:
            return f"[{self.client_name}] {base_message}"
        return base_message


class ClientExecutionError(ClientError):
    """Raised specifically when an error occurs during the execution phase of a client method (e.g., map_identifiers)."""

    pass


class ClientInitializationError(ClientError):
    """Raised when an error occurs during client initialization."""

    pass


class ConfigurationError(BiomapperError):
    """Raised for configuration-related issues (e.g., missing endpoints, invalid settings)."""

    pass


class CacheError(BiomapperError):
    """Raised for errors related to cache database operations."""

    pass


class CacheTransactionError(CacheError):
    """Raised specifically for errors during cache database transactions (commit, rollback)."""

    pass


class CacheRetrievalError(CacheError):
    """Raised when there's an error retrieving data from the cache."""

    pass
