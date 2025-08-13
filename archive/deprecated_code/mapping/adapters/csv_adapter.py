"""
csv_adapter.py

Adapter for extracting and normalizing identifiers from MetabolitesCSV endpoint values.
Integrates with extractors utility and provides CSV file loading capabilities.
"""
import logging
from typing import Any, Dict, Optional, List
import pandas as pd
from cachetools import LRUCache

from biomapper.mapping.extractors import extract_all_ids, SUPPORTED_ID_TYPES
from biomapper.mapping.metadata.interfaces import EndpointAdapter
from biomapper.config import get_settings


class CSVAdapter(EndpointAdapter):
    """
    Adapter for extracting identifiers from single string values, typically CSV cells.
    Also provides CSV file loading capabilities with selective column loading and caching.
    Implements the EndpointAdapter interface.
    """

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        resource_name: str = "csv_adapter",
        cache_max_size: Optional[int] = None,
        endpoint=None,
    ):
        # Consider adding super().__init__() if EndpointAdapter evolves a base init
        self.config = config or {}
        self.resource_name = resource_name
        self.endpoint = endpoint
        self.logger = logging.getLogger(__name__)

        # Determine cache size from settings if not explicitly provided
        if cache_max_size is None:
            settings = get_settings()
            cache_max_size = settings.csv_adapter_cache_size

        # Initialize LRU cache for CSV data
        # Cache key: (file_path, frozenset(columns_to_load) if columns_to_load else None)
        self._data_cache: LRUCache = LRUCache(maxsize=cache_max_size)

        # Initialize performance monitoring counters
        self._cache_hits: int = 0
        self._cache_misses: int = 0

    async def extract_ids(
        self,
        value: str,
        endpoint_id: int,  # Currently unused, but part of the interface
        ontology_type: str,
        **kwargs,
    ) -> List[Dict[str, Any]]:
        """Extract IDs of a specific ontology type from a value.

        Args:
            value: The value (e.g., cell content) to extract IDs from.
            endpoint_id: The endpoint ID (contextual).
            ontology_type: The specific ontology type (e.g., 'hmdb', 'chebi') to extract.
            **kwargs: Additional keyword arguments.

        Returns:
            List containing a dict {'id': extracted_id, 'ontology_type': ontology_type, 'confidence': 1.0}
            if found, otherwise an empty list.
        """
        extracted = extract_all_ids(value)
        found_id = extracted.get(ontology_type)
        if found_id:
            return [
                {
                    "id": found_id,
                    "ontology_type": ontology_type,
                    "confidence": 1.0,  # Direct extraction assumed high confidence
                }
            ]
        return []

    def get_supported_extractions(self, endpoint_id: int) -> List[str]:
        """Get supported extraction ontology types for this adapter.

        Args:
            endpoint_id: The endpoint ID (contextual).

        Returns:
            List of supported ontology type strings (e.g., ['hmdb', 'chebi']).
        """
        # Ideally, get this dynamically from extractors.py
        return list(SUPPORTED_ID_TYPES)

    async def load_data(
        self,
        file_path: Optional[str] = None,
        columns_to_load: Optional[List[str]] = None,
    ) -> pd.DataFrame:
        """Load CSV data with selective column loading and caching.

        Args:
            file_path: Path to the CSV file. If None, uses endpoint's file path.
            columns_to_load: List of column names to load. If None or empty, loads all columns.

        Returns:
            pandas DataFrame containing the loaded data.

        Raises:
            ValueError: If file_path is not provided and no endpoint is configured.
            FileNotFoundError: If the specified file does not exist.
        """
        # Determine file path
        if file_path is None:
            if self.endpoint is None:
                raise ValueError(
                    "file_path must be provided when no endpoint is configured"
                )

            # Try to get file path from endpoint configuration
            if hasattr(self.endpoint, "file_path") and self.endpoint.file_path:
                file_path = self.endpoint.file_path
            elif hasattr(self.endpoint, "url") and self.endpoint.url:
                file_path = self.endpoint.url
            elif (
                hasattr(self.endpoint, "connection_details")
                and self.endpoint.connection_details
            ):
                # Parse connection_details JSON to get file_path
                import json

                try:
                    connection_details = json.loads(self.endpoint.connection_details)
                    file_path = connection_details.get("file_path")
                    if not file_path:
                        raise ValueError(
                            f"No file_path found in connection_details for endpoint {self.endpoint}"
                        )
                except (json.JSONDecodeError, TypeError) as e:
                    raise ValueError(
                        f"Invalid connection_details JSON for endpoint {self.endpoint}: {e}"
                    )
            else:
                raise ValueError(
                    f"Could not determine file path from endpoint {self.endpoint}"
                )

        # Create cache key
        columns_key = frozenset(columns_to_load) if columns_to_load else None
        cache_key = (file_path, columns_key)

        # Check cache first
        if cache_key in self._data_cache:
            self._cache_hits += 1
            self.logger.debug(
                f"Cache hit for file: {file_path}, columns: {columns_to_load}"
            )
            return self._data_cache[cache_key]

        # Record cache miss
        self._cache_misses += 1

        self.logger.info(f"Loading CSV data from: {file_path}")
        if columns_to_load:
            self.logger.info(f"Loading only columns: {columns_to_load}")

        # Get CSV reading options from endpoint configuration
        read_kwargs = {}
        if (
            self.endpoint
            and hasattr(self.endpoint, "connection_details")
            and self.endpoint.connection_details
        ):
            import json

            try:
                connection_details = json.loads(self.endpoint.connection_details)
                if "delimiter" in connection_details:
                    read_kwargs["delimiter"] = connection_details["delimiter"]
                if "sep" in connection_details:
                    read_kwargs["sep"] = connection_details["sep"]
            except (json.JSONDecodeError, TypeError):
                pass  # Use default pandas options

        # Load data from file
        try:
            if columns_to_load:
                # First check what columns are available
                try:
                    available_data = pd.read_csv(
                        file_path, nrows=0, **read_kwargs
                    )  # Just get header
                    available_columns = available_data.columns.tolist()

                    # Filter to only existing columns
                    existing_columns = [
                        col for col in columns_to_load if col in available_columns
                    ]
                    missing_columns = [
                        col for col in columns_to_load if col not in available_columns
                    ]

                    if missing_columns:
                        self.logger.warning(
                            f"Some columns not found in {file_path}: {missing_columns}"
                        )
                        self.logger.info(f"Available columns: {available_columns}")

                    if not existing_columns:
                        raise ValueError(
                            f"None of the requested columns {columns_to_load} exist in {file_path}"
                        )

                    # Load only the existing columns
                    self.logger.info(f"Loading existing columns: {existing_columns}")
                    data = pd.read_csv(
                        file_path, usecols=existing_columns, **read_kwargs
                    )
                except pd.errors.EmptyDataError:
                    # Handle empty file case
                    data = pd.DataFrame()

            else:
                # Load all columns
                data = pd.read_csv(file_path, **read_kwargs)

            # Store in cache
            self._data_cache[cache_key] = data

            self.logger.info(
                f"Successfully loaded {len(data)} rows and {len(data.columns)} columns from {file_path}"
            )

            return data

        except FileNotFoundError:
            self.logger.error(f"File not found: {file_path}")
            raise
        except pd.errors.ParserError as e:
            self.logger.error(f"Error parsing CSV file {file_path}: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error loading CSV file {file_path}: {e}")
            raise

    def clear_cache(self) -> None:
        """Clear the data cache and reset performance counters."""
        self._data_cache.clear()
        self._cache_hits = 0
        self._cache_misses = 0
        self.logger.info("CSV data cache cleared and performance counters reset")

    def get_cache_info(self) -> Dict[str, Any]:
        """Get information about the current cache state.

        Returns:
            Dictionary containing cache statistics.
        """
        return {
            "cache_size": len(self._data_cache),
            "max_size": self._data_cache.maxsize,
            "cached_files": list(self._data_cache.keys()),
        }

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get performance statistics for the cache.

        Returns:
            Dictionary containing cache performance metrics including hits, misses,
            hit rate, current size, and max size.
        """
        total_requests = self._cache_hits + self._cache_misses
        hit_rate = (self._cache_hits / total_requests) if total_requests > 0 else 0.0

        return {
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "total_requests": total_requests,
            "hit_rate": hit_rate,
            "cache_size": len(self._data_cache),
            "max_size": self._data_cache.maxsize,
        }
