"""Client for interacting with the KEGG API.

Based on the KEGG REST API documentation at https://rest.kegg.jp/

Supported operations:
- info: Get database statistics
- list: List entries in a database
- find: Search entries by keywords
- get: Retrieve entry details
- conv: Convert between KEGG and external database IDs
- link: Find related entries
"""

import logging
import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union, Tuple

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
    rate_limit: float = (
        0.34  # Minimum time between requests (seconds) - allows ~3 requests per second
    )


@dataclass(frozen=True)
class KEGGResult:
    """Result from KEGG entity lookup."""

    kegg_id: str
    name: str
    formula: Optional[str] = None
    exact_mass: Optional[float] = None
    mol_weight: Optional[float] = None
    inchi: Optional[str] = None
    smiles: Optional[str] = None
    other_dbs: Dict[str, str] = field(default_factory=dict)
    pathway_ids: List[str] = field(default_factory=list)
    raw_data: str = ""

    def get_pubchem_id(self) -> Optional[str]:
        """Get PubChem ID if available."""
        return self.other_dbs.get("pubchem")

    def get_chebi_id(self) -> Optional[str]:
        """Get ChEBI ID if available."""
        return self.other_dbs.get("chebi")

    def get_hmdb_id(self) -> Optional[str]:
        """Get HMDB ID if available."""
        return self.other_dbs.get("hmdb")


class KEGGClient:
    """Client for interacting with the KEGG REST API."""

    def __init__(self, config: Optional[KEGGConfig] = None) -> None:
        """Initialize the KEGG API client.

        Args:
            config: Optional KEGGConfig object with custom settings
        """
        self.config = config or KEGGConfig()
        self.session = self._setup_session()
        self.last_request_time = (
            0.0  # Track the time of the last request for rate limiting
        )

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

    def _make_request(
        self, endpoint: str, params: Optional[Dict[str, Any]] = None
    ) -> str:
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
            # Implement rate limiting - ensure we respect KEGG's 3 requests per second limit
            current_time = time.time()
            elapsed = current_time - self.last_request_time
            if elapsed < self.config.rate_limit:
                # Sleep to respect rate limit
                sleep_time = self.config.rate_limit - elapsed
                logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
                time.sleep(sleep_time)

            # Make the request
            url = f"{self.config.base_url}/{endpoint}"
            response = self.session.get(url, params=params, timeout=self.config.timeout)
            response.raise_for_status()

            # Update the last request time
            self.last_request_time = time.time()

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
            "pathway_ids": [],
            "raw_data": text,  # Store raw data for later extraction
        }

        current_section = None
        for line in text.strip().split("\n"):
            if not line:
                continue

            # Handle section headers (starts at beginning of line)
            if not line.startswith(" "):
                current_section = line.split(" ")[0]
                content = line[len(current_section) + 1 :].strip()

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
                    match = re.search(r"(map\d+)", content)
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

        # Extract SMILES and InChI if present in the text
        smiles_match = re.search(r"SMILES:\s+(.+?)(?=\n|$)", text)
        inchi_match = re.search(r"InChI=(.+?)(?=\n|$)", text)

        if smiles_match:
            result["smiles"] = smiles_match.group(1).strip()
        if inchi_match:
            result["inchi"] = "InChI=" + inchi_match.group(1).strip()

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
            endpoint = f"get/{clean_id}"
            if not clean_id.startswith("C"):
                # If it's not already in the C00xxx format, try with cpd: prefix
                endpoint = f"get/cpd:{clean_id}"

            entry_text = self._make_request(endpoint)

            # If empty response, the compound does not exist
            if not entry_text.strip():
                logger.warning(f"No KEGG entry found for ID: {kegg_id}")
                return None

            # Parse the entry text
            parsed = self._parse_compound_entry(entry_text)
            if not parsed:
                logger.warning(f"Failed to parse KEGG entry for ID: {kegg_id}")
                return None

            # Create and return the result object with all available data
            return KEGGResult(
                kegg_id=parsed.get("kegg_id", clean_id),
                name=parsed.get("name", ""),
                formula=parsed.get("formula"),
                exact_mass=parsed.get("exact_mass"),
                mol_weight=parsed.get("mol_weight"),
                inchi=parsed.get("inchi"),
                smiles=parsed.get("smiles"),
                other_dbs=parsed.get("other_dbs", {}),
                pathway_ids=parsed.get("pathway_ids", []),
                raw_data=parsed.get("raw_data", ""),
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
            # Search KEGG for compounds matching the name using find operation
            search_text = self._make_request(f"find/compound/{name}")
            if not search_text.strip():
                logger.info(f"No KEGG compounds found for name: {name}")
                return []

            results = []
            # Parse search results (format: cpd:C00031 Glucose)
            for line in search_text.strip().split("\n"):
                if not line.strip():
                    continue

                # Split by the first space to separate ID from description
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
                        logger.warning(
                            f"Failed to get details for KEGG ID {kegg_id}: {str(e)}"
                        )
                        continue

            return results
        except Exception as e:
            logger.error(f"KEGG search failed: {str(e)}")
            raise KEGGError(f"Search failed: {str(e)}") from e

    def find_compounds(self, query: str, max_results: int = 5) -> List[KEGGResult]:
        """Find compounds matching the query using the KEGG find operation.

        This is an alias for search_by_name since our verification script tries to use it.

        Args:
            query: The query to search for
            max_results: Maximum number of results to return

        Returns:
            List of KEGGResult objects

        Raises:
            KEGGError: If search fails
        """
        return self.search_by_name(query, max_results)

    def search_compound(self, query: str, max_results: int = 5) -> List[KEGGResult]:
        """Search for compounds by name or identifier.

        This is another alias for search_by_name since our verification script tries to use it.

        Args:
            query: The query to search for
            max_results: Maximum number of results to return

        Returns:
            List of KEGGResult objects

        Raises:
            KEGGError: If search fails
        """
        return self.search_by_name(query, max_results)

    def get_info(self) -> Dict[str, str]:
        """Get KEGG database statistics using the info operation.

        Returns:
            Dictionary with database statistics

        Raises:
            KEGGError: If the request fails
        """
        try:
            info_text = self._make_request("info/kegg")
            result = {}

            for line in info_text.strip().split("\n"):
                if line and ":" in line:
                    key, value = line.split(":", 1)
                    result[key.strip()] = value.strip()

            return result
        except Exception as e:
            logger.error(f"Failed to get KEGG info: {str(e)}")
            raise KEGGError(f"Failed to get KEGG info: {str(e)}") from e

    def convert_id(
        self, source_id: str, target_db: str = "pubchem"
    ) -> List[Tuple[str, str]]:
        """Convert KEGG IDs to/from external database IDs using the conv operation.

        Args:
            source_id: The ID to convert (e.g., "C00031" or "pubchem:5793")
            target_db: Target database for conversion (e.g., "pubchem", "chebi")

        Returns:
            List of tuples with (source_id, target_id)

        Raises:
            KEGGError: If the conversion fails
        """
        try:
            # Determine if the source ID is a KEGG ID or an external DB ID
            if source_id.startswith("C") or source_id.startswith("cpd:"):
                # Converting from KEGG to external DB
                clean_id = source_id.replace("cpd:", "")
                conv_text = self._make_request(f"conv/{target_db}/{clean_id}")
            else:
                # Converting from external DB to KEGG
                db_prefix = ""
                db_id = source_id

                # Handle prefixed IDs (e.g., "pubchem:5793")
                if ":" in source_id:
                    db_prefix, db_id = source_id.split(":", 1)
                    conv_text = self._make_request(f"conv/compound/{db_prefix}:{db_id}")
                else:
                    # Assume the target_db is the source database for this ID
                    conv_text = self._make_request(f"conv/compound/{target_db}:{db_id}")

            results = []
            # Format is tab-separated: target_id source_id
            for line in conv_text.strip().split("\n"):
                if not line.strip():
                    continue

                parts = line.split("\t")
                if len(parts) == 2:
                    results.append((parts[1], parts[0]))

            return results
        except Exception as e:
            logger.error(f"KEGG ID conversion failed: {str(e)}")
            raise KEGGError(f"ID conversion failed: {str(e)}") from e

    def find_related_entries(
        self, source_id: str, target_db: str
    ) -> List[Tuple[str, str]]:
        """Find related entries using the link operation.

        Args:
            source_id: Source entry ID
            target_db: Target database (e.g., "pathway", "pubchem")

        Returns:
            List of tuples with (source_id, target_id)

        Raises:
            KEGGError: If the request fails
        """
        try:
            link_text = self._make_request(f"link/{target_db}/{source_id}")
            results = []

            # Format is tab-separated: target_id source_id
            for line in link_text.strip().split("\n"):
                if not line.strip():
                    continue

                parts = line.split("\t")
                if len(parts) == 2:
                    results.append((parts[1], parts[0]))

            return results
        except Exception as e:
            logger.error(f"KEGG link operation failed: {str(e)}")
            raise KEGGError(f"Link operation failed: {str(e)}") from e
