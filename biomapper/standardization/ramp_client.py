"""
RaMP-DB API Client

This module provides a Python interface to the RaMP-DB REST API.
It handles authentication, request formation, and response parsing
for interacting with the RaMP database of metabolic pathways.
"""

import requests
from typing import List, Dict, Union, Optional
import json
from dataclasses import dataclass
from collections import defaultdict
from itertools import combinations
from enum import Enum

class RaMPAPIError(Exception):
    """Custom exception for RaMP API errors"""
    pass

class AnalyteType(Enum):
    """Enumeration for analyte types in RaMP queries"""
    METABOLITE = "metabolite"
    GENE = "gene"
    BOTH = "both"

@dataclass
class RaMPConfig:
    """Configuration for RaMP API client"""
    base_url: str = "https://rampdb.nih.gov/api"
    timeout: int = 30

@dataclass
class PathwayStats:
    """Statistics about pathways for a metabolite"""
    total_pathways: int
    pathways_by_source: dict
    unique_pathway_names: set
    pathway_sources: set

class RaMPClient:
    """Client for interacting with the RaMP-DB API"""
    
    def __init__(self, config: Optional[RaMPConfig] = None):
        """Initialize the RaMP API client
        
        Args:
            config: Optional RaMPConfig object with custom settings
        """
        self.config = config or RaMPConfig()
        self.session = requests.Session()
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict:
        """Make a request to the RaMP API
        
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
                method=method,
                url=url,
                timeout=self.config.timeout,
                **kwargs
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise RaMPAPIError(f"Request failed: {str(e)}") from e
    
    def get_source_versions(self) -> Dict:
        """Get RaMP source database versions
        
        Returns:
            Dict containing version information
        """
        return self._make_request("GET", "source-versions")
    
    def get_id_types(self) -> Dict:
        """Get valid RaMP database prefixes for genes and metabolites
        
        Returns:
            Dict containing valid ID prefixes
        """
        return self._make_request("GET", "id-types")
    
    def get_pathways_from_analytes(self, analytes: List[str]) -> Dict[str, List[Dict]]:
        """Get pathways associated with a list of analyte IDs
        
        Args:
            analytes: List of analyte IDs (must include source prefix, e.g. "hmdb:HMDB0000001")
            
        Returns:
            Dict containing:
                - data: List of pathway dictionaries with pathway information
                - function_call: The R function call used
                - numFoundIds: Number of IDs found
        """
        payload = {"analytes": analytes}
        return self._make_request("POST", "pathways-from-analytes", json=payload)
    
    def get_chemical_classes(self, metabolites: List[str]) -> Dict:
        """Get chemical classes for a list of metabolite IDs
        
        Args:
            metabolites: List of metabolite IDs (must include source prefix)
            
        Returns:
            Dict containing chemical class information
        """
        payload = {"metabolites": metabolites}
        return self._make_request("POST", "chemical-classes", json=payload)
    
    def get_chemical_properties(self, metabolites: List[str]) -> Dict:
        """Get chemical properties for a list of metabolite IDs
        
        Args:
            metabolites: List of metabolite IDs (must include source prefix)
            
        Returns:
            Dict containing chemical properties
        """
        payload = {"metabolites": metabolites}
        return self._make_request("POST", "chemical-properties", json=payload)
    
    def get_ontologies_from_metabolites(
        self, 
        metabolites: List[str], 
        names_or_ids: str = "ids"
    ) -> Dict:
        """Get ontology mappings for a list of metabolites
        
        Args:
            metabolites: List of metabolite IDs or names
            names_or_ids: Whether the input is names or ids (default: "ids")
            
        Returns:
            Dict containing ontology mappings
        """
        payload = {
            "metabolite": metabolites,
            "namesOrIds": names_or_ids
        }
        return self._make_request("POST", "ontologies-from-metabolites", json=payload)

    def get_metabolites_from_ontologies(
        self,
        ontologies: List[str],
        output_format: str = "json"
    ) -> Dict:
        """Get metabolites associated with ontology terms
        
        Args:
            ontologies: List of ontology terms
            output_format: Desired output format (default: "json")
            
        Returns:
            Dict containing metabolite information
        """
        payload = {
            "ontology": ontologies,
            "format": output_format
        }
        return self._make_request("POST", "metabolites-from-ontologies", json=payload)
    
    def analyze_pathway_stats(self, pathways_data: Dict) -> Dict[str, PathwayStats]:
        """Analyze pathway statistics for each metabolite
        
        Args:
            pathways_data: Response from get_pathways_from_analytes()
            
        Returns:
            Dict mapping metabolite IDs to their PathwayStats
        """
        stats = {}
        
        if "result" not in pathways_data:
            return stats
            
        # Group pathways by metabolite
        pathways_by_metabolite = defaultdict(list)
        for pathway in pathways_data["result"]:
            metabolite_id = pathway["inputId"]
            pathways_by_metabolite[metabolite_id].append(pathway)
            
        # Calculate stats for each metabolite
        for metabolite_id, pathways in pathways_by_metabolite.items():
            pathways_by_source = defaultdict(list)
            unique_names = set()
            sources = set()
            
            for pathway in pathways:
                source = pathway["pathwaySource"]
                name = pathway["pathwayName"]
                pathways_by_source[source].append(pathway)
                unique_names.add(name)
                sources.add(source)
            
            stats[metabolite_id] = PathwayStats(
                total_pathways=len(pathways),
                pathways_by_source={k: len(v) for k, v in pathways_by_source.items()},
                unique_pathway_names=unique_names,
                pathway_sources=sources
            )
            
        return stats
        
    def find_pathway_overlaps(self, pathways_data: Dict) -> Dict[str, int]:
        """Find pathways that are shared between metabolites
        
        Args:
            pathways_data: Response from get_pathways_from_analytes()
            
        Returns:
            Dict mapping pathway names to number of metabolites involved
        """
        if "result" not in pathways_data:
            return {}
            
        pathway_counts = defaultdict(set)
        
        # Count metabolites per pathway
        for pathway in pathways_data["result"]:
            name = pathway["pathwayName"]
            metabolite_id = pathway["inputId"]
            pathway_counts[name].add(metabolite_id)
            
        # Convert sets to counts
        return {name: len(metabolites) for name, metabolites in pathway_counts.items()}

    def perform_chemical_enrichment(self, metabolites: List[str]) -> Dict:
        """Perform chemical class enrichment analysis
        
        Args:
            metabolites: List of metabolite IDs (must include source prefix)
            
        Returns:
            Dict containing enrichment results
        """
        payload = {"metabolites": metabolites}
        return self._make_request("POST", "chemical-enrichment", json=payload)

# Example usage:
if __name__ == "__main__":
    # Initialize client
    client = RaMPClient()
    
    # Example metabolite IDs
    test_metabolites = [
        "hmdb:HMDB0000001",
        "hmdb:HMDB0000002"
    ]
    
    # Get chemical properties
    try:
        properties = client.get_chemical_properties(test_metabolites)
        print(json.dumps(properties, indent=2))
    except RaMPAPIError as e:
        print(f"Error: {e}")