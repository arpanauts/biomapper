# Parser Plugin Architecture

## Overview

The Parser Plugin Architecture provides a flexible, extensible system for parsing biological identifiers and metadata from various sources. Instead of hardcoded heuristics, parsers are registered as plugins with priority ordering and confidence scoring.

## Core Components

### ParserRegistry

```python
from typing import Protocol, Dict, List, Optional, Type
from pydantic import BaseModel, Field
from abc import ABC, abstractmethod

class ParseResult(BaseModel):
    """Result from a parser attempt."""
    success: bool
    parsed_value: Optional[Any]
    confidence: float = Field(ge=0.0, le=1.0)
    parser_name: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

class BiologicalParser(Protocol):
    """Protocol for all biological data parsers."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Unique name for this parser."""
        pass
    
    @property
    @abstractmethod
    def priority(self) -> int:
        """Priority order (lower numbers run first)."""
        pass
    
    @property
    @abstractmethod
    def supported_types(self) -> List[str]:
        """List of identifier types this parser supports."""
        pass
    
    @abstractmethod
    async def can_parse(self, value: str, identifier_type: Optional[str] = None) -> bool:
        """Quick check if this parser might handle the value."""
        pass
    
    @abstractmethod
    async def parse(self, value: str, identifier_type: Optional[str] = None) -> ParseResult:
        """Attempt to parse the value."""
        pass

class ParserRegistry:
    """Registry for biological data parsers."""
    
    def __init__(self):
        self._parsers: Dict[str, BiologicalParser] = {}
        self._type_parsers: Dict[str, List[BiologicalParser]] = {}
    
    def register(self, parser: BiologicalParser) -> None:
        """Register a parser plugin."""
        self._parsers[parser.name] = parser
        
        # Index by supported types
        for id_type in parser.supported_types:
            if id_type not in self._type_parsers:
                self._type_parsers[id_type] = []
            self._type_parsers[id_type].append(parser)
            # Sort by priority
            self._type_parsers[id_type].sort(key=lambda p: p.priority)
    
    async def parse(
        self, 
        value: str, 
        identifier_type: Optional[str] = None,
        confidence_threshold: float = 0.7
    ) -> List[ParseResult]:
        """Parse a value using appropriate parsers."""
        results = []
        
        # Get candidate parsers
        if identifier_type and identifier_type in self._type_parsers:
            candidates = self._type_parsers[identifier_type]
        else:
            # Try all parsers in priority order
            candidates = sorted(self._parsers.values(), key=lambda p: p.priority)
        
        # Try each parser
        for parser in candidates:
            if await parser.can_parse(value, identifier_type):
                result = await parser.parse(value, identifier_type)
                if result.success and result.confidence >= confidence_threshold:
                    results.append(result)
        
        return sorted(results, key=lambda r: r.confidence, reverse=True)
```

## Parser Implementations

### CAS Number Parser

```python
import re
from typing import List, Optional

class CASNumberParser(BiologicalParser):
    """Parser for CAS Registry Numbers with multi-value support."""
    
    name = "cas_number_parser"
    priority = 10
    supported_types = ["CAS", "cas_number", "cas"]
    
    # CAS format: XXXXXX-XX-X where X is digit and last is check digit
    CAS_PATTERN = re.compile(r'(\d{2,7}-\d{2}-\d)')
    
    async def can_parse(self, value: str, identifier_type: Optional[str] = None) -> bool:
        """Check if value looks like CAS number(s)."""
        if not value or not isinstance(value, str):
            return False
        
        # Quick check for CAS format
        return bool(self.CAS_PATTERN.search(value))
    
    async def parse(self, value: str, identifier_type: Optional[str] = None) -> ParseResult:
        """Parse single or multiple CAS numbers."""
        matches = self.CAS_PATTERN.findall(value)
        
        if not matches:
            return ParseResult(
                success=False,
                parsed_value=None,
                confidence=0.0,
                parser_name=self.name
            )
        
        # Validate each CAS number
        valid_cas = []
        for cas in matches:
            if self._validate_cas_checksum(cas):
                valid_cas.append(cas)
        
        if not valid_cas:
            return ParseResult(
                success=False,
                parsed_value=None,
                confidence=0.0,
                parser_name=self.name,
                metadata={"invalid_cas": matches}
            )
        
        # Calculate confidence based on validation
        confidence = len(valid_cas) / len(matches)
        
        return ParseResult(
            success=True,
            parsed_value=valid_cas if len(valid_cas) > 1 else valid_cas[0],
            confidence=confidence,
            parser_name=self.name,
            metadata={
                "is_multi_value": len(valid_cas) > 1,
                "separator": ";" if ";" in value else ",",
                "raw_matches": matches,
                "valid_count": len(valid_cas)
            }
        )
    
    def _validate_cas_checksum(self, cas: str) -> bool:
        """Validate CAS number checksum."""
        parts = cas.split('-')
        if len(parts) != 3:
            return False
        
        try:
            # Extract digits
            digits = parts[0] + parts[1]
            check_digit = int(parts[2])
            
            # Calculate checksum
            total = sum((i + 1) * int(d) for i, d in enumerate(reversed(digits)))
            calculated_check = total % 10
            
            return calculated_check == check_digit
        except (ValueError, IndexError):
            return False
```

### LOINC Code Parser

```python
class LOINCParser(BiologicalParser):
    """Parser for LOINC codes with hierarchical structure support."""
    
    name = "loinc_parser"
    priority = 20
    supported_types = ["LOINC", "loinc", "clinical_lab"]
    
    # LOINC patterns
    LOINC_PATTERN = re.compile(r'(\d{1,5}-\d)')
    LOINC_FULL_PATTERN = re.compile(r'(\d{1,5}-\d),([^,]+),([^,]+)')
    
    async def can_parse(self, value: str, identifier_type: Optional[str] = None) -> bool:
        """Check if value contains LOINC code."""
        if not value or not isinstance(value, str):
            return False
        
        return bool(self.LOINC_PATTERN.search(value))
    
    async def parse(self, value: str, identifier_type: Optional[str] = None) -> ParseResult:
        """Parse LOINC code and extract components."""
        # Try full pattern first (includes name and category)
        full_match = self.LOINC_FULL_PATTERN.match(value)
        if full_match:
            return ParseResult(
                success=True,
                parsed_value={
                    "code": full_match.group(1),
                    "name": full_match.group(2),
                    "category": full_match.group(3)
                },
                confidence=1.0,
                parser_name=self.name,
                metadata={
                    "format": "full",
                    "components": self._parse_loinc_name(full_match.group(2))
                }
            )
        
        # Try simple pattern
        simple_match = self.LOINC_PATTERN.search(value)
        if simple_match:
            return ParseResult(
                success=True,
                parsed_value={"code": simple_match.group(1)},
                confidence=0.8,
                parser_name=self.name,
                metadata={"format": "simple"}
            )
        
        return ParseResult(
            success=False,
            parsed_value=None,
            confidence=0.0,
            parser_name=self.name
        )
    
    def _parse_loinc_name(self, name: str) -> Dict[str, str]:
        """Parse LOINC long name components."""
        # LOINC names follow pattern: Component:Property:Time:System:Scale:Method
        parts = name.split(':')
        components = {}
        
        if len(parts) >= 1:
            components["component"] = parts[0]
        if len(parts) >= 2:
            components["property"] = parts[1]
        if len(parts) >= 3:
            components["time"] = parts[2]
        if len(parts) >= 4:
            components["system"] = parts[3]
        if len(parts) >= 5:
            components["scale"] = parts[4]
        if len(parts) >= 6:
            components["method"] = parts[5]
        
        return components
```

### Cross-Reference Parser

```python
class CrossReferenceParser(BiologicalParser):
    """Parser for cross-reference identifiers (e.g., UMLS:C1234567)."""
    
    name = "xref_parser"
    priority = 30
    supported_types = ["xref", "cross_reference", "synonyms"]
    
    # Pattern for database:identifier format
    XREF_PATTERN = re.compile(r'([A-Z][A-Z0-9_.]+):([A-Za-z0-9_.-]+)')
    
    async def can_parse(self, value: str, identifier_type: Optional[str] = None) -> bool:
        """Check if value contains cross-references."""
        if not value or not isinstance(value, str):
            return False
        
        return bool(self.XREF_PATTERN.search(value))
    
    async def parse(self, value: str, identifier_type: Optional[str] = None) -> ParseResult:
        """Parse cross-references."""
        # Handle multiple cross-references separated by |
        xrefs = []
        
        # Split by common separators
        for separator in ['|', ';', ',']:
            if separator in value:
                parts = value.split(separator)
                for part in parts:
                    matches = self.XREF_PATTERN.findall(part.strip())
                    xrefs.extend(matches)
                break
        else:
            # No separator, try direct match
            matches = self.XREF_PATTERN.findall(value)
            xrefs.extend(matches)
        
        if not xrefs:
            return ParseResult(
                success=False,
                parsed_value=None,
                confidence=0.0,
                parser_name=self.name
            )
        
        # Group by database
        grouped = {}
        for db, identifier in xrefs:
            if db not in grouped:
                grouped[db] = []
            grouped[db].append(identifier)
        
        return ParseResult(
            success=True,
            parsed_value=grouped,
            confidence=0.95,
            parser_name=self.name,
            metadata={
                "total_xrefs": len(xrefs),
                "databases": list(grouped.keys()),
                "separator_detected": separator if 'separator' in locals() else None
            }
        )
```

## Parser Configuration

Parsers can be configured via YAML:

```yaml
parser_config:
  registry:
    confidence_threshold: 0.7
    
  parsers:
    cas_number:
      enabled: true
      priority: 10
      options:
        validate_checksum: true
        multi_value_separators: [";", ",", "|"]
    
    loinc:
      enabled: true
      priority: 20
      options:
        parse_components: true
        validate_format: true
    
    cross_reference:
      enabled: true
      priority: 30
      options:
        separators: ["|", ";", ","]
        known_databases:
          - UMLS
          - UNII
          - RXNORM
          - MESH
          - CHEBI
          - KEGG
          - HMDB
```

## Integration with Actions

Actions use the parser registry:

```python
class LoadDatasetIdentifiersParams(BaseModel):
    file_path: str
    column_mappings: List[ColumnMapping]
    parser_config: Optional[Dict[str, Any]] = None

@register_action("LOAD_DATASET_IDENTIFIERS")
class LoadDatasetIdentifiersAction(TypedStrategyAction[LoadDatasetIdentifiersParams, LoadResult]):
    def __init__(self):
        super().__init__()
        self.parser_registry = ParserRegistry()
        self._register_default_parsers()
    
    def _register_default_parsers(self):
        """Register default parser plugins."""
        self.parser_registry.register(CASNumberParser())
        self.parser_registry.register(LOINCParser())
        self.parser_registry.register(CrossReferenceParser())
    
    async def execute_typed(
        self,
        params: LoadDatasetIdentifiersParams,
        context: StrategyExecutionContext
    ) -> LoadResult:
        """Load and parse identifiers."""
        parsed_records = []
        
        async for chunk in self._stream_file(params.file_path):
            for record in chunk:
                parsed_record = {}
                
                for mapping in params.column_mappings:
                    value = record.get(mapping.column_name)
                    if value:
                        # Use parser registry
                        parse_results = await self.parser_registry.parse(
                            value,
                            mapping.identifier_type
                        )
                        
                        if parse_results:
                            # Use highest confidence result
                            best_result = parse_results[0]
                            parsed_record[mapping.identifier_type] = {
                                "raw": value,
                                "parsed": best_result.parsed_value,
                                "parser": best_result.parser_name,
                                "confidence": best_result.confidence,
                                "metadata": best_result.metadata
                            }
                
                if parsed_record:
                    parsed_records.append(parsed_record)
        
        return LoadResult(
            total_records=len(parsed_records),
            parsed_records=parsed_records,
            parser_stats=self._calculate_parser_stats(parsed_records)
        )
```

## Benefits

1. **Extensibility**: New parsers can be added without modifying core code
2. **Flexibility**: Parsers can be enabled/disabled via configuration
3. **Robustness**: Multiple parsers can attempt to parse ambiguous data
4. **Confidence**: Each parse result includes confidence score
5. **Debugging**: Detailed metadata helps trace parsing decisions

## Next Steps

- Implement additional parsers for other biological identifier types
- Add parser composition for complex hierarchical data
- Create parser testing framework with real-world examples
- Build parser performance monitoring and optimization