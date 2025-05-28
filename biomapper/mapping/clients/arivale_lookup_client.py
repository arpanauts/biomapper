"""Client to map identifiers using a direct lookup from a local metadata file.

This client loads data from a TSV file and provides mapping between different 
identifier types (e.g., UniProt IDs to Arivale Protein IDs).
"""

import asyncio
import logging
import pandas as pd
import csv
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path

from biomapper.core.exceptions import ClientInitializationError, ClientExecutionError
from biomapper.mapping.clients.base_client import (
    BaseMappingClient,
    CachedMappingClientMixin,
    FileLookupClientMixin,
)

logger = logging.getLogger(__name__)


class ArivaleMetadataLookupClient(
    CachedMappingClientMixin, FileLookupClientMixin, BaseMappingClient
):
    """Client to map identifiers using a direct lookup from a local metadata file.
    
    This client:
    1. Loads mappings from a TSV file specified in the configuration
    2. Provides bidirectional mapping between identifiers
    3. Handles composite identifiers (e.g., comma-separated UniProt IDs)
    4. Uses in-memory caching for better performance
    
    The file is expected to have headers and contain at least the key and value
    columns specified in the configuration.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None, cache_size: int = 10000):
        """Initialize the client and load the lookup map from the file.
        
        Args:
            config: Configuration dictionary containing:
                - file_path (str): Path to the TSV metadata file.
                - key_column (str): Column name containing the source identifiers (e.g., UniProt ACs).
                - value_column (str): Column name containing the target identifiers (e.g., Arivale Protein IDs).
            cache_size: Maximum number of entries to store in the cache.
        """
        # Initialize FileLookupClientMixin with explicit keys to match TSV file
        self._file_path_key = "file_path"
        self._key_column_key = "key_column"
        self._value_column_key = "value_column"
        
        # Initialize all parent classes with appropriate parameters
        super().__init__(cache_size=cache_size, config=config)
        
        # Initialize lookup maps
        self._lookup_map: Dict[str, str] = {}
        self._component_lookup_map: Dict[str, str] = {}
        self._reverse_lookup_map: Dict[str, List[str]] = {}
        
        # Load the lookup data from the file
        self._load_lookup_data()
        
        # Mark as initialized
        self._initialized = True
        
    def _load_lookup_data(self) -> None:
        """Load the lookup data from the file specified in the configuration.
        
        This method reads the TSV file, processes the data, and populates the 
        lookup maps used for mapping identifiers.
        
        Raises:
            ClientInitializationError: If the file cannot be loaded or processed.
        """
        file_path = self._get_file_path()
        key_column = self._get_key_column()
        value_column = self._get_value_column()
        
        logger.debug(f"Loading mapping from {file_path}")
        try:
            logger.info(f"Loading Arivale lookup map from {file_path}")
            file_path_obj = Path(file_path)
            if not file_path_obj.is_file():
                raise ClientInitializationError(
                    f"Lookup file not found: {file_path}",
                    client_name=self.__class__.__name__,
                    details={"file_path": file_path}
                )

            # Find header row, skipping comments
            header_line_num = 0
            with open(file_path_obj, "r", encoding="utf-8") as f:
                for i, line in enumerate(f):
                    if not line.strip().startswith("#"):
                        header_line_num = i
                        break

            # Get delimiter from config, default to tab
            delimiter = self._config.get("delimiter", "\t") if hasattr(self, '_config') else "\t"
            
            df = pd.read_csv(
                file_path_obj,
                sep=delimiter,
                skiprows=header_line_num,
                quoting=csv.QUOTE_ALL,  # Match check script
                on_bad_lines="warn",
            )
            logger.debug(
                f"Client loaded columns: {df.columns.tolist()} using quoting=QUOTE_ALL"
            )

            # Verify exact column names seen by pandas
            if key_column not in df.columns or value_column not in df.columns:
                logger.error(
                    f"Required columns '{key_column}' or '{value_column}' not found in DataFrame. "
                    f"Columns: {df.columns.tolist()}"
                )
                raise ClientInitializationError(
                    "Missing required columns after loading data file.",
                    client_name=self.__class__.__name__,
                    details={"file_path": file_path, "missing_columns": [key_column, value_column]}
                )

            # Populate the lookup map
            for _, row in df.iterrows():
                # Access columns using the configured names
                uniprot_val_raw = str(row[key_column])
                name_val_raw = str(row[value_column])

                # Check for null/empty UniProt ID *before* stripping
                if pd.isna(uniprot_val_raw) or not str(uniprot_val_raw).strip():
                    continue  # Skip row if UniProt ID is missing or empty

                # Strip whitespace and surrounding quotes
                key_val = uniprot_val_raw.strip().strip('"')
                value_val = name_val_raw.strip().strip('"')

                # Skip if value is empty after stripping
                if not value_val:
                    continue

                # Treat the entire stripped key_val as the key, do not split.
                # This matches the check script and UKBB loading logic.
                k = key_val.strip()
                if k:  # Ensure key is not empty after stripping
                    if k in self._lookup_map:
                        if self._lookup_map[k] != value_val:
                            logger.warning(
                                f"Duplicate key '{k}' found in {file_path}. "
                                f"Keeping first value '{self._lookup_map[k]}', ignoring '{value_val}'."
                            )
                    else:
                        self._lookup_map[k] = value_val
                        
                        # Update reverse lookup map
                        if value_val not in self._reverse_lookup_map:
                            self._reverse_lookup_map[value_val] = []
                        if k not in self._reverse_lookup_map[value_val]:
                            self._reverse_lookup_map[value_val].append(k)

                # Populate component lookup map
                components = [
                    comp.strip() for comp in key_val.split(",") if comp.strip()
                ]
                for component in components:
                    if component in self._component_lookup_map:
                        # Handle cases where a component maps to multiple Arivale IDs
                        # For now, warn and keep the first mapping found for simplicity
                        if self._component_lookup_map[component] != value_val:
                            logger.warning(
                                f"Component '{component}' from key '{key_val}' maps to new value '{value_val}', "
                                f"but already mapped to '{self._component_lookup_map[component]}'. Keeping first mapping."
                            )
                    else:
                        self._component_lookup_map[component] = value_val
                        
                        # Update reverse lookup for components as well
                        if value_val not in self._reverse_lookup_map:
                            self._reverse_lookup_map[value_val] = []
                        if component not in self._reverse_lookup_map[value_val]:
                            self._reverse_lookup_map[value_val].append(component)

            logger.info(
                f"Loaded {len(self._lookup_map)} unique key-value pairs into lookup map."
            )
            logger.info(
                f"Loaded {len(self._component_lookup_map)} unique component keys into component map."
            )
            logger.info(
                f"Created reverse lookup map with {len(self._reverse_lookup_map)} entries."
            )
            
            # Preload cache - don't use asyncio.create_task here
            # as it requires a running event loop which might not be available during init
            self._cache_preload_needed = True
            
        except ClientInitializationError:
            # Re-raise client initialization errors
            raise
        except Exception as e:
            logger.error(
                f"{self.__class__.__name__}: Failed to load lookup map from {file_path}: {e}"
            )
            raise ClientInitializationError(
                f"Failed to load lookup data: {str(e)}",
                client_name=self.__class__.__name__,
                details={"file_path": file_path, "error": str(e)}
            )

    async def _preload_cache(self) -> None:
        """Preload the cache with all mappings from the lookup map.
        
        This ensures that all lookups will be cache hits, providing the best
        performance for repeated lookups.
        """
        logger.info(f"Preloading cache with {len(self._lookup_map)} entries...")
        
        # Create a batch of results to add to the cache
        cache_entries: Dict[str, Tuple[Optional[List[str]], Optional[str]]] = {}
        
        # Add direct lookup entries
        for key, value in self._lookup_map.items():
            cache_entries[key] = self.format_result([value], key)
            
        # Add component lookup entries
        for component, value in self._component_lookup_map.items():
            cache_entries[component] = self.format_result([value], component)
            
        # Add all entries to the cache at once
        await self._add_many_to_cache(cache_entries)
        
        # Set cache as initialized
        self._cache_initialized = True
        logger.info(f"Cache preloaded with {len(cache_entries)} entries.")

    async def map_identifiers(
        self, identifiers: List[str], config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Map identifiers using the loaded Arivale lookup map, handling composite keys.
        
        Args:
            identifiers: List of identifiers to map.
            config: Optional configuration overrides for this specific call.
            
        Returns:
            A dictionary in the format expected by MappingExecutor:
            {
                'primary_ids': List of unique successfully mapped target IDs,
                'input_to_primary': Dict mapping original input ID to its FIRST mapped target ID,
                'errors': List of dicts for identifiers that could not be mapped.
            }
        """
        if not self._initialized:
            raise ClientExecutionError(
                "Client not properly initialized",
                client_name=self.__class__.__name__
            )
            
        if hasattr(self, "_cache_preload_needed") and self._cache_preload_needed:
            await self._preload_cache()
            self._cache_preload_needed = False
        
        # Temporary dict to hold results in the client's original format
        client_format_results: Dict[str, Tuple[Optional[List[str]], Optional[str]]] = {}
        miss_count = 0
        found_count = 0
        cache_hit_count = 0
        
        for identifier in identifiers:
            cached_result = await self._get_from_cache(identifier)
            if cached_result is not None:
                client_format_results[identifier] = cached_result
                # Update counts based on whether the cached result was a successful mapping
                if cached_result[0] is not None and len(cached_result[0]) > 0:
                    found_count += 1
                else:
                    miss_count += 1
                cache_hit_count += 1
                continue
                
            identifier_stripped = identifier.strip()
            mapped_this_id = False
            # successful_component_id = None # Not directly needed for the final structure

            direct_match_found = identifier_stripped in self._lookup_map
            if direct_match_found:
                result_tuple = self.format_result(
                    [self._lookup_map[identifier_stripped]],
                    identifier_stripped
                )
                client_format_results[identifier] = result_tuple
                mapped_this_id = True
                await self._add_to_cache(identifier, result_tuple)
                
            elif "," in identifier_stripped or "_" in identifier_stripped:
                components = [comp.strip() for comp in identifier_stripped.replace("_", ",").split(",") if comp.strip()]
                target_ids_for_components = set()
                found_component_match = False
                first_successful_component_for_input = None

                for component in components:
                    component_stripped = component.strip()
                    component_match_found = component_stripped in self._component_lookup_map
                    if component_match_found:
                        target_ids_for_components.add(self._component_lookup_map[component_stripped])
                        if not found_component_match:
                            first_successful_component_for_input = component_stripped
                        found_component_match = True

                if found_component_match:
                    result_tuple = self.format_result(
                        sorted(list(target_ids_for_components)),
                        first_successful_component_for_input
                    )
                    client_format_results[identifier] = result_tuple
                    mapped_this_id = True
                    await self._add_to_cache(identifier, result_tuple)

            if not mapped_this_id:
                result_tuple = self.format_result(None, None)
                client_format_results[identifier] = result_tuple
                miss_count += 1
                await self._add_to_cache(identifier, result_tuple)
            else:
                found_count += 1

        # Transform client_format_results into the executor's expected format
        final_primary_ids_set = set()
        final_input_to_primary = {}
        final_errors = []

        for original_id, result_tuple_val in client_format_results.items():
            mapped_ids_list, _ = result_tuple_val # We don't need successful_component for the final structure here
            if mapped_ids_list and len(mapped_ids_list) > 0:
                # Take the first mapped ID as the primary one for this input
                primary_mapped_id = mapped_ids_list[0]
                final_primary_ids_set.add(primary_mapped_id) # Add to set of all unique mapped IDs
                final_input_to_primary[original_id] = primary_mapped_id # Map input to its primary
            else:
                final_errors.append({
                    'input_id': original_id,
                    'error_type': 'NO_MAPPING_FOUND',
                    'message': f'No Arivale mapping found for {original_id}'
                })

        logger.info(
            f"Arivale Lookup: Mapped {len(final_input_to_primary)} (found) / {len(final_errors)} (missed) out of {len(identifiers)} "
            f"input identifiers. Cache hits: {cache_hit_count}/{len(identifiers)}"
        )
        
        return {
            'primary_ids': list(final_primary_ids_set),
            'input_to_primary': final_input_to_primary,
            'secondary_ids': {}, # Arivale client doesn't produce secondary IDs in this context
            'errors': final_errors
        }
        
    async def reverse_map_identifiers(
        self, identifiers: List[str], config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Map identifiers in the reverse direction (from Arivale IDs to source IDs).
        
        Args:
            identifiers: List of Arivale identifiers to map back to source identifiers.
            config: Optional configuration overrides for this specific call.
            
        Returns:
            A dictionary in the format expected by MappingExecutor:
            {
                'primary_ids': List of unique successfully mapped source (e.g., UniProtKB) IDs,
                'input_to_primary': Dict mapping original Arivale ID to its FIRST mapped source ID,
                'errors': List of dicts for Arivale IDs that could not be reverse mapped.
            }
        """
        if not self._initialized:
            raise ClientExecutionError(
                "Client not properly initialized",
                client_name=self.__class__.__name__
            )
            
        if hasattr(self, "_cache_preload_needed") and self._cache_preload_needed:
            await self._preload_cache()
            self._cache_preload_needed = False
            
        # Temporary dict to hold results in the client's original format
        client_format_results: Dict[str, Tuple[Optional[List[str]], Optional[str]]] = {}
        miss_count = 0
        found_count = 0
        
        for identifier in identifiers:
            identifier_processed = identifier.strip().strip('"')  # Apply .strip('"') here
            
            if identifier_processed in self._reverse_lookup_map:
                client_format_results[identifier] = self.format_result(
                    self._reverse_lookup_map[identifier_processed], # Use identifier_processed
                    identifier_processed  # Use identifier_processed as the 'successful_input_id'
                )
                found_count += 1
            else:
                client_format_results[identifier] = self.format_result(None, None)
                miss_count += 1
                
        # Transform client_format_results into the executor's expected format
        final_primary_ids_set = set()
        final_input_to_primary = {}
        final_errors = []

        for original_arivale_id, result_tuple_val in client_format_results.items():
            mapped_source_ids_list, _ = result_tuple_val # We don't need successful_component for reverse map
            if mapped_source_ids_list and len(mapped_source_ids_list) > 0:
                # Take the first mapped source ID as the primary one for this input
                primary_mapped_source_id = mapped_source_ids_list[0]
                final_primary_ids_set.add(primary_mapped_source_id)
                final_input_to_primary[original_arivale_id] = primary_mapped_source_id
            else:
                final_errors.append({
                    'input_id': original_arivale_id,
                    'error_type': 'NO_REVERSE_MAPPING_FOUND',
                    'message': f'No reverse Arivale mapping found for {original_arivale_id}'
                })

        logger.info(
            f"Arivale Reverse Lookup: Mapped {len(final_input_to_primary)} (found) / {len(final_errors)} (missed) "
            f"out of {len(identifiers)} input identifiers."
        )
        
        return {
            'primary_ids': list(final_primary_ids_set),
            'input_to_primary': final_input_to_primary,
            'secondary_ids': {}, # Not applicable for this reverse lookup client
            'errors': final_errors
        }

# Ensure the client is registered if this file is imported directly for testing or other purposes