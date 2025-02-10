"""Base classes for API clients."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import logging
import aiohttp
import asyncio
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class APIResponse:
    """Standard response from API clients."""
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    raw_response: Optional[Dict[str, Any]] = None


class BaseAPIClient(ABC):
    """Base class for all API clients."""
    
    def __init__(self, base_url: str, api_key: Optional[str] = None):
        """Initialize client.
        
        Args:
            base_url: Base URL for API
            api_key: Optional API key
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def __aenter__(self):
        """Create session on enter."""
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Close session on exit."""
        if self.session:
            await self.session.close()
            
    @abstractmethod
    async def search(self, query: str) -> APIResponse:
        """Search the API with query.
        
        Args:
            query: Search query
            
        Returns:
            APIResponse with results
        """
        pass
    
    @abstractmethod
    async def get_by_id(self, entity_id: str) -> APIResponse:
        """Get entity by ID.
        
        Args:
            entity_id: ID to lookup
            
        Returns:
            APIResponse with entity data
        """
        pass
    
    async def batch_search(
        self,
        queries: List[str],
        batch_size: int = 10,
        delay: float = 0.1
    ) -> List[APIResponse]:
        """Search multiple queries in batches.
        
        Args:
            queries: List of search queries
            batch_size: Number of concurrent requests
            delay: Delay between batches in seconds
            
        Returns:
            List of APIResponse objects
        """
        results = []
        for i in range(0, len(queries), batch_size):
            batch = queries[i:i + batch_size]
            tasks = [self.search(query) for query in batch]
            batch_results = await asyncio.gather(*tasks)
            results.extend(batch_results)
            if i + batch_size < len(queries):
                await asyncio.sleep(delay)
        return results
    
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        **kwargs
    ) -> APIResponse:
        """Make HTTP request to API.
        
        Args:
            method: HTTP method
            endpoint: API endpoint
            **kwargs: Additional arguments for request
            
        Returns:
            APIResponse object
        """
        if not self.session:
            self.session = aiohttp.ClientSession()
            
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        # Add API key if present
        headers = kwargs.pop('headers', {})
        if self.api_key:
            headers['Authorization'] = f"Bearer {self.api_key}"
            
        try:
            async with self.session.request(
                method,
                url,
                headers=headers,
                **kwargs
            ) as response:
                response.raise_for_status()
                data = await response.json()
                return APIResponse(
                    success=True,
                    data=data,
                    raw_response=data
                )
        except aiohttp.ClientError as e:
            logger.error(f"API request failed: {e}")
            return APIResponse(
                success=False,
                error=str(e)
            )
