"""Client for interacting with the RefMet API."""

import logging
from dataclasses import dataclass
from typing import Any, Optional, Dict
import re
import pandas as pd
import io

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

logging.basicConfig(level=logging.DEBUG)


class RefMetError(Exception):
    """Custom exception for RefMet API errors."""

    pass


@dataclass
class RefMetConfig:
    """Configuration for RefMet API client."""

    base_url: str = "https://www.metabolomicsworkbench.org/databases/refmet"
    timeout: int = 30
    max_retries: int = 3
    backoff_factor: float = 0.5


class RefMetResult:
    """Result from RefMet entity lookup."""
    
    def __init__(self, data: Dict[str, Any]):
        self.refmet_id = data.get("refmet_id", "")
        self.name = data.get("name", "")
        self.formula = data.get("formula", "")
        self.exact_mass = data.get("exact_mass", "")
        self.inchikey = data.get("inchikey", "")
        self.pubchem_id = data.get("pubchem_id", "")
        self.chebi_id = data.get("chebi_id", "")
        self.hmdb_id = data.get("hmdb_id", "")
        self.kegg_id = data.get("kegg_id", "")
        self.raw_data = data  # Store the original data


class RefMetClient:
    """Client for interacting with the RefMet REST API."""

    def __init__(self, config: Optional[RefMetConfig] = None) -> None:
        """Initialize the RefMet API client.

        Args:
            config: Optional RefMetConfig object with custom settings
        """
        self.config = config or RefMetConfig()
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

    def preprocess_complex_terms(self, term: str) -> list[str]:
        """Break down complex terms into simpler searchable terms.

        Args:
            term: Complex term like "Total HDL cholesterol"

        Returns:
            List of simpler terms to search
        """
        skip_words = {"total", "free", "ratio", "concentration", "average", "diameter"}

        term = term.lower()
        for split_word in ["in", "to", "of", "and"]:
            term = term.replace(f" {split_word} ", ";")

        parts = [p.strip() for p in term.split(";") if p.strip()]

        cleaned_parts = []
        for part in parts:
            words = part.split()
            words = [w for w in words if w not in skip_words]
            if words:
                cleaned_parts.append(" ".join(words))

        return cleaned_parts

    def search_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Search RefMet by compound name."""
        # Clean and lowercase the name
        clean_name = re.sub(r"[^a-zA-Z0-9\s\-]", " ", name)
        clean_name = re.sub(r"\s+", " ", clean_name).strip().lower()

        url = f"{self.config.base_url}/name_to_refmet_new_minID.php"
        payload = {"metabolite_name": clean_name}

        retries = 0
        while retries < self.config.max_retries:
            try:
                response = self.session.post(
                    url, data=payload, timeout=self.config.timeout
                )
                response.raise_for_status()

                if not response.content:
                    return None

                # Parse TSV response
                df = pd.read_csv(io.StringIO(response.text), sep="\t")
                if df.empty:
                    return None

                # Extract first row
                row = df.iloc[0]

                # Helper function to safely get values
                def safe_get(val: Any) -> str:
                    return (
                        str(val).strip()
                        if pd.notna(val) and str(val).strip() != "-"
                        else ""
                    )

                # Get ChEBI ID and add prefix if it's a valid ID
                chebi_id = safe_get(row.get("ChEBI_ID"))
                if chebi_id and chebi_id.isdigit():
                    chebi_id = f"CHEBI:{chebi_id}"

                # Map all expected fields
                result = {
                    "refmet_id": safe_get(row.get("RefMet_ID")),
                    "name": safe_get(row.get("Standardized name")),
                    "formula": safe_get(row.get("Formula")),
                    "exact_mass": safe_get(row.get("Exact mass")),
                    "inchikey": safe_get(row.get("INCHI_KEY")),
                    "pubchem_id": safe_get(row.get("PubChem_CID")),
                    "chebi_id": chebi_id,
                    "hmdb_id": safe_get(row.get("HMDB_ID")),
                    "kegg_id": safe_get(row.get("KEGG_ID")),
                }

                # Remove empty fields
                result = {k: v for k, v in result.items() if v}

                return result if result else None

            except Exception as e:
                logger.error(f"RefMet search failed: {str(e)}")
                retries += 1
                if retries == self.config.max_retries:
                    return None

        return None

    def _direct_search(self, name: str) -> Optional[Dict[str, Any]]:
        """Internal method for direct RefMet search.

        Args:
            name: Name to search for

        Returns:
            Dict containing compound info or None if search fails
        """
        # Clean the name
        clean_name = re.sub(r"[^a-zA-Z0-9\s\-]", " ", name)
        clean_name = re.sub(r"\s+", " ", clean_name).strip().lower()

        url = f"{self.config.base_url}/name_to_refmet_new_minID.php"
        payload = {"metabolite_name": clean_name}

        try:
            response = self.session.post(url, data=payload, timeout=self.config.timeout)
            response.raise_for_status()

            if not response.content:
                return None

            return self._process_response(response.text)

        except Exception as e:
            logger.warning(f"RefMet search failed for '{name}': {str(e)}")
            return None

    def get_entity_by_id(self, refmet_id: str) -> Optional[RefMetResult]:
        """Get RefMet entity by ID.
        
        Args:
            refmet_id: RefMet ID in format 'REFMET:123' or '123'
            
        Returns:
            RefMetResult object or None if the entity is not found
            
        Raises:
            RefMetError: If the request fails
        """
        try:
            # Clean ID format - handle REFMET: prefix if present
            clean_id = refmet_id.replace("REFMET:", "")
            
            # RefMet doesn't have a direct ID lookup API endpoint, so we use the metabolite name endpoint
            # and filter by ID in the results
            url = f"{self.config.base_url}/refmet_all.php"
            
            try:
                response = self.session.get(url, timeout=self.config.timeout)
                response.raise_for_status()
                
                # Parse the TSV data
                df = pd.read_csv(io.StringIO(response.text), sep="\t")
                
                # Find the row with matching RefMet ID
                matching_rows = df[df["RefMet_ID"] == clean_id]
                
                if matching_rows.empty:
                    logger.warning(f"No RefMet entity found for ID: {refmet_id}")
                    return None
                    
                # Get the first matching row
                row = matching_rows.iloc[0]
                
                # Process the result
                result = self._create_result_from_row(row)
                return RefMetResult(result) if result else None
                
            except Exception as e:
                logger.error(f"RefMet API request failed: {str(e)}")
                raise RefMetError(f"API request failed: {str(e)}") from e
                
        except Exception as e:
            logger.error(f"RefMet entity lookup failed: {str(e)}")
            raise RefMetError(f"Entity lookup failed: {str(e)}") from e
    
    def _create_result_from_row(self, row) -> Dict[str, Any]:
        """Create a result dictionary from a DataFrame row.
        
        Args:
            row: Pandas DataFrame row with RefMet data
            
        Returns:
            Dictionary with processed RefMet data
        """
        # Get RefMet ID and add prefix if needed
        refmet_id = str(row.get("RefMet_ID", ""))
        if refmet_id and not refmet_id.startswith("REFMET:"):
            refmet_id = f"REFMET:{refmet_id}"
        
        # Get ChEBI ID and add prefix if it's a valid ID
        chebi_id = row.get("ChEBI_ID", "")
        if pd.notna(chebi_id) and str(chebi_id).strip() and str(chebi_id).strip() != "-":
            chebi_id = f"CHEBI:{chebi_id}"
        else:
            chebi_id = ""
            
        # Create the result dictionary
        return {
            "refmet_id": refmet_id,
            "name": str(row.get("Standardized name", "")),
            "formula": str(row.get("Formula", "")),
            "exact_mass": str(row.get("Exact mass", "")),
            "inchikey": str(row.get("INCHI_KEY", "")),
            "pubchem_id": str(row.get("PubChem_CID", "")),
            "chebi_id": chebi_id,
            "hmdb_id": str(row.get("HMDB_ID", "")),
            "kegg_id": str(row.get("KEGG_ID", "")),
        }

    def _process_response(
        self, response_text: str
    ) -> Optional[Dict[str, Optional[str]]]:
        """Process the RefMet response text."""
        try:
            df = pd.read_csv(io.StringIO(response_text), sep="\t")
            if df.empty:
                return None

            row = df.iloc[0]
            return self._create_result_from_row(row)

        except Exception as e:
            logger.error(f"Error processing RefMet response: {e}")
            return None
