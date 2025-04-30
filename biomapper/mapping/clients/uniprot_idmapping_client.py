import asyncio
import logging
import time
from typing import List, Dict, Optional, Any

import aiohttp

logger = logging.getLogger(__name__)

UNIPROT_IDMAPPING_API_BASE_URL = "https://rest.uniprot.org/idmapping"
POLLING_INTERVAL_SECONDS = 5
MAX_WAIT_SECONDS = 300  # 5 minutes
CONCURRENT_REQUESTS = 5  # Limit concurrent checks


class UniProtIDMappingClient:
    """Client for mapping identifiers using the UniProt ID Mapping service.

    Handles submitting mapping jobs, polling for results, and retrieving them.
    Maps from UniProtKB AC/ID to a specified target database (e.g., Ensembl).
    """

    def __init__(
        self,
        from_db: str = "UniProtKB_AC-ID",
        to_db: str = "Ensembl",
        base_url: str = UNIPROT_IDMAPPING_API_BASE_URL,
        config: Optional[Dict] = None,
    ):
        """
        Initializes the client.

        Args:
            from_db: The database name for the source identifiers (as defined by UniProt).
            to_db: The database name for the target identifiers (as defined by UniProt).
            base_url: The base URL for the UniProt ID Mapping API.
            config: Optional configuration dictionary (currently unused by this client).
        """
        self.base_url = base_url
        self.from_db = from_db
        self.to_db = to_db
        self.semaphore = asyncio.Semaphore(CONCURRENT_REQUESTS)

    async def _submit_job(
        self, session: aiohttp.ClientSession, ids: List[str]
    ) -> Optional[str]:
        """Submit a job to the UniProt ID Mapping service."""
        url = f"{self.base_url}/run"
        payload = {"ids": ",".join(ids), "from": self.from_db, "to": self.to_db}
        try:
            async with session.post(url, data=payload) as response:
                response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
                data = await response.json()
                job_id = data.get("jobId")
                if not job_id:
                    logger.error(
                        f"Failed to submit UniProt ID Mapping job. Response: {data}"
                    )
                    return None
                logger.info(f"Submitted UniProt ID Mapping job: {job_id}")
                return job_id
        except aiohttp.ClientError as e:
            logger.error(f"Error submitting UniProt ID Mapping job: {e}")
            return None

    async def _check_job_status(
        self, session: aiohttp.ClientSession, job_id: str
    ) -> Optional[Dict[str, Any]]:
        """Check the status of a UniProt ID Mapping job."""
        url = f"{self.base_url}/status/{job_id}"
        try:
            async with self.semaphore:  # Limit concurrent status checks
                async with session.get(url) as response:
                    # Allow 400, it might mean the job finished and results are ready (or job expired)
                    if response.status >= 500:
                        response.raise_for_status()
                    data = await response.json()
                    logger.debug(f"Job {job_id} status check response: {data}")
                    return data
        except aiohttp.ClientError as e:
            logger.error(f"Error checking status for job {job_id}: {e}")
            return None

    async def _get_job_results(
        self, session: aiohttp.ClientSession, job_id: str
    ) -> Optional[Dict[str, Any]]:
        """Retrieve the results for a completed UniProt ID Mapping job."""
        # Try the new /results/{job_id} endpoint first
        url_results = f"{self.base_url}/results/{job_id}"
        try:
            async with session.get(url_results, params={"format": "json"}) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(
                        f"Retrieved results for job {job_id} via /results endpoint."
                    )
                    return data
                elif response.status == 404:  # Not found, maybe results are at /stream?
                    logger.warning(
                        f"Job {job_id} results not found at /results, potentially expired or very large. Status: {response.status}"
                    )
                    # We could potentially try /stream here for very large results, but for now, treat as unavailable.
                    return None
                else:
                    # Other errors (e.g., 400 Bad Request might indicate issues)
                    response.raise_for_status()
                    return None  # Should not be reached if raise_for_status works
        except aiohttp.ClientError as e:
            logger.error(
                f"Error retrieving results for job {job_id} from {url_results}: {e}"
            )
            return None

    async def map_identifiers(
        self, identifiers: List[str], config: Optional[Dict] = None
    ) -> Dict[str, Optional[str]]:
        """Map a list of identifiers using the UniProt ID Mapping service.

        Args:
            identifiers: A list of identifiers to map (e.g., UniProtKB ACs).
            config: Optional configuration dictionary (currently unused by this client).

        Returns:
            A dictionary mapping original input IDs to the *first* mapped target ID found,
            or None if no mapping was found for an ID.
        """
        if not identifiers:
            return {}

        async with aiohttp.ClientSession() as session:
            job_id = await self._submit_job(session, identifiers)
            if not job_id:
                return {
                    identifier: None for identifier in identifiers
                }  # Job submission failed

            start_time = time.time()
            results_data = None  # Initialize results_data to None
            while True:
                status_response = await self._check_job_status(session, job_id)

                if status_response is None:
                    # Error checking status - break and let final processing handle it
                    logger.error(f"Failed to get status for job {job_id}.")
                    break

                # Check if results are directly in the status response
                if "results" in status_response:
                    logger.info(
                        f"Job {job_id} results found directly in status response."
                    )
                    results_data = status_response
                    break  # Exit polling loop

                # Otherwise, check the jobStatus field
                job_status = status_response.get("jobStatus")

                if job_status == "FINISHED":
                    logger.info(
                        f"Job {job_id} reported status FINISHED. Retrieving results..."
                    )
                    # Results were not in status, so try fetching explicitly
                    results_data = await self._get_job_results(session, job_id)
                    break  # Exit polling loop
                elif job_status in ["RUNNING", "QUEUED"]:
                    logger.debug(f"Job {job_id} status: {job_status}. Waiting...")
                    pass  # Continue polling
                else:
                    # Includes FAILURE, NOT_FOUND, ERROR, or jobStatus is None etc.
                    logger.error(
                        f"Job {job_id} failed or encountered an issue. Status: {job_status}. Response: {status_response}"
                    )
                    # results_data remains None
                    break  # Exit polling loop

                if time.time() - start_time > MAX_WAIT_SECONDS:
                    logger.error(
                        f"Job {job_id} timed out after {MAX_WAIT_SECONDS} seconds."
                    )
                    # results_data remains None
                    break  # Exit polling loop

                await asyncio.sleep(POLLING_INTERVAL_SECONDS)
            # --- End Polling Loop ---

            # Process results
            final_mapping: Dict[str, Optional[str]] = {
                identifier: None for identifier in identifiers
            }
            if results_data and "results" in results_data:
                count = 0
                for item in results_data["results"]:
                    input_id = item.get("from")
                    mapped_id_info = item.get("to")

                    if input_id in final_mapping:
                        # Extract the target ID
                        target_id: Optional[str] = None
                        if mapped_id_info:
                            if isinstance(mapped_id_info, dict) and mapped_id_info.get(
                                "primaryAccession"
                            ):
                                target_id = mapped_id_info["primaryAccession"]
                            elif isinstance(mapped_id_info, str):
                                target_id = mapped_id_info  # Handle cases where 'to' is just a string

                        # Update mapping only if a valid target was found and not already mapped
                        if target_id is not None and final_mapping[input_id] is None:
                            final_mapping[input_id] = target_id
                            count += 1
                            logger.debug(f"Mapped {input_id} -> {target_id}")
                        elif target_id is not None:
                            logger.debug(
                                f"Skipping update for {input_id}, already mapped to {final_mapping[input_id]}"
                            )
                        # else: target_id is None (no mapping found for this item)
                    else:
                        logger.warning(
                            f"Mapped ID '{input_id}' from UniProt results was not in the original input list."
                        )
                logger.info(
                    f"Successfully processed {count} mappings out of {len(identifiers)} potential results for job {job_id}."
                )
            elif results_data is None:
                logger.error(
                    f"No results were obtained for job {job_id} (failed, timed out, or error retrieving)."
                )
            else:
                logger.warning(
                    f"Job {job_id} finished but results format was unexpected: {results_data}"
                )

            return final_mapping


# Example Usage (Optional - for testing)
async def run_example():
    logging.basicConfig(level=logging.INFO)
    logger.info("Running UniProt ID Mapping Client Example...")
    client = UniProtIDMappingClient()
    test_ids = ["P05067", "P38398", "P04637", "NONEXISTENTAC"]  # APP, BRCA1, TP53
    results = await client.map_identifiers(identifiers=test_ids)
    print("\n--- Mapping Results (UniProtKB_AC -> Ensembl) ---")
    for uniprot_ac, ensembl_id in results.items():
        print(f"  {uniprot_ac}: {ensembl_id}")


if __name__ == "__main__":
    asyncio.run(run_example())
