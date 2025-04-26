import asyncio
import logging
import re
import time
from typing import List, Dict, Optional, Any, AsyncGenerator

import aiohttp
import requests

logger = logging.getLogger(__name__)

API_URL = "https://rest.uniprot.org"
POLLING_INTERVAL_S = 3
DEFAULT_TIMEOUT_S = 60

# UniProt ID Mapping limits batch size, though not explicitly stated for /results endpoint
# We'll fetch in batches if pagination is present.

# Helper function to parse Link header for pagination (adapted from sync example)
def get_next_link(headers: Optional[aiohttp.typedefs.LooseHeaders]) -> Optional[str]:
    if not headers or "Link" not in headers:
        return None
    re_next_link = re.compile(r'<(.+)>;\s*rel="next"', re.IGNORECASE)
    match = re_next_link.search(headers["Link"])
    if match:
        return match.group(1)
    return None

class UniProtNameClient:
    """
    Client for mapping protein/gene names or symbols to UniProtKB Accession IDs
    using the UniProt ID Mapping API. Intended to back the 'UniProt_NameSearch'
    MappingResource.
    """

    def __init__(self, timeout: int = DEFAULT_TIMEOUT_S):
        self.base_url = API_URL
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        # Consider adding retry logic to the session if needed
        self.session = aiohttp.ClientSession(timeout=self.timeout)

    async def close_session(self):
        """Close the underlying aiohttp session."""
        await self.session.close()

    async def _submit_job(self, ids: List[str]) -> str:
        """Submit a UniProt ID Mapping API job.

        Args:
            ids: List of gene/protein names to map.

        Returns:
            The job ID string.
        """
        # Note: UniProt documentation suggests using specific database names.
        # 'Gene_Name' is a common identifier type used in examples.
        # 'UniProtKB' is the target for Accession IDs.
        # If this fails, consult https://rest.uniprot.org/configure/idmapping/fields
        from_db = "Gene_Name"
        to_db = "UniProtKB" # Changed from UniProtKB_AC-ID based on docs
        payload = {
            "from": from_db,
            "to": to_db,
            "ids": ",".join(ids),
            "taxIds": "9606" # Added Taxonomy ID for Human
        }
        logger.debug(f"Submitting UniProt ID Mapping payload: {payload}")
        async with self.session.post(f"{self.base_url}/idmapping/run", data=payload) as response:
            response.raise_for_status() # Raise exceptions for 4xx/5xx errors
            data = await response.json()
            job_id = data.get("jobId")
            if not job_id:
                raise ValueError("UniProt ID Mapping API did not return a jobId.")
            logger.debug(f"Submitted UniProt ID Mapping job {job_id} for {len(ids)} names.")
            return job_id

    async def _check_job_status(self, job_id: str) -> bool:
        """Check the status of a submitted job using the /status endpoint."""
        status_url = f"{self.base_url}/idmapping/status/{job_id}"
        try:
            # Use allow_redirects=False to prevent following potential redirects to /details
            async with self.session.get(status_url, allow_redirects=False) as response:
                logger.debug(f"Checking status for job {job_id}. Status URL: {status_url}, Status code: {response.status}")
                response.raise_for_status()

                try:
                    data = await response.json()
                    # Only log the jobStatus, not the whole payload which should be small
                    job_status = data.get("jobStatus")
                    logger.debug(f"Job {job_id} status from API: {job_status}")
                except aiohttp.ContentTypeError:
                    text_response = await response.text()
                    logger.error(f"Job {job_id} status response was not JSON. Status: {response.status}. Response text: {text_response[:100]}...")
                    return False # Treat as error/indeterminate
                except Exception as e:
                    logger.exception(f"Error parsing JSON from status response for job {job_id}", exc_info=True)
                    return False # Treat as error/indeterminate

                if job_status == "FINISHED":
                    logger.debug(f"Job {job_id} reported FINISHED by status endpoint.")
                    return True # Finished
                elif job_status in ["RUNNING", "NEW", "QUEUED"]:
                    logger.debug(f"Job {job_id} status: {job_status}.")
                    return False # Not finished yet
                elif job_status is None:
                    logger.warning(f"Job {job_id} status response missing 'jobStatus'. Full Response: {data}")
                    return False # Treat as indeterminate
                else:
                    # Handle potential failures reported by the status endpoint
                    logger.error(f"Job {job_id} failed or has unexpected status via status endpoint: {job_status}. Response: {data}")
                    # Consider raising an exception or returning False based on desired behavior
                    # For now, returning False to let polling continue/timeout might be safer
                    return False
        except aiohttp.ClientError as e:
            logger.error(f"HTTP error checking status for job {job_id}: {e}")
            return False # Treat HTTP errors during polling as 'not finished'

    async def _get_job_results(self, job_id: str) -> Dict[str, str]:
        """Fetch results for a completed job, following the redirect from /details."""
        details_url = f"{self.base_url}/idmapping/details/{job_id}"
        actual_results_url: Optional[str] = None
        mapped_results = {}
        failed_ids = []

        # 1. Fetch the /details URL to get the redirect URL
        try:
            logger.debug(f"Fetching details for job {job_id} from {details_url} to get redirect URL.")
            async with self.session.get(details_url) as response:
                response.raise_for_status()
                try:
                    details_data = await response.json(content_type=None)
                    actual_results_url = details_data.get("redirectURL")
                    if actual_results_url:
                        logger.debug(f"Got redirect URL for job {job_id}: {actual_results_url}")
                    else:
                        logger.error(f"Job {job_id} details response missing 'redirectURL'. Data: {details_data}")
                        return {}
                except Exception as e:
                    raw_text = await response.text()
                    logger.exception(f"Error parsing JSON from details response for job {job_id}. Status: {response.status}. Response text: {raw_text[:500]}...", exc_info=True)
                    return {}
        except aiohttp.ClientError as e:
            logger.error(f"HTTP error fetching details URL for job {job_id}: {e}")
            return {}
        except Exception as e:
            logger.exception(f"Unexpected error fetching details for job {job_id}", exc_info=True)
            return {}

        # 2. Fetch results from the actual_results_url (handling pagination)
        current_page_url = actual_results_url
        while current_page_url:
            try:
                async with self.session.get(current_page_url) as response:
                    logger.debug(f"Fetching results page for job {job_id} from {current_page_url}. Status: {response.status}")
                    response.raise_for_status()

                    try:
                        data = await response.json(content_type=None) # Use content_type=None for flexibility
                        logger.debug(f"Job {job_id} results PARSED data keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
                    except aiohttp.ContentTypeError:
                        text_response = await response.text()
                        logger.error(f"Job {job_id} results response was not JSON. Status: {response.status}, URL: {current_page_url}. Response text: {text_response[:500]}...")
                        # Cannot proceed if results are not JSON
                        return {} # Return empty or raise an error
                    except Exception as e:
                        logger.exception(f"Error parsing JSON from results response for job {job_id}, URL: {current_page_url}", exc_info=True)
                        return {} # Return empty or raise an error

                    # Process results from the current page
                    current_results = data.get("results", [])
                    logger.debug(f"Job {job_id} found {len(current_results)} result items on this page.")
                    for item in current_results:
                        logger.debug(f"Processing item: {item}") # Log each item
                        original_name = item.get("from")
                        uniprot_data = item.get("to")
                        if original_name and uniprot_data and isinstance(uniprot_data, dict):
                            uniprot_id = uniprot_data.get("primaryAccession")
                            if uniprot_id:
                                # Store only the primary accession for simplicity
                                mapped_results[original_name] = f"UniProtKB:{uniprot_id}"
                            else:
                                logger.warning(f"Missing 'primaryAccession' in result item for '{original_name}': {uniprot_data}")
                        else:
                            logger.warning(f"Invalid result item format: {item}")

                    # Store failed IDs if present in the first page response (should only be in first?)
                    if "failedIds" in data and not failed_ids:
                       failed_ids = data.get("failedIds", [])
                       logger.debug(f"Job {job_id} found failed IDs: {failed_ids}")
                       if failed_ids:
                            logger.info(f"Job {job_id} reported {len(failed_ids)} failed IDs: {failed_ids}")

                    # Check for next page link in headers
                    link_header = response.headers.get("Link")
                    logger.debug(f"Job {job_id} Link header: {link_header}")
                    next_link = None
                    if link_header:
                        links = requests.utils.parse_header_links(link_header)
                        for link in links:
                            if link.get("rel") == "next":
                                next_link = link.get("url")
                                break

                    if next_link:
                        logger.debug(f"Found next page link for job {job_id}: {next_link}")
                        current_page_url = next_link # Continue to next page
                    else:
                        current_page_url = None # No more pages

            except aiohttp.ClientError as e:
                logger.error(f"HTTP error fetching results page for job {job_id} from {current_page_url}: {e}")
                return {} # Return empty on error
            except Exception as e:
                 logger.exception(f"Unexpected error fetching results page for job {job_id}, URL: {current_page_url}", exc_info=True)
                 return {} # Return empty on error

        logger.info(f"Successfully fetched results for job {job_id}. Mapped {len(mapped_results)} IDs.")
        return mapped_results

    async def find_uniprot_ids_by_names(self, names: List[str]) -> Dict[str, str]:
        """Find UniProtKB IDs for a list of gene names."""
        if not self.session or self.session.closed:
            raise ValueError("Client session is closed or not initialized.")

        if not names:
            return {}

        job_id = None
        max_polls = 20 # Limit polling attempts (e.g., 20 * 3s = 1 min timeout)
        poll_count = 0
        try:
            job_id = await self._submit_job(names)

            while poll_count < max_polls:
                await asyncio.sleep(POLLING_INTERVAL_S)
                logger.debug(f"Polling status for job {job_id} (Attempt {poll_count + 1}/{max_polls})...")
                job_finished = await self._check_job_status(job_id)
                if job_finished:
                    logger.debug(f"Loop condition met for job {job_id}, breaking loop.")
                    break
                logger.debug(f"Job {job_id} not finished, continuing loop.")
                poll_count += 1

            if poll_count >= max_polls:
                logger.error(f"Polling timeout for job {job_id} after {poll_count} attempts.")
                return {} # Return empty on timeout

            logger.debug(f"Loop finished for job {job_id}. Proceeding to get results.")
            results = await self._get_job_results(job_id)
            return results

        except aiohttp.ClientError as e:
            logger.error(f"Network/HTTP error during UniProt mapping for job {job_id or 'UNKNOWN'}: {e}", exc_info=True)
            return {} # Return empty on network errors
        except Exception as e:
            logger.exception(f"Unexpected error during UniProt mapping for job {job_id or 'UNKNOWN'}", exc_info=True)
            return {} # Return empty on other errors

# Example Usage (Optional - for testing)
async def run_example():
    logging.basicConfig(level=logging.INFO, # Changed level back to INFO
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    client = UniProtNameClient()
    test_names = ["APP", "BRCA1", "NonExistentProteinXYZ", "TP53"]
    try:
        logger.info(f"Mapping names: {test_names}")
        mapping_results = await client.find_uniprot_ids_by_names(test_names)
        logger.info(f"Mapping Results: {mapping_results}")

        # Expected partial output (exact ACs may vary slightly but should be present):
        # {'APP': 'P05067', 'BRCA1': 'P38398', 'TP53': 'P04637'}
        # 'NonExistentProteinXYZ' should be absent or logged as failed.

    finally:
        await client.close_session()
        logger.info("Client session closed.")

if __name__ == "__main__":
    asyncio.run(run_example())
