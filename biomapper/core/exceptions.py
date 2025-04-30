class BiomapperError(Exception):
    """Base exception class for biomapper-specific errors."""
    pass

class NoPathFoundError(BiomapperError):
    """Raised when no valid mapping path can be found between endpoints."""
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
