# /home/ubuntu/biomapper/biomapper/mapping/clients/uniprot_name_client.py
import requests
import logging
from typing import Optional, Dict, Any, Tuple
import asyncio

# TODO: Import or define UniProtConfig, potentially adapting from uniprot_focused_mapper.py
# TODO: Decide on async vs sync session based on executor integration

logger = logging.getLogger(__name__)

class UniProtNameClient:
    """
    Client for searching UniProtKB by protein/gene name or symbol
    to find UniProt Accession IDs. Intended to back the 'UniProt_NameSearch'
    MappingResource.
    """
    # Placeholder for config - replace with actual config class later
    DEFAULT_CONFIG = {
        "base_url": "https://rest.uniprot.org",
        "timeout": 30,
        "max_retries": 3, # Add retries config if needed
        "polling_interval": 3 # Add polling if needed for async jobs
    }

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = self.DEFAULT_CONFIG.copy()
        if config:
            self.config.update(config) # Allow overriding defaults
        # TODO: Define self.session (requests.Session or aiohttp.ClientSession)
        self.session = self._create_session() # Placeholder
        self.search_url = f"{self.config['base_url']}/uniprotkb/search"

    def _create_session(self) -> requests.Session:
        # Placeholder: Implement session creation with potential retries
        # Adapt from uniprot_focused_mapper.py if suitable
        session = requests.Session()
        # Add retry logic here if needed
        return session

    # Consider making this async if the executor calls it asynchronously
    async def find_uniprot_id(self, name: str, organism_id: Optional[int] = 9606) -> Tuple[Optional[str], float]:
        """
        Searches UniProtKB for a given name/symbol and returns the top UniProtKB AC.

        Args:
            name: The protein name or gene symbol to search for.
            organism_id: NCBI taxonomy ID for filtering (default: 9606 for Human).
                         Set to None to disable organism filtering.

        Returns:
            A tuple containing the primary UniProtKB Accession ID (e.g., 'P05067') and
            a confidence score (1.0 for success, 0.0 otherwise), or (None, 0.0).
            Handles potential multiple matches by returning the first/best hit.
        """
        # Construct query robustly, handling potential special characters if needed
        # Ensure field names (gene, protein_name) are correct per UniProt API docs
        # Removed invalid 'name' field based on API error response
        query_parts = [f'(gene:{name} OR protein_name:{name})']
        if organism_id:
            query_parts.append(f'organism_id:{organism_id}')
        # Add filter for reviewed (Swiss-Prot) entries
        query_parts.append('reviewed:true')

        # Use 'AND' operator to combine terms
        query = " AND ".join(f"({part})" for part in query_parts)

        # Inner synchronous function to perform the actual request
        def _sync_request():
            params = {
                "query": query,
                "fields": "accession,gene_primary", # Request accession and primary gene name
                "format": "json",
                "size": 1 # Only need the top hit for the simplest case
            }
            try:
                logger.debug(f"Querying UniProt Search API: {self.search_url} with params: {params}")
                # Use the existing synchronous session
                response = self.session.get(
                    self.search_url,
                    params=params,
                    timeout=self.config['timeout']
                )
                response.raise_for_status()
                results = response.json()
                logger.debug(f"UniProt Search API response: {results}")

                if results and "results" in results and len(results["results"]) > 0:
                    # Extract primary accession from the first result
                    primary_accession = results["results"][0].get("primaryAccession")
                    if primary_accession:
                        logger.info(f"Found UniProt ID {primary_accession} for name '{name}'")
                        return primary_accession, 1.0
                    else:
                        logger.warning(f"No primaryAccession found in UniProt result for name '{name}'")
                        return None, 0.0
                else:
                    logger.warning(f"No results found in UniProt for name '{name}' with query '{query}'")
                    return None, 0.0
            except requests.exceptions.HTTPError as e:
                logger.error(f"HTTP error querying UniProt Search API for name '{name}': {e} - Response: {e.response.text}")
                return None, 0.0
            except requests.exceptions.RequestException as e:
                logger.error(f"Request error querying UniProt Search API for name '{name}': {e}")
                return None, 0.0
            except Exception as e:
                logger.exception(f"Unexpected error querying UniProt Search API for name '{name}': {e}") # Use logger.exception to include traceback
                return None, 0.0

        # Run the synchronous request function in a separate thread
        try:
            result = await asyncio.to_thread(_sync_request)
            return result
        except Exception as e:
            logger.error(f"Error running UniProt search request in thread: {e}", exc_info=True)
            return None, 0.0

    def close_session(self):
        """Close the underlying requests session."""
        # TODO: Implement proper session closing if using aiohttp
        if self.session:
            self.session.close()

# Example Usage (Optional - for testing)
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    client = UniProtNameClient()
    test_name = "APP" # Amyloid precursor protein
    uniprot_id = client.find_uniprot_id(test_name)
    if uniprot_id:
        print(f"Found UniProt ID for {test_name}: {uniprot_id}") # Expected: P05067
    else:
        print(f"Could not find UniProt ID for {test_name}")

    test_name_fail = "NonExistentProteinXYZ"
    uniprot_id_fail = client.find_uniprot_id(test_name_fail)
    if not uniprot_id_fail:
        print(f"Correctly failed to find UniProt ID for {test_name_fail}")

    client.close_session()
