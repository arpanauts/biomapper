"""Mock API clients matching real API interfaces for testing."""

from typing import Dict, Any, List, Optional
import asyncio
from unittest.mock import MagicMock


class MockUniProtAPIClient:
    """Mock client matching real UniProt API interface."""
    
    def __init__(self, cache_size: int = 10000, timeout: int = 30):
        """Initialize mock client."""
        self.cache_size = cache_size
        self.timeout = timeout
        self._cache = {}
        self._call_count = {
            "map_identifiers": 0,
            "resolve_batch": 0,
            "_fetch_uniprot_search_results": 0
        }
    
    async def map_identifiers(
        self,
        source_identifiers: List[str],
        target_ontology_type: Optional[str] = None,
        mapping_params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Mock implementation for mapping identifiers."""
        self._call_count["map_identifiers"] += 1
        
        # Return mock mapping results
        results = {}
        for identifier in source_identifiers:
            # Simulate successful mapping for most IDs
            if identifier.startswith("P") or identifier.startswith("Q"):
                results[identifier] = {
                    "primary_accession": identifier,
                    "status": "active",
                    "confidence": 1.0
                }
            elif identifier == "OBSOLETE123":
                results[identifier] = {
                    "primary_accession": None,
                    "status": "obsolete",
                    "confidence": 0.0
                }
            else:
                # Simulate unmapped ID
                results[identifier] = {
                    "primary_accession": None,
                    "status": "not_found",
                    "confidence": 0.0
                }
        
        return {
            "mappings": results,
            "unmapped": [id for id, r in results.items() if r["primary_accession"] is None],
            "total": len(source_identifiers)
        }
    
    async def resolve_batch(
        self,
        protein_ids: List[str],
        include_metadata: bool = False
    ) -> Dict[str, Any]:
        """Mock implementation for batch resolution."""
        self._call_count["resolve_batch"] += 1
        
        results = {}
        for protein_id in protein_ids:
            if protein_id.startswith("P") or protein_id.startswith("Q"):
                result = {
                    "accession": protein_id,
                    "name": f"Protein {protein_id}",
                    "organism": "Homo sapiens"
                }
                if include_metadata:
                    result["metadata"] = {
                        "created": "2020-01-01",
                        "modified": "2023-01-01",
                        "version": 2
                    }
                results[protein_id] = result
            else:
                results[protein_id] = None
        
        return results
    
    async def _fetch_uniprot_search_results(self, query: str) -> Dict[str, Any]:
        """Mock implementation for search."""
        self._call_count["_fetch_uniprot_search_results"] += 1
        
        # Parse query to extract accessions
        accessions = []
        if "accession:" in query:
            parts = query.split("accession:")
            for part in parts[1:]:
                acc = part.split()[0].strip()
                if acc:
                    accessions.append(acc)
        
        # Return mock search results
        results = []
        for acc in accessions:
            if acc.startswith("P") or acc.startswith("Q"):
                results.append({
                    "primaryAccession": acc,
                    "organism": {"scientificName": "Homo sapiens"},
                    "proteinDescription": {
                        "recommendedName": {
                            "fullName": {"value": f"Protein {acc}"}
                        }
                    }
                })
        
        return {"results": results}
    
    def get_call_count(self, method_name: str) -> int:
        """Get number of times a method was called."""
        return self._call_count.get(method_name, 0)
    
    def reset_call_counts(self):
        """Reset all call counts."""
        for key in self._call_count:
            self._call_count[key] = 0


class MockChemblAPIClient:
    """Mock client for ChEMBL API."""
    
    def __init__(self):
        """Initialize mock client."""
        self._call_count = {
            "search_compounds": 0,
            "get_compound_by_id": 0
        }
    
    def search_compounds(
        self,
        query: str,
        limit: Optional[int] = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Mock compound search."""
        self._call_count["search_compounds"] += 1
        
        # Return mock compounds
        results = []
        if "aspirin" in query.lower():
            results.append({
                "chembl_id": "CHEMBL25",
                "pref_name": "ASPIRIN",
                "max_phase": 4,
                "molecule_type": "Small molecule"
            })
        
        if limit:
            results = results[:limit]
        
        return results
    
    def get_compound_by_id(self, chembl_id: str) -> Dict[str, Any]:
        """Mock getting compound by ID."""
        self._call_count["get_compound_by_id"] += 1
        
        if chembl_id == "CHEMBL25":
            return {
                "chembl_id": "CHEMBL25",
                "pref_name": "ASPIRIN",
                "max_phase": 4,
                "molecule_type": "Small molecule",
                "molecule_properties": {
                    "mw_freebase": 180.16,
                    "alogp": 1.19
                }
            }
        
        return None
    
    def get_call_count(self, method_name: str) -> int:
        """Get number of times a method was called."""
        return self._call_count.get(method_name, 0)


class MockPubChemAPIClient:
    """Mock client for PubChem API."""
    
    def __init__(self):
        """Initialize mock client."""
        self._call_count = {
            "get_compound": 0,
            "search_by_name": 0
        }
    
    def get_compound(
        self,
        cid: str,
        namespace: Optional[str] = "cid",
        domain: Optional[str] = "compound"
    ) -> Dict[str, Any]:
        """Mock getting compound by CID."""
        self._call_count["get_compound"] += 1
        
        if cid == "2244":
            return {
                "CID": 2244,
                "MolecularFormula": "C9H8O4",
                "MolecularWeight": 180.16,
                "IUPACName": "2-acetyloxybenzoic acid",
                "InChIKey": "BSYNRYMUTXBXSQ-UHFFFAOYSA-N"
            }
        
        return None
    
    def search_by_name(
        self,
        name: str,
        max_results: Optional[int] = 10
    ) -> List[Dict[str, Any]]:
        """Mock searching by name."""
        self._call_count["search_by_name"] += 1
        
        results = []
        if "aspirin" in name.lower():
            results.append({
                "CID": 2244,
                "Title": "Aspirin",
                "MolecularFormula": "C9H8O4"
            })
        
        if max_results:
            results = results[:max_results]
        
        return results
    
    def get_call_count(self, method_name: str) -> int:
        """Get number of times a method was called."""
        return self._call_count.get(method_name, 0)


class MockHMDBAPIClient:
    """Mock client for HMDB API."""
    
    def __init__(self):
        """Initialize mock client."""
        self._call_count = {
            "get_metabolite": 0,
            "search_metabolites": 0
        }
    
    def get_metabolite(self, hmdb_id: str) -> Dict[str, Any]:
        """Mock getting metabolite by HMDB ID."""
        self._call_count["get_metabolite"] += 1
        
        if hmdb_id == "HMDB0001875":
            return {
                "accession": "HMDB0001875",
                "name": "Acetylsalicylic acid",
                "chemical_formula": "C9H8O4",
                "monoisotopic_molecular_weight": 180.042259,
                "iupac_name": "2-acetyloxybenzoic acid",
                "synonyms": ["Aspirin", "ASA"]
            }
        
        return None
    
    def search_metabolites(
        self,
        query: str,
        search_type: Optional[str] = "name",
        limit: Optional[int] = 10
    ) -> List[Dict[str, Any]]:
        """Mock searching metabolites."""
        self._call_count["search_metabolites"] += 1
        
        results = []
        if "aspirin" in query.lower() or "acetylsalicylic" in query.lower():
            results.append({
                "accession": "HMDB0001875",
                "name": "Acetylsalicylic acid",
                "chemical_formula": "C9H8O4"
            })
        
        if limit:
            results = results[:limit]
        
        return results
    
    def get_call_count(self, method_name: str) -> int:
        """Get number of times a method was called."""
        return self._call_count.get(method_name, 0)


class MockFailingAPIClient:
    """Mock client that simulates API failures for testing error handling."""
    
    def __init__(self, failure_mode: str = "network"):
        """
        Initialize with specific failure mode.
        
        Args:
            failure_mode: Type of failure to simulate
                - "network": Network/connection errors
                - "timeout": Timeout errors
                - "rate_limit": Rate limiting errors
                - "invalid_response": Invalid response format
        """
        self.failure_mode = failure_mode
    
    async def map_identifiers(self, *args, **kwargs):
        """Simulate failing API call."""
        if self.failure_mode == "network":
            raise ConnectionError("Failed to connect to API server")
        elif self.failure_mode == "timeout":
            await asyncio.sleep(100)  # Simulate long delay
            raise TimeoutError("API request timed out")
        elif self.failure_mode == "rate_limit":
            raise Exception("API rate limit exceeded (429)")
        elif self.failure_mode == "invalid_response":
            return "Invalid response format - not a dict"
        else:
            raise Exception(f"Unknown failure mode: {self.failure_mode}")
    
    def get_data(self, *args, **kwargs):
        """Simulate failing synchronous call."""
        if self.failure_mode == "network":
            raise ConnectionError("Failed to connect to API server")
        elif self.failure_mode == "timeout":
            raise TimeoutError("API request timed out")
        else:
            raise Exception(f"API error: {self.failure_mode}")


def create_mock_client(client_type: str, **kwargs) -> Any:
    """
    Factory function to create mock API clients.
    
    Args:
        client_type: Type of client to create
            - "uniprot": Mock UniProt client
            - "chembl": Mock ChEMBL client
            - "pubchem": Mock PubChem client
            - "hmdb": Mock HMDB client
            - "failing": Mock client that fails
        **kwargs: Additional arguments for client initialization
        
    Returns:
        Mock client instance
    """
    clients = {
        "uniprot": MockUniProtAPIClient,
        "chembl": MockChemblAPIClient,
        "pubchem": MockPubChemAPIClient,
        "hmdb": MockHMDBAPIClient,
        "failing": MockFailingAPIClient
    }
    
    if client_type not in clients:
        raise ValueError(f"Unknown client type: {client_type}")
    
    return clients[client_type](**kwargs)