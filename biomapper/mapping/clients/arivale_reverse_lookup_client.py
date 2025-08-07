"""Client to map identifiers in reverse direction using a direct lookup from a local metadata file.

This client is specialized for reverse mapping (from Arivale IDs to UniProt IDs)
and builds on the same infrastructure as the forward mapping client.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple

from biomapper.core.exceptions import ClientExecutionError
from biomapper.mapping.clients.base_client import (
    BaseMappingClient,
    CachedMappingClientMixin,
    FileLookupClientMixin,
)
from biomapper.mapping.clients.arivale_lookup_client import ArivaleMetadataLookupClient

logger = logging.getLogger(__name__)


class ArivaleReverseLookupClient(
    CachedMappingClientMixin, FileLookupClientMixin, BaseMappingClient
):
    """Client to map identifiers in reverse direction (from Arivale IDs to UniProt IDs).

    This client reuses the ArivaleMetadataLookupClient infrastructure but specializes
    in reverse mapping. It's more efficient to use this client for reverse mapping
    than to create a regular ArivaleMetadataLookupClient and call reverse_map_identifiers.
    """

    def __init__(
        self, config: Optional[Dict[str, Any]] = None, cache_size: int = 10000
    ):
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

        # Internally use the ArivaleMetadataLookupClient to handle the file loading logic
        # This avoids duplicating the file parsing code
        self._forward_client = ArivaleMetadataLookupClient(config=config)

        # Mark as initialized once the forward client is ready
        self._initialized = self._forward_client._initialized

    async def map_identifiers(
        self, identifiers: List[str], config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Tuple[Optional[List[str]], Optional[str]]]:
        """Map Arivale identifiers to UniProt identifiers.

        Args:
            identifiers: List of Arivale identifiers to map to UniProt IDs.
            config: Optional configuration overrides for this specific call.

        Returns:
            Dictionary mapping original Arivale IDs to a tuple:
            (list of mapped UniProt IDs or None, the target Arivale ID that yielded the match or None).
        """
        if not self._initialized:
            raise ClientExecutionError(
                "Client not properly initialized", client_name=self.__class__.__name__
            )

        # Delegate to the forward client's reverse mapping method
        return await self._forward_client.reverse_map_identifiers(identifiers, config)

    async def reverse_map_identifiers(
        self, identifiers: List[str], config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Tuple[Optional[List[str]], Optional[str]]]:
        """Map UniProt identifiers to Arivale identifiers (forward mapping).

        This method implements the forward mapping direction for this client,
        which is actually the reverse of its primary purpose.

        Args:
            identifiers: List of UniProt identifiers to map to Arivale IDs.
            config: Optional configuration overrides for this specific call.

        Returns:
            Dictionary mapping original UniProt IDs to a tuple:
            (list of mapped Arivale IDs or None, the source UniProt ID that yielded the match or None).
        """
        if not self._initialized:
            raise ClientExecutionError(
                "Client not properly initialized", client_name=self.__class__.__name__
            )

        # Delegate to the forward client's forward mapping method
        return await self._forward_client.map_identifiers(identifiers, config)
