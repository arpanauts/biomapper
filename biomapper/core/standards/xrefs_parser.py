"""Parser for complex xrefs (cross-references) fields in biological databases.

This module handles the parsing of complex cross-reference fields that contain
multiple identifier types with various delimiters and formats.
"""

import re
import logging
from typing import Dict, List, Optional, Set, Tuple, Any
from collections import defaultdict

from .identifier_registry import IdentifierRegistry, IdentifierMatch, get_registry

logger = logging.getLogger(__name__)


class XrefsParser:
    """Parse complex xrefs fields with multiple identifier types.
    
    Handles various formats found in biological databases:
    - Pipe-separated: "UniProtKB:P12345||RefSeq:NP_001234"
    - Semicolon-separated: "UniProtKB:P12345;RefSeq:NP_001234"
    - Space-separated: "UniProtKB:P12345 RefSeq:NP_001234"
    - Mixed delimiters and malformed entries
    """
    
    # Common database prefixes and their normalized forms
    PREFIX_MAPPING = {
        'UniProtKB': 'uniprot',
        'uniprot': 'uniprot',
        'UniProt': 'uniprot',
        'PR': 'uniprot',  # Protein Resource also uses UniProt IDs
        'sp': 'uniprot',  # SwissProt
        'tr': 'uniprot',  # TrEMBL
        'ENSEMBL': 'ensembl',
        'Ensembl': 'ensembl',
        'RefSeq': 'refseq',
        'NCBIGene': 'ncbi_gene',
        'NCBI_Gene': 'ncbi_gene',
        'EntrezGene': 'ncbi_gene',
        'GeneID': 'ncbi_gene',
        'HMDB': 'hmdb',
        'ChEBI': 'chebi',
        'CHEBI': 'chebi',
        'KEGG': 'kegg',
        'PubChem': 'pubchem',
        'InChIKey': 'inchikey',
        'MESH': 'mesh',
        'GO': 'go',
        'HGNC': 'hgnc',
        'MGI': 'mgi',
        'RGD': 'rgd'
    }
    
    # Regex patterns for common delimiters
    DELIMITER_PATTERNS = [
        r'\|\|',  # Double pipe
        r';',     # Semicolon
        r'\|',    # Single pipe
        r',',     # Comma
        r'\s+'    # Whitespace
    ]
    
    def __init__(self, registry: Optional[IdentifierRegistry] = None):
        """Initialize the parser.
        
        Args:
            registry: IdentifierRegistry instance (uses global if not provided)
        """
        self.registry = registry or get_registry()
        self._delimiter_regex = re.compile('|'.join(self.DELIMITER_PATTERNS))
        
    def parse(self, xrefs: str, normalize: bool = True) -> Dict[str, List[str]]:
        """Parse xrefs field into dictionary of identifier types and values.
        
        Args:
            xrefs: Cross-references string
            normalize: Whether to normalize extracted identifiers
            
        Returns:
            Dictionary mapping identifier types to lists of identifiers
        """
        if not xrefs or not isinstance(xrefs, str):
            return {}
            
        xrefs = xrefs.strip()
        if not xrefs:
            return {}
            
        result = defaultdict(list)
        seen = defaultdict(set)  # Track duplicates per type
        
        # Split by various delimiters
        parts = self._delimiter_regex.split(xrefs)
        
        for part in parts:
            part = part.strip()
            if not part:
                continue
                
            # Try to parse as prefix:identifier format
            if ':' in part:
                try:
                    prefix, identifier = part.split(':', 1)
                    prefix = prefix.strip()
                    identifier = identifier.strip()
                    
                    if not prefix or not identifier:
                        continue
                        
                    # Map prefix to normalized type
                    id_type = self.PREFIX_MAPPING.get(prefix, prefix.lower())
                    
                    # Normalize the identifier if requested
                    if normalize and id_type in self.registry.get_supported_types():
                        match = self.registry.normalize_any(identifier, preferred_type=id_type)
                        if match:
                            identifier = match.full_id
                            id_type = match.identifier_type
                            
                    # Add if not duplicate
                    if identifier not in seen[id_type]:
                        result[id_type].append(identifier)
                        seen[id_type].add(identifier)
                        
                except ValueError:
                    # Not a valid prefix:identifier format
                    logger.debug(f"Could not parse xref part: {part}")
                    
            else:
                # Try to auto-detect identifier type
                if normalize:
                    match = self.registry.normalize_any(part)
                    if match:
                        id_type = match.identifier_type
                        identifier = match.full_id
                        if identifier not in seen[id_type]:
                            result[id_type].append(identifier)
                            seen[id_type].add(identifier)
                            
        return dict(result)
        
    def extract_uniprot(self, xrefs: str) -> List[str]:
        """Extract all UniProt identifiers from xrefs.
        
        Args:
            xrefs: Cross-references string
            
        Returns:
            List of unique UniProt identifiers
        """
        parsed = self.parse(xrefs, normalize=True)
        
        # Combine all sources that contain UniProt IDs
        uniprot_ids = []
        for source in ['uniprot', 'UniProtKB', 'PR', 'sp', 'tr']:
            if source in parsed:
                uniprot_ids.extend(parsed[source])
                
        # Deduplicate while preserving order
        seen = set()
        result = []
        for uid in uniprot_ids:
            # Normalize to remove prefixes if present
            match = self.registry.normalize_any(uid, preferred_type='uniprot')
            if match:
                base_id = match.base_id
                if base_id not in seen:
                    seen.add(base_id)
                    result.append(base_id)
                    
        return result
        
    def extract_all_identifiers(self, xrefs: str) -> Dict[str, List[str]]:
        """Extract all recognizable identifiers from xrefs.
        
        Args:
            xrefs: Cross-references string
            
        Returns:
            Dictionary mapping identifier types to lists of identifiers
        """
        return self.parse(xrefs, normalize=True)
        
    def get_primary_identifier(self, xrefs: str, preferred_types: Optional[List[str]] = None) -> Optional[str]:
        """Get the most reliable/primary identifier from xrefs.
        
        Args:
            xrefs: Cross-references string
            preferred_types: Ordered list of preferred identifier types
            
        Returns:
            The primary identifier or None if no valid identifiers found
        """
        if not preferred_types:
            # Default priority order
            preferred_types = ['uniprot', 'ensembl', 'ncbi_gene', 'refseq', 'hmdb', 'chebi', 'kegg']
            
        parsed = self.parse(xrefs, normalize=True)
        
        # Return first identifier from preferred types
        for id_type in preferred_types:
            if id_type in parsed and parsed[id_type]:
                return parsed[id_type][0]
                
        # If no preferred type found, return first available
        for identifiers in parsed.values():
            if identifiers:
                return identifiers[0]
                
        return None
        
    def extract_by_type(self, xrefs: str, identifier_type: str) -> List[str]:
        """Extract all identifiers of a specific type.
        
        Args:
            xrefs: Cross-references string
            identifier_type: Type of identifier to extract
            
        Returns:
            List of identifiers of the specified type
        """
        parsed = self.parse(xrefs, normalize=True)
        return parsed.get(identifier_type, [])
        
    def merge_xrefs(self, xrefs_list: List[str]) -> str:
        """Merge multiple xrefs strings into a single deduplicated string.
        
        Args:
            xrefs_list: List of xrefs strings to merge
            
        Returns:
            Merged xrefs string with double-pipe delimiter
        """
        all_identifiers = defaultdict(set)
        
        for xrefs in xrefs_list:
            if not xrefs:
                continue
            parsed = self.parse(xrefs, normalize=True)
            for id_type, identifiers in parsed.items():
                all_identifiers[id_type].update(identifiers)
                
        # Build merged string
        parts = []
        for id_type, identifiers in sorted(all_identifiers.items()):
            # Use the original prefix format for output
            prefix = id_type.upper() if id_type in ['hmdb', 'kegg', 'chebi'] else id_type
            for identifier in sorted(identifiers):
                # Don't add prefix if identifier already has it
                if ':' in identifier:
                    parts.append(identifier)
                else:
                    parts.append(f"{prefix}:{identifier}")
                    
        return '||'.join(parts)
        
    def validate_xrefs(self, xrefs: str) -> Dict[str, Any]:
        """Validate xrefs and return statistics.
        
        Args:
            xrefs: Cross-references string
            
        Returns:
            Dictionary with validation results and statistics
        """
        result = {
            'valid': False,
            'total_identifiers': 0,
            'valid_identifiers': 0,
            'invalid_parts': [],
            'duplicates': [],
            'by_type': {}
        }
        
        if not xrefs:
            return result
            
        parts = self._delimiter_regex.split(xrefs)
        parsed = self.parse(xrefs, normalize=True)
        
        # Count valid identifiers
        for id_type, identifiers in parsed.items():
            result['valid_identifiers'] += len(identifiers)
            result['by_type'][id_type] = len(identifiers)
            
        # Find invalid parts
        for part in parts:
            part = part.strip()
            if not part:
                continue
            result['total_identifiers'] += 1
            
            # Check if this part was successfully parsed
            found = False
            if ':' in part:
                try:
                    prefix, identifier = part.split(':', 1)
                    # Check if this identifier appears in parsed results
                    for id_list in parsed.values():
                        if any(identifier in id_str for id_str in id_list):
                            found = True
                            break
                except ValueError:
                    pass
                    
            if not found:
                # Try auto-detection
                match = self.registry.normalize_any(part)
                if not match:
                    result['invalid_parts'].append(part)
                    
        # Check for duplicates within types
        for id_type, identifiers in parsed.items():
            if len(identifiers) != len(set(identifiers)):
                result['duplicates'].append(id_type)
                
        result['valid'] = len(result['invalid_parts']) == 0
        return result
        
    def standardize_xrefs(self, xrefs: str) -> str:
        """Standardize an xrefs string to a consistent format.
        
        Args:
            xrefs: Cross-references string
            
        Returns:
            Standardized xrefs string with consistent formatting
        """
        parsed = self.parse(xrefs, normalize=True)
        
        if not parsed:
            return ""
            
        # Build standardized string with consistent prefixes and delimiter
        parts = []
        
        # Use a consistent order for output
        type_order = ['uniprot', 'ensembl', 'ncbi_gene', 'refseq', 'hmdb', 
                     'chebi', 'kegg', 'pubchem', 'inchikey']
        
        # Add known types first in order
        for id_type in type_order:
            if id_type in parsed:
                prefix = self._get_standard_prefix(id_type)
                for identifier in sorted(parsed[id_type]):
                    parts.append(f"{prefix}:{identifier}")
                    
        # Add any remaining types
        for id_type, identifiers in sorted(parsed.items()):
            if id_type not in type_order:
                prefix = self._get_standard_prefix(id_type)
                for identifier in sorted(identifiers):
                    parts.append(f"{prefix}:{identifier}")
                    
        return '||'.join(parts)
        
    def _get_standard_prefix(self, id_type: str) -> str:
        """Get the standard prefix for an identifier type.
        
        Args:
            id_type: Normalized identifier type
            
        Returns:
            Standard prefix to use in output
        """
        prefix_map = {
            'uniprot': 'UniProtKB',
            'ensembl': 'ENSEMBL',
            'ncbi_gene': 'NCBIGene',
            'refseq': 'RefSeq',
            'hmdb': 'HMDB',
            'chebi': 'ChEBI',
            'kegg': 'KEGG',
            'pubchem': 'PubChem',
            'inchikey': 'InChIKey',
            'hgnc': 'HGNC',
            'go': 'GO',
            'mesh': 'MESH'
        }
        return prefix_map.get(id_type, id_type.upper())