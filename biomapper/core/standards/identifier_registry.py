"""Central registry for biological identifier types and their normalizers.

This module provides a unified interface for detecting and normalizing
any biological identifier type.
"""

import re
from typing import Dict, List, Tuple, Optional, Any, Set
from dataclasses import dataclass
import logging

from .identifier_normalizer import (
    IdentifierNormalizer,
    NormalizationResult,
    UniProtNormalizer,
    HMDBNormalizer,
    EnsemblNormalizer,
    NCBIGeneNormalizer,
    CHEBINormalizer,
    KEGGNormalizer
)

logger = logging.getLogger(__name__)


@dataclass
class IdentifierMatch:
    """Result of identifier detection and normalization."""
    identifier_type: str
    base_id: str
    full_id: str
    confidence: float
    source_format: Optional[str] = None
    original: Optional[str] = None


class IdentifierRegistry:
    """Central registry for all identifier types and their normalizers.
    
    This class provides:
    - Automatic detection of identifier types
    - Normalization using the appropriate normalizer
    - Extraction of all identifiers from complex text
    - Handling of ambiguous cases with confidence scores
    """
    
    def __init__(self):
        """Initialize the registry with default normalizers."""
        self.normalizers: Dict[str, IdentifierNormalizer] = {}
        self._initialize_default_normalizers()
        
        # Priority order for ambiguous cases (e.g., plain numbers)
        self.type_priority = [
            'uniprot',      # Most specific patterns
            'ensembl',
            'hmdb',
            'chebi',
            'kegg',
            'ncbi_gene'     # Most generic (plain numbers)
        ]
        
    def _initialize_default_normalizers(self):
        """Register all default normalizers."""
        self.register('uniprot', UniProtNormalizer())
        self.register('hmdb', HMDBNormalizer())
        self.register('ensembl', EnsemblNormalizer())
        self.register('ncbi_gene', NCBIGeneNormalizer())
        self.register('chebi', CHEBINormalizer())
        self.register('kegg', KEGGNormalizer())
        
    def register(self, identifier_type: str, normalizer: IdentifierNormalizer):
        """Register a new normalizer.
        
        Args:
            identifier_type: Type name for the identifier (e.g., 'uniprot')
            normalizer: Normalizer instance
        """
        self.normalizers[identifier_type] = normalizer
        logger.debug(f"Registered normalizer for type: {identifier_type}")
        
    def detect_type(self, identifier: str) -> List[Tuple[str, float]]:
        """Auto-detect identifier type with confidence scores.
        
        Args:
            identifier: Identifier string to analyze
            
        Returns:
            List of (type, confidence) tuples, sorted by confidence
        """
        if not identifier:
            return []
            
        results = []
        
        for id_type in self.type_priority:
            if id_type not in self.normalizers:
                continue
                
            normalizer = self.normalizers[id_type]
            result = normalizer.normalize(identifier)
            
            if result:
                results.append((id_type, result.confidence))
                
        # Sort by confidence (highest first)
        results.sort(key=lambda x: x[1], reverse=True)
        return results
        
    def normalize_any(self, identifier: str, preferred_type: Optional[str] = None) -> Optional[IdentifierMatch]:
        """Normalize any identifier, auto-detecting its type.
        
        Args:
            identifier: Identifier to normalize
            preferred_type: If specified, try this type first
            
        Returns:
            IdentifierMatch with normalized results, or None if invalid
        """
        if not identifier:
            return None
            
        identifier = identifier.strip()
        
        # Try preferred type first if specified
        if preferred_type and preferred_type in self.normalizers:
            result = self.normalizers[preferred_type].normalize(identifier)
            if result:
                return IdentifierMatch(
                    identifier_type=preferred_type,
                    base_id=result.base_id,
                    full_id=result.full_id,
                    confidence=result.confidence,
                    source_format=result.source_format,
                    original=identifier
                )
                
        # Auto-detect type
        detections = self.detect_type(identifier)
        
        if not detections:
            return None
            
        # Use the highest confidence match
        best_type, confidence = detections[0]
        result = self.normalizers[best_type].normalize(identifier)
        
        if result:
            return IdentifierMatch(
                identifier_type=best_type,
                base_id=result.base_id,
                full_id=result.full_id,
                confidence=result.confidence,
                source_format=result.source_format,
                original=identifier
            )
            
        return None
        
    def normalize_batch(self, identifiers: List[str]) -> List[Optional[IdentifierMatch]]:
        """Normalize multiple identifiers efficiently.
        
        Args:
            identifiers: List of identifiers to normalize
            
        Returns:
            List of IdentifierMatch results (None for invalid)
        """
        return [self.normalize_any(id_) for id_ in identifiers]
        
    def extract_all_identifiers(self, text: str) -> Dict[str, List[str]]:
        """Extract all recognizable identifiers from text.
        
        Args:
            text: Text to search for identifiers
            
        Returns:
            Dictionary mapping identifier types to lists of found identifiers
        """
        results = {}
        
        for id_type, normalizer in self.normalizers.items():
            found = normalizer.extract_from_text(text)
            if found:
                results[id_type] = found
                
        return results
        
    def extract_and_normalize(self, text: str) -> List[IdentifierMatch]:
        """Extract and normalize all identifiers from text.
        
        Args:
            text: Text to process
            
        Returns:
            List of normalized identifier matches
        """
        all_identifiers = self.extract_all_identifiers(text)
        matches = []
        
        for id_type, identifiers in all_identifiers.items():
            normalizer = self.normalizers[id_type]
            for identifier in identifiers:
                result = normalizer.normalize(identifier)
                if result:
                    matches.append(IdentifierMatch(
                        identifier_type=id_type,
                        base_id=result.base_id,
                        full_id=result.full_id,
                        confidence=result.confidence,
                        source_format=result.source_format,
                        original=identifier
                    ))
                    
        return matches
        
    def is_valid(self, identifier: str, identifier_type: Optional[str] = None) -> bool:
        """Check if an identifier is valid.
        
        Args:
            identifier: Identifier to check
            identifier_type: Specific type to check, or None for any type
            
        Returns:
            True if valid for the specified type (or any type)
        """
        if identifier_type:
            if identifier_type in self.normalizers:
                return self.normalizers[identifier_type].is_valid(identifier)
            return False
            
        # Check if valid for any type
        for normalizer in self.normalizers.values():
            if normalizer.is_valid(identifier):
                return True
        return False
        
    def get_supported_types(self) -> List[str]:
        """Get list of all supported identifier types.
        
        Returns:
            List of identifier type names
        """
        return list(self.normalizers.keys())
        
    def get_statistics(self, identifiers: List[str]) -> Dict[str, Any]:
        """Analyze a list of identifiers and return statistics.
        
        Args:
            identifiers: List of identifiers to analyze
            
        Returns:
            Dictionary with statistics about identifier types, formats, etc.
        """
        stats = {
            'total': len(identifiers),
            'valid': 0,
            'invalid': 0,
            'by_type': {},
            'by_format': {},
            'ambiguous': 0
        }
        
        for identifier in identifiers:
            detections = self.detect_type(identifier)
            
            if not detections:
                stats['invalid'] += 1
                continue
                
            stats['valid'] += 1
            
            # Count ambiguous cases (multiple types with same confidence)
            if len(detections) > 1 and detections[0][1] == detections[1][1]:
                stats['ambiguous'] += 1
                
            # Get the best match
            match = self.normalize_any(identifier)
            if match:
                # Count by type
                if match.identifier_type not in stats['by_type']:
                    stats['by_type'][match.identifier_type] = 0
                stats['by_type'][match.identifier_type] += 1
                
                # Count by format
                format_key = f"{match.identifier_type}_{match.source_format or 'standard'}"
                if format_key not in stats['by_format']:
                    stats['by_format'][format_key] = 0
                stats['by_format'][format_key] += 1
                
        return stats


# Singleton instance for convenience
_registry = None

def get_registry() -> IdentifierRegistry:
    """Get the global identifier registry instance.
    
    Returns:
        The singleton IdentifierRegistry instance
    """
    global _registry
    if _registry is None:
        _registry = IdentifierRegistry()
    return _registry


def normalize_identifier(identifier: str) -> Optional[IdentifierMatch]:
    """Convenience function to normalize any identifier.
    
    Args:
        identifier: Identifier to normalize
        
    Returns:
        IdentifierMatch or None if invalid
    """
    return get_registry().normalize_any(identifier)


def detect_identifier_type(identifier: str) -> Optional[str]:
    """Convenience function to detect identifier type.
    
    Args:
        identifier: Identifier to analyze
        
    Returns:
        Most likely identifier type or None
    """
    detections = get_registry().detect_type(identifier)
    return detections[0][0] if detections else None