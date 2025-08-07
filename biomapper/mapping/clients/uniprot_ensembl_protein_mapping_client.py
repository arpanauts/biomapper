"""Client for mapping Ensembl Protein IDs (ENSP...) to UniProtKB accession numbers using UniProt's ID Mapping API.

This client supports mapping from Ensembl_Protein database to UniProtKB accessions.
It handles proper formatting of Ensembl Protein IDs and provides detailed error reporting.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple

from biomapper.mapping.clients.uniprot_idmapping_client import UniProtIDMappingClient

logger = logging.getLogger(__name__)


class UniProtEnsemblProteinMappingClient(UniProtIDMappingClient):
    """Client for mapping Ensembl Protein IDs (ENSP...) to UniProtKB accession numbers.

    Extends the base UniProtIDMappingClient with specific configuration for the
    Ensembl Protein ID to UniProtKB accession mapping.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the client with configuration for mapping Ensembl Protein IDs to UniProtKB.

        Args:
            config: Optional configuration dictionary.
                   If provided, it can override the default from_db and to_db settings.
        """
        # Use the provided config or create a new one
        merged_config = config or {}

        # Set the default mapping direction: Ensembl Protein IDs → UniProtKB
        # Override only if not explicitly provided in config
        if "from_db" not in merged_config:
            merged_config[
                "from_db"
            ] = "Ensembl_Protein"  # Correct db name based on API testing
        if "to_db" not in merged_config:
            merged_config["to_db"] = "UniProtKB"  # Correct db name based on API testing

        # Extract parent class parameters from config
        parent_kwargs = {
            "from_db": merged_config.pop("from_db"),
            "to_db": merged_config.pop("to_db"),
        }

        # Add optional parameters if present in config
        if "base_url" in merged_config:
            parent_kwargs["base_url"] = merged_config.pop("base_url")
        if "timeout" in merged_config:
            parent_kwargs["timeout"] = merged_config.pop("timeout")
        if "session" in merged_config:
            parent_kwargs["session"] = merged_config.pop("session")

        # Initialize the parent class with our configuration
        super().__init__(**parent_kwargs)

        logger.info(
            f"Initialized {self.__class__.__name__} for mapping {self.from_db} to {self.to_db}"
        )

    async def map_identifiers(
        self, identifiers: List[str], config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Tuple[Optional[List[str]], Optional[str]]]:
        """Map Ensembl Protein IDs to UniProtKB accession numbers.

        Args:
            identifiers: List of Ensembl Protein IDs (ENSP...) to map.
            config: Optional additional configuration.

        Returns:
            Dictionary mapping input Ensembl Protein IDs to tuples of:
                - Optional[List[str]]: List of mapped UniProtKB accessions or None if no mapping found
                - Optional[str]: The source component ID that provided the successful mapping or None
        """
        logger.info(
            f"Mapping {len(identifiers)} Ensembl Protein IDs to UniProtKB accessions"
        )

        # Clean up the identifiers to ensure they are valid Ensembl Protein IDs
        # Remove any potential version numbers (e.g., ENSP00000123456.1 -> ENSP00000123456)
        clean_identifiers = []
        id_mapping = {}  # Maps clean IDs back to original IDs

        for identifier in identifiers:
            # Basic validation - must be ENSP followed by numbers
            if not identifier.startswith("ENSP"):
                logger.warning(
                    f"Skipping invalid Ensembl Protein ID format: {identifier}"
                )
                continue

            # Remove version if present
            clean_id = identifier.split(".")[0]
            clean_identifiers.append(clean_id)
            id_mapping[clean_id] = identifier

        if not clean_identifiers:
            logger.warning("No valid Ensembl Protein IDs provided")
            return {identifier: (None, None) for identifier in identifiers}

        # The parent class implementation handles the mapping logic
        # Parent returns Dict[str, Optional[str]] which we need to convert to tuple format
        parent_results = await super().map_identifiers(clean_identifiers, config)

        # Convert parent results (Dict[str, Tuple[Optional[List[str]], Optional[str]]])
        # to tuple format - no conversion needed anymore as parent now returns tuples
        tuple_results = parent_results

        # Map the tuple results back to the original identifiers
        final_results: Dict[str, Tuple[Optional[List[str]], Optional[str]]] = {}
        for orig_id in identifiers:
            clean_id = orig_id.split(".")[0] if orig_id.startswith("ENSP") else orig_id
            final_results[orig_id] = tuple_results.get(clean_id, (None, None))

        # Check if we got no results at all, and log a warning
        if all(v[0] is None for v in final_results.values()):
            logger.warning(
                "No mappings found for any Ensembl Protein IDs. This may indicate an issue with "
                "the IDs provided or the UniProt ID Mapping service. Check that your IDs are valid "
                "and that the service is functioning properly."
            )

        return final_results


# Example Usage (for testing)
async def run_example() -> None:
    """Run a simple example to test the client."""

    logging.basicConfig(level=logging.INFO)

    client = UniProtEnsemblProteinMappingClient()
    # Example Ensembl Protein IDs (ENSP...)
    test_ids = [
        "ENSP00000256509",
        "ENSP00000380628",
        "ENSP00000265371",
        "ENSP00000INVALID",
    ]

    results = await client.map_identifiers(test_ids)

    print("\n--- Mapping Results (Ensembl_PRO -> UniProtKB) ---")
    for ensembl_id, (uniprot_ids, _) in results.items():
        if uniprot_ids:
            print(f"  {ensembl_id}: {', '.join(uniprot_ids)}")
        else:
            print(f"  {ensembl_id}: None")


if __name__ == "__main__":
    import asyncio

    asyncio.run(run_example())
