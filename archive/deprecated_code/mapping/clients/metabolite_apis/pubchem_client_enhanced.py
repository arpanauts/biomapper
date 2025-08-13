"""Enhanced PubChem client with metabolite-specific features."""

import logging
from typing import List, Dict, Optional
from enum import Enum

import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class PubChemIdType(str, Enum):
    """Supported PubChem identifier types."""

    CID = "cid"
    NAME = "name"
    SMILES = "smiles"
    INCHI = "inchi"
    INCHIKEY = "inchikey"
    FORMULA = "formula"


class PubChemCompoundInfo(BaseModel):
    """Structure for PubChem compound information."""

    cid: Optional[int] = None
    molecular_formula: Optional[str] = Field(None, alias="MolecularFormula")
    molecular_weight: Optional[float] = Field(None, alias="MolecularWeight")
    iupac_name: Optional[str] = Field(None, alias="IUPACName")
    inchi: Optional[str] = Field(None, alias="InChI")
    inchikey: Optional[str] = Field(None, alias="InChIKey")
    canonical_smiles: Optional[str] = Field(None, alias="CanonicalSMILES")
    isomeric_smiles: Optional[str] = Field(None, alias="IsomericSMILES")
    synonyms: List[str] = Field(default_factory=list)
    error: Optional[str] = None
    identifier: str = ""

    class Config:
        populate_by_name = True


class PubChemEnhancedClient:
    """Enhanced PubChem client with metabolite-specific features.

    Provides comprehensive compound information retrieval from PubChem,
    including chemical properties, synonyms, and cross-references.
    """

    BASE_URL = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"

    def __init__(self, timeout: int = 30, rate_limit_per_second: float = 5.0):
        """Initialize PubChem client.

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

    async def get_compound_info(
        self, identifier: str, id_type: PubChemIdType = PubChemIdType.CID
    ) -> PubChemCompoundInfo:
        """Get comprehensive compound information.

        Args:
            identifier: Compound identifier
            id_type: Type of identifier (cid, name, smiles, inchi, inchikey)

        Returns:
            PubChemCompoundInfo object with compound data
        """
        # Ensure session is initialized
        if not self._session:
            await self.initialize()

        # Get basic properties
        properties = [
            "MolecularFormula",
            "MolecularWeight",
            "IUPACName",
            "InChI",
            "InChIKey",
            "CanonicalSMILES",
            "IsomericSMILES",
        ]

        # For name searches, we need to handle differently
        if id_type == PubChemIdType.NAME:
            # URL encode the name for safety
            import urllib.parse

            encoded_identifier = urllib.parse.quote(identifier)
        else:
            encoded_identifier = identifier

        properties_url = (
            f"{self.BASE_URL}/compound/{id_type.value}/{encoded_identifier}/"
            f"property/{','.join(properties)}/JSON"
        )

        try:
            logger.debug(
                f"Fetching PubChem data for {identifier} (type: {id_type.value})"
            )

            # Get properties
            response = await self._session.get(properties_url)

            if response.status_code == 404:
                logger.warning(f"PubChem compound not found: {identifier}")
                return PubChemCompoundInfo(
                    identifier=identifier, error=f"Compound not found: {identifier}"
                )

            response.raise_for_status()
            data = response.json()

            # Extract properties
            if "PropertyTable" in data and "Properties" in data["PropertyTable"]:
                properties_data = data["PropertyTable"]["Properties"][0]
                compound_info = PubChemCompoundInfo(**properties_data)
                compound_info.identifier = identifier

                # Get CID if not already present
                if "CID" in properties_data:
                    compound_info.cid = properties_data["CID"]

                # Get synonyms using the CID
                if compound_info.cid:
                    synonyms = await self._get_synonyms(
                        str(compound_info.cid), PubChemIdType.CID
                    )
                    compound_info.synonyms = synonyms

                return compound_info
            else:
                return PubChemCompoundInfo(
                    identifier=identifier, error="Invalid response format"
                )

        except httpx.TimeoutException:
            logger.error(f"Timeout fetching PubChem data for {identifier}")
            return PubChemCompoundInfo(identifier=identifier, error="Request timeout")
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching PubChem data for {identifier}: {e}")
            return PubChemCompoundInfo(
                identifier=identifier, error=f"HTTP error: {e.response.status_code}"
            )
        except Exception as e:
            logger.error(f"Error fetching PubChem data for {identifier}: {e}")
            return PubChemCompoundInfo(identifier=identifier, error=str(e))

    async def _get_synonyms(
        self, identifier: str, id_type: PubChemIdType, max_synonyms: int = 20
    ) -> List[str]:
        """Get compound synonyms.

        Args:
            identifier: Compound identifier
            id_type: Type of identifier
            max_synonyms: Maximum number of synonyms to return

        Returns:
            List of synonyms
        """
        url = f"{self.BASE_URL}/compound/{id_type.value}/{identifier}/synonyms/JSON"

        try:
            response = await self._session.get(url)

            if response.status_code == 404:
                return []

            response.raise_for_status()
            data = response.json()

            # Extract synonyms
            if "InformationList" in data and "Information" in data["InformationList"]:
                info = data["InformationList"]["Information"][0]
                if "Synonym" in info:
                    return info["Synonym"][:max_synonyms]

            return []

        except Exception as e:
            logger.debug(f"Error fetching synonyms for {identifier}: {e}")
            return []

    async def search_by_name(
        self, name: str, max_results: int = 10
    ) -> List[PubChemCompoundInfo]:
        """Search for compounds by name.

        Args:
            name: Compound name to search
            max_results: Maximum number of results

        Returns:
            List of matching compounds
        """
        # Ensure session is initialized
        if not self._session:
            await self.initialize()

        import urllib.parse

        encoded_name = urllib.parse.quote(name)

        # First, search for CIDs
        search_url = f"{self.BASE_URL}/compound/name/{encoded_name}/cids/JSON"

        try:
            response = await self._session.get(search_url)

            if response.status_code == 404:
                return []

            response.raise_for_status()
            data = response.json()

            # Get CIDs
            cids = data.get("IdentifierList", {}).get("CID", [])[:max_results]

            if not cids:
                return []

            # Get info for each CID
            results = []
            for cid in cids:
                info = await self.get_compound_info(str(cid), PubChemIdType.CID)
                if not info.error:
                    results.append(info)

            return results

        except Exception as e:
            logger.error(f"Error searching PubChem for '{name}': {e}")
            return []

    async def get_cross_references(self, cid: int) -> Dict[str, List[str]]:
        """Get cross-references to other databases.

        Args:
            cid: PubChem compound ID

        Returns:
            Dictionary of database names to identifier lists
        """
        # Ensure session is initialized
        if not self._session:
            await self.initialize()

        url = f"{self.BASE_URL}/compound/cid/{cid}/xrefs/RegistryID/JSON"

        try:
            response = await self._session.get(url)

            if response.status_code == 404:
                return {}

            response.raise_for_status()
            data = response.json()

            # Parse cross-references
            xrefs: Dict[str, List[str]] = {}

            if "InformationList" in data and "Information" in data["InformationList"]:
                for info in data["InformationList"]["Information"]:
                    if "RegistryID" in info:
                        for reg_id in info["RegistryID"]:
                            # Parse registry IDs (format: "DATABASE:ID")
                            if ":" in reg_id:
                                db_name, db_id = reg_id.split(":", 1)
                                if db_name not in xrefs:
                                    xrefs[db_name] = []
                                xrefs[db_name].append(db_id)

            return xrefs

        except Exception as e:
            logger.error(f"Error fetching cross-references for CID {cid}: {e}")
            return {}

    async def batch_get_compound_info(
        self, identifiers: List[tuple[str, PubChemIdType]], max_concurrent: int = 3
    ) -> Dict[str, PubChemCompoundInfo]:
        """Get compound information for multiple identifiers.

        Args:
            identifiers: List of (identifier, id_type) tuples
            max_concurrent: Maximum concurrent requests

        Returns:
            Dictionary mapping identifier to compound info
        """
        # Ensure session is initialized
        if not self._session:
            await self.initialize()

        results = {}

        # Process in batches to respect rate limits
        import asyncio

        for i in range(0, len(identifiers), max_concurrent):
            batch = identifiers[i : i + max_concurrent]

            # Create tasks for batch
            tasks = [
                self.get_compound_info(identifier, id_type)
                for identifier, id_type in batch
            ]

            # Execute batch
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            # Store results
            for (identifier, _), result in zip(batch, batch_results):
                if isinstance(result, Exception):
                    results[identifier] = PubChemCompoundInfo(
                        identifier=identifier, error=str(result)
                    )
                else:
                    results[identifier] = result

            # Rate limiting between batches
            if i + max_concurrent < len(identifiers):
                await asyncio.sleep(max_concurrent / self.rate_limit_per_second)

        return results
