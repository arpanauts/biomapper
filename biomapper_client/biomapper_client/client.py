"""Biomapper API client implementation."""

from typing import Any, Dict, Optional
import httpx
from pydantic import BaseModel, Field


class BiomapperClientError(Exception):
    """Base exception for BiomapperClient errors."""
    pass


class ApiError(BiomapperClientError):
    """Raised when the API returns a non-200 status code."""
    
    def __init__(self, status_code: int, message: str, response_body: Optional[Any] = None):
        self.status_code = status_code
        self.response_body = response_body
        super().__init__(f"API Error (status {status_code}): {message}")


class NetworkError(BiomapperClientError):
    """Raised when there are network-related issues."""
    pass


class BiomapperClient:
    """Asynchronous client for the Biomapper API."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        """Initialize the BiomapperClient.
        
        Args:
            base_url: The base URL of the Biomapper API. Defaults to http://localhost:8000
        """
        self.base_url = base_url.rstrip("/")
        self._client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self):
        """Enter the runtime context for the async client."""
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=10800.0  # 3 hours for strategy execution (needed for KG2C with 267K+ rows)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit the runtime context, closing the client."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    @property
    def client(self) -> httpx.AsyncClient:
        """Get the httpx client instance."""
        if self._client is None:
            raise RuntimeError(
                "Client not initialized. Use 'async with BiomapperClient() as client:' "
                "or manually call __aenter__ and __aexit__"
            )
        return self._client
    
    async def execute_strategy(self, strategy_name: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a strategy on the Biomapper API.
        
        Args:
            strategy_name: The name of the strategy to execute
            context: The context dictionary to pass to the strategy
            
        Returns:
            The response from the API as a dictionary
            
        Raises:
            ApiError: If the API returns a non-200 status code
            NetworkError: If there are network-related issues
            BiomapperClientError: For other client-related errors
        """
        url = f"/api/strategies/{strategy_name}/execute"
        
        try:
            response = await self.client.post(
                url,
                json=context,  # Send the context directly as it now contains all required fields
                headers={"Content-Type": "application/json"}
            )
            
            # Check for successful response
            if response.status_code != 200:
                # Try to parse error message from response
                try:
                    error_data = response.json()
                    error_message = error_data.get("detail", response.text)
                except Exception:
                    error_message = response.text
                
                raise ApiError(
                    status_code=response.status_code,
                    message=error_message,
                    response_body=response.text
                )
            
            # Parse and return the successful response
            return response.json()
            
        except httpx.NetworkError as e:
            raise NetworkError(f"Network error occurred: {str(e)}") from e
        except httpx.TimeoutException as e:
            raise NetworkError(f"Request timeout: {str(e)}") from e
        except ApiError:
            # Re-raise our own API errors
            raise
        except Exception as e:
            # Catch any other unexpected errors
            raise BiomapperClientError(f"Unexpected error: {str(e)}") from e