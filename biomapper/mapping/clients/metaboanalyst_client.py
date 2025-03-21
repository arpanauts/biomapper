"""Client for interacting with the MetaboAnalyst API."""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class MetaboAnalystError(Exception):
    """Custom exception for MetaboAnalyst API errors."""

    pass


@dataclass
class MetaboAnalystConfig:
    """Configuration for MetaboAnalyst API client."""

    base_url: str = "https://rest.xialab.ca/api"
    timeout: int = 30
    max_retries: int = 3
    backoff_factor: float = 0.5


@dataclass
class MetaboAnalystResult:
    """Result from MetaboAnalyst compound mapping."""

    input_id: str
    name: Optional[str] = None
    hmdb_id: Optional[str] = None
    pubchem_id: Optional[str] = None
    chebi_id: Optional[str] = None
    metlin_id: Optional[str] = None
    kegg_id: Optional[str] = None
    match_found: bool = False
    raw_data: Optional[Dict[str, Any]] = None


class MetaboAnalystClient:
    """Client for interacting with the MetaboAnalyst REST API.
    
    This client provides access to the MetaboAnalyst 6.0 compound mapping API,
    which allows for conversion between different compound identifiers.
    
    Example:
        ```python
        client = MetaboAnalystClient()
        results = client.map_compounds(
            ["glucose", "ATP", "caffeine"], 
            input_type="name"
        )
        for result in results:
            print(f"{result.input_id} -> HMDB: {result.hmdb_id}")
        ```
    """

    # Valid input types supported by the API
    VALID_INPUT_TYPES = ["name", "hmdb", "pubchem", "chebi", "metlin", "kegg"]

    def __init__(self, config: Optional[MetaboAnalystConfig] = None) -> None:
        """Initialize the MetaboAnalyst API client.

        Args:
            config: Optional MetaboAnalystConfig object with custom settings
        """
        self.config = config or MetaboAnalystConfig()
        self.session = self._setup_session()

    def _setup_session(self) -> requests.Session:
        """Configure requests session with retries and timeouts.

        Returns:
            Configured requests Session object
        """
        session = requests.Session()

        retry_strategy = Retry(
            total=self.config.max_retries,
            backoff_factor=self.config.backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        return session

    def map_compounds(
        self, compounds: List[str], input_type: str = "name"
    ) -> List[MetaboAnalystResult]:
        """Map compounds using MetaboAnalyst API.
        
        Args:
            compounds: List of compound identifiers
            input_type: Type of identifiers (name, hmdb, pubchem, chebi, metlin, kegg)
            
        Returns:
            List of MetaboAnalystResult objects
            
        Raises:
            MetaboAnalystError: If the API call fails or returns an error
            ValueError: If input_type is not valid
        """
        if not compounds:
            return []

        if input_type not in self.VALID_INPUT_TYPES:
            valid_types = ", ".join(self.VALID_INPUT_TYPES)
            raise ValueError(
                f"Invalid input_type: {input_type}. Must be one of: {valid_types}"
            )

        # Join compounds with semicolons as expected by the API
        query_list = ";".join(compounds)

        # Prepare the request payload
        payload = {
            "queryList": query_list,
            "inputType": input_type,
        }

        # Make the API request
        endpoint = "mapcompounds"
        url = f"{self.config.base_url}/{endpoint}"

        try:
            response = self.session.post(
                url,
                json=payload,
                timeout=self.config.timeout,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            
            # Parse the response
            data = response.json()
            results = self._parse_response(data, compounds)
            return results
            
        except requests.exceptions.RequestException as e:
            logger.error(f"MetaboAnalyst API request failed: {e}")
            raise MetaboAnalystError(f"API request failed: {e}")

    def _parse_response(
        self, response_data: Dict[str, Any], input_compounds: List[str]
    ) -> List[MetaboAnalystResult]:
        """Parse the API response into MetaboAnalystResult objects.
        
        Args:
            response_data: JSON response from the API
            input_compounds: Original list of input compounds
            
        Returns:
            List of MetaboAnalystResult objects
        """
        results = []
        
        # Handle case where API returns an error message
        if "error" in response_data:
            logger.error(f"MetaboAnalyst API returned error: {response_data['error']}")
            raise MetaboAnalystError(f"API error: {response_data['error']}")
        
        # The API returns a list of matched compounds
        if "matches" not in response_data:
            logger.warning("No 'matches' field found in API response")
            # Return empty results for all input compounds
            return [
                MetaboAnalystResult(input_id=compound, match_found=False)
                for compound in input_compounds
            ]
        
        matches = response_data["matches"]
        
        # Create a mapping from input compound to result
        input_to_result = {}
        
        for match in matches:
            # Extract the input ID (original query)
            input_id = match.get("query", "")
            
            if not input_id:
                logger.warning(f"Match missing 'query' field: {match}")
                continue
                
            # Create result object
            result = MetaboAnalystResult(
                input_id=input_id,
                name=match.get("name"),
                hmdb_id=match.get("hmdb"),
                pubchem_id=match.get("pubchem"),
                chebi_id=match.get("chebi"),
                metlin_id=match.get("metlin"),
                kegg_id=match.get("kegg"),
                match_found=True,
                raw_data=match,
            )
            
            input_to_result[input_id] = result
        
        # Ensure we return results for all input compounds
        for compound in input_compounds:
            if compound in input_to_result:
                results.append(input_to_result[compound])
            else:
                # No match found for this compound
                results.append(MetaboAnalystResult(input_id=compound, match_found=False))
        
        return results
