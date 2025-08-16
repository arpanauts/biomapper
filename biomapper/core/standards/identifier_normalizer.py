"""Biological identifier normalization framework.

This module provides a comprehensive system for normalizing biological identifiers
to handle format variations that can significantly impact match rates.
"""

import re
from abc import ABC, abstractmethod
from typing import Tuple, List, Optional, Set
from dataclasses import dataclass


@dataclass
class NormalizationResult:
    """Result of identifier normalization."""
    base_id: str  # Base identifier without isoforms/versions
    full_id: str  # Full normalized identifier
    confidence: float = 1.0  # Confidence score (0-1)
    source_format: Optional[str] = None  # Detected source format


class IdentifierNormalizer(ABC):
    """Abstract base class for all identifier normalizers."""
    
    @abstractmethod
    def normalize(self, raw_id: str) -> Optional[NormalizationResult]:
        """Normalize a single identifier.
        
        Args:
            raw_id: Raw identifier string
            
        Returns:
            NormalizationResult or None if invalid
        """
        pass
    
    @abstractmethod
    def extract_from_text(self, text: str) -> List[str]:
        """Extract all identifiers from free text.
        
        Args:
            text: Text to search for identifiers
            
        Returns:
            List of extracted identifiers
        """
        pass
    
    @abstractmethod
    def is_valid(self, identifier: str) -> bool:
        """Check if an identifier is valid for this type."""
        pass
    
    def batch_normalize(self, identifiers: List[str]) -> List[Optional[NormalizationResult]]:
        """Normalize multiple identifiers efficiently.
        
        Args:
            identifiers: List of raw identifiers
            
        Returns:
            List of normalization results (None for invalid)
        """
        return [self.normalize(id_) for id_ in identifiers]


class UniProtNormalizer(IdentifierNormalizer):
    """Normalizer for UniProt identifiers.
    
    Handles:
    - Standard format: P12345, Q6EMK4
    - With isoform: P12345-1, Q6EMK4-2
    - Prefixed: UniProtKB:P12345, PR:Q6EMK4, uniprot:P12345
    - With version: P12345.2
    - Combined: UniProtKB:P12345-1.2
    """
    
    # Core UniProt pattern (without prefixes/suffixes) - simplified to avoid nested groups
    CORE_PATTERN = r'(?:[OPQ][0-9][A-Z0-9]{3}[0-9]|[A-NR-Z][0-9](?:[A-Z][A-Z0-9]{2}[0-9]){1,2})'
    
    # Full pattern with all variations - simplified grouping
    FULL_PATTERN = re.compile(
        r'^(?:(?:UniProtKB|uniprot|UniProt|PR|sp|tr)[:\s]+)?'  # Optional prefix
        r'(' + CORE_PATTERN + r')'  # Core identifier (group 1)
        r'(?:-(\d+))?'  # Optional isoform (group 2)
        r'(?:\.(\d+))?'  # Optional version (group 3)
        r'$',
        re.IGNORECASE
    )
    
    # Pattern for extraction from text - capture full identifier with isoforms
    EXTRACT_PATTERN = re.compile(
        r'(?:(?:UniProtKB|uniprot|UniProt|PR|sp|tr)[:\s]+)?'
        r'(' + CORE_PATTERN + r')'
        r'(-\d+)?'  # Capture isoform separately
        r'(?:\.\d+)?',
        re.IGNORECASE
    )
    
    def normalize(self, raw_id: str) -> Optional[NormalizationResult]:
        """Normalize a UniProt identifier."""
        if not raw_id:
            return None
            
        raw_id = raw_id.strip()
        match = self.FULL_PATTERN.match(raw_id)
        
        if not match:
            return None
            
        base_id = match.group(1).upper()  # The core identifier
        isoform = match.group(2)          # Optional isoform number
        version = match.group(3)          # Optional version number
        
        full_id = base_id
        
        # Add isoform if present
        if isoform:
            full_id = f"{base_id}-{isoform}"
            
        # Detect source format
        source_format = "standard"
        if ":" in raw_id or raw_id.lower().startswith(("uniprot", "pr", "sp", "tr")):
            source_format = "prefixed"
        elif "-" in raw_id and isoform:
            source_format = "with_isoform"
        elif "." in raw_id and version:
            source_format = "with_version"
            
        return NormalizationResult(
            base_id=base_id,
            full_id=full_id,
            confidence=1.0,
            source_format=source_format
        )
    
    def extract_from_text(self, text: str) -> List[str]:
        """Extract UniProt identifiers from text."""
        matches = self.EXTRACT_PATTERN.findall(text)
        # Return unique matches, reconstructing full identifier with isoforms
        seen = set()
        result = []
        for match in matches:
            if isinstance(match, tuple):
                core_id = match[0]
                isoform = match[1] if len(match) > 1 and match[1] else ""
                full_id = core_id.upper() + (isoform if isoform else "")
            else:
                full_id = match.upper()
            
            if full_id and full_id not in seen:
                seen.add(full_id)
                result.append(full_id)
        return result
    
    def is_valid(self, identifier: str) -> bool:
        """Check if identifier is a valid UniProt ID."""
        return self.normalize(identifier) is not None
    
    def strip_isoform(self, uniprot_id: str) -> str:
        """Remove isoform suffix from UniProt ID."""
        result = self.normalize(uniprot_id)
        return result.base_id if result else uniprot_id
    
    def strip_version(self, uniprot_id: str) -> str:
        """Remove version number from UniProt ID."""
        # Version is already stripped in base_id
        result = self.normalize(uniprot_id)
        return result.base_id if result else uniprot_id


class HMDBNormalizer(IdentifierNormalizer):
    """Normalizer for HMDB (Human Metabolome Database) identifiers.
    
    Handles:
    - Standard: HMDB0001234 (7 digits with leading zeros)
    - Wrong case: hmdb0001234
    - Wrong padding: HMDB00001234, HMDB001234
    - Old format: HMDB00001 (5 digits)
    """
    
    # Pattern to match HMDB identifiers with flexible digit count
    PATTERN = re.compile(r'^(?:HMDB)?(\d+)$', re.IGNORECASE)
    
    def normalize(self, raw_id: str) -> Optional[NormalizationResult]:
        """Normalize an HMDB identifier to HMDB0001234 format."""
        if not raw_id:
            return None
            
        raw_id = raw_id.strip()
        match = self.PATTERN.match(raw_id)
        
        if not match:
            return None
            
        digits = match.group(1)
        original_case = raw_id
        
        # Determine target format based on digit count
        if len(digits) == 4:
            # 4 digits - likely meant to be 7-digit format
            normalized = f"HMDB{digits.zfill(7)}"
            confidence = 1.0
        elif len(digits) == 5:
            # Old format: keep as 5 digits  
            normalized = f"HMDB{digits}"
            confidence = 0.9
        elif len(digits) == 6:
            # 6 digits - normalize to 7
            normalized = f"HMDB{digits.zfill(7)}"
            confidence = 1.0
        elif len(digits) == 7:
            # Standard new format
            normalized = f"HMDB{digits}"
            confidence = 1.0
        else:
            # 8+ digits - take last 7, or very short numbers pad to 7
            if len(digits) > 7:
                normalized = f"HMDB{digits[-7:]}"
            else:
                normalized = f"HMDB{digits.zfill(7)}"
            confidence = 1.0
            
        # Detect source format
        source_format = "standard"
        
        # Check case issues first
        if original_case.lower().startswith("hmdb") and not original_case.startswith("HMDB"):
            source_format = "wrong_case"
        # Check if it's digits only (no HMDB prefix)
        elif not original_case.upper().startswith("HMDB"):
            source_format = "digits_only" 
        # Check padding issues (for any case where normalization changed the format)
        elif original_case.startswith("HMDB") and original_case != normalized and len(digits) != 5:
            source_format = "wrong_padding"
                
        return NormalizationResult(
            base_id=normalized,
            full_id=normalized,
            confidence=confidence,
            source_format=source_format
        )
    
    def extract_from_text(self, text: str) -> List[str]:
        """Extract HMDB identifiers from text."""
        pattern = re.compile(r'HMDB\d{4,8}', re.IGNORECASE)
        matches = pattern.findall(text)
        # Normalize and deduplicate
        seen = set()
        result = []
        for match in matches:
            normalized = self.normalize(match)
            if normalized and normalized.full_id not in seen:
                seen.add(normalized.full_id)
                result.append(normalized.full_id)
        return result
    
    def is_valid(self, identifier: str) -> bool:
        """Check if identifier is a valid HMDB ID."""
        return self.normalize(identifier) is not None


class EnsemblNormalizer(IdentifierNormalizer):
    """Normalizer for Ensembl identifiers.
    
    Handles:
    - Gene: ENSG00000168140 (ENSG + 11 digits)
    - Transcript: ENST00000306864 (ENST + 11 digits)  
    - Protein: ENSP00000306864 (ENSP + 11 digits)
    - With version: ENSG00000168140.5
    - Prefixed: ENSEMBL:ENSG00000168140
    """
    
    PATTERNS = {
        'gene': re.compile(r'^(?:ENSEMBL[:\s]+)?'
                          r'(ENSG\d{11})'
                          r'(?:\.(\d+))?$', re.IGNORECASE),
        'transcript': re.compile(r'^(?:ENSEMBL[:\s]+)?'
                                r'(ENST\d{11})'
                                r'(?:\.(\d+))?$', re.IGNORECASE),
        'protein': re.compile(r'^(?:ENSEMBL[:\s]+)?'
                             r'(ENSP\d{11})'
                             r'(?:\.(\d+))?$', re.IGNORECASE)
    }
    
    # Combined pattern for extraction
    EXTRACT_PATTERN = re.compile(
        r'(?:ENSEMBL[:\s]+)?(ENS[GTP]\d{11})(?:\.\d+)?',
        re.IGNORECASE
    )
    
    def normalize(self, raw_id: str) -> Optional[NormalizationResult]:
        """Normalize an Ensembl identifier."""
        if not raw_id:
            return None
            
        raw_id = raw_id.strip()
        
        for id_type, pattern in self.PATTERNS.items():
            match = pattern.match(raw_id)
            if match:
                base_id = match.group(1).upper()
                full_id = base_id
                if match.group(2):  # Version number
                    full_id = f"{base_id}.{match.group(2)}"
                    
                source_format = "prefixed" if ":" in raw_id else "standard"
                
                return NormalizationResult(
                    base_id=base_id,
                    full_id=full_id,
                    confidence=1.0,
                    source_format=source_format
                )
                
        return None
    
    def extract_from_text(self, text: str) -> List[str]:
        """Extract Ensembl identifiers from text."""
        matches = self.EXTRACT_PATTERN.findall(text)
        # Deduplicate and uppercase
        return list(set(m.upper() for m in matches))
    
    def is_valid(self, identifier: str) -> bool:
        """Check if identifier is a valid Ensembl ID."""
        return self.normalize(identifier) is not None
    
    def get_type(self, identifier: str) -> Optional[str]:
        """Get the type of Ensembl identifier (gene, transcript, or protein)."""
        result = self.normalize(identifier)
        if result:
            if result.base_id.startswith('ENSG'):
                return 'gene'
            elif result.base_id.startswith('ENST'):
                return 'transcript'
            elif result.base_id.startswith('ENSP'):
                return 'protein'
        return None


class NCBIGeneNormalizer(IdentifierNormalizer):
    """Normalizer for NCBI Gene identifiers.
    
    Handles:
    - Prefixed: NCBIGene:12345, NCBI_Gene:12345
    - EntrezGene: EntrezGene:12345
    - GeneID: GeneID:12345
    - Plain number: 12345 (when context suggests it's an NCBI Gene ID)
    """
    
    PATTERN = re.compile(
        r'^(?:(?:NCBIGene|NCBI_Gene|EntrezGene|GeneID|Entrez)[:\s]+)?'
        r'(\d+)$',
        re.IGNORECASE
    )
    
    EXTRACT_PATTERN = re.compile(
        r'(?:NCBIGene|NCBI_Gene|EntrezGene|GeneID|Entrez)[:\s]+(\d+)',
        re.IGNORECASE
    )
    
    def normalize(self, raw_id: str) -> Optional[NormalizationResult]:
        """Normalize an NCBI Gene identifier."""
        if not raw_id:
            return None
            
        raw_id = raw_id.strip()
        match = self.PATTERN.match(raw_id)
        
        if not match:
            return None
            
        gene_id = match.group(1)
        
        # Confidence is lower for plain numbers
        confidence = 0.5 if raw_id == gene_id else 1.0
        
        source_format = "plain_number" if raw_id == gene_id else "prefixed"
        
        return NormalizationResult(
            base_id=gene_id,
            full_id=f"NCBIGene:{gene_id}",
            confidence=confidence,
            source_format=source_format
        )
    
    def extract_from_text(self, text: str) -> List[str]:
        """Extract NCBI Gene identifiers from text."""
        matches = self.EXTRACT_PATTERN.findall(text)
        # Return unique gene IDs
        return list(set(matches))
    
    def is_valid(self, identifier: str) -> bool:
        """Check if identifier is a valid NCBI Gene ID."""
        return self.normalize(identifier) is not None


class CHEBINormalizer(IdentifierNormalizer):
    """Normalizer for ChEBI (Chemical Entities of Biological Interest) identifiers.
    
    Handles:
    - Standard: CHEBI:12345
    - Without prefix: 12345
    - With CHEBI prefix variations: ChEBI:12345, chebi:12345
    """
    
    PATTERN = re.compile(r'^(?:CHEBI[:\s]+)?(\d+)$', re.IGNORECASE)
    EXTRACT_PATTERN = re.compile(r'CHEBI[:\s]+(\d+)', re.IGNORECASE)
    
    def normalize(self, raw_id: str) -> Optional[NormalizationResult]:
        """Normalize a ChEBI identifier."""
        if not raw_id:
            return None
            
        raw_id = raw_id.strip()
        match = self.PATTERN.match(raw_id)
        
        if not match:
            return None
            
        chebi_id = match.group(1)
        
        source_format = "plain_number" if raw_id == chebi_id else "prefixed"
        confidence = 0.7 if source_format == "plain_number" else 1.0
        
        return NormalizationResult(
            base_id=chebi_id,
            full_id=f"CHEBI:{chebi_id}",
            confidence=confidence,
            source_format=source_format
        )
    
    def extract_from_text(self, text: str) -> List[str]:
        """Extract ChEBI identifiers from text."""
        matches = self.EXTRACT_PATTERN.findall(text)
        return list(set(matches))
    
    def is_valid(self, identifier: str) -> bool:
        """Check if identifier is a valid ChEBI ID."""
        return self.normalize(identifier) is not None


class KEGGNormalizer(IdentifierNormalizer):
    """Normalizer for KEGG identifiers.
    
    Handles multiple KEGG databases:
    - Compound: C00001
    - Drug: D00001
    - Glycan: G00001
    - Reaction: R00001
    - Pathway: map00010, hsa00010
    - Gene: K00001
    - With prefix: KEGG:C00001
    """
    
    PATTERN = re.compile(
        r'^(?:KEGG[:\s]+)?'
        r'([CDGRK]\d{5}|(?:map|[a-z]{3})\d{5})$',
        re.IGNORECASE
    )
    
    EXTRACT_PATTERN = re.compile(
        r'(?:KEGG[:\s]+)?([CDGRK]\d{5}|(?:map|[a-z]{3})\d{5})',
        re.IGNORECASE
    )
    
    def normalize(self, raw_id: str) -> Optional[NormalizationResult]:
        """Normalize a KEGG identifier."""
        if not raw_id:
            return None
            
        raw_id = raw_id.strip()
        match = self.PATTERN.match(raw_id)
        
        if not match:
            return None
            
        kegg_id = match.group(1).upper() if match.group(1)[0].isalpha() and match.group(1)[0].isupper() else match.group(1).lower()
        
        source_format = "prefixed" if ":" in raw_id else "standard"
        
        return NormalizationResult(
            base_id=kegg_id,
            full_id=f"KEGG:{kegg_id}",
            confidence=1.0,
            source_format=source_format
        )
    
    def extract_from_text(self, text: str) -> List[str]:
        """Extract KEGG identifiers from text."""
        matches = self.EXTRACT_PATTERN.findall(text)
        # Normalize case
        result = []
        for m in matches:
            if m[0].isalpha() and m[0].isupper():
                result.append(m.upper())
            else:
                result.append(m.lower())
        return list(set(result))
    
    def is_valid(self, identifier: str) -> bool:
        """Check if identifier is a valid KEGG ID."""
        return self.normalize(identifier) is not None
    
    def get_database(self, identifier: str) -> Optional[str]:
        """Get the KEGG database type for an identifier."""
        result = self.normalize(identifier)
        if result:
            first_char = result.base_id[0].upper()
            if first_char == 'C':
                return 'compound'
            elif first_char == 'D':
                return 'drug'
            elif first_char == 'G':
                return 'glycan'
            elif first_char == 'R':
                return 'reaction'
            elif first_char == 'K':
                return 'orthology'
            elif result.base_id.startswith(('map', 'hsa', 'eco', 'mmu')):
                return 'pathway'
        return None