import asyncio
import logging
import re
from typing import Dict, List, Optional, Tuple

import aiohttp

logger = logging.getLogger(__name__)

# Constants for UniProt API
UNIPROT_API_BASE_URL = "https://rest.uniprot.org"
CONCURRENT_REQUESTS = 10 # Limit concurrent requests to UniProt search

class UniProtNameClient:
    """Client for mapping protein/gene names/symbols to UniProtKB Accession IDs.

    Uses the UniProtKB Search API (/uniprotkb/search).
    Requires a list of gene symbols (e.g., from HGNC) or names.
    Maps them to UniProtKB canonical accession IDs.
    Prioritizes reviewed human entries.
    """

    def __init__(self, base_url: str = UNIPROT_API_BASE_URL, config: Optional[Dict] = None):
        """Initialize the client.
        
        Args:
            base_url: The base URL for the UniProt API.
            config: Optional configuration dictionary (currently unused by this client).
        """
        self.base_url = base_url
        self.semaphore = asyncio.Semaphore(CONCURRENT_REQUESTS)
        # Cache for gene symbol results
        self.cache: Dict[str, Optional[List[str]]] = {}

    async def _search_single_gene(self, session: aiohttp.ClientSession, gene_symbol: str) -> Optional[List[str]]:
        """Search UniProtKB for a single gene symbol and return the top reviewed accession."""
        # Check cache first
        if gene_symbol in self.cache:
            logger.debug(f"Cache hit for gene {gene_symbol}")
            return self.cache[gene_symbol]
            
        query = f'(gene:"{gene_symbol}") AND (organism_id:9606) AND (reviewed:true)'
        params = {
            'query': query,
            'fields': 'accession',
            'format': 'json',
            'size': 1
        }
        search_url = f"{self.base_url}/uniprotkb/search"

        async with self.semaphore: # Limit concurrency
            try:
                async with session.get(search_url, params=params) as response:
                    # Add a small delay to be nice to the API
                    await asyncio.sleep(0.1)
                    response.raise_for_status()
                    data = await response.json()
                    results = data.get('results')
                    if results and len(results) > 0:
                        accession = results[0].get('primaryAccession')
                        logger.debug(f"Found accession {accession} for gene {gene_symbol}")
                        # Store in cache
                        self.cache[gene_symbol] = [accession]
                        # Return as a list containing the single accession
                        return [accession]
                    else:
                        logger.debug(f"No reviewed UniProtKB entry found for gene {gene_symbol}")
                        # Store negative result in cache too
                        self.cache[gene_symbol] = None
                        return None
            except aiohttp.ClientResponseError as e:
                # Log common errors like 400 Bad Request (often malformed query) or 429 Too Many Requests
                logger.warning(f"HTTP error {e.status} searching for gene {gene_symbol}: {e.message}. URL: {e.request_info.url}")
                return None
            except Exception as e:
                logger.error(f"Error searching for gene {gene_symbol}: {e}", exc_info=True)
                return None
    
    def _handle_composite_gene_symbol(self, gene_symbol: str) -> Tuple[bool, List[str]]:
        """Detect and split composite gene symbols (like GENE1_GENE2_GENE3).
        
        Returns:
            Tuple containing: (is_composite, [list_of_individual_genes])
        """
        # Pattern: GENE1_GENE2 or GENE1_GENE2_GENE3
        if '_' in gene_symbol:
            # Split by underscore
            gene_parts = gene_symbol.split('_')
            return True, gene_parts
        return False, [gene_symbol]

    async def _process_composite_gene(self, session: aiohttp.ClientSession, gene_symbol: str) -> Optional[List[str]]:
        """Handle composite gene identifiers by trying each component individually."""
        is_composite, gene_parts = self._handle_composite_gene_symbol(gene_symbol)
        
        if not is_composite:
            # Regular gene symbol
            return await self._search_single_gene(session, gene_symbol)
        
        # Try each component of the composite gene and use the first successful match
        logger.info(f"Processing composite gene symbol: {gene_symbol} → {gene_parts}")
        for part in gene_parts:
            result = await self._search_single_gene(session, part)
            if result:
                logger.info(f"Found match for composite gene {gene_symbol} using component {part}: {result}")
                return result
        
        # If nothing matched, try one more approach - use OR in the query
        # This is less likely to succeed but worth trying
        try:
            query_parts = ' OR '.join([f'gene:"{part}"' for part in gene_parts])
            query = f'({query_parts}) AND (organism_id:9606) AND (reviewed:true)'
            
            params = {
                'query': query,
                'fields': 'accession',
                'format': 'json',
                'size': 1
            }
            search_url = f"{self.base_url}/uniprotkb/search"
            
            async with self.semaphore:
                async with session.get(search_url, params=params) as response:
                    await asyncio.sleep(0.1)
                    response.raise_for_status()
                    data = await response.json()
                    results = data.get('results')
                    if results and len(results) > 0:
                        accession = results[0].get('primaryAccession')
                        logger.info(f"Found composite match for {gene_symbol} using OR query: {accession}")
                        return [accession]
        except Exception as e:
            logger.warning(f"Error in composite OR query for {gene_symbol}: {e}")
        
        logger.warning(f"No match found for any component of composite gene {gene_symbol}")
        return None

    async def map_identifiers(self, identifiers: List[str], config: Optional[Dict] = None) -> Dict[str, Optional[List[str]]]:
        """Map a list of gene symbols/names to UniProtKB ACs using the search API.

        Args:
            identifiers: A list of gene symbols or names (previously 'ids').
            config: Optional configuration dictionary (currently unused by this client).

        Returns:
            A dictionary mapping original IDs to UniProtKB ACs (or None if not found).
        """
        all_results: Dict[str, Optional[List[str]]] = {}
        if not identifiers:
            return {}

        async with aiohttp.ClientSession() as session:
            # Process all gene symbols with the composite handler
            tasks = [self._process_composite_gene(session, gene_id) for gene_id in identifiers]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for original_id, result in zip(identifiers, results):
                if isinstance(result, Exception):
                    logger.error(f"Task for ID {original_id} failed: {result}")
                    all_results[original_id] = None
                elif result is None:
                    # Explicitly store None if search returned no result
                    all_results[original_id] = None
                else:
                    all_results[original_id] = result

        mapped_count = sum(1 for v in all_results.values() if v is not None)
        logger.info(f"Finished UniProt search. Found mappings for {mapped_count}/{len(identifiers)} identifiers.")
        return all_results

# Example Usage (Optional - for testing)
async def run_example():
    logging.basicConfig(level=logging.INFO)
    client = UniProtNameClient()
    # Example gene symbols
    test_ids = ["TP53", "EGFR", "BRCA1", "NONEXISTENTGENE", "AARSD1", "ABHD14B"]
    results = await client.map_identifiers(test_ids)
    print("Mapping Results:")
    for gene, accession in results.items():
        print(f"  {gene}: {accession}")

if __name__ == "__main__":
    asyncio.run(run_example())
