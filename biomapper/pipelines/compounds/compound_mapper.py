"""Compound mapping implementation."""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Dict, Any

from ...core.base_mapper import APIMapper, MappingResult
from ...core.base_client import BaseAPIClient, APIResponse
from ...schemas.domain_schema import DomainDocument

logger = logging.getLogger(__name__)


class CompoundClass(Enum):
    """Types of compound measurements."""
    SIMPLE = "simple"  # Direct compound measurement
    RATIO = "ratio"  # Ratio between two compounds
    CONCENTRATION = "concentration"  # Concentration in specific matrix/tissue
    COMPOSITE = "composite"  # Composite measurement of multiple compounds
    LIPOPROTEIN = "lipoprotein"  # Lipoprotein particle measurements


class CompoundDocument(DomainDocument):
    """Standard compound document."""
    name: str
    compound_class: CompoundClass
    primary_id: Optional[str] = None
    secondary_id: Optional[str] = None
    refmet_id: Optional[str] = None
    refmet_name: Optional[str] = None
    chebi_id: Optional[str] = None
    chebi_name: Optional[str] = None
    hmdb_id: Optional[str] = None
    pubchem_id: Optional[str] = None
    confidence: float = 0.0
    source: str = "api"
    metadata: Dict[str, Any] = None

    def update_from_rag(self, rag_result: MappingResult) -> None:
        """Update document with RAG mapping results."""
        if rag_result.mapped_entity:
            # Update fields from mapped entity
            self.primary_id = rag_result.mapped_entity.primary_id
            self.refmet_id = rag_result.mapped_entity.refmet_id
            self.refmet_name = rag_result.mapped_entity.refmet_name
            self.chebi_id = rag_result.mapped_entity.chebi_id
            self.chebi_name = rag_result.mapped_entity.chebi_name
            self.hmdb_id = rag_result.mapped_entity.hmdb_id
            self.pubchem_id = rag_result.mapped_entity.pubchem_id
            self.confidence = rag_result.confidence
            self.source = "rag"
        else:
            # Handle case where no match is found
            self.confidence = 0.0
            self.source = "rag_no_match"
            if rag_result.metadata:
                self.metadata = rag_result.metadata


class CompoundMapper(APIMapper[CompoundDocument]):
    """Maps compound names to standard identifiers using multiple API clients."""
    
    def __init__(self, api_clients: List[BaseAPIClient]):
        """Initialize mapper with API clients."""
        super().__init__(api_clients[0])  # Use first client as primary
        self.api_clients = api_clients
        
    async def map_entity(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None
    ) -> MappingResult:
        """Map compound name using multiple API clients.
        
        Args:
            text: Compound name to map
            context: Optional context
            
        Returns:
            Mapping result
        """
        best_result = None
        best_confidence = 0.0
        
        # Try each API client
        for client in self.api_clients:
            try:
                response = await client.search(text)
                if response.success and response.data:
                    result = await self._process_response(text, response, context)
                    if result.confidence > best_confidence:
                        best_result = result
                        best_confidence = result.confidence
            except Exception as e:
                logger.error(f"Error with {client.__class__.__name__}: {e}")
                continue
                
        if best_result:
            return best_result
            
        # No matches found
        return MappingResult(
            input_text=text,
            mapped_entity=None,
            confidence=0.0,
            source="api",
            metadata={"error": "No matches found"}
        )
    
    async def _process_response(
        self,
        input_text: str,
        response: APIResponse,
        context: Optional[Dict[str, Any]]
    ) -> MappingResult:
        """Process API response into mapping result."""
        if not response.success or not response.data:
            return MappingResult(
                input_text=input_text,
                mapped_entity=None,
                confidence=0.0,
                source="api",
                metadata={"error": response.error or "No data"}
            )
            
        # Create compound document from response
        compound = CompoundDocument(
            name=input_text,
            compound_class=CompoundClass.SIMPLE,  # Default to simple
            metadata=response.data
        )
        
        # Extract IDs and names based on source
        if isinstance(response.data, dict):
            compound.refmet_id = response.data.get("refmet_id")
            compound.refmet_name = response.data.get("refmet_name")
            compound.chebi_id = response.data.get("chebi_id")
            compound.chebi_name = response.data.get("chebi_name")
            compound.hmdb_id = response.data.get("hmdb_id")
            compound.pubchem_id = response.data.get("pubchem_id")
            
        # Calculate confidence based on number of matched IDs
        matched_ids = sum(1 for x in [
            compound.refmet_id,
            compound.chebi_id,
            compound.hmdb_id,
            compound.pubchem_id
        ] if x is not None)
        compound.confidence = matched_ids / 4.0  # Simple confidence score
        
        return MappingResult(
            input_text=input_text,
            mapped_entity=compound,
            confidence=compound.confidence,
            source="api",
            metadata=response.data
        )
