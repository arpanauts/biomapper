"""HMDB (Human Metabolome Database) API client for metabolite information retrieval."""

import logging
from typing import List, Dict, Optional
import xml.etree.ElementTree as ET
from xml.etree.ElementTree import ParseError

import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class HMDBMetaboliteInfo(BaseModel):
    """Structure for HMDB metabolite information."""

    hmdb_id: str
    common_name: Optional[str] = None
    iupac_name: Optional[str] = None
    synonyms: List[str] = Field(default_factory=list)
    chemical_formula: Optional[str] = None
    inchi: Optional[str] = None
    inchikey: Optional[str] = None
    kegg_id: Optional[str] = None
    pubchem_cid: Optional[str] = None
    chemspider_id: Optional[str] = None
    description: Optional[str] = None
    error: Optional[str] = None


class HMDBClient:
    """Client for Human Metabolome Database API.

    Provides access to metabolite information from HMDB, including
    chemical names, synonyms, identifiers, and structural information.
    """

    BASE_URL = "https://hmdb.ca"

    def __init__(self, timeout: int = 30, rate_limit_per_second: float = 10.0):
        """Initialize HMDB client.

        Args:
            timeout: Request timeout in seconds
            rate_limit_per_second: Maximum requests per second
        """
        self.timeout = timeout
        self.rate_limit_per_second = rate_limit_per_second
        self._session: Optional[httpx.AsyncClient] = None

    async def initialize(self) -> None:
        """Initialize the HTTP session."""
        if not self._session:
            self._session = httpx.AsyncClient(
                timeout=self.timeout, headers={"User-Agent": "Biomapper/1.0"}
            )

    async def close(self) -> None:
        """Close the HTTP session."""
        if self._session:
            await self._session.aclose()
            self._session = None

    async def get_metabolite_info(self, hmdb_id: str) -> HMDBMetaboliteInfo:
        """Get metabolite information by HMDB ID.

        Args:
            hmdb_id: HMDB identifier (e.g., "HMDB0000001" or "0000001")

        Returns:
            HMDBMetaboliteInfo object with metabolite data
        """
        # Ensure session is initialized
        if not self._session:
            await self.initialize()

        # Normalize HMDB ID format
        if not hmdb_id.startswith("HMDB"):
            # Remove any leading zeros and re-pad to 7 digits
            numeric_part = hmdb_id.lstrip("0") or "0"
            hmdb_id = f"HMDB{numeric_part.zfill(7)}"

        url = f"{self.BASE_URL}/metabolites/{hmdb_id}.xml"

        try:
            logger.debug(f"Fetching HMDB data for {hmdb_id}")
            response = await self._session.get(url)

            if response.status_code == 404:
                logger.warning(f"HMDB ID {hmdb_id} not found")
                return HMDBMetaboliteInfo(
                    hmdb_id=hmdb_id, error=f"HMDB ID {hmdb_id} not found"
                )

            response.raise_for_status()

            # Parse XML response
            return self._parse_hmdb_xml(response.text, hmdb_id)

        except httpx.TimeoutException:
            logger.error(f"Timeout fetching HMDB data for {hmdb_id}")
            return HMDBMetaboliteInfo(hmdb_id=hmdb_id, error="Request timeout")
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching HMDB data for {hmdb_id}: {e}")
            return HMDBMetaboliteInfo(
                hmdb_id=hmdb_id, error=f"HTTP error: {e.response.status_code}"
            )
        except Exception as e:
            logger.error(f"Error fetching HMDB data for {hmdb_id}: {e}")
            return HMDBMetaboliteInfo(hmdb_id=hmdb_id, error=str(e))

    def _parse_hmdb_xml(self, xml_content: str, hmdb_id: str) -> HMDBMetaboliteInfo:
        """Parse HMDB XML response.

        Args:
            xml_content: XML response content
            hmdb_id: HMDB ID being parsed

        Returns:
            HMDBMetaboliteInfo object
        """
        try:
            # Handle namespace in HMDB XML
            # HMDB uses a namespace, so we need to handle it properly
            root = ET.fromstring(xml_content)

            # Extract namespace if present
            namespace = ""
            if root.tag.startswith("{"):
                namespace = root.tag.split("}")[0] + "}"

            def find_text(path: str) -> Optional[str]:
                """Find text with namespace handling."""
                elem = root.find(namespace + path.replace("/", f"/{namespace}"))
                return elem.text if elem is not None and elem.text else None

            def find_all_text(path: str) -> List[str]:
                """Find all text values with namespace handling."""
                elements = root.findall(namespace + path.replace("/", f"/{namespace}"))
                return [elem.text for elem in elements if elem.text]

            # Extract metabolite information
            info = HMDBMetaboliteInfo(
                hmdb_id=hmdb_id,
                common_name=find_text("name"),
                iupac_name=find_text("iupac_name"),
                chemical_formula=find_text("chemical_formula"),
                inchi=find_text("inchi"),
                inchikey=find_text("inchikey"),
                kegg_id=find_text("kegg_id"),
                pubchem_cid=find_text("pubchem_compound_id"),
                chemspider_id=find_text("chemspider_id"),
                description=find_text("description"),
            )

            # Get synonyms
            synonyms = find_all_text("synonyms/synonym")
            if synonyms:
                info.synonyms = synonyms

            return info

        except ParseError as e:
            logger.error(f"Error parsing HMDB XML for {hmdb_id}: {e}")
            return HMDBMetaboliteInfo(
                hmdb_id=hmdb_id, error=f"XML parsing error: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Unexpected error parsing HMDB XML for {hmdb_id}: {e}")
            return HMDBMetaboliteInfo(hmdb_id=hmdb_id, error=f"Parsing error: {str(e)}")

    async def batch_get_metabolite_info(
        self, hmdb_ids: List[str], max_concurrent: int = 5
    ) -> Dict[str, HMDBMetaboliteInfo]:
        """Get metabolite information for multiple HMDB IDs.

        Args:
            hmdb_ids: List of HMDB identifiers
            max_concurrent: Maximum concurrent requests

        Returns:
            Dictionary mapping HMDB ID to metabolite info
        """
        # Ensure session is initialized
        if not self._session:
            await self.initialize()

        results = {}

        # Process in batches to respect rate limits
        import asyncio

        for i in range(0, len(hmdb_ids), max_concurrent):
            batch = hmdb_ids[i : i + max_concurrent]

            # Create tasks for batch
            tasks = [self.get_metabolite_info(hmdb_id) for hmdb_id in batch]

            # Execute batch
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            # Store results
            for hmdb_id, result in zip(batch, batch_results):
                if isinstance(result, Exception):
                    results[hmdb_id] = HMDBMetaboliteInfo(
                        hmdb_id=hmdb_id, error=str(result)
                    )
                else:
                    results[hmdb_id] = result

            # Rate limiting between batches
            if i + max_concurrent < len(hmdb_ids):
                await asyncio.sleep(max_concurrent / self.rate_limit_per_second)

        return results
