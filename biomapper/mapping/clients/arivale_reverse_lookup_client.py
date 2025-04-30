import asyncio
import logging
import pandas as pd
import csv
from typing import Dict, List, Optional, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class ArivaleReverseLookupClient:
    """Client to map Arivale Protein IDs back to UniProt IDs using the metadata file."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initializes the client and loads the reverse lookup map from the file.

        Args:
            config: Configuration dictionary containing:
                - file_path (str): Path to the TSV metadata file.
                - key_column (str): Column name containing Arivale Protein IDs ('name').
                - value_column (str): Column name containing UniProt IDs ('uniprot').
        """
        self._lookup_map: Dict[str, str] = {}
        self._config = config or {}

        file_path = self._config.get("file_path")
        # These config keys define how the client *interprets* the data for mapping,
        # but the actual column names from the file are hardcoded below for loading.
        # key_column = self._config.get("key_column") # Config key for input ID type (Arivale name)
        # value_column = self._config.get("value_column") # Config key for output ID type (UniProt)

        if not file_path:
            logger.error(
                f"{self.__class__.__name__}: Missing required configuration: 'file_path'"
            )
            return

        logger.debug(f"ArivaleReverseLookupClient loading reverse mapping from {file_path}")
        try:
            logger.info(f"Loading Arivale reverse lookup map from {file_path}")
            self._file_path = Path(file_path)
            if not self._file_path.is_file():
                raise FileNotFoundError(
                    f"Arivale reverse lookup file not found: {self._file_path}"
                )

            # Find header row, skipping comments
            header_line_num = 0
            with open(self._file_path, "r", encoding="utf-8") as f:
                for i, line in enumerate(f):
                    if not line.strip().startswith("#"):
                        header_line_num = i
                        break

            df = pd.read_csv(
                self._file_path,
                sep="\t",
                skiprows=header_line_num,
                quoting=csv.QUOTE_ALL,
                on_bad_lines="warn",
            )
            logger.debug(
                f"Arivale reverse client loaded columns: {df.columns.tolist()}"
            )

            # Define the columns we need from the file
            key_col_from_file = "name" # Arivale ID is the key for reverse lookup
            value_col_from_file = "uniprot" # UniProt ID is the value

            if key_col_from_file not in df.columns or value_col_from_file not in df.columns:
                logger.error(
                    f"Required columns '{key_col_from_file}' or '{value_col_from_file}' not found. Columns: {df.columns.tolist()}"
                )
                raise ValueError("Missing required columns for Arivale reverse lookup.")

            # Populate the reverse lookup map
            duplicates_found = 0
            for _, row in df.iterrows():
                key_val_raw = str(row[key_col_from_file])
                value_val_raw = str(row[value_col_from_file])

                # Skip if key (Arivale ID) or value (UniProt ID) is missing/empty
                if pd.isna(key_val_raw) or not str(key_val_raw).strip() or \
                   pd.isna(value_val_raw) or not str(value_val_raw).strip():
                    continue

                # Strip whitespace and surrounding quotes
                key_val = key_val_raw.strip().strip('"')
                value_val = value_val_raw.strip().strip('"')

                k = key_val.strip() # Key is Arivale ID
                v = value_val.strip() # Value is UniProt ID

                if k: # Ensure key is not empty
                    if k in self._lookup_map:
                        duplicates_found += 1
                        # In reverse map, multiple Arivale IDs might map to the *same* UniProt ID, which is fine.
                        # But a single Arivale ID should map to only one UniProt ID.
                        # If we find a duplicate Arivale ID, log a warning like the original client.
                        if self._lookup_map[k] != v:
                             logger.warning(
                                f"Duplicate key (Arivale ID) '{k}' found in {self._file_path}. "
                                f"Keeping first value '{self._lookup_map[k]}', ignoring '{v}'."
                            )
                    else:
                        self._lookup_map[k] = v
            
            if duplicates_found > 0:
                 logger.warning(f"Found {duplicates_found} duplicate Arivale IDs (keys) while building reverse map.")

            logger.info(
                f"Loaded {len(self._lookup_map)} unique key-value pairs into reverse lookup map."
            )

        except FileNotFoundError:
            logger.error(
                f"{self.__class__.__name__}: Metadata file not found at {file_path}"
            )
        except KeyError as e:
            logger.error(
                f"{self.__class__.__name__}: Column error in {file_path}: {e}."
            )
        except Exception as e:
            logger.error(
                f"{self.__class__.__name__}: Failed to load reverse lookup map from {file_path}: {e}", exc_info=True
            )

    async def map_identifiers(
        self, identifiers: List[str], config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, List[str]]:
        """Maps input Arivale Protein IDs to UniProt IDs using the preloaded map.

        Args:
            identifiers: A list of Arivale Protein IDs to map.
            config: Optional configuration.

        Returns:
            A dictionary where keys are the input Arivale IDs found, and values
            are lists containing the single corresponding UniProt ID.
        """
        logger.debug(
            f"ArivaleReverseLookupClient received {len(identifiers)} IDs to map: {identifiers[:10]}..."
        )
        if not self._lookup_map:
            logger.error("Arivale reverse mapping data failed to load. Cannot map identifiers.")
            return {identifier: None for identifier in identifiers}

        await asyncio.sleep(0)

        results: Dict[str, List[str]] = {}
        found_count = 0
        miss_count = 0

        for i, identifier in enumerate(identifiers):
            identifier_stripped = identifier.strip() # Key is Arivale ID

            if identifier_stripped in self._lookup_map:
                results[identifier] = [
                    self._lookup_map[identifier_stripped]
                ] # Value is UniProt ID
                found_count += 1
            else:
                miss_count += 1
                if miss_count < 5:
                     logger.debug(
                        f"Arivale reverse lookup MISS: Identifier '{identifier}' (stripped: '{identifier_stripped}') not in map."
                    )

        logger.info(
            f"Arivale Reverse Lookup: Mapped {found_count} (found) / {miss_count} (missed) out of {len(identifiers)} input identifiers."
        )
        return results
