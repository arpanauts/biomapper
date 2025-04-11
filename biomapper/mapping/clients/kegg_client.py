"""Client for interacting with the KEGG API."""

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class KEGGError(Exception):
    """Custom exception for KEGG API errors."""

    pass


@dataclass(frozen=True)
class KEGGConfig:
    """Configuration for KEGG API client."""

    base_url: str = "https://rest.kegg.jp"
    timeout: int = 30
    max_retries: int = 3
    backoff_factor: float = 0.5


@dataclass(frozen=True)
class KEGGResult:
    """Result from KEGG entity lookup."""

    kegg_id: str
    name: str
    formula: Optional[str] = None
    exact_mass: Optional[float] = None
    mol_weight: Optional[float] = None
    other_dbs: Dict[str, str] = field(default_factory=dict)
    pathway_ids: List[str] = field(default_factory=list)


class KEGGClient:
    """Client for interacting with the KEGG REST API."""

    def __init__(self, config: Optional[KEGGConfig] = None) -> None:
        """Initialize the KEGG API client.

        Args:
            config: Optional KEGGConfig object with custom settings
        """
        self.config = config or KEGGConfig()
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

    def _make_request(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> str:
        """Make a request to the KEGG API.

        Args:
            endpoint: API endpoint to request
            params: Optional request parameters

        Returns:
            Text response from the API

        Raises:
            KEGGError: If the request fails
        """
        try:
            url = f"{self.config.base_url}/{endpoint}"
            response = self.session.get(
                url,
                params=params,
                timeout=self.config.timeout
            )
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            logger.error(f"KEGG API request failed: {str(e)}")
            raise KEGGError(f"API request failed: {str(e)}") from e

    def _parse_compound_entry(self, text: str) -> Dict[str, Any]:
        """Parse a KEGG compound entry text into a structured dictionary.

        Args:
            text: Raw text of KEGG compound entry

        Returns:
            Dictionary with parsed fields
        """
        if not text.strip():
            return {}

        result: Dict[str, Any] = {
            "other_dbs": {},
            "names": [],
            "pathway_ids": []
        }

        current_section = None
        for line in text.strip().split("\n"):
            if not line:
                continue

            # Handle section headers (starts at beginning of line)
            if not line.startswith(" "):
                current_section = line.split(" ")[0]
                content = line[len(current_section) + 1:].strip()
                
                if current_section == "ENTRY":
                    # Extract ID from ENTRY line
                    entry_parts = content.split()
                    result["kegg_id"] = entry_parts[0]
                elif current_section == "NAME":
                    result["names"].append(content.rstrip(";"))
                elif current_section == "FORMULA":
                    result["formula"] = content
                elif current_section == "EXACT_MASS":
                    try:
                        result["exact_mass"] = float(content)
                    except ValueError:
                        pass
                elif current_section == "MOL_WEIGHT":
                    try:
                        result["mol_weight"] = float(content)
                    except ValueError:
                        pass
            
            # Handle multi-line sections (starts with spaces)
            elif line.startswith(" ") and current_section:
                content = line.strip()
                
                if current_section == "NAME":
                    result["names"].append(content.rstrip(";"))
                elif current_section == "PATHWAY":
                    # Extract pathway ID
                    match = re.search(r'(map\d+)', content)
                    if match:
                        result["pathway_ids"].append(match.group(1))
                elif current_section == "DBLINKS":
                    # Parse database links (e.g., "ChEBI: 15365")
                    parts = content.split(":", 1)
                    if len(parts) == 2:
                        db_name = parts[0].strip().lower()
                        db_id = parts[1].strip()
                        
                        # Format based on database
                        if db_name == "chebi":
                            result["other_dbs"]["chebi"] = f"CHEBI:{db_id}"
                        elif db_name == "pubchem":
                            result["other_dbs"]["pubchem"] = f"CID:{db_id}"
                        elif db_name == "hmdb":
                            result["other_dbs"]["hmdb"] = db_id
                        else:
                            result["other_dbs"][db_name] = db_id

        # Use the first name as the primary name
        if result.get("names"):
            result["name"] = result["names"][0]
        else:
            result["name"] = ""

        return result

    def get_entity_by_id(self, kegg_id: str) -> Optional[KEGGResult]:
        """Get compound information by KEGG ID.

        Args:
            kegg_id: KEGG compound ID (e.g., "C00031")

        Returns:
            KEGGResult containing compound information

        Raises:
            KEGGError: If entity lookup fails
        """
        try:
            # Clean the ID format - strip "cpd:" prefix if present
            clean_id = kegg_id.replace("cpd:", "")
            if not clean_id.startswith("C"):
                logger.warning(f"KEGG ID {kegg_id} is not in expected format (C00xxx)")

            # Get compound information from KEGG
            entry_text = self._make_request(f"get/cpd:{clean_id}")
            
            # If empty response, the compound does not exist
            if not entry_text.strip():
                logger.warning(f"No KEGG entry found for ID: {kegg_id}")
                return None
                
            # Parse the entry text
            parsed = self._parse_compound_entry(entry_text)
            if not parsed:
                logger.warning(f"Failed to parse KEGG entry for ID: {kegg_id}")
                return None
                
            # Create the result object
            return KEGGResult(
                kegg_id=f"cpd:{clean_id}" if not kegg_id.startswith("cpd:") else kegg_id,
                name=parsed.get("name", ""),
                formula=parsed.get("formula"),
                exact_mass=parsed.get("exact_mass"),
                mol_weight=parsed.get("mol_weight"),
                other_dbs=parsed.get("other_dbs", {}),
                pathway_ids=parsed.get("pathway_ids", [])
            )
        except Exception as e:
            logger.error(f"KEGG entity lookup failed: {str(e)}")
            raise KEGGError(f"Entity lookup failed: {str(e)}") from e

    def search_by_name(self, name: str, max_results: int = 5) -> List[KEGGResult]:
        """Search KEGG by compound name.

        Args:
            name: The compound name to search for
            max_results: Maximum number of results to return

        Returns:
            List of KEGGResult objects

        Raises:
            KEGGError: If search fails
        """
        try:
            # Search KEGG for compounds matching the name
            search_text = self._make_request(f"find/compound/{name}")
            if not search_text.strip():
                logger.info(f"No KEGG compounds found for name: {name}")
                return []
                
            results = []
            # Parse search results (format: cpd:C00031 Glucose)
            for line in search_text.strip().split("\n"):
                if not line.strip():
                    continue
                    
                parts = line.split(maxsplit=1)
                if len(parts) >= 1:
                    kegg_id = parts[0]
                    
                    # Get detailed information for each result
                    try:
                        result = self.get_entity_by_id(kegg_id)
                        if result:
                            results.append(result)
                            
                            if len(results) >= max_results:
                                break
                    except KEGGError as e:
                        logger.warning(f"Failed to get details for KEGG ID {kegg_id}: {str(e)}")
                        continue
            
            return results
        except Exception as e:
            logger.error(f"KEGG search failed: {str(e)}")
            raise KEGGError(f"Search failed: {str(e)}") from e
