import asyncio
import logging
import pandas as pd
import csv
from typing import Dict, List, Optional, Any
from pathlib import Path

logger = logging.getLogger(__name__)

class ArivaleMetadataLookupClient:
    """Client to map identifiers using a direct lookup from a local metadata file."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initializes the client and loads the lookup map from the file.

        Args:
            config: Configuration dictionary containing:
                - file_path (str): Path to the TSV metadata file.
                - key_column (str): Column name containing the source identifiers (e.g., UniProt ACs).
                - value_column (str): Column name containing the target identifiers (e.g., Arivale Protein IDs).
        """
        self._lookup_map: Dict[str, str] = {}
        self._config = config or {}

        file_path = self._config.get("file_path")
        key_column = self._config.get("key_column")
        value_column = self._config.get("value_column")

        if not all([file_path, key_column, value_column]):
            logger.error(
                f"{self.__class__.__name__}: Missing required configuration: 'file_path', 'key_column', or 'value_column'"
            )
            # Consider raising an error or handling this state more explicitly
            return

        logger.debug(f"ArivaleMetadataLookupClient loading mapping from {file_path}")
        try:
            logger.info(f"Loading Arivale lookup map from {file_path}")
            self._file_path = Path(file_path)
            if not self._file_path.is_file():
                raise FileNotFoundError(f"Arivale lookup file not found: {self._file_path}")

            # Find header row, skipping comments
            header_line_num = 0
            with open(self._file_path, 'r', encoding='utf-8') as f:
                for i, line in enumerate(f):
                    if not line.strip().startswith('#'):
                        header_line_num = i
                        break

            df = pd.read_csv(
                self._file_path,
                sep='\t',
                skiprows=header_line_num,
                quoting=csv.QUOTE_ALL, # Match check script
                on_bad_lines='warn'
            )
            logger.debug(f"Arivale client loaded columns: {df.columns.tolist()} using quoting=QUOTE_ALL")

            # Verify exact column names seen by pandas
            uniprot_col_name = 'uniprot' # Assume no quotes based on check script
            name_col_name = 'name'       # Assume no quotes based on check script
            if uniprot_col_name not in df.columns or name_col_name not in df.columns:
                logger.error(f"Required columns '{uniprot_col_name}' or '{name_col_name}' not found in DataFrame. Columns: {df.columns.tolist()}")
                raise ValueError("Missing required columns after loading Arivale data.")

            # Populate the lookup map
            for _, row in df.iterrows():
                # Access columns *without* extra quotes in the name
                uniprot_val_raw = str(row[uniprot_col_name]) 
                name_val_raw = str(row[name_col_name])
                
                # Check for null/empty UniProt ID *before* stripping
                if pd.isna(uniprot_val_raw) or not str(uniprot_val_raw).strip():
                    continue # Skip row if UniProt ID is missing or empty
                
                # Strip whitespace and surrounding quotes
                key_val = uniprot_val_raw.strip().strip('"')
                value_val = name_val_raw.strip().strip('"')

                # Treat the entire stripped key_val as the key, do not split.
                # This matches the check script and UKBB loading logic.
                k = key_val.strip()
                if k: # Ensure key is not empty after stripping
                    if k in self._lookup_map:
                        if self._lookup_map[k] != value_val:
                            logger.warning(f"Duplicate key '{k}' found in {file_path}. Keeping first value '{self._lookup_map[k]}', ignoring '{value_val}'.")
                    else:
                        self._lookup_map[k] = value_val
                        
            logger.info(f"Loaded {len(self._lookup_map)} unique key-value pairs into lookup map.")

        except FileNotFoundError:
            logger.error(f"{self.__class__.__name__}: Metadata file not found at {file_path}")
            # Consider raising an error
        except KeyError as e:
            logger.error(f"{self.__class__.__name__}: Column error in {file_path}: {e}. Check if header names need quotes in 'usecols'.")
        except Exception as e:
            logger.error(f"{self.__class__.__name__}: Failed to load lookup map from {file_path}: {e}")
            # Consider raising an error

    async def map_identifiers(
        self, identifiers: List[str], config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, List[str]]:
        """Maps input identifiers (e.g., UniProt ACs) to target identifiers (e.g., Arivale Protein IDs)
           using the preloaded lookup map.

        Args:
            identifiers: A list of source identifiers to map.
            config: Optional configuration (not typically used by this client post-init,
                    but included for interface compatibility).

        Returns:
            A dictionary where keys are the input identifiers found in the map,
            and values are lists containing the single corresponding target identifier.
            Identifiers not found in the map are excluded.
        """
        logger.debug(f"ArivaleMetadataLookupClient received {len(identifiers)} IDs to map: {identifiers[:10]}...")
        if not self._lookup_map:
            logger.error("Arivale mapping data failed to load. Cannot map identifiers.")
            return {identifier: None for identifier in identifiers}

        await asyncio.sleep(0) # Yield control briefly

        results: Dict[str, List[str]] = {}

        found_count = 0
        miss_count = 0
        logged_miss_details = False # Flag to log details only once
        sample_keys_logged = False # Flag to log sample keys only once

        if self._lookup_map:
             sample_map_keys_repr = [repr(k) for k in list(self._lookup_map.keys())[:5]]
             logger.debug(f"Sample map keys (repr): {sample_map_keys_repr}")
             logger.debug(f"Type of first map key: {type(list(self._lookup_map.keys())[0]) if self._lookup_map else 'N/A'}")

        for i, identifier in enumerate(identifiers):
            identifier_stripped = identifier.strip() # Ensure input is also stripped

            if identifier_stripped in self._lookup_map:
                results[identifier] = [self._lookup_map[identifier_stripped]] # Use original identifier as key in results
                found_count += 1
            else:
                miss_count += 1
                if miss_count < 5: 
                    logger.debug(f"Arivale lookup MISS: Identifier '{identifier}' (stripped: '{identifier_stripped}') not in map.")
                    found_case_insensitive = False
                    for key in self._lookup_map.keys():
                        if key.lower() == identifier_stripped.lower():
                            logger.debug(f"  -> Found case-insensitive match: Map key '{key}' vs Input '{identifier_stripped}'")
                            found_case_insensitive = True
                            break
                    if not found_case_insensitive:
                         logger.debug(f"  -> No case-insensitive match found either.")

        logger.info(f"Arivale Lookup: Mapped {found_count} (found) / {miss_count} (missed) out of {len(identifiers)} input identifiers.")
        return results
