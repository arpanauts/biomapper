"""Client for interacting with the PubChem API."""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union
import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class PubChemError(Exception):
    """Custom exception for PubChem API errors."""

    pass


@dataclass(frozen=True)
class PubChemConfig:
    """Configuration for PubChem API client."""

    base_url: str = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
    timeout: int = 30
    max_retries: int = 3
    backoff_factor: float = 0.5
    rate_limit_wait: float = 0.2  # Time to wait between requests to avoid rate limiting


@dataclass(frozen=True)
class PubChemResult:
    """Result from PubChem entity lookup."""

    pubchem_cid: str
    name: str
    formula: Optional[str] = None
    mass: Optional[float] = None
    smiles: Optional[str] = None
    inchi: Optional[str] = None
    inchikey: Optional[str] = None
    synonyms: Optional[List[str]] = None
    xrefs: Optional[Dict[str, str]] = None


class PubChemClient:
    """Client for interacting with the PubChem API."""

    def __init__(self, config: Optional[PubChemConfig] = None) -> None:
        """Initialize the PubChem API client.

        Args:
            config: Optional PubChemConfig object with custom settings
        """
        self.config = config or PubChemConfig()
        self.session = self._setup_session()
        self._last_request_time = 0

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
        self, url: str, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make a request to the PubChem API with rate limiting.

        Args:
            url: URL to request
            params: Optional request parameters

        Returns:
            JSON response as dictionary

        Raises:
            PubChemError: If the request fails
        """
        # Implement basic rate limiting
        elapsed = time.time() - self._last_request_time
        if elapsed < self.config.rate_limit_wait:
            time.sleep(self.config.rate_limit_wait - elapsed)

        try:
            self._last_request_time = time.time()
            response = self.session.get(url, params=params, timeout=self.config.timeout)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"PubChem API request failed: {str(e)}")
            raise PubChemError(f"API request failed: {str(e)}") from e
        except ValueError as e:
            logger.error(f"Invalid JSON response: {str(e)}")
            raise PubChemError(f"Invalid JSON response: {str(e)}") from e

    def get_property(
        self, pubchem_id: str, properties: Union[str, List[str]]
    ) -> Dict[str, Any]:
        """Get property data for a compound.

        Args:
            pubchem_id: PubChem CID
            properties: Properties to retrieve (e.g. 'MolecularFormula', 'InChI')

        Returns:
            Dictionary of property values

        Raises:
            PubChemError: If property retrieval fails
        """
        if isinstance(properties, str):
            properties = [properties]

        properties_str = ",".join(properties)
        url = f"{self.config.base_url}/compound/cid/{pubchem_id}/property/{properties_str}/JSON"

        try:
            data = self._make_request(url)
            if "PropertyTable" not in data or "Properties" not in data["PropertyTable"]:
                raise PubChemError(f"No property data found for CID {pubchem_id}")

            if not data["PropertyTable"]["Properties"]:
                raise PubChemError(f"Empty property list for CID {pubchem_id}")

            return data["PropertyTable"]["Properties"][0]
        except Exception as e:
            logger.error(f"PubChem property retrieval failed: {str(e)}")
            raise PubChemError(f"Property retrieval failed: {str(e)}") from e

    def get_compound_xrefs(self, pubchem_id: str) -> Dict[str, str]:
        """Get cross-references to other databases.

        Args:
            pubchem_id: PubChem CID

        Returns:
            Dictionary of cross-references

        Raises:
            PubChemError: If xref retrieval fails
        """
        url = f"{self.config.base_url}/compound/cid/{pubchem_id}/xrefs/RN,HMDB,CHEBI,KEGG/JSON"

        try:
            data = self._make_request(url)

            if (
                "InformationList" not in data
                or "Information" not in data["InformationList"]
            ):
                logger.warning(f"No xref data found for CID {pubchem_id}")
                return {}

            xref_data = data["InformationList"]["Information"][0]

            # Process and format the xrefs
            xrefs = {}

            if "HMDB" in xref_data:
                xref_hmdb = xref_data["HMDB"]
                if isinstance(xref_hmdb, list) and xref_hmdb:
                    xrefs["hmdb"] = xref_hmdb[0]

            if "ChEBI" in xref_data:
                xref_chebi = xref_data["ChEBI"]
                if isinstance(xref_chebi, list) and xref_chebi:
                    chebi_id = xref_chebi[0]
                    if not chebi_id.startswith("CHEBI:"):
                        chebi_id = f"CHEBI:{chebi_id}"
                    xrefs["chebi"] = chebi_id

            if "KEGG" in xref_data:
                xref_kegg = xref_data["KEGG"]
                if isinstance(xref_kegg, list) and xref_kegg:
                    xrefs["kegg"] = xref_kegg[0]

            return xrefs
        except Exception as e:
            logger.warning(f"PubChem xref retrieval failed: {str(e)}")
            return {}

    def get_entity_by_id(self, pubchem_id: str) -> Optional[PubChemResult]:
        """Get compound information by PubChem CID.

        Args:
            pubchem_id: PubChem CID (with or without 'CID:' prefix)

        Returns:
            PubChemResult containing compound information

        Raises:
            PubChemError: If entity lookup fails
        """
        try:
            # Strip CID: prefix if present
            clean_id = (
                pubchem_id.replace("CID:", "")
                if pubchem_id.startswith("CID:")
                else pubchem_id
            )

            # Get basic properties
            props = self.get_property(
                clean_id,
                [
                    "MolecularFormula",
                    "MolecularWeight",
                    "CanonicalSMILES",
                    "InChI",
                    "InChIKey",
                    "IUPACName",
                ],
            )

            # Get cross-references
            xrefs = self.get_compound_xrefs(clean_id)

            # Create result object
            result = PubChemResult(
                pubchem_cid=f"CID:{clean_id}"
                if not pubchem_id.startswith("CID:")
                else pubchem_id,
                name=props.get("IUPACName", ""),
                formula=props.get("MolecularFormula"),
                mass=float(props.get("MolecularWeight", 0))
                if "MolecularWeight" in props
                else None,
                smiles=props.get("CanonicalSMILES"),
                inchi=props.get("InChI"),
                inchikey=props.get("InChIKey"),
                xrefs=xrefs,
            )

            return result
        except Exception as e:
            logger.error(f"PubChem entity lookup failed: {str(e)}")
            raise PubChemError(f"Entity lookup failed: {str(e)}") from e

    def search_by_name(self, name: str, max_results: int = 5) -> List[PubChemResult]:
        """Search PubChem by compound name.

        Args:
            name: The compound name to search for
            max_results: Maximum number of results to return

        Returns:
            List of PubChemResult objects

        Raises:
            PubChemError: If search fails
        """
        try:
            # First search by name to get CIDs
            search_url = f"{self.config.base_url}/compound/name/{name}/cids/JSON"
            search_data = self._make_request(search_url)

            if (
                "IdentifierList" not in search_data
                or "CID" not in search_data["IdentifierList"]
            ):
                logger.info(f"No results found for '{name}'")
                return []

            cids = search_data["IdentifierList"]["CID"][:max_results]

            results = []
            for cid in cids:
                try:
                    result = self.get_entity_by_id(str(cid))
                    if result:
                        results.append(result)
                except PubChemError as e:
                    logger.warning(f"Failed to get details for CID {cid}: {str(e)}")
                    continue

            return results
        except Exception as e:
            logger.error(f"PubChem search failed: {str(e)}")
            raise PubChemError(f"Search failed: {str(e)}") from e
