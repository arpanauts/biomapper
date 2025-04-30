import asyncio
import logging
import pandas as pd
from typing import Dict, List, Optional, Any

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

        try:
            logger.info(f"Loading Arivale lookup map from {file_path}")
            df = pd.read_csv(file_path, sep='\t', usecols=[key_column, value_column], comment='#')
            df = df.dropna(subset=[key_column, value_column])

            for _, row in df.iterrows():
                key_val = str(row[key_column])
                value_val = str(row[value_column])
                # Handle potentially multiple keys in the key_column, separated by comma/semicolon/space
                keys = [k.strip() for k in key_val.replace(';', ',').replace(' ', ',').split(',') if k.strip()]
                for k in keys:
                    if k in self._lookup_map:
                        # Decide on handling duplicates: log warning, overwrite, skip?
                        # For now, log a warning and keep the first value encountered.
                        if self._lookup_map[k] != value_val:
                             logger.warning(f"Duplicate key '{k}' found in {file_path}. Keeping first value '{self._lookup_map[k]}', ignoring '{value_val}'.")
                    else:
                        self._lookup_map[k] = value_val
            logger.info(f"Loaded {len(self._lookup_map)} unique key-value pairs into lookup map.")

        except FileNotFoundError:
            logger.error(f"{self.__class__.__name__}: Metadata file not found at {file_path}")
            # Consider raising an error
        except KeyError as e:
            logger.error(f"{self.__class__.__name__}: Column error in {file_path}: {e}")
            # Consider raising an error
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
        # This operation is CPU-bound (dictionary lookup), so no real async benefit,
        # but keep the async signature for compatibility with MappingExecutor.
        await asyncio.sleep(0) # Yield control briefly

        results: Dict[str, List[str]] = {}
        for identifier in identifiers:
            if identifier in self._lookup_map:
                results[identifier] = [self._lookup_map[identifier]]
            else:
                # Log missing identifiers if needed (might be verbose)
                # logger.debug(f"Identifier '{identifier}' not found in Arivale lookup map.")
                pass

        logger.info(f"Arivale Lookup: Mapped {len(results)} out of {len(identifiers)} input identifiers.")
        return results
