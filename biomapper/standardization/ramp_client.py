"""RaMP-DB API Client for interfacing with the RaMP database."""

import json
from collections import defaultdict
from dataclasses import dataclass
from enum import Enum
from typing import Any

import requests


class RaMPAPIError(Exception):
    """Custom exception for RaMP API errors."""

    pass


class AnalyteType(Enum):
    """Enumeration for analyte types in RaMP queries."""

    METABOLITE = "metabolite"
    GENE = "gene"
    BOTH = "both"


@dataclass
class RaMPConfig:
    """Configuration for RaMP API client."""

    base_url: str = "https://rampdb.nih.gov/api"
    timeout: int = 30


@dataclass
class PathwayStats:
    """Statistics about pathways associated with an analyte."""

    total_pathways: int
    pathways_by_source: dict[str, int]
    unique_pathway_names: set[str]
    pathway_sources: set[str]


class RaMPClient:
    """Client for interacting with the RaMP-DB API."""

    def __init__(self, config: RaMPConfig | None = None) -> None:
        """Initialize the RaMP API client.

        Args:
            config: Optional RaMPConfig object with custom settings.
        """
        self.config = config or RaMPConfig()
        self.session = requests.Session()

    def _make_request(
        self, method: str, endpoint: str, **kwargs: Any
    ) -> dict[str, Any]:
        """Make a request to the RaMP API.

        Args:
            method: HTTP method to use
            endpoint: API endpoint to call
            **kwargs: Additional arguments to pass to requests

        Returns:
            Dict containing the response data

        Raises:
            RaMPAPIError: If the request fails
        """
        url = f"{self.config.base_url}/{endpoint}"

        try:
            response = self.session.request(
                method=method, url=url, timeout=self.config.timeout, **kwargs
            )
            response.raise_for_status()
            return dict(response.json())
        except requests.exceptions.RequestException as e:
            raise RaMPAPIError(f"Request failed: {e!s}") from e

    def get_source_versions(self) -> dict[str, Any]:
        """Get available source database versions."""
        return self._make_request("GET", "source-versions")

    def get_valid_id_types(self) -> dict[str, Any]:
        """Get valid ID types."""
        return self._make_request("GET", "validIdTypes")

    def get_pathway_info(self, pathway_id: str) -> dict[str, Any]:
        """Retrieve detailed information about a specific pathway."""
        return self._make_request("GET", f"pathwayInfo/{pathway_id}")

    def get_metabolite_info(self, metabolite_id: str) -> dict[str, Any]:
        """Retrieve detailed information about a specific metabolite."""
        return self._make_request("GET", f"metaboliteInfo/{metabolite_id}")

    def get_pathways_from_analytes(
        self, analytes: list[str]
    ) -> dict[str, list[dict[str, str]]]:
        """Get pathways associated with given analytes."""
        payload = {"analytes": analytes}
        return self._make_request("POST", "pathways-from-analytes", json=payload)

    def get_chemical_classes(self, metabolites: list[str]) -> dict[str, Any]:
        """Get chemical classes for given metabolites."""
        payload = {"metabolites": metabolites}
        return self._make_request("POST", "chemical-classes", json=payload)

    def get_chemical_properties(self, metabolites: list[str]) -> dict[str, Any]:
        """Get chemical properties for given metabolites."""
        payload = {"metabolites": metabolites}
        return self._make_request("POST", "chemical-properties", json=payload)

    def get_ontologies_from_metabolites(
        self, metabolites: list[str], names_or_ids: str = "ids"
    ) -> dict[str, Any]:
        """Get ontology mappings for metabolites."""
        payload = {"metabolite": metabolites, "namesOrIds": names_or_ids}
        return self._make_request("POST", "ontologies-from-metabolites", json=payload)

    def get_metabolites_from_ontologies(
        self, ontologies: list[str], output_format: str = "json"
    ) -> dict[str, Any]:
        """Get metabolites associated with ontology terms."""
        payload = {"ontology": ontologies, "format": output_format}
        return self._make_request("POST", "metabolites-from-ontologies", json=payload)

    def analyze_pathway_stats(
        self, pathways_data: dict[str, Any]
    ) -> dict[str, PathwayStats]:
        """Analyze pathway statistics from response data."""
        stats: dict[str, PathwayStats] = {}

        if "result" not in pathways_data:
            return stats

        # Group pathways by analyte
        pathways_by_analyte = defaultdict(list)
        for pathway in pathways_data["result"]:
            analyte_id = pathway["inputId"]
            pathways_by_analyte[analyte_id].append(pathway)

        # Calculate stats for each analyte
        for analyte_id, pathways in pathways_by_analyte.items():
            pathways_by_source = defaultdict(list)
            unique_names = set()
            sources = set()

            for pathway in pathways:
                source = pathway["pathwaySource"]
                name = pathway["pathwayName"]
                pathways_by_source[source].append(pathway)
                unique_names.add(name)
                sources.add(source)

            stats[analyte_id] = PathwayStats(
                total_pathways=len(pathways),
                pathways_by_source={k: len(v) for k, v in pathways_by_source.items()},
                unique_pathway_names=unique_names,
                pathway_sources=sources,
            )

        return stats

    def find_pathway_overlaps(self, pathways_data: dict[str, Any]) -> dict[str, int]:
        """Find overlapping pathways in response data."""
        if "result" not in pathways_data:
            return {}

        pathway_counts = defaultdict(set)

        # Count analytes per pathway
        for pathway in pathways_data["result"]:
            name = pathway["pathwayName"]
            analyte_id = pathway["inputId"]
            pathway_counts[name].add(analyte_id)

        # Convert sets to counts
        return {name: len(analytes) for name, analytes in pathway_counts.items()}

    def get_common_reaction_analytes(self, analytes: list[str]) -> dict[str, Any]:
        """Get common reaction analytes."""
        payload = {"analyte": analytes}
        return self._make_request("POST", "common-reaction-analytes", json=payload)

    def get_reactions_from_analytes(self, analytes: list[str]) -> dict[str, Any]:
        """Get reactions associated with analytes."""
        payload = {"analytes": analytes}
        return self._make_request("POST", "reactions-from-analytes", json=payload)

    def get_reaction_classes(self, analytes: list[str]) -> dict[str, Any]:
        """Get reaction classes for analytes."""
        payload = {"analytes": analytes}
        return self._make_request(
            "POST", "reaction-classes-from-analytes", json=payload
        )

    def perform_chemical_enrichment(self, metabolites: list[str]) -> dict[str, Any]:
        """Perform chemical enrichment analysis."""
        payload = {"metabolites": metabolites}
        return self._make_request("POST", "chemical-enrichment", json=payload)

    def get_pathway_by_analyte(
        self, analyte_ids: list[str], analyte_type: AnalyteType = AnalyteType.BOTH
    ) -> dict[str, Any]:
        """Find pathways associated with given analytes."""
        params = {
            "sourceId": analyte_ids,
            "queryType": analyte_type.value,
        }
        return self._make_request("GET", "pathwayFromAnalyte", params=params)

    def get_pathway_by_name(self, pathway_name: str) -> dict[str, Any]:
        """Search for pathways by name or description."""
        params = {"pathway": pathway_name}
        return self._make_request("GET", "pathwayFromName", params=params)

    def get_pathway_by_ontology(self, ontology_id: str) -> dict[str, Any]:
        """Find pathways using ontology identifiers."""
        params = {"ontologyId": ontology_id}
        return self._make_request("GET", "pathwayFromOntology", params=params)

    def get_analytes_by_pathway(
        self, pathway_id: str, analyte_type: AnalyteType = AnalyteType.BOTH
    ) -> dict[str, Any]:
        """Retrieve analytes associated with a pathway."""
        params = {"pathwayId": pathway_id, "queryType": analyte_type.value}
        return self._make_request("GET", "analyteFromPathway", params=params)

    def get_analytes_by_ontology(
        self, ontology_id: str, analyte_type: AnalyteType = AnalyteType.BOTH
    ) -> dict[str, Any]:
        """Find analytes using ontology identifiers."""
        params = {"ontologyId": ontology_id, "queryType": analyte_type.value}
        return self._make_request("GET", "analyteFromOntology", params=params)


# Example usage:
if __name__ == "__main__":
    # Initialize client
    client = RaMPClient()

    # Example metabolite IDs (with prefix)
    test_metabolites = ["hmdb:HMDB0000001", "hmdb:HMDB0000002"]

    # Get chemical properties
    try:
        properties = client.get_chemical_properties(test_metabolites)
        print(json.dumps(properties, indent=2))
    except RaMPAPIError as e:
        print(f"Error: {e}")
