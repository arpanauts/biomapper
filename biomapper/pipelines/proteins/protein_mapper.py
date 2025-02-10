"""Protein mapping implementation."""

import logging
from dataclasses import dataclass
from typing import List, Optional, Dict, Any

from ...core.base_mapper import APIMapper, MappingResult
from ...core.base_client import BaseAPIClient, APIResponse
from ...schemas.domain_schema import DomainDocument

logger = logging.getLogger(__name__)


@dataclass
class ProteinDocument(DomainDocument):
    """Standard protein document."""
    name: str
    uniprot_id: Optional[str] = None
    uniprot_name: Optional[str] = None
    gene_name: Optional[str] = None
    organism: Optional[str] = None
    sequence: Optional[str] = None
    confidence: float = 0.0
    source: str = "api"
    metadata: Dict[str, Any] = None

    def update_from_rag(self, rag_result: MappingResult) -> None:
        """Update document with RAG mapping results."""
        if rag_result.mapped_entity:
            self.uniprot_id = rag_result.mapped_entity.uniprot_id
            self.uniprot_name = rag_result.mapped_entity.uniprot_name
            self.gene_name = rag_result.mapped_entity.gene_name
            self.organism = rag_result.mapped_entity.organism
            self.sequence = rag_result.mapped_entity.sequence
            self.confidence = rag_result.confidence
            self.source = "rag"
            if rag_result.metadata:
                self.metadata = rag_result.metadata


class ProteinMapper(APIMapper[ProteinDocument]):
    """Maps protein names to standard identifiers using UniProt API."""
    
    def __init__(self, api_client: BaseAPIClient):
        """Initialize mapper with UniProt client."""
        super().__init__(api_client)
        
    async def map_entity(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None
    ) -> MappingResult:
        """Map protein name using UniProt.
        
        Args:
            text: Protein name or identifier to map
            context: Optional context (e.g., organism)
            
        Returns:
            Mapping result
        """
        try:
            # Add organism to query if provided
            query = text
            if context and "organism" in context:
                query = f"{text} AND organism:{context['organism']}"
                
            response = await self.client.search(query)
            return await self._process_response(text, response, context)
            
        except Exception as e:
            logger.error(f"Error mapping protein {text}: {e}")
            return MappingResult(
                input_text=text,
                mapped_entity=None,
                confidence=0.0,
                source="api",
                metadata={"error": str(e)}
            )
    
    async def _process_response(
        self,
        input_text: str,
        response: APIResponse,
        context: Optional[Dict[str, Any]]
    ) -> MappingResult:
        """Process UniProt API response into mapping result."""
        if not response.success or not response.data:
            return MappingResult(
                input_text=input_text,
                mapped_entity=None,
                confidence=0.0,
                source="api",
                metadata={"error": response.error or "No data"}
            )
            
        # Create protein document from response
        data = response.data
        protein = ProteinDocument(
            name=input_text,
            uniprot_id=data.get("id"),
            uniprot_name=data.get("name"),
            gene_name=data.get("gene_name"),
            organism=data.get("organism"),
            sequence=data.get("sequence"),
            metadata=data
        )
        
        # Calculate confidence based on match quality
        # Better confidence if we have ID and sequence
        protein.confidence = 0.5  # Base confidence for name match
        if protein.uniprot_id:
            protein.confidence += 0.3
        if protein.sequence:
            protein.confidence += 0.2
            
        return MappingResult(
            input_text=input_text,
            mapped_entity=protein,
            confidence=protein.confidence,
            source="api",
            metadata=response.data
        )
