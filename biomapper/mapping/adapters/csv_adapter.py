"""
csv_adapter.py

Adapter for extracting and normalizing identifiers from MetabolitesCSV endpoint values.
Integrates with extractors utility.
"""
from typing import Any, Dict, Optional, List
from biomapper.mapping.extractors import extract_all_ids, SUPPORTED_ID_TYPES
from biomapper.mapping.metadata.interfaces import EndpointAdapter

class CSVAdapter(EndpointAdapter):
    """
    Adapter for extracting identifiers from single string values, typically CSV cells.
    Implements the EndpointAdapter interface.
    """
    def __init__(self, config: Optional[Dict[str, Any]] = None, resource_name: str = "csv_adapter"):
        # Consider adding super().__init__() if EndpointAdapter evolves a base init
        self.config = config or {}
        self.resource_name = resource_name

    async def extract_ids(
        self,
        value: str, 
        endpoint_id: int, # Currently unused, but part of the interface
        ontology_type: str,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """Extract IDs of a specific ontology type from a value.

        Args:
            value: The value (e.g., cell content) to extract IDs from.
            endpoint_id: The endpoint ID (contextual).
            ontology_type: The specific ontology type (e.g., 'hmdb', 'chebi') to extract.
            **kwargs: Additional keyword arguments.
            
        Returns:
            List containing a dict {'id': extracted_id, 'ontology_type': ontology_type, 'confidence': 1.0}
            if found, otherwise an empty list.
        """
        extracted = extract_all_ids(value)
        found_id = extracted.get(ontology_type)
        if found_id:
            return [{
                "id": found_id,
                "ontology_type": ontology_type,
                "confidence": 1.0 # Direct extraction assumed high confidence
            }]
        return []

    def get_supported_extractions(self, endpoint_id: int) -> List[str]:
        """Get supported extraction ontology types for this adapter.
        
        Args:
            endpoint_id: The endpoint ID (contextual).
            
        Returns:
            List of supported ontology type strings (e.g., ['hmdb', 'chebi']).
        """
        # Ideally, get this dynamically from extractors.py
        return list(SUPPORTED_ID_TYPES) 
