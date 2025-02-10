"""Client for interacting with SPOKE graph database."""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union
import logging

import aiohttp
from aiohttp.client_exceptions import ClientError

logger = logging.getLogger(__name__)


@dataclass
class SPOKEConfig:
    """Configuration for SPOKE database connection."""

    host: str
    port: int = 8529
    username: Optional[str] = None
    password: Optional[str] = None
    database: str = "_system"
    use_ssl: bool = True
    timeout: int = 30


class SPOKEError(Exception):
    """Base exception for SPOKE client errors."""

    pass


class SPOKEDBClient:
    """Client for interacting with SPOKE graph database."""

    def __init__(self, config: SPOKEConfig) -> None:
        """Initialize SPOKE client.

        Args:
            config: Configuration for SPOKE connection
        """
        self.config = config
        self._session: Optional[aiohttp.ClientSession] = None

    @property
    def base_url(self) -> str:
        """Get base URL for SPOKE API."""
        protocol = "https" if self.config.use_ssl else "http"
        return f"{protocol}://{self.config.host}:{self.config.port}"

    async def __aenter__(self) -> "SPOKEDBClient":
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.disconnect()

    async def connect(self) -> None:
        """Establish connection to SPOKE."""
        if self._session is None:
            self._session = aiohttp.ClientSession(
                headers={"Content-Type": "application/json"}
            )
            # Test connection
            try:
                await self.execute_query("RETURN 1")
            except Exception as e:
                await self.disconnect()
                raise SPOKEError(f"Failed to connect to SPOKE: {e}") from e

    async def disconnect(self) -> None:
        """Close SPOKE connection."""
        if self._session is not None:
            await self._session.close()
            self._session = None

    async def execute_query(
        self,
        query: str,
        bind_vars: Optional[Dict[str, Any]] = None,
        batch_size: int = 1000,
    ) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
        """Execute AQL query against SPOKE.

        Args:
            query: AQL query string
            bind_vars: Optional query parameters
            batch_size: Number of results to fetch per batch

        Returns:
            Query results as list or dict

        Raises:
            SPOKEError: If query execution fails
        """
        if self._session is None:
            await self.connect()

        payload = {
            "query": query,
            "batchSize": batch_size,
        }
        if bind_vars:
            payload["bindVars"] = bind_vars

        try:
            assert self._session is not None
            async with self._session.post(
                f"{self.base_url}/_api/cursor",
                json=payload,
                auth=aiohttp.BasicAuth(
                    self.config.username or "",
                    self.config.password or "",
                ),
            ) as response:
                response.raise_for_status()
                result = await response.json()
                return result.get("result", [])

        except ClientError as e:
            logger.error("SPOKE query failed: %s", str(e))
            raise SPOKEError(f"Query execution failed: {e}") from e
        except Exception as e:
            logger.error("Unexpected error in SPOKE query: %s", str(e))
            raise SPOKEError(f"Unexpected error: {e}") from e

    async def get_node_by_id(
        self, node_id: str, collection: str
    ) -> Optional[Dict[str, Any]]:
        """Fetch a node by its ID.

        Args:
            node_id: Node identifier
            collection: Node collection name

        Returns:
            Node data if found, None otherwise
        """
        query = "FOR doc IN @@collection FILTER doc._id == @id RETURN doc"
        bind_vars = {"@collection": collection, "id": node_id}

        try:
            result = await self.execute_query(query, bind_vars)
            return dict(result[0]) if result else None
        except Exception as e:
            logger.error("Failed to fetch node %s: %s", node_id, str(e))
            return None

    async def get_nodes_by_property(
        self,
        collection: str,
        property_name: str,
        property_value: Any,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch nodes by a property value.

        Args:
            collection: Node collection name
            property_name: Name of property to match
            property_value: Value to match
            limit: Optional limit on number of results

        Returns:
            List of matching nodes
        """
        query = """
        FOR doc IN @@collection
            FILTER doc[@prop] == @value
            LIMIT @limit
            RETURN doc
        """
        bind_vars = {
            "@collection": collection,
            "prop": property_name,
            "value": property_value,
            "limit": limit or 1000,
        }

        try:
            result = await self.execute_query(query, bind_vars)
            return [dict(node) for node in result]
        except Exception as e:
            logger.error(
                "Failed to fetch nodes with %s=%s: %s",
                property_name,
                property_value,
                str(e),
            )
            return []
