"""UniProt focused mapper for protein mapping."""

import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Any

import requests


@dataclass
class UniProtConfig:
    """Configuration for UniProt API client"""

    base_url: str = "https://rest.uniprot.org"
    polling_interval: int = 3
    max_retries: int = 5
    timeout: int = 30


class UniprotFocusedMapper:
    """Client for mapping between key biological databases."""

    # Key database mappings available
    CORE_MAPPINGS = {
        "Protein/Gene": [
            "UniProtKB_AC-ID",  # Source database
            "GeneCards",
            "RefSeq_Protein",
            "Ensembl",
            "PDB",
        ],
        "Pathways": ["KEGG", "Reactome"],
        "Chemical/Drug": ["ChEMBL", "DrugBank"],
        "Disease": [
            "MIM"  # OMIM
        ],
    }

    def __init__(self, config: Optional[UniProtConfig] = None) -> None:
        """Initialize the mapper with optional configuration.

        Args:
            config: Optional configuration object for the UniProt API client
        """
        self.config = config or UniProtConfig()
        self.session = self._create_session()

    def _create_session(self) -> requests.Session:
        """Create requests session with retries"""
        session = requests.Session()
        retry_strategy = requests.adapters.Retry(
            total=self.config.max_retries,
            backoff_factor=0.25,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["GET", "POST"],  # Allow retries on both GET and POST
        )
        adapter = requests.adapters.HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    def get_available_mappings(self) -> Dict[str, List[str]]:
        """Get available mapping categories and target databases.

        Returns:
            Dictionary of categories and their available target databases
        """
        return {
            category: [db for db in dbs if db != "UniProtKB_AC-ID"]
            for category, dbs in self.CORE_MAPPINGS.items()
        }

    def map_id(self, protein_id: str, target_db: str) -> Dict[str, Any]:
        """Map a UniProt ID to a target database ID.

        Args:
            protein_id: UniProt accession (e.g., 'P05067')
            target_db: Target database name from CORE_MAPPINGS (e.g., 'Ensembl', 'GeneCards')

        Returns:
            Dictionary containing mapping results or empty dict if mapping fails

        Raises:
            ValueError: If target_db is not in CORE_MAPPINGS
        """
        # Validate target database
        valid_targets = [
            db
            for category in self.CORE_MAPPINGS.values()
            for db in category
            if db != "UniProtKB_AC-ID"
        ]

        if target_db not in valid_targets:
            raise ValueError(
                f"Invalid target database. Choose from: {', '.join(valid_targets)}"
            )

        # Submit job
        job_id = self._submit_job("UniProtKB_AC-ID", target_db, [protein_id])
        if not job_id:
            return {}

        # Poll until complete
        max_attempts = self.config.max_retries * 2
        for _ in range(max_attempts):
            results_url = self._check_job_status(job_id)
            if results_url:
                return self._get_job_results(results_url)

            time.sleep(self.config.polling_interval)

        return {}

    def _submit_job(self, from_db: str, to_db: str, ids: List[str]) -> str | None:
        """Submit a mapping job to the UniProt API.

        Args:
            from_db: Source database identifier
            to_db: Target database identifier
            ids: List of identifiers to map

        Returns:
            Job ID string if successful, None otherwise
        """
        url = f"{self.config.base_url}/idmapping/run"
        try:
            response = self.session.post(
                url,
                data={  # Use data= for form encoding instead of json=
                    "from": from_db,
                    "to": to_db,
                    "ids": ",".join(ids),
                },
                timeout=self.config.timeout,
            )
            response.raise_for_status()
            result = dict(response.json())  # Explicit cast for mypy
            return result.get("jobId")
        except (requests.exceptions.RequestException, ValueError):
            return None

    def _get_job_results(self, url: str) -> Dict[str, Any]:
        """Get results from a completed mapping job.

        Args:
            url: URL to fetch results from

        Returns:
            Dictionary containing mapping results
        """
        for attempt in range(self.config.max_retries + 1):
            try:
                response = self.session.get(url, timeout=self.config.timeout)
                response.raise_for_status()
                return dict(response.json())
            except requests.exceptions.RequestException:
                # Always retry unless it's the last attempt
                if attempt == self.config.max_retries:
                    return {}
                time.sleep(0.25 * (2**attempt))  # Exponential backoff
        return {}

    def _map_to_database(
        self, from_db: str, to_db: str, ids: List[str]
    ) -> Dict[str, Any]:
        """Map identifiers between databases."""
        max_attempts = 20  # Maximum number of polling attempts
        attempt = 0

        try:
            job_id = self._submit_job(from_db, to_db, ids)
            if not job_id:
                return {}

            while attempt < max_attempts:
                url = self._check_job_status(job_id)
                if url:
                    results = self._get_job_results(url)
                    return results if isinstance(results, dict) else {}
                time.sleep(self.config.polling_interval)
                attempt += 1

            # If we exceed max attempts, return empty result
            print(f"Warning: Mapping timed out after {max_attempts} attempts")
            return {}

        except requests.exceptions.RequestException as e:
            print(f"Warning: Mapping failed: {e}")
            return {}

    def _check_job_status(self, job_id: str) -> str | None:
        """Check the status of a mapping job.

        Args:
            job_id: ID of the mapping job to check

        Returns:
            Results URL if job is complete, None otherwise
        """
        url = f"{self.config.base_url}/idmapping/status/{job_id}"
        try:
            response = self.session.get(
                url,
                timeout=self.config.timeout,
                allow_redirects=False,  # Don't auto-follow redirects
            )

            # Check for redirect which indicates results are ready
            if response.status_code == 303:
                return response.headers.get("Location")

            response.raise_for_status()
            return None
        except requests.exceptions.RequestException:
            return None

    def _should_retry(self, error: requests.exceptions.RequestException) -> bool:
        """Determine if request should be retried based on error."""
        if isinstance(
            error, (requests.exceptions.Timeout, requests.exceptions.ConnectionError)
        ):
            return True
        if hasattr(error, "response") and error.response is not None:
            return error.response.status_code in {500, 502, 503, 504}
        return False

    def _retry_request(self, url: str) -> Dict[str, Any]:
        """Retry a failed request with exponential backoff."""
        for attempt in range(self.config.max_retries):
            try:
                time.sleep(2**attempt)  # Exponential backoff
                results_req = requests.get(url, timeout=self.config.timeout)
                results_req.raise_for_status()
                return dict(results_req.json())
            except requests.exceptions.RequestException:  # pragma: no cover
                continue
        return {}  # Return empty dict if all retries fail

    def _make_request(self, url: str) -> Dict[str, Any]:
        response: Dict[str, Any] = {}
        try:
            results_req = requests.get(url, timeout=self.config.timeout)
            results_req.raise_for_status()
            response = dict(results_req.json())  # Cast to dict to satisfy mypy
            return response
        except requests.exceptions.RequestException as e:  # pragma: no cover
            if self._should_retry(e):
                return self._retry_request(url)
            return response

    def _generate_mappings(
        self, proteins: Set[str], categories: Optional[List[str]] = None
    ) -> Dict[str, Dict[str, List[str]]]:
        """Generate mappings for a set of proteins with progress tracking.

        Args:
            proteins: Set of UniProt IDs to map
            categories: Optional list of categories to map. If None, maps all.

        Returns:
            Dict mapping protein IDs to their database mappings.
        """
        mappings: Dict[str, Dict[str, List[str]]] = {}

        # Process proteins in chunks
        for i in range(0, len(proteins), 100):  # Using chunk_size of 100
            protein_chunk = list(proteins)[i : i + 100]
            chunk_results = self._process_chunk(protein_chunk, categories)
            mappings.update(chunk_results)

        return mappings

    def _process_chunk(
        self, chunk: List[str], categories: Optional[List[str]] = None
    ) -> Dict[str, Dict[str, List[str]]]:
        """Process a chunk of proteins for mapping.

        Args:
            chunk: List of protein IDs to process
            categories: Optional list of categories to map

        Returns:
            Dictionary of mapping results for the chunk
        """
        chunk_mappings: Dict[str, Dict[str, List[str]]] = {}

        for protein in chunk:
            try:
                # Get valid target databases for each category
                target_dbs: List[str] = []
                for category in categories or ["Protein/Gene"]:
                    if category in self.CORE_MAPPINGS:
                        target_dbs.extend(
                            [
                                db
                                for db in self.CORE_MAPPINGS[category]
                                if db != "UniProtKB_AC-ID"
                            ]
                        )

                # Map to each target database
                protein_mappings: Dict[str, List[str]] = {}
                for target_db in target_dbs:
                    result = self.map_id(protein, target_db)
                    if result.get("results"):
                        mapped_ids: List[str] = []
                        for mapping in result["results"]:
                            to_id = mapping.get("to")
                            if isinstance(to_id, dict):
                                to_id = to_id.get("id")
                            if isinstance(to_id, str):  # Type guard
                                mapped_ids.append(to_id)
                        if mapped_ids:
                            protein_mappings[target_db] = mapped_ids

                if protein_mappings:
                    chunk_mappings[protein] = protein_mappings

            except Exception as e:
                print(f"\nWarning: Mapping failed for protein {protein}: {str(e)}")
                continue

        return chunk_mappings


# Example usage
if __name__ == "__main__":  # pragma: no cover
    mapper = UniprotFocusedMapper()

    # Show available mapping options
    print("Available mapping categories:")
    for category, databases in mapper.get_available_mappings().items():
        print(f"\n{category}:")
        for db in databases:
            print(f"  - {db}")

    # Example mapping
    print("\nExample mapping for APP protein (P05067):")
    results = mapper.map_id("P05067", "Ensembl")

    # Print results by category
    for category, databases in mapper.CORE_MAPPINGS.items():
        print(f"\n=== {category} Mappings ===")
        for db in databases:
            if db in results:
                print(f"\n{db}:")
                if "results" in results[db]:
                    for mapping in results[db]["results"]:
                        from_id = mapping.get("from", "N/A")
                        to_id = mapping.get("to", "N/A")
                        if isinstance(to_id, dict):
                            to_id = to_id.get("id", "N/A")
                        print(f"  {from_id} -> {to_id}")
