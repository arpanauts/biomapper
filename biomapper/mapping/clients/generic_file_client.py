import csv
import logging
from typing import Dict, List, Optional, Any, Tuple
import os

from biomapper.mapping.clients.base_client import BaseMappingClient, FileLookupClientMixin, CachedMappingClientMixin
from biomapper.core.exceptions import ClientInitializationError
from biomapper.config import settings # For DATA_DIR resolution

logger = logging.getLogger(__name__)

class GenericFileLookupClient(CachedMappingClientMixin, FileLookupClientMixin, BaseMappingClient):
    """
    A generic mapping client that performs lookups in a delimited text file.
    It reads a file (e.g., TSV, CSV) into memory and maps identifiers
    from a specified key column to a specified value column.

    Required configuration keys:
    - 'file_path': Path to the lookup file. Can use ${DATA_DIR}.
    - 'key_column': Name of the column in the file to use as the lookup key.
    - 'value_column': Name of the column in the file whose values will be returned.
    - 'delimiter': The delimiter used in the file (e.g., '\\t' for TSV, ',' for CSV).
    Optional configuration keys:
    - 'cache_size': Maximum number of entries for the LRU cache (default: 1024).
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        # Explicitly initialize mixins and base class in a controlled order.
        BaseMappingClient.__init__(self, config)
        FileLookupClientMixin.__init__(self) 
        cache_size = self.get_config_value('cache_size', 1024)
        CachedMappingClientMixin.__init__(self, cache_size=cache_size)
        
        self._lookup_data: Dict[str, List[str]] = {}
        self._load_data() # Load data synchronously during initialization

    def get_required_config_keys(self) -> List[str]:
        parent_keys = FileLookupClientMixin.get_required_config_keys(self)
        return parent_keys + ['delimiter']

    def _resolve_data_dir(self, file_path: str) -> str:
        """Resolves ${DATA_DIR} placeholder in the file path."""
        if "${DATA_DIR}" in file_path:
            if settings.data_dir:
                return file_path.replace("${DATA_DIR}", str(settings.data_dir))
            else:
                raise ClientInitializationError(
                    f"{self.__class__.__name__}: DATA_DIR placeholder found in file_path "
                    f"'{file_path}' but settings.data_dir is not configured.",
                    client_name=self.__class__.__name__
                )
        return file_path

    def _load_data(self) -> None:
        file_path_raw = self._get_file_path() # From FileLookupClientMixin
        key_column_name = self._get_key_column()
        value_column_name = self._get_value_column()
        delimiter = self.get_config_value('delimiter')

        # These checks are largely covered by _validate_config, but good for clarity
        if not file_path_raw:
             raise ClientInitializationError(
                f"{self.__class__.__name__}: Configuration key '{self._file_path_key}' is missing or empty.", # type: ignore
                client_name=self.__class__.__name__
            )
        if not key_column_name:
            raise ClientInitializationError(
                f"{self.__class__.__name__}: Configuration key '{self._key_column_key}' is missing or empty.", # type: ignore
                client_name=self.__class__.__name__
            )
        if not value_column_name:
            raise ClientInitializationError(
                f"{self.__class__.__name__}: Configuration key '{self._value_column_key}' is missing or empty.", # type: ignore
                client_name=self.__class__.__name__
            )
        if not delimiter:
            raise ClientInitializationError(
                f"{self.__class__.__name__}: Configuration key 'delimiter' is missing or empty.",
                client_name=self.__class__.__name__
            )

        file_path = self._resolve_data_dir(file_path_raw)
        logger.info(f"{self.__class__.__name__}: Loading data from '{file_path}' using delimiter '{repr(delimiter)}'")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f, delimiter=delimiter)
                header = next(reader, None)
                if not header:
                    raise ClientInitializationError(
                        f"{self.__class__.__name__}: File '{file_path}' is empty or has no header.",
                        client_name=self.__class__.__name__
                    )

                try:
                    key_idx = header.index(key_column_name)
                    value_idx = header.index(value_column_name)
                except ValueError as e:
                    raise ClientInitializationError(
                        f"{self.__class__.__name__}: Column not found in header of '{file_path}'. "
                        f"Header: {header}. Missing column: {e}. Ensure '{key_column_name}' and "
                        f"'{value_column_name}' are present.",
                        client_name=self.__class__.__name__
                    )

                for row_num, row in enumerate(reader):
                    if len(row) <= max(key_idx, value_idx):
                        logger.warning(
                            f"{self.__class__.__name__}: Skipping malformed row {row_num + 2} in '{file_path}'. "
                            f"Expected at least {max(key_idx, value_idx) + 1} columns, got {len(row)}. Row: {row}"
                        )
                        continue
                    
                    key = row[key_idx]
                    value = row[value_idx]
                    
                    if key not in self._lookup_data:
                        self._lookup_data[key] = []
                    self._lookup_data[key].append(value)
            
            logger.info(f"{self.__class__.__name__}: Successfully loaded {len(self._lookup_data)} unique keys from '{file_path}'.")

        except FileNotFoundError:
            raise ClientInitializationError(
                f"{self.__class__.__name__}: File not found: '{file_path}'",
                client_name=self.__class__.__name__
            )
        except IOError as e:
            raise ClientInitializationError(
                f"{self.__class__.__name__}: Error reading file '{file_path}': {e}",
                client_name=self.__class__.__name__
            )
        except Exception as e:
            raise ClientInitializationError(
                f"{self.__class__.__name__}: Unexpected error loading data from '{file_path}': {e}",
                client_name=self.__class__.__name__
            )

    async def map_identifiers(
        self, identifiers: List[str], config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Tuple[Optional[List[str]], Optional[str]]]:
        
        results: Dict[str, Tuple[Optional[List[str]], Optional[str]]] = {}
        identifiers_to_fetch_from_source: List[str] = []

        for identifier in identifiers:
            cached_result = await self._get_from_cache(identifier)
            if cached_result is not None:
                results[identifier] = cached_result
                logger.debug(f"{self.__class__.__name__}: Cache hit for identifier '{identifier}'")
            else:
                identifiers_to_fetch_from_source.append(identifier)
                logger.debug(f"{self.__class__.__name__}: Cache miss for identifier '{identifier}'")

        if identifiers_to_fetch_from_source:
            for identifier in identifiers_to_fetch_from_source:
                target_ids = self._lookup_data.get(identifier)
                formatted_result = self.format_result(target_ids=target_ids, component_id=None)
                results[identifier] = formatted_result
                await self._add_to_cache(identifier, formatted_result)

        return results
