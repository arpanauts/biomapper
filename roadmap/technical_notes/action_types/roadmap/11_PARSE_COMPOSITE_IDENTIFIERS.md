# PARSE_COMPOSITE_IDENTIFIERS Action Type

## Overview

`PARSE_COMPOSITE_IDENTIFIERS` splits composite identifier strings (e.g., "P12345,P67890" or "ENSG001|ENSG002") into individual identifiers. This is essential for handling real-world data where multiple IDs are concatenated in a single field.

### Purpose
- Split composite identifiers into individual components
- Handle various separator patterns
- Preserve mapping between composite and individual IDs
- Support nested composite patterns
- Clean and validate split identifiers

### Use Cases
- Parse Arivale protein composite IDs (e.g., "P29460,P29459")
- Split multi-value transcript IDs
- Handle pipe-delimited cross-references
- Process semicolon-separated gene lists
- Extract individual IDs from complex annotations

## Design Decisions

### Key Features
1. **Flexible Separators**: Support any delimiter pattern
2. **Nested Composites**: Handle multiple levels of splitting
3. **Validation**: Optionally validate split IDs
4. **Relationship Preservation**: Track which IDs came from same composite
5. **Whitespace Handling**: Clean IDs during splitting

## Implementation Details

### Parameter Model
```python
class CompositePattern(BaseModel):
    """Pattern for splitting composite identifiers."""
    separator: str = Field(..., description="Separator character(s)")
    level: int = Field(default=1, description="Nesting level for multi-level splits")
    trim_whitespace: bool = Field(default=True)
    remove_empty: bool = Field(default=True)

class ParseCompositeIdentifiersParams(BaseModel):
    """Parameters for parsing composite identifiers."""
    
    # Input configuration
    input_context_key: str = Field(..., description="Key containing identifiers to parse")
    id_field: Optional[str] = Field(None, description="Field to extract if data is complex")
    
    # Splitting configuration
    patterns: List[CompositePattern] = Field(
        default=[CompositePattern(separator=",")],
        description="Patterns to apply in order"
    )
    
    # Processing options
    preserve_original: bool = Field(
        default=True,
        description="Keep original composite ID in results"
    )
    unique_only: bool = Field(default=False, description="Return only unique IDs")
    lowercase: bool = Field(default=False)
    
    # Validation
    validate_format: bool = Field(default=False)
    entity_type: Optional[str] = Field(None, description="For validation")
    skip_invalid: bool = Field(default=True)
    
    # Output configuration
    output_context_key: str = Field(..., description="Where to store results")
    output_format: Literal['flat', 'mapped', 'detailed'] = Field(
        default='flat',
        description="flat=list, mapped=composite->ids, detailed=full info"
    )
    
    # Error handling
    continue_on_error: bool = Field(default=True)
    warn_on_no_split: bool = Field(default=False)
```

### Result Model
```python
class CompositeParseResult(BaseModel):
    """Result from parsing a single composite ID."""
    original: str
    split_ids: List[str]
    pattern_used: str
    is_composite: bool

class ParseCompositeIdentifiersResult(ActionResult):
    """Result from parsing composite identifiers."""
    
    # Statistics
    total_input: int
    composite_count: int
    individual_count: int
    unique_count: int
    
    # Pattern usage
    pattern_matches: Dict[str, int]  # pattern -> count
    no_split_count: int
    
    # Validation results
    validation_failures: int
    invalid_examples: List[str]
    
    # Examples
    composite_examples: List[CompositeParseResult]
```

### Core Implementation
```python
class ParseCompositeIdentifiers(TypedStrategyAction[ParseCompositeIdentifiersParams, ParseCompositeIdentifiersResult]):
    """Parse composite identifiers into individual components."""
    
    def get_params_model(self) -> type[ParseCompositeIdentifiersParams]:
        return ParseCompositeIdentifiersParams
    
    async def execute_typed(
        self,
        params: ParseCompositeIdentifiersParams,
        context: ExecutionContext,
        executor: MappingExecutor
    ) -> ParseCompositeIdentifiersResult:
        """Parse composite identifiers."""
        
        # Load input data
        input_data = context.get(params.input_context_key)
        if not input_data:
            raise ValueError(f"No data found at {params.input_context_key}")
        
        # Extract identifiers
        identifiers = self._extract_identifiers(input_data, params.id_field)
        
        # Initialize results
        all_parsed = []
        pattern_matches = defaultdict(int)
        composite_examples = []
        invalid_ids = []
        
        # Get validator if needed
        validator = self._get_validator(params.entity_type) if params.validate_format else None
        
        # Process each identifier
        for identifier in identifiers:
            if not identifier:
                continue
            
            parsed_result = self._parse_composite(
                identifier=str(identifier),
                patterns=params.patterns,
                params=params
            )
            
            # Track statistics
            if parsed_result.is_composite:
                pattern_matches[parsed_result.pattern_used] += 1
                if len(composite_examples) < 10:
                    composite_examples.append(parsed_result)
            
            # Validate if requested
            if validator and params.validate_format:
                valid_ids = []
                for id_val in parsed_result.split_ids:
                    if validator.validate(id_val, params.entity_type):
                        valid_ids.append(id_val)
                    else:
                        invalid_ids.append(id_val)
                        if not params.skip_invalid:
                            valid_ids.append(id_val)
                
                parsed_result.split_ids = valid_ids
            
            all_parsed.append(parsed_result)
        
        # Format output based on params
        output_data = self._format_output(all_parsed, params)
        context[params.output_context_key] = output_data
        
        # Calculate statistics
        total_individual = sum(len(p.split_ids) for p in all_parsed)
        unique_ids = set()
        for p in all_parsed:
            unique_ids.update(p.split_ids)
        
        return ParseCompositeIdentifiersResult(
            status='success',
            processed_count=len(identifiers),
            error_count=len(invalid_ids),
            total_input=len(identifiers),
            composite_count=sum(1 for p in all_parsed if p.is_composite),
            individual_count=total_individual,
            unique_count=len(unique_ids),
            pattern_matches=dict(pattern_matches),
            no_split_count=sum(1 for p in all_parsed if not p.is_composite),
            validation_failures=len(invalid_ids),
            invalid_examples=invalid_ids[:10],
            composite_examples=composite_examples
        )
    
    def _parse_composite(
        self,
        identifier: str,
        patterns: List[CompositePattern],
        params: ParseCompositeIdentifiersParams
    ) -> CompositeParseResult:
        """Parse a single identifier with multiple patterns."""
        
        current_ids = [identifier]
        pattern_used = None
        is_composite = False
        
        # Apply patterns in order
        for pattern in patterns:
            new_ids = []
            any_split = False
            
            for id_val in current_ids:
                if pattern.separator in id_val:
                    splits = id_val.split(pattern.separator)
                    any_split = True
                    
                    # Clean splits
                    for split in splits:
                        if pattern.trim_whitespace:
                            split = split.strip()
                        if pattern.remove_empty and not split:
                            continue
                        new_ids.append(split)
                else:
                    new_ids.append(id_val)
            
            if any_split:
                current_ids = new_ids
                pattern_used = pattern.separator
                is_composite = True
        
        # Apply final transformations
        final_ids = []
        for id_val in current_ids:
            if params.lowercase:
                id_val = id_val.lower()
            final_ids.append(id_val)
        
        # Handle preserve_original
        if params.preserve_original and is_composite:
            final_ids.insert(0, identifier)
        
        # Handle unique_only
        if params.unique_only:
            final_ids = list(dict.fromkeys(final_ids))  # Preserve order
        
        return CompositeParseResult(
            original=identifier,
            split_ids=final_ids if is_composite else [identifier],
            pattern_used=pattern_used or "none",
            is_composite=is_composite
        )
    
    def _format_output(
        self,
        parsed_results: List[CompositeParseResult],
        params: ParseCompositeIdentifiersParams
    ) -> Any:
        """Format output based on requested format."""
        
        if params.output_format == 'flat':
            # Simple list of all IDs
            all_ids = []
            for result in parsed_results:
                all_ids.extend(result.split_ids)
            return all_ids if not params.unique_only else list(dict.fromkeys(all_ids))
        
        elif params.output_format == 'mapped':
            # Dict mapping composite -> list of IDs
            mapping = {}
            for result in parsed_results:
                if result.is_composite or len(result.split_ids) > 1:
                    mapping[result.original] = result.split_ids
            return mapping
        
        elif params.output_format == 'detailed':
            # Full details for each
            return [result.dict() for result in parsed_results]
```

## Testing Strategy

```python
@pytest.mark.asyncio
async def test_basic_comma_split():
    """Test basic comma-separated splitting."""
    action = ParseCompositeIdentifiers()
    context = {
        'protein_ids': ['P12345', 'P29460,P29459', 'Q11111', 'P11111,P22222,P33333']
    }
    
    result = await action.execute_typed(
        params=ParseCompositeIdentifiersParams(
            input_context_key='protein_ids',
            patterns=[CompositePattern(separator=',')],
            output_context_key='split_ids'
        ),
        context=context,
        executor=mock_executor
    )
    
    assert result.total_input == 4
    assert result.composite_count == 2
    assert result.individual_count == 7  # 1 + 2 + 1 + 3
    assert result.pattern_matches[','] == 2

@pytest.mark.asyncio
async def test_multi_level_splitting():
    """Test nested composite patterns."""
    action = ParseCompositeIdentifiers()
    context = {
        'complex_ids': ['GENE1|GENE2;GENE3|GENE4', 'GENE5']
    }
    
    result = await action.execute_typed(
        params=ParseCompositeIdentifiersParams(
            input_context_key='complex_ids',
            patterns=[
                CompositePattern(separator=';', level=1),
                CompositePattern(separator='|', level=2)
            ],
            output_context_key='genes'
        ),
        context=context,
        executor=mock_executor
    )
    
    assert result.individual_count == 5  # GENE1-5
    assert context['genes'] == ['GENE1', 'GENE2', 'GENE3', 'GENE4', 'GENE5']
```

## Examples

### Basic Protein Composite Parsing
```yaml
- action:
    type: PARSE_COMPOSITE_IDENTIFIERS
    params:
      input_context_key: "arivale_proteins"
      patterns:
        - separator: ","
          trim_whitespace: true
      preserve_original: true
      validate_format: true
      entity_type: "protein"
      output_context_key: "arivale_proteins_expanded"
```

### Complex Cross-Reference Parsing
```yaml
- action:
    type: PARSE_COMPOSITE_IDENTIFIERS
    params:
      input_context_key: "metabolite_xrefs"
      patterns:
        - separator: "|"  # First split by pipe
        - separator: ";"  # Then by semicolon
      unique_only: true
      output_format: "mapped"
      output_context_key: "xref_mapping"
```

## Integration Notes

### Typically Follows
- `LOAD_DATASET_IDENTIFIERS` - Parse after loading
- `EXTRACT_CROSS_REFERENCES` - Split xref values

### Typically Precedes  
- `VALIDATE_IDENTIFIER_FORMAT` - Validate split IDs
- `RESOLVE_HISTORICAL_IDENTIFIERS` - Resolve each ID
- `CALCULATE_SET_OVERLAP` - Use expanded sets