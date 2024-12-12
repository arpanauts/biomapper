"""
UniChem API Client

This module provides a Python interface to the UniChem REST API.
It handles request formation and response parsing for retrieving
metabolite information across various chemical databases.
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class UniChemError(Exception):
    """Custom exception for UniChem API errors"""

    pass


@dataclass
class UniChemConfig:
    """Configuration for UniChem API client"""

    base_url: str = "https://www.ebi.ac.uk/unichem/rest"
    timeout: int = 30
    max_retries: int = 3
    backoff_factor: float = 0.5


class UniChemClient:
    """Client for interacting with the UniChem REST API"""

    def __init__(self, config: Optional[UniChemConfig] = None) -> None:
        """Initialize the UniChem API client

        Args:
            config: Optional UniChemConfig object with custom settings
        """
        self.config = config or UniChemConfig()
        self.session = self._setup_session()

    def _setup_session(self) -> requests.Session:
        """Configure requests session with retries and timeouts

        Returns:
            Configured requests Session object
        """
        session = requests.Session()

        # Configure retry strategy
        retry_strategy = Retry(
            total=self.config.max_retries,
            backoff_factor=self.config.backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        return session

    def _make_request(self, endpoint: str) -> Any:
        """Make a request to the UniChem API

        Args:
            endpoint: API endpoint to call

        Returns:
            Response data as either a dict or list

        Raises:
            UniChemError: If the request fails
        """
        url = f"{self.config.base_url}/{endpoint}"

        try:
            response = self.session.get(url, timeout=self.config.timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"UniChem API request failed: {str(e)}")
            raise UniChemError(f"Request failed: {str(e)}") from e

    def get_compound_info_by_inchikey(self, inchikey: str) -> Dict[str, List[str]]:
        """Get compound information by InChIKey

        Args:
            inchikey: InChIKey to search for

        Returns:
            Dict containing lists of IDs from different sources
        """
        endpoint = f"inchikey/{inchikey}"
        # Cast the result to Any first to handle both list and dict responses
        raw_result: Any = self._make_request(endpoint)

        compound_list: List[Dict[str, Any]] = []
        if isinstance(raw_result, list):
            compound_list = raw_result
        elif isinstance(raw_result, dict):
            compound_list = [raw_result]

        return self._process_compound_result(compound_list)

    def _process_compound_result(
        self, result: List[Dict[str, Any]]
    ) -> Dict[str, List[str]]:
        """Process compound result from UniChem API

        Args:
            result: List of compound results from API

        Returns:
            Dict containing lists of IDs for each source
        """
        # Initialize with empty lists
        processed_result: Dict[str, List[str]] = {
            "chembl_ids": [],
            "chebi_ids": [],
            "pubchem_ids": [],
            "kegg_ids": [],
            "hmdb_ids": [],
        }

        # Process valid entries
        for entry in result:
            src_id = entry.get("src_id")
            compound_id = entry.get("src_compound_id")

            if compound_id is None:
                continue

            # Handle both string and int src_ids
            src_id_int: int | None = None
            if isinstance(src_id, int):
                src_id_int = src_id
            elif isinstance(src_id, str):
                try:
                    src_id_int = int(src_id)
                except ValueError:
                    continue
            else:
                continue

            # Map source IDs to result keys
            if src_id_int == 1:
                processed_result["chembl_ids"].append(str(compound_id))
            elif src_id_int == 7:
                processed_result["chebi_ids"].append(str(compound_id))
            elif src_id_int == 22:
                processed_result["pubchem_ids"].append(str(compound_id))
            elif src_id_int == 6:
                processed_result["kegg_ids"].append(str(compound_id))
            elif src_id_int == 2:
                processed_result["hmdb_ids"].append(str(compound_id))

        return processed_result

    def get_source_information(self) -> Dict[str, Any]:
        """Retrieve information about available data sources

        Returns:
            Dict containing source database information

        Raises:
            UniChemError: If the request fails
        """
        endpoint = "sources"
        response = self._make_request(endpoint)
        # Cast response to dict to satisfy type checker
        return dict(response)

    def get_structure_search(
        self,
        structure: str,
        search_type: str,
    ) -> dict[str, Any]:
        """
        Search for compounds by structure using SMILES or InChI.

        Args:
            structure: The structure to search for
            search_type: Type of structure (smiles or inchi)

        Returns:
            dict: The search results
        """
        if search_type not in ["smiles", "inchi"]:
            raise ValueError("Search type must be either 'smiles' or 'inchi'")

        endpoint = f"structure/{structure}/{search_type}"
        response = self._make_request(endpoint)
        # Cast response to dict to satisfy type checker
        return dict(response)


# Example usage:
if __name__ == "__main__":
    # Initialize client
    client = UniChemClient()

    # Example InChIKey
    try:
        info = client.get_compound_info_by_inchikey("RYYVLZVUVIJVGH-UHFFFAOYSA-N")
        print(f"Found compound IDs: {info}")
    except UniChemError as e:
        print(f"Error: {e}")
