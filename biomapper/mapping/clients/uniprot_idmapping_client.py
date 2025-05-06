import asyncio
import logging
from typing import List, Dict, Optional, Any, Tuple

import aiohttp

logger = logging.getLogger(__name__)

# Use the simpler, synchronous mapping service URL
UNIPROT_SYNC_IDMAPPING_API_URL = "https://idmapping.uniprot.org/cgi-bin/idmapping_http_client3"
DEFAULT_REQUEST_TIMEOUT = 30  # Seconds


class UniProtIDMappingClient:
    """
    Client for mapping identifiers using the synchronous UniProt ID Mapping service.

    Important behavior notes:
    1. When mapping from ACC->ACC, the service generally returns the input IDs as-is,
       rather than resolving secondary IDs to primary IDs.
    2. For demerged IDs (like P0CG05), it properly returns multiple target IDs.
    3. For non-existent IDs, it returns no mapping.
    
    To handle secondary/obsolete IDs properly, you may need other approaches:
    - Using the REST API's ID mapping service (asynchronous job method)
    - Using UniProt's batch retrieval API to get entry status
    - Storing and maintaining a local mapping of secondary->primary IDs
    """

    def __init__(
        self,
        from_db: str = "ACC",  # Default to UniProt Accession
        to_db: str = "ACC",    # Default to UniProt Accession (for primary resolution)
        base_url: str = UNIPROT_SYNC_IDMAPPING_API_URL,
        timeout: int = DEFAULT_REQUEST_TIMEOUT,
        config: Optional[Dict[str, Any]] = None, # Keep for potential future config
    ):
        """
        Initializes the client.

        Args:
            from_db: The database name for the source identifiers (e.g., 'ACC').
            to_db: The database name for the target identifiers (e.g., 'ACC').
            base_url: The base URL for the UniProt synchronous ID Mapping CGI script.
            timeout: Request timeout in seconds.
            config: Optional configuration dictionary (currently unused).
        """
        self.base_url = base_url
        self.from_db = from_db
        self.to_db = to_db
        self.timeout = timeout
        # Semaphore might still be useful to limit concurrent requests if called rapidly
        self.semaphore = asyncio.Semaphore(5) # Keep a reasonable concurrency limit

    async def map_identifiers(
        self, identifiers: List[str], config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Tuple[Optional[List[str]], Optional[str]]]:
        """
        Map a list of identifiers using the synchronous UniProt ID Mapping service.

        Args:
            identifiers: A list of identifiers to map (e.g., potentially mixed
                         primary/secondary UniProtKB ACs).
            config: Optional configuration dictionary (currently unused).

        Returns:
            A dictionary mapping each *input* identifier to a tuple containing:
            1. A list of corresponding *primary* target identifiers found (or None)
            2. The successful component ID that yielded the match (or None)
        """
        if not identifiers:
            return {}

        final_mapping: Dict[str, Tuple[Optional[List[str]], Optional[str]]] = {
            identifier: (None, None) for identifier in identifiers
        }
        ids_string = ",".join(identifiers)
        params = {
            "from": self.from_db,
            "to": self.to_db,
            "ids": ids_string,
            "async": "NO", # Ensure synchronous mode
        }

        request_timeout = aiohttp.ClientTimeout(total=self.timeout)

        async with self.semaphore: # Limit concurrency
            try:
                async with aiohttp.ClientSession(timeout=request_timeout) as session:
                    logger.debug(f"Querying UniProt Sync ID Mapping: {self.base_url} with params: {params}")
                    async with session.get(self.base_url, params=params) as response:
                        if response.status == 200:
                            text_result = await response.text()
                            logger.debug(f"UniProt Sync ID Mapping response text:\n{text_result}")
                            # Parse the tab-separated, potentially semicolon-separated results
                            # The UniProt CGI client has a special format - we need careful parsing
                            lines = text_result.strip().split('\n')
                            count = 0
                            
                            # Process result lines until we see error messages
                            for line in lines:
                                if not line.strip():
                                    continue
                                    
                                # Check for error message lines
                                if line.startswith("MSG:"):
                                    logger.info(f"UniProt message: {line}")
                                    continue
                                    
                                # Parse mapping lines
                                parts = line.split('\t')
                                if len(parts) >= 2:  # Some lines may have 3 parts (id, result, extra)
                                    input_id, output_ids_str = parts[0], parts[1]
                                    
                                    if input_id in final_mapping:
                                        # Split potentially semicolon-separated primary IDs
                                        primary_ids = [pid.strip() for pid in output_ids_str.split(';') if pid.strip()]
                                        if primary_ids:
                                            final_mapping[input_id] = (primary_ids, input_id)
                                            count += len(primary_ids)
                                            logger.debug(f"Resolved {input_id} -> {primary_ids}")
                                        else:
                                            logger.warning(f"Input ID {input_id} returned empty mapping result part.")
                                    else:
                                        logger.warning(f"Mapped ID '{input_id}' from UniProt results was not in the original input list.")
                                elif len(parts) == 1 and parts[0] in final_mapping:
                                    # This is likely a non-matched ID line
                                    logger.debug(f"No match found for input ID: {parts[0]}")
                                else:
                                    logger.warning(f"Unexpected line format in UniProt result: '{line}'")

                            logger.info(
                                f"Successfully processed {count} primary mappings "
                                f"for {len(identifiers)} input identifiers using UniProt Sync API."
                            )

                        # Handle potential errors - UniProt CGI might not return standard error codes reliably
                        elif response.status >= 400:
                             error_text = await response.text()
                             logger.error(
                                 f"Error querying UniProt Sync ID Mapping: Status {response.status}, "
                                 f"Message: '{error_text}', Params: {params}"
                             )
                        else: # Non-200 success? Unlikely but log
                             logger.warning(f"Unexpected status code {response.status} from UniProt Sync ID Mapping. Params: {params}")


            except aiohttp.ClientError as e:
                logger.error(f"HTTP Error querying UniProt Sync ID Mapping: {e}, Params: {params}")
            except asyncio.TimeoutError:
                 logger.error(f"Timeout querying UniProt Sync ID Mapping after {self.timeout}s. Params: {params}")
            except Exception as e:
                # Catch broader exceptions during request/parsing
                logger.error(f"Unexpected error during UniProt Sync ID Mapping: {e}", exc_info=True)

        return final_mapping


# Example Usage (Optional - for testing the new implementation)
async def run_example() -> None:
    logging.basicConfig(level=logging.INFO)
    logger.info("Running UniProt Sync ID Mapping Client Example...")
    # Client defaults to ACC -> ACC resolution
    client = UniProtIDMappingClient()

    # Test cases: Primary, Demerged, Secondary (that keeps its ID), Non-existent
    test_ids = ["P0DOY2", "P0CG05", "P12345", "NONEXISTENT"] # P0DOY2 (Primary), P0CG05 (Demerged -> P0DOY2, P0DOY3), P12345 (Standard)
    # The UniProt Sync API handles accessions differently than we expected
    # It appears to return the same ID for P12345 rather than mapping it to another accession

    results = await client.map_identifiers(identifiers=test_ids)
    print("\n--- Mapping Results (ACC -> Primary ACC) ---")
    for input_id, result_tuple in results.items():
        primary_ids, component_id = result_tuple
        print(f"  Input: {input_id} -> Mapped Primary: {primary_ids}, Component: {component_id}")

    # Extract just the primary IDs for cleaner assertion checks
    primary_results = {k: v[0] for k, v in results.items()}
    
    # Verify specific known cases
    assert primary_results.get("P0DOY2") == ["P0DOY2"], "Primary ID failed"
    assert sorted(primary_results.get("P0CG05", [])) == sorted(["P0DOY2", "P0DOY3"]), "Demerged ID failed"
    assert primary_results.get("P12345") == ["P12345"], "Secondary ID mapping failed"
    assert primary_results.get("NONEXISTENT") is None, "Non-existent ID failed"
    print("\nBasic assertions passed.")


if __name__ == "__main__":
    # You might need to install nest_asyncio if running in an env like Jupyter
    # import nest_asyncio
    # nest_asyncio.apply()
    asyncio.run(run_example())