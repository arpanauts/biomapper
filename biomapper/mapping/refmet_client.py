"""Client for interacting with the RefMet API."""

import logging
from dataclasses import dataclass
from typing import Any, Optional, Dict
import re
from io import StringIO
import pandas as pd

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


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

    def search_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Search RefMet by compound name.

        Args:
            name: Metabolite name to search for

        Returns:
            Dict containing compound info or None if search fails
        """
        try:
            # Clean the name
            clean_name = re.sub(r"[^a-zA-Z0-9\s]", " ", name)
            clean_name = " ".join(clean_name.split())

            url = f"{self.config.base_url}/name_to_refmet_new_minID.php"
            payload = {"metabolite_name": clean_name}

            response = self.session.post(url, data=payload, timeout=self.config.timeout)
            response.raise_for_status()

            if not response.content:
                return None

            # Parse tab-delimited response using pandas
            try:
                df = pd.read_csv(StringIO(response.text), sep="\t")
                if df.empty or len(df.columns) < 6:  # Check for required columns
                    return None
            except pd.errors.EmptyDataError:
                return None
            except pd.errors.ParserError:  # Handle malformed TSV
                return None

            # Get first match
            try:
                result = df.iloc[0].to_dict()
                return {
                    "refmet_id": str(result.get("refmet_id", "")),
                    "name": str(result.get("name", "")),
                    "formula": str(result.get("formula", "")),
                    "exact_mass": str(result.get("exact_mass", "")),
                    "inchikey": str(result.get("inchikey", "")),
                    "pubchem_id": str(result.get("pubchem_id", "")),
                }
            except (KeyError, IndexError):
                return None

        except requests.RequestException:
            return None
