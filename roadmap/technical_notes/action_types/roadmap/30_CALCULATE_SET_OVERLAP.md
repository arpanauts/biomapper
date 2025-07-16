# CALCULATE_SET_OVERLAP Action Type

## Overview

`CALCULATE_SET_OVERLAP` performs comprehensive set analysis between two or more identifier sets, providing detailed statistics about overlaps, differences, and relationships. This is a core analysis action used in most mapping strategies.

### Purpose
- Compare identifier sets from different sources
- Calculate overlap statistics and coverage metrics
- Identify unique identifiers in each set
- Support N-way comparisons (not just pairwise)
- Generate visualization-ready data

### Use Cases
- Compare UKBB vs HPA protein coverage
- Analyze metabolite overlap between datasets
- Find common genes across experiments
- Identify missing identifiers for gap analysis
- Multi-dataset intersection analysis

## Design Decisions

### Key Features
1. **N-way Comparisons**: Support 2+ sets, not just pairwise
2. **Rich Statistics**: Beyond simple counts - percentages, ratios, distributions
3. **Flexible Input**: Accept various input formats from context
4. **Visualization Ready**: Output data suitable for Venn diagrams
5. **Memory Efficient**: Stream large sets when needed

### Error Handling Strategy
Following the error handling patterns, this action:
- Validates input sets exist in context
- Handles empty sets gracefully
- Continues with partial data if configured
- Reports detailed errors with context

## Implementation Details

### Parameter Model
```python
class SetDefinition(BaseModel):
    """Definition of a set to analyze."""
    context_key: str = Field(..., description="Key in context containing identifiers")
    label: str = Field(..., description="Human-readable label for this set")
    id_field: Optional[str] = Field(None, description="Field to extract if data is complex")

class CalculateSetOverlapParams(BaseModel):
    """Parameters for set overlap calculation."""
    
    # Input sets (2 or more)
    sets: List[SetDefinition] = Field(
        ...,
        min_items=2,
        description="Sets to compare"
    )
    
    # Comparison options
    case_sensitive: bool = Field(default=True)
    normalize_ids: bool = Field(default=False)
    id_normalizer: Optional[str] = Field(None, description="Entity type for normalization")
    
    # Output options
    calculate_pairwise: bool = Field(default=True, description="Calculate all pairwise overlaps")
    include_examples: bool = Field(default=True, description="Include example IDs in results")
    max_examples: int = Field(default=10, ge=1, le=100)
    
    # Statistics to calculate
    calculate_jaccard: bool = Field(default=True)
    calculate_coverage: bool = Field(default=True)
    calculate_distribution: bool = Field(default=False)
    
    # Output configuration
    output_context_key: str = Field(..., description="Where to store results")
    save_set_operations: bool = Field(default=True, description="Save intersection/difference sets")
    
    # Error handling (following patterns)
    continue_on_missing_set: bool = Field(default=False)
    min_set_size: int = Field(default=0, description="Minimum size to include set")
```

### Result Model
```python
class SetStatistics(BaseModel):
    """Statistics for a single set."""
    label: str
    size: int
    unique_count: int
    unique_percentage: float
    examples: List[str]

class PairwiseOverlap(BaseModel):
    """Overlap between two sets."""
    set_a_label: str
    set_b_label: str
    intersection_size: int
    union_size: int
    jaccard_index: float
    a_coverage: float  # % of A in intersection
    b_coverage: float  # % of B in intersection
    unique_to_a: int
    unique_to_b: int
    intersection_examples: List[str]

class CalculateSetOverlapResult(ActionResult):
    """Result from set overlap calculation."""
    
    # Set information
    set_count: int
    set_statistics: List[SetStatistics]
    total_unique_ids: int
    
    # Overlap information
    full_intersection_size: int  # Common to ALL sets
    full_intersection_percentage: float
    full_intersection_examples: List[str]
    
    # Pairwise comparisons
    pairwise_overlaps: Optional[List[PairwiseOverlap]]
    
    # Saved set operations (if requested)
    saved_sets: Optional[Dict[str, str]]  # operation -> context_key
    
    # Visualization data
    venn_data: Optional[Dict[str, Any]]  # For plotting
```

### Core Implementation
```python
class CalculateSetOverlap(TypedStrategyAction[CalculateSetOverlapParams, CalculateSetOverlapResult]):
    """Calculate comprehensive set overlap statistics."""
    
    def get_params_model(self) -> type[CalculateSetOverlapParams]:
        return CalculateSetOverlapParams
    
    async def execute_typed(
        self,
        params: CalculateSetOverlapParams,
        context: ExecutionContext,
        executor: MappingExecutor
    ) -> CalculateSetOverlapResult:
        """Calculate set overlaps with comprehensive statistics."""
        
        # Load sets from context with error handling
        loaded_sets = {}
        for set_def in params.sets:
            try:
                data = context.get(set_def.context_key)
                if data is None:
                    if params.continue_on_missing_set:
                        executor.logger.warning(f"Set '{set_def.label}' not found at {set_def.context_key}")
                        continue
                    else:
                        raise ValueError(f"Required set '{set_def.label}' not found at {set_def.context_key}")
                
                # Extract identifiers based on data structure
                ids = self._extract_identifiers(data, set_def.id_field)
                
                # Normalize if requested
                if params.normalize_ids:
                    ids = self._normalize_identifiers(ids, params)
                
                # Check minimum size
                if len(ids) < params.min_set_size:
                    executor.logger.warning(f"Set '{set_def.label}' has {len(ids)} IDs, below minimum {params.min_set_size}")
                    continue
                
                loaded_sets[set_def.label] = set(ids)
                
            except Exception as e:
                # Use error handling patterns
                if self._should_continue_on_error(e, params):
                    executor.logger.error(f"Error loading set '{set_def.label}': {e}")
                    continue
                else:
                    raise
        
        # Validate we have enough sets
        if len(loaded_sets) < 2:
            raise ValueError(f"Need at least 2 sets, only loaded {len(loaded_sets)}")
        
        # Calculate statistics
        set_stats = []
        all_ids = set()
        
        for label, id_set in loaded_sets.items():
            all_ids.update(id_set)
            
            # Calculate unique IDs (in this set only)
            unique_ids = id_set.copy()
            for other_label, other_set in loaded_sets.items():
                if other_label != label:
                    unique_ids -= other_set
            
            set_stats.append(SetStatistics(
                label=label,
                size=len(id_set),
                unique_count=len(unique_ids),
                unique_percentage=len(unique_ids) / len(id_set) * 100 if id_set else 0,
                examples=list(id_set)[:params.max_examples] if params.include_examples else []
            ))
        
        # Calculate full intersection
        full_intersection = set.intersection(*loaded_sets.values()) if loaded_sets else set()
        
        # Calculate pairwise overlaps
        pairwise_overlaps = []
        if params.calculate_pairwise and len(loaded_sets) > 1:
            for i, (label_a, set_a) in enumerate(loaded_sets.items()):
                for label_b, set_b in list(loaded_sets.items())[i+1:]:
                    intersection = set_a & set_b
                    union = set_a | set_b
                    
                    pairwise_overlaps.append(PairwiseOverlap(
                        set_a_label=label_a,
                        set_b_label=label_b,
                        intersection_size=len(intersection),
                        union_size=len(union),
                        jaccard_index=len(intersection) / len(union) if union else 0,
                        a_coverage=len(intersection) / len(set_a) * 100 if set_a else 0,
                        b_coverage=len(intersection) / len(set_b) * 100 if set_b else 0,
                        unique_to_a=len(set_a - set_b),
                        unique_to_b=len(set_b - set_a),
                        intersection_examples=list(intersection)[:params.max_examples] if params.include_examples else []
                    ))
        
        # Save set operations if requested
        saved_sets = {}
        if params.save_set_operations:
            # Save intersection
            context[f"{params.output_context_key}_intersection"] = list(full_intersection)
            saved_sets["intersection"] = f"{params.output_context_key}_intersection"
            
            # Save unique sets
            for label, id_set in loaded_sets.items():
                unique_ids = id_set.copy()
                for other_label, other_set in loaded_sets.items():
                    if other_label != label:
                        unique_ids -= other_set
                
                key = f"{params.output_context_key}_{label}_unique"
                context[key] = list(unique_ids)
                saved_sets[f"{label}_unique"] = key
        
        # Create result
        result = CalculateSetOverlapResult(
            status='success',
            processed_count=len(all_ids),
            error_count=0,
            set_count=len(loaded_sets),
            set_statistics=set_stats,
            total_unique_ids=len(all_ids),
            full_intersection_size=len(full_intersection),
            full_intersection_percentage=len(full_intersection) / len(all_ids) * 100 if all_ids else 0,
            full_intersection_examples=list(full_intersection)[:params.max_examples] if params.include_examples else [],
            pairwise_overlaps=pairwise_overlaps if params.calculate_pairwise else None,
            saved_sets=saved_sets if params.save_set_operations else None,
            venn_data=self._generate_venn_data(loaded_sets) if len(loaded_sets) <= 4 else None
        )
        
        # Store result in context
        context[params.output_context_key] = result
        
        return result
```

## Testing Strategy

```python
@pytest.mark.asyncio
async def test_basic_two_set_overlap():
    """Test basic overlap calculation between two sets."""
    action = CalculateSetOverlap()
    context = {
        'ukbb_proteins': ['P12345', 'P67890', 'Q11111', 'Q22222'],
        'hpa_proteins': ['P12345', 'Q11111', 'Q33333', 'Q44444']
    }
    
    result = await action.execute_typed(
        params=CalculateSetOverlapParams(
            sets=[
                SetDefinition(context_key='ukbb_proteins', label='UKBB'),
                SetDefinition(context_key='hpa_proteins', label='HPA')
            ],
            output_context_key='overlap_analysis'
        ),
        context=context,
        executor=mock_executor
    )
    
    assert result.set_count == 2
    assert result.full_intersection_size == 2  # P12345, Q11111
    assert result.total_unique_ids == 6
    
    # Check pairwise
    pairwise = result.pairwise_overlaps[0]
    assert pairwise.intersection_size == 2
    assert pairwise.unique_to_a == 2  # P67890, Q22222
    assert pairwise.unique_to_b == 2  # Q33333, Q44444
    assert pairwise.jaccard_index == 2/6  # 0.333...

@pytest.mark.asyncio
async def test_three_way_overlap():
    """Test N-way overlap with 3 sets."""
    # Test with metabolite datasets
    # Verify full intersection vs pairwise
    pass

@pytest.mark.asyncio
async def test_error_handling():
    """Test error handling for missing sets."""
    # Test continue_on_missing_set behavior
    # Test minimum size filtering
    pass
```

## Examples

### Basic UKBB vs HPA Comparison
```yaml
- action:
    type: CALCULATE_SET_OVERLAP
    params:
      sets:
        - context_key: "ukbb_uniprot_ids"
          label: "UKBB Proteins"
        - context_key: "hpa_uniprot_ids"
          label: "HPA Proteins"
      calculate_jaccard: true
      include_examples: true
      save_set_operations: true
      output_context_key: "ukbb_hpa_overlap"
```

### Multi-Dataset Metabolite Analysis
```yaml
- action:
    type: CALCULATE_SET_OVERLAP
    params:
      sets:
        - context_key: "arivale_metabolites"
          label: "Arivale"
          id_field: "hmdb_id"
        - context_key: "kegg_metabolites"
          label: "KEGG"
          id_field: "compound_id"
        - context_key: "hmdb_metabolites"
          label: "HMDB"
          id_field: "accession"
      normalize_ids: true
      id_normalizer: "metabolite"
      calculate_distribution: true
      output_context_key: "metabolite_coverage_analysis"
```

### Complex Gene Analysis
```yaml
- action:
    type: CALCULATE_SET_OVERLAP
    params:
      sets:
        - context_key: "expressed_genes"
          label: "Expressed"
        - context_key: "mutated_genes"
          label: "Mutated"
        - context_key: "drug_target_genes"
          label: "Drug Targets"
        - context_key: "disease_genes"
          label: "Disease Associated"
      case_sensitive: false
      max_examples: 20
      save_set_operations: true
      output_context_key: "gene_overlap_analysis"
```

## Integration Notes

### Typically Follows
- `LOAD_DATASET_IDENTIFIERS` - Load sets to compare
- `RESOLVE_HISTORICAL_IDENTIFIERS` - Normalize IDs first
- `FILTER_IDENTIFIERS` - Pre-filter sets

### Typically Precedes
- `GENERATE_MAPPING_REPORT` - Include overlap stats
- `RANK_MAPPING_CANDIDATES` - Use overlap for scoring
- `VISUALIZE_RESULTS` - Create Venn diagrams

### Context Usage
```python
# Input: Expects lists or sets in context
context['set1'] = ['ID1', 'ID2', 'ID3']
context['set2'] = {'ID2', 'ID3', 'ID4'}

# Output: Comprehensive results
context['overlap_results'] = CalculateSetOverlapResult(...)
context['overlap_results_intersection'] = ['ID2', 'ID3']
context['overlap_results_set1_unique'] = ['ID1']
```

## Performance Considerations

1. **Set Operations**: Use Python sets for O(1) lookups
2. **Memory Usage**: ~40 bytes per unique identifier
3. **Large Sets**: Consider streaming for sets >10M IDs
4. **Normalization Cost**: Cache normalized IDs
5. **Example Generation**: Limit examples for large sets