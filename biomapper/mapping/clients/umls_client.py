# /home/ubuntu/biomapper/biomapper/mapping/clients/umls_client.py
import requests
import logging
from typing import Optional, Dict, Any, List, Union, cast, TypedDict, Iterable
# from lxml.html import fromstring # Potentially needed for TGT extraction

# TODO: Add configuration model (e.g., Pydantic) for API key, base_url, version

logger = logging.getLogger(__name__)


class UMLSClient:
    """
    Client for interacting with the UMLS Terminology Services (UTS) API.
    Requires a UMLS account and API key for authentication.

    Primarily used for searching terms to find Concept Unique Identifiers (CUIs).
    See: https://documentation.uts.nlm.nih.gov/rest/home.html
    """

    # Default config - requires api_key to be set
    DEFAULT_CONFIG = {
        "base_url": "https://uts-ws.nlm.nih.gov/rest",
        "version": "current",
        "api_key": None,  # MUST be provided in config
        "timeout": 60,
        "auth_endpoint": "https://utslogin.nlm.nih.gov/cas/v1/api-key",
    }

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = self.DEFAULT_CONFIG.copy()
        if config:
            self.config.update(config)

        if not self.config.get("api_key"):
            raise ValueError("UMLS API key must be provided in the configuration.")

        self.session = requests.Session()
        # TODO: Implement robust session management and authentication (TGT/Service Tickets)
        self.tgt = self._get_ticket_granting_ticket()  # Placeholder

    def _get_ticket_granting_ticket(self) -> Optional[str]:
        """Authenticates with the UMLS API key to get a Ticket-Granting Ticket (TGT)."""
        # Placeholder implementation - Requires parsing HTML or specific auth flow
        # See: https://documentation.uts.nlm.nih.gov/rest/authentication.html
        params = {"apikey": self.config["api_key"]}
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        try:
            # This needs proper implementation - the example below is conceptual
            # response = self.session.post(self.config['auth_endpoint'], data=params, headers=headers)
            # response.raise_for_status()
            # tgt = fromstring(response.text).xpath('//form/@action')[0] # Example parsing
            # logger.info("Successfully obtained UMLS TGT.")
            # return tgt
            logger.warning("UMLS TGT retrieval is not fully implemented.")
            return "dummy-tgt"  # Return a dummy value for now
        except requests.exceptions.RequestException as e:
            logger.error(f"Error obtaining UMLS TGT: {e}")
            return None
        except Exception as e:
            logger.error(f"Error parsing UMLS TGT response: {e}")
            return None

    def _get_service_ticket(self, tgt: str) -> Optional[str]:
        """Gets a single-use Service Ticket (ST) using the TGT."""
        # Placeholder implementation
        # See: https://documentation.uts.nlm.nih.gov/rest/authentication.html
        params = {"service": self.config["base_url"]}
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        auth_url_with_tgt = f"{self.config['auth_endpoint']}/{tgt}"
        try:
            # response = self.session.post(auth_url_with_tgt, data=params, headers=headers)
            # response.raise_for_status()
            # service_ticket = response.text
            # logger.debug("Successfully obtained UMLS Service Ticket.")
            # return service_ticket
            logger.warning("UMLS Service Ticket retrieval is not fully implemented.")
            return "dummy-st"  # Return a dummy value for now
        except requests.exceptions.RequestException as e:
            logger.error(f"Error obtaining UMLS Service Ticket: {e}")
            return None

    def search_term(
        self,
        term: str,
        search_type: str = "exact",
        input_type: str = "string",
        result_type: str = "CUI",
        page_size: int = 10,
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Searches the UMLS Metathesaurus for a given term.

        Args:
            term: The term to search for.
            search_type: Type of search (e.g., 'exact', 'words', 'leftTruncation').
            input_type: Type of input term (e.g., 'string', 'sourceConcept', 'sourceDescriptor').
            result_type: Type of result to retrieve (usually 'CUI').
            page_size: Number of results per page.

        Returns:
            A list of result dictionaries containing CUIs and names, or None on failure.
        """
        if not self.tgt:
            logger.error("Cannot perform search without a valid UMLS TGT.")
            return None

        service_ticket = self._get_service_ticket(self.tgt)
        if not service_ticket:
            logger.error("Cannot perform search without a valid UMLS Service Ticket.")
            return None

        search_url = f"{self.config['base_url']}/search/{self.config['version']}"
        params = {
            "string": term,
            "inputType": input_type,
            "searchType": search_type,
            "resultType": result_type,
            "pageSize": page_size,
            "ticket": service_ticket,
        }

        try:
            logger.debug(f"Querying UMLS Search API: {search_url} with term: {term}")
            # Convert params to appropriate type for requests
            request_params = {k: v for k, v in params.items()}
            # Convert timeout to float for requests
            timeout_val = (
                float(self.config["timeout"])
                if self.config["timeout"] is not None
                else None
            )
            response = self.session.get(
                search_url,
                params=request_params,
                timeout=timeout_val,  # type: ignore
            )
            response.raise_for_status()
            results = response.json()

            # The actual results are nested under 'result' -> 'results'
            if results and "result" in results and "results" in results["result"]:
                search_results = results["result"]["results"]
                logger.info(
                    f"Found {len(search_results)} UMLS results for term '{term}'."
                )
                # Type cast to ensure correct return type
                return cast(
                    List[Dict[str, Any]], search_results
                )  # List of dicts, e.g., [{'ui': 'C0003733', 'name': 'Aspirin'}, ...]
            else:
                logger.warning(
                    f"No UMLS results found for term '{term}'. Response: {results}"
                )
                return []  # Return empty list for no results
        except requests.exceptions.HTTPError as e:
            logger.error(
                f"HTTP error querying UMLS Search API for term '{term}': {e} - Response: {e.response.text}"
            )
            return None
        except requests.exceptions.RequestException as e:
            logger.error(
                f"Request error querying UMLS Search API for term '{term}': {e}"
            )
            return None
        except Exception as e:
            logger.exception(
                f"Unexpected error querying UMLS Search API for term '{term}': {e}"
            )
            return None

    def close_session(self) -> None:
        """Close the underlying requests session."""
        if self.session:
            self.session.close()


# Example Usage (Requires API Key in environment variable UMLS_API_KEY)
if __name__ == "__main__":
    import os

    api_key = os.environ.get("UMLS_API_KEY")
    if not api_key:
        print("Please set the UMLS_API_KEY environment variable to run the example.")
    else:
        logging.basicConfig(level=logging.INFO)
        client_config = {"api_key": api_key}
        client = UMLSClient(config=client_config)

        # Note: Authentication is stubbed, so this will likely fail or use dummy tickets
        test_term = "aspirin"
        print(f"\nSearching for term: {test_term}")
        results = client.search_term(test_term, search_type="exact")
        if results is not None:
            print(f"Found {len(results)} results:")
            for res in results[:5]:  # Print top 5
                print(f"  CUI: {res.get('ui')}, Name: {res.get('name')}")
        else:
            print("Search failed.")

        test_term_fail = "NonExistentTermXYZ123"
        print(f"\nSearching for term: {test_term_fail}")
        results_fail = client.search_term(test_term_fail)
        if results_fail is not None and len(results_fail) == 0:
            print("Correctly found no results.")
        elif results_fail is not None:
            print(f"Found unexpected results: {results_fail}")
        else:
            print("Search failed.")

        client.close_session()
