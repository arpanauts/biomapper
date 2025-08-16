# RESOLVE_HISTORICAL_IDENTIFIERS Action Type

## Overview

`RESOLVE_HISTORICAL_IDENTIFIERS` is a generalized action for resolving obsolete, deprecated, or historical identifiers to their current versions. It works across all entity types by leveraging the Entity Behavior Registry for type-specific resolution logic.

### Purpose
- Resolve deprecated identifiers to current primary IDs
- Handle ID mergers, splits, and replacements
- Work across all entity types (proteins, genes, metabolites, etc.)
- Support batch resolution for performance
- Provide detailed provenance of ID changes

### Use Cases
- Resolve obsolete UniProt accessions to current ones
- Update deprecated gene symbols to current nomenclature
- Handle metabolite ID changes across database versions
- Resolve clinical terminology updates (ICD-9 to ICD-10)
- Track identifier evolution over time

## Design Decisions

### Generalization Strategy
1. **Entity Registry**: Each entity type registers its resolution logic
2. **Common Interface**: All resolvers follow same input/output pattern
3. **Caching Layer**: Share cache across entity types
4. **Batch Processing**: Optimize API calls for all types
5. **Fallback Chain**: Try multiple resolution strategies

## Implementation Details

### Parameter Model
```python
class HistoricalResolutionStrategy(str, Enum):
    """Strategy for handling historical IDs."""
    LATEST_PRIMARY = "latest_primary"  # Get most recent primary ID
    ALL_CURRENT = "all_current"  # Get all current IDs (for splits)
    TRACK_LINEAGE = "track_lineage"  # Full history tracking
    PREFER_REVIEWED = "prefer_reviewed"  # For proteins, prefer SwissProt

class ResolveHistoricalIdentifiersParams(BaseModel):
    """Parameters for historical ID resolution."""
    
    # Input configuration
    input_context_key: str = Field(..., description="Key containing IDs to resolve")
    id_field: Optional[str] = Field(None, description="Field to extract if complex data")
    
    # Resolution configuration
    entity_type: str = Field(..., description="Entity type for resolution")
    resolution_strategy: HistoricalResolutionStrategy = Field(
        default=HistoricalResolutionStrategy.LATEST_PRIMARY
    )
    
    # Processing options
    batch_size: int = Field(default=200, ge=1, le=1000)
    include_obsolete: bool = Field(default=False, description="Keep obsolete IDs in output")
    expand_composites: bool = Field(default=True, description="Expand composite/demerged IDs")
    
    # Caching configuration
    use_cache: bool = Field(default=True)
    cache_ttl_days: int = Field(default=30)
    force_refresh: bool = Field(default=False)
    
    # Output configuration
    output_context_key: str = Field(..., description="Where to store resolved IDs")
    track_changes: bool = Field(default=True, description="Track what changed")
    include_provenance: bool = Field(default=True)
    
    # Error handling
    continue_on_error: bool = Field(default=True)
    fallback_to_original: bool = Field(default=True)
    warn_on_no_resolution: bool = Field(default=True)
```

### Result Model
```python
class ResolutionRecord(BaseModel):
    """Record of a single ID resolution."""
    original_id: str
    resolved_ids: List[str]
    resolution_type: str  # "unchanged", "updated", "merged", "split", "obsolete"
    confidence: float
    source: str  # Which resolver was used
    timestamp: datetime

class ResolveHistoricalIdentifiersResult(ActionResult):
    """Result from historical ID resolution."""
    
    # Summary statistics
    total_input: int
    resolved_count: int
    unchanged_count: int
    updated_count: int
    obsolete_count: int
    failed_count: int
    
    # Resolution details
    resolution_types: Dict[str, int]  # type -> count
    sources_used: Dict[str, int]  # resolver -> count
    
    # Change tracking
    changes: Optional[List[ResolutionRecord]]
    
    # Performance metrics
    cache_hits: int
    api_calls: int
    resolution_time_ms: float
```

### Core Implementation
```python
class ResolveHistoricalIdentifiers(TypedStrategyAction[ResolveHistoricalIdentifiersParams, ResolveHistoricalIdentifiersResult]):
    """Resolve historical identifiers across entity types."""
    
    def __init__(self):
        super().__init__()
        self.resolver_registry = EntityBehaviorRegistry.get_instance()
        self.cache_manager = CacheManager.get_instance()
    
    def get_params_model(self) -> type[ResolveHistoricalIdentifiersParams]:
        return ResolveHistoricalIdentifiersParams
    
    async def execute_typed(
        self,
        params: ResolveHistoricalIdentifiersParams,
        context: ExecutionContext,
        executor: MappingExecutor
    ) -> ResolveHistoricalIdentifiersResult:
        """Resolve historical identifiers."""
        
        # Get resolver for entity type
        resolver = self.resolver_registry.get_resolver(params.entity_type)
        if not resolver:
            raise ValueError(f"No resolver registered for entity type: {params.entity_type}")
        
        # Load input identifiers
        input_ids = self._extract_identifiers(
            context.get(params.input_context_key),
            params.id_field
        )
        
        # Initialize tracking
        resolution_records = []
        statistics = defaultdict(int)
        resolved_ids = []
        
        # Process in batches
        for batch_start in range(0, len(input_ids), params.batch_size):
            batch = input_ids[batch_start:batch_start + params.batch_size]
            
            # Check cache first
            cached_results = {}
            uncached_ids = []
            
            if params.use_cache and not params.force_refresh:
                for id_val in batch:
                    cache_key = f"{params.entity_type}:historical:{id_val}"
                    cached = await self.cache_manager.get(cache_key)
                    if cached:
                        cached_results[id_val] = cached
                        statistics['cache_hits'] += 1
                    else:
                        uncached_ids.append(id_val)
            else:
                uncached_ids = batch
            
            # Resolve uncached IDs
            if uncached_ids:
                try:
                    batch_results = await resolver.resolve_historical(
                        identifiers=uncached_ids,
                        strategy=params.resolution_strategy,
                        include_obsolete=params.include_obsolete,
                        expand_composites=params.expand_composites
                    )
                    statistics['api_calls'] += 1
                    
                    # Cache results
                    if params.use_cache:
                        for id_val, result in batch_results.items():
                            cache_key = f"{params.entity_type}:historical:{id_val}"
                            await self.cache_manager.set(
                                cache_key,
                                result,
                                ttl_days=params.cache_ttl_days
                            )
                    
                except Exception as e:
                    if params.continue_on_error:
                        executor.logger.error(f"Failed to resolve batch: {e}")
                        # Use fallback
                        if params.fallback_to_original:
                            for id_val in uncached_ids:
                                batch_results[id_val] = {
                                    'resolved': [id_val],
                                    'type': 'fallback',
                                    'confidence': 0.5
                                }
                    else:
                        raise
            
            # Process results
            all_results = {**cached_results, **batch_results}
            
            for original_id, resolution in all_results.items():
                # Track resolution type
                res_type = resolution.get('type', 'unknown')
                statistics[res_type] += 1
                
                # Extract resolved IDs
                resolved = resolution.get('resolved', [])
                if not resolved and params.fallback_to_original:
                    resolved = [original_id]
                    res_type = 'unchanged'
                
                resolved_ids.extend(resolved)
                
                # Track changes if requested
                if params.track_changes:
                    resolution_records.append(ResolutionRecord(
                        original_id=original_id,
                        resolved_ids=resolved,
                        resolution_type=res_type,
                        confidence=resolution.get('confidence', 1.0),
                        source=resolution.get('source', params.entity_type),
                        timestamp=datetime.utcnow()
                    ))
                
                # Log warnings
                if not resolved and params.warn_on_no_resolution:
                    executor.logger.warning(f"No resolution found for {params.entity_type} ID: {original_id}")
        
        # Remove duplicates if needed
        unique_resolved = list(dict.fromkeys(resolved_ids))
        
        # Store results
        context[params.output_context_key] = unique_resolved
        
        # Add provenance if requested
        if params.include_provenance:
            provenance_key = f"{params.output_context_key}_provenance"
            context[provenance_key] = resolution_records
        
        return ResolveHistoricalIdentifiersResult(
            status='success',
            processed_count=len(input_ids),
            error_count=statistics.get('failed', 0),
            total_input=len(input_ids),
            resolved_count=len(unique_resolved),
            unchanged_count=statistics.get('unchanged', 0),
            updated_count=statistics.get('updated', 0),
            obsolete_count=statistics.get('obsolete', 0),
            failed_count=statistics.get('failed', 0),
            resolution_types=dict(statistics),
            sources_used={params.entity_type: len(input_ids)},
            changes=resolution_records if params.track_changes else None,
            cache_hits=statistics.get('cache_hits', 0),
            api_calls=statistics.get('api_calls', 0),
            resolution_time_ms=0  # TODO: Implement timing
        )
```

## Entity-Specific Resolvers

### Protein Resolver Example
```python
class UniProtHistoricalResolver:
    """UniProt-specific historical resolution."""
    
    async def resolve_historical(
        self,
        identifiers: List[str],
        strategy: str,
        **kwargs
    ) -> Dict[str, Dict]:
        """Resolve UniProt historical IDs."""
        # Implementation using UniProt API
        # Handles demergers, secondary to primary, etc.
        pass

# Register with entity registry
EntityBehaviorRegistry.register(
    entity_type='protein',
    behavior='historical_resolution',
    handler=UniProtHistoricalResolver()
)
```

## Testing Strategy

```python
@pytest.mark.asyncio
async def test_protein_historical_resolution():
    """Test UniProt historical resolution."""
    action = ResolveHistoricalIdentifiers()
    
    # Mock resolver registration
    mock_resolver = Mock()
    mock_resolver.resolve_historical.return_value = {
        'P00001': {'resolved': ['P99999'], 'type': 'updated'},
        'P00002': {'resolved': ['P00002'], 'type': 'unchanged'},
        'P0CG05': {'resolved': ['P0DOY2', 'P0DOY3'], 'type': 'split'}
    }
    
    context = {
        'old_proteins': ['P00001', 'P00002', 'P0CG05']
    }
    
    result = await action.execute_typed(
        params=ResolveHistoricalIdentifiersParams(
            input_context_key='old_proteins',
            entity_type='protein',
            output_context_key='current_proteins'
        ),
        context=context,
        executor=mock_executor
    )
    
    assert result.updated_count == 1
    assert result.unchanged_count == 1
    assert 'split' in result.resolution_types
    assert len(context['current_proteins']) == 4  # P99999, P00002, P0DOY2, P0DOY3
```

## Examples

### Basic Protein Resolution
```yaml
- action:
    type: RESOLVE_HISTORICAL_IDENTIFIERS
    params:
      input_context_key: "ukbb_raw_uniprot_ids"
      entity_type: "protein"
      resolution_strategy: "latest_primary"
      batch_size: 200
      output_context_key: "ukbb_current_uniprot_ids"
```

### Gene Symbol Updates with Tracking
```yaml
- action:
    type: RESOLVE_HISTORICAL_IDENTIFIERS
    params:
      input_context_key: "old_gene_symbols"
      entity_type: "gene"
      resolution_strategy: "track_lineage"
      track_changes: true
      include_provenance: true
      output_context_key: "current_gene_symbols"
```

### Metabolite ID Resolution with Caching
```yaml
- action:
    type: RESOLVE_HISTORICAL_IDENTIFIERS
    params:
      input_context_key: "legacy_metabolite_ids"
      entity_type: "metabolite"
      use_cache: true
      cache_ttl_days: 90
      expand_composites: true
      fallback_to_original: true
      output_context_key: "current_metabolite_ids"
```

## Integration Notes

### Requires
- Entity-specific resolvers registered
- Cache manager configured
- Network access for API calls

### Typically Follows
- `LOAD_DATASET_IDENTIFIERS` - Load IDs to resolve
- `PARSE_COMPOSITE_IDENTIFIERS` - Split before resolving

### Typically Precedes
- `CALCULATE_SET_OVERLAP` - Compare resolved sets
- `MAP_VIA_CROSS_REFERENCE` - Use current IDs for mapping