# Develop Metabolite Mapping Strategies

## Overview

This prompt guides the development of 10 metabolite mapping strategies for biomapper. These strategies map metabolite datasets between Israeli10k, Arivale, UK Biobank NMR, and target ontologies (KG2c and SPOKE) using various identifier bridges (HMDB, InChIKey, CTS).

## Prerequisites

Before developing these strategies, ensure the following actions are implemented:
1. `METABOLITE_EXTRACT_IDENTIFIERS` - Extract HMDB, InChIKey, CHEBI, KEGG from various formats
2. `METABOLITE_NORMALIZE_HMDB` - Standardize HMDB formats (HMDB0001234 vs HMDB00001234)
3. `METABOLITE_CTS_BRIDGE` - Chemical Translation Service bridge
4. `METABOLITE_MULTI_BRIDGE` - Multiple bridge resolution
5. `NIGHTINGALE_NMR_MATCH` - Specialized Nightingale NMR matching

Use the biomapper-action-developer agent to implement these actions first if not available.

## Strategy Naming Convention

Follow the format from `/home/ubuntu/biomapper/configs/STRATEGY_ORGANIZATION_GUIDE.md`:
```
met_[source]_to_[target]_[bridge]_v1_base.yaml
```

## Strategies to Develop

### 1. Israeli10k Metabolomics to KG2c
**File**: `configs/strategies/experimental/met_isr_metab_to_kg2c_hmdb_v1_base.yaml`
**Purpose**: Map Israeli10k metabolomics data to KG2c metabolite ontology
**Source Files**:
- `/procedure/data/local_data/MAPPING_ONTOLOGIES/israeli10k/israeli10k_metabolomics_metadata.csv`
- `/procedure/data/local_data/MAPPING_ONTOLOGIES/kg2.10.2c_ontologies/kg2c_metabolites.csv`

**Action Sequence**:
```yaml
steps:
  - name: load_israeli10k
    action:
      type: LOAD_DATASET_IDENTIFIERS
      params:
        file_path: "${metadata.source_files[0].path}"
        identifier_column: "hmdb_id"
        output_key: "israeli10k_metabolites_raw"
  
  - name: load_kg2c
    action:
      type: LOAD_DATASET_IDENTIFIERS
      params:
        file_path: "${metadata.target_files[0].path}"
        identifier_column: "xrefs"
        output_key: "kg2c_metabolites_raw"
  
  - name: extract_israeli10k_ids
    action:
      type: METABOLITE_EXTRACT_IDENTIFIERS
      params:
        input_key: "israeli10k_metabolites_raw"
        extract_hmdb: true
        extract_inchikey: true
        extract_chebi: false
        extract_kegg: false
        output_key: "israeli10k_metabolites"
  
  - name: extract_kg2c_ids
    action:
      type: METABOLITE_EXTRACT_IDENTIFIERS
      params:
        input_key: "kg2c_metabolites_raw"
        xrefs_column: "xrefs"
        extract_hmdb: true
        extract_inchikey: true
        extract_chebi: true
        extract_kegg: true
        output_key: "kg2c_metabolites"
  
  - name: normalize_hmdb
    action:
      type: METABOLITE_NORMALIZE_HMDB
      params:
        input_key: "israeli10k_metabolites"
        hmdb_column: "hmdb_id"
        target_format: "HMDB0001234"
        output_key: "israeli10k_normalized"
  
  - name: cts_bridge
    action:
      type: METABOLITE_CTS_BRIDGE
      params:
        source_key: "israeli10k_normalized"
        target_key: "kg2c_metabolites"
        source_id_type: "hmdb"
        target_id_type: "inchikey"
        output_key: "cts_mapped"
  
  - name: calculate_overlap
    action:
      type: CALCULATE_SET_OVERLAP
      params:
        dataset1_key: "israeli10k_normalized"
        dataset2_key: "kg2c_metabolites"
        output_key: "overlap_statistics"
  
  - name: export_mapping
    action:
      type: EXPORT_DATASET
      params:
        dataset_key: "cts_mapped"
        output_path: "${parameters.output_dir}/israeli10k_kg2c_metabolites.tsv"
```

### 2. Israeli10k Lipidomics to KG2c
**File**: `configs/strategies/experimental/met_isr_lipid_to_kg2c_hmdb_v1_base.yaml`
**Purpose**: Map Israeli10k lipidomics data to KG2c metabolite ontology
**Source Files**:
- `/procedure/data/local_data/MAPPING_ONTOLOGIES/israeli10k/israeli10k_lipidomics_metadata.csv`
- `/procedure/data/local_data/MAPPING_ONTOLOGIES/kg2.10.2c_ontologies/kg2c_metabolites.csv`

[Similar structure to strategy #1, with lipidomics source]

### 3. Arivale Metabolomics to KG2c
**File**: `configs/strategies/experimental/met_arv_to_kg2c_multi_v1_base.yaml`
**Purpose**: Map Arivale metabolomics to KG2c using multiple bridges
**Source Files**:
- `/procedure/data/local_data/MAPPING_ONTOLOGIES/arivale/metabolomics_metadata.tsv`
- `/procedure/data/local_data/MAPPING_ONTOLOGIES/kg2.10.2c_ontologies/kg2c_metabolites.csv`

**Action Sequence**:
```yaml
steps:
  - name: load_arivale
    action:
      type: LOAD_DATASET_IDENTIFIERS
      params:
        file_path: "${metadata.source_files[0].path}"
        identifier_column: "metabolite_id"
        output_key: "arivale_metabolites_raw"
  
  - name: load_kg2c
    # ... (as above)
  
  - name: extract_arivale_ids
    action:
      type: METABOLITE_EXTRACT_IDENTIFIERS
      params:
        input_key: "arivale_metabolites_raw"
        extract_hmdb: true
        extract_inchikey: true
        extract_chebi: true
        extract_kegg: true
        compound_field: "metabolite_id"
        output_key: "arivale_metabolites"
  
  - name: normalize_hmdb
    # ... (as above)
  
  - name: multi_bridge
    action:
      type: METABOLITE_MULTI_BRIDGE
      params:
        source_key: "arivale_normalized"
        target_key: "kg2c_metabolites"
        bridge_types: ["hmdb", "inchikey", "chebi", "kegg"]
        max_attempts: 3
        fallback_to_semantic: true
        output_key: "multi_mapped"
  
  # ... rest of pipeline
```

### 4. UKBB NMR to KG2c
**File**: `configs/strategies/experimental/met_ukb_nmr_to_kg2c_nightingale_v1_base.yaml`
**Purpose**: Map UKBB NMR metabolites to KG2c using Nightingale reference
**Source Files**:
- `/procedure/data/local_data/MAPPING_ONTOLOGIES/ukbb/UKBB_NMR_Meta.tsv`
- `/procedure/data/local_data/MAPPING_ONTOLOGIES/kg2.10.2c_ontologies/kg2c_metabolites.csv`

**Action Sequence**:
```yaml
steps:
  - name: load_ukbb_nmr
    action:
      type: LOAD_DATASET_IDENTIFIERS
      params:
        file_path: "${metadata.source_files[0].path}"
        identifier_column: "biomarker"
        output_key: "ukbb_nmr_raw"
  
  - name: load_kg2c
    # ... (as above)
  
  - name: extract_ukbb_ids
    action:
      type: METABOLITE_EXTRACT_IDENTIFIERS
      params:
        input_key: "ukbb_nmr_raw"
        biomarker_column: "biomarker"
        extract_hmdb: true
        extract_inchikey: false
        output_key: "ukbb_nmr_metabolites"
  
  - name: nightingale_match
    action:
      type: NIGHTINGALE_NMR_MATCH
      params:
        input_key: "ukbb_nmr_metabolites"
        biomarker_column: "biomarker"
        reference_file: "/procedure/data/local_data/references/nightingale_nmr_reference.csv"
        match_threshold: 0.85
        output_key: "nightingale_matched"
  
  - name: normalize_hmdb
    action:
      type: METABOLITE_NORMALIZE_HMDB
      params:
        input_key: "nightingale_matched"
        output_key: "ukbb_normalized"
  
  - name: calculate_overlap
    # ... (as above)
  
  - name: export_mapping
    # ... (as above)
```

### 5. Israeli10k Metabolomics to SPOKE
**File**: `configs/strategies/experimental/met_isr_metab_to_spoke_inchikey_v1_base.yaml`
**Purpose**: Map Israeli10k metabolomics to SPOKE metabolites via InChIKey
**Source Files**:
- `/procedure/data/local_data/MAPPING_ONTOLOGIES/israeli10k/israeli10k_metabolomics_metadata.csv`
- `/procedure/data/local_data/MAPPING_ONTOLOGIES/spoke_ontologies/spoke_metabolites.csv`

[Similar structure with InChIKey as primary bridge]

### 6. Israeli10k Lipidomics to SPOKE
**File**: `configs/strategies/experimental/met_isr_lipid_to_spoke_inchikey_v1_base.yaml`
**Purpose**: Map Israeli10k lipidomics to SPOKE metabolites
**Source Files**:
- `/procedure/data/local_data/MAPPING_ONTOLOGIES/israeli10k/israeli10k_lipidomics_metadata.csv`
- `/procedure/data/local_data/MAPPING_ONTOLOGIES/spoke_ontologies/spoke_metabolites.csv`

[Similar structure for lipidomics]

### 7. Arivale Metabolomics to SPOKE
**File**: `configs/strategies/experimental/met_arv_to_spoke_multi_v1_base.yaml`
**Purpose**: Map Arivale metabolomics to SPOKE using multiple bridges
**Source Files**:
- `/procedure/data/local_data/MAPPING_ONTOLOGIES/arivale/metabolomics_metadata.tsv`
- `/procedure/data/local_data/MAPPING_ONTOLOGIES/spoke_ontologies/spoke_metabolites.csv`

[Similar to strategy #3 with SPOKE target]

### 8. UKBB NMR to SPOKE
**File**: `configs/strategies/experimental/met_ukb_nmr_to_spoke_nightingale_v1_enhanced.yaml`
**Purpose**: Map UKBB NMR to SPOKE with Nightingale + CTS bridge
**Source Files**:
- `/procedure/data/local_data/MAPPING_ONTOLOGIES/ukbb/UKBB_NMR_Meta.tsv`
- `/procedure/data/local_data/MAPPING_ONTOLOGIES/spoke_ontologies/spoke_metabolites.csv`

**Action Sequence**:
```yaml
steps:
  # Load and extract as in strategy #4
  
  - name: nightingale_match
    # ... (as above)
  
  - name: cts_bridge
    action:
      type: METABOLITE_CTS_BRIDGE
      params:
        source_key: "nightingale_matched"
        target_key: "spoke_metabolites"
        source_id_type: "hmdb"
        target_id_type: "inchikey"
        output_key: "cts_enhanced"
  
  # ... rest of pipeline
```

### 9. Multi-Source Metabolite Analysis
**File**: `configs/strategies/experimental/met_multi_to_unified_semantic_v1_enhanced.yaml`
**Purpose**: Complex multi-source metabolite harmonization
**Source Files**:
- `/procedure/data/local_data/MAPPING_ONTOLOGIES/arivale/metabolomics_metadata.tsv`
- `/procedure/data/local_data/MAPPING_ONTOLOGIES/ukbb/UKBB_NMR_Meta.tsv`
- `/procedure/data/local_data/MAPPING_ONTOLOGIES/israeli10k/israeli10k_metabolomics_metadata.csv`
- `/procedure/data/local_data/MAPPING_ONTOLOGIES/israeli10k/israeli10k_lipidomics_metadata.csv`

**Action Sequence**:
```yaml
steps:
  # Load all four sources
  - name: load_arivale
    # ... (as above)
  
  - name: load_ukbb_nmr
    # ... (as above)
  
  - name: load_israeli10k_metab
    # ... (as above)
  
  - name: load_israeli10k_lipid
    # ... (as above)
  
  # Extract and normalize all
  - name: extract_all_ids
    # ... (extract from each dataset)
  
  - name: normalize_all_hmdb
    # ... (normalize each dataset)
  
  # Merge datasets
  - name: merge_datasets
    action:
      type: MERGE_DATASETS
      params:
        dataset_keys:
          - "arivale_normalized"
          - "ukbb_normalized"
          - "israeli10k_metab_normalized"
          - "israeli10k_lipid_normalized"
        merge_strategy: "union"
        deduplicate: true
        output_key: "merged_metabolites"
  
  # Calculate three-way overlap
  - name: three_way_overlap
    action:
      type: CALCULATE_THREE_WAY_OVERLAP
      params:
        dataset1_key: "arivale_normalized"
        dataset2_key: "ukbb_normalized"
        dataset3_key: "israeli10k_metab_normalized"
        output_key: "three_way_statistics"
  
  # Export unified dataset
  - name: export_unified
    action:
      type: EXPORT_DATASET
      params:
        dataset_key: "merged_metabolites"
        output_path: "${parameters.output_dir}/unified_metabolites.tsv"
```

### 10. Semantic Metabolite Enrichment Pipeline
**File**: `configs/strategies/experimental/met_multi_semantic_enrichment_v1_advanced.yaml`
**Purpose**: Advanced semantic matching with vector enhancement
**Components**: Combines multiple advanced matching techniques

**Action Sequence**:
```yaml
steps:
  # Load source datasets
  
  - name: semantic_match
    action:
      type: SEMANTIC_METABOLITE_MATCH
      params:
        source_key: "source_metabolites"
        target_key: "target_metabolites"
        model: "biobert"
        threshold: 0.8
        output_key: "semantic_matched"
  
  - name: vector_enhance
    action:
      type: VECTOR_ENHANCED_MATCH
      params:
        input_key: "semantic_matched"
        embedding_model: "mol2vec"
        similarity_metric: "cosine"
        min_similarity: 0.75
        output_key: "vector_enhanced"
  
  - name: combine_matches
    action:
      type: COMBINE_METABOLITE_MATCHES
      params:
        match_results:
          - "cts_matched"
          - "semantic_matched"
          - "vector_enhanced"
        combination_strategy: "weighted_vote"
        weights: [0.4, 0.3, 0.3]
        output_key: "combined_matches"
  
  - name: generate_report
    action:
      type: GENERATE_METABOLOMICS_REPORT
      params:
        dataset_key: "combined_matches"
        include_statistics: true
        include_visualizations: true
        output_path: "${parameters.output_dir}/metabolomics_report.html"
```

## Metadata Requirements

Each strategy must include comprehensive metadata:

```yaml
metadata:
  # Required fields
  id: "met_isr_metab_to_kg2c_hmdb_v1_base"
  name: "Israeli10k Metabolomics to KG2c via HMDB"
  version: "1.0.0"
  created: "2025-01-08"
  author: "biomapper-team"
  entity_type: "metabolites"
  source_dataset: "israeli10k"
  target_dataset: "kg2c"
  bridge_type: ["hmdb", "cts"]
  
  # Quality tracking
  quality_tier: "experimental"
  validation_status: "pending"
  expected_match_rate: 0.75  # Lower than proteins due to complexity
  actual_match_rate: null
  
  # Data tracking
  source_files:
    - path: "/procedure/data/local_data/MAPPING_ONTOLOGIES/israeli10k/israeli10k_metabolomics_metadata.csv"
      last_updated: "2024-08-01"
      row_count: 3421
  target_files:
    - path: "/procedure/data/local_data/MAPPING_ONTOLOGIES/kg2.10.2c_ontologies/kg2c_metabolites.csv"
      last_updated: "2024-10-01"
      row_count: 28000
  
  # Optional fields
  description: "Maps Israeli10k metabolomics data to KG2c metabolite ontology using HMDB identifiers and CTS bridge"
  tags: ["metabolomics", "hmdb", "cts", "israeli10k", "kg2c"]
  dependencies: []
  supersedes: null
  citation: null
```

## Special Considerations for Metabolites

### 1. Identifier Format Variations
Metabolites have more identifier format variations than proteins:
- HMDB: HMDB0001234 vs HMDB00001234 (7 vs 8 digits)
- InChIKey: Fixed 27-character format but case sensitive
- CHEBI: CHEBI:12345 vs 12345
- KEGG: C00001 vs KEGG:C00001

### 2. Nightingale NMR Specifics
UKBB NMR data uses Nightingale biomarker names that need special handling:
- Biomarker names like "Total_C", "LDL_C" 
- Need reference mapping to standard identifiers
- May require fuzzy matching for variations

### 3. CTS Bridge Limitations
Chemical Translation Service has rate limits and may fail:
- Implement retry logic with exponential backoff
- Cache successful translations
- Fallback to other bridge types when CTS fails

### 4. Lipid Nomenclature
Lipidomics data has complex nomenclature:
- Systematic names: PC(16:0/18:1)
- Common names: Phosphatidylcholine
- Need specialized parsing for lipid classes

## Testing Requirements

### Unit Tests
```python
# tests/unit/configs/strategies/test_metabolite_strategies.py

import pytest
from biomapper_client import BiomapperClient

@pytest.fixture
def client():
    return BiomapperClient()

def test_israeli10k_kg2c_strategy_loads(client):
    """Test strategy loads and validates."""
    strategy = client.get_strategy("met_isr_metab_to_kg2c_hmdb_v1_base")
    assert strategy is not None
    assert strategy.metadata.entity_type == "metabolites"

def test_nightingale_nmr_matching(client, sample_nmr_data):
    """Test Nightingale NMR specific matching."""
    result = client.execute_strategy(
        "met_ukb_nmr_to_kg2c_nightingale_v1_base",
        parameters={"output_dir": "/tmp/test"}
    )
    assert result.success
    assert result.statistics.nightingale_matched > 0

def test_cts_bridge_fallback(client, mock_cts_failure):
    """Test CTS bridge fallback behavior."""
    result = client.execute_strategy(
        "met_isr_metab_to_spoke_inchikey_v1_base",
        parameters={"enable_fallback": True}
    )
    assert result.success
    assert "fallback_used" in result.metadata
```

### Integration Tests
```python
# tests/integration/strategies/test_metabolite_mapping_integration.py

def test_multi_source_metabolite_pipeline(client, real_data_subset):
    """Test multi-source metabolite harmonization."""
    result = client.execute_strategy(
        "met_multi_to_unified_semantic_v1_enhanced"
    )
    assert result.success
    assert result.statistics.sources_integrated == 4
    assert result.statistics.total_unique_metabolites > 0
```

## Validation Criteria

Metabolite strategies have specific validation requirements:

1. **Identifier Extraction**
   - Correctly extracts HMDB from various formats
   - Handles missing identifiers gracefully
   - Parses compound fields with multiple IDs

2. **Format Normalization**
   - HMDB normalized to consistent format
   - InChIKey case handling correct
   - CHEBI prefix handling consistent

3. **Bridge Performance**
   - CTS bridge success rate ≥ 60%
   - Fallback mechanisms work correctly
   - Nightingale matching ≥ 80% for known biomarkers

4. **Match Rates**
   - HMDB direct matching: ≥ 70%
   - InChIKey matching: ≥ 65%
   - Multi-bridge combined: ≥ 75%
   - Semantic matching: ≥ 50% (experimental)

## Common Issues and Solutions

### Issue: Low HMDB Match Rates
**Solution**: Check HMDB format normalization. May have 7 vs 8 digit inconsistency.

### Issue: CTS Bridge Timeouts
**Solution**: Implement chunking and rate limiting. Consider local CTS mirror.

### Issue: Nightingale Biomarker Mismatches
**Solution**: Update Nightingale reference file. Consider fuzzy matching for variations.

### Issue: InChIKey Case Sensitivity
**Solution**: Ensure consistent case handling (typically uppercase).

## Parallel Development

Metabolite strategies can be developed by multiple team members:

- **Developer 1**: Strategies 1-3 (Israeli10k to KG2c/SPOKE)
- **Developer 2**: Strategies 4, 8 (UKBB NMR with Nightingale)
- **Developer 3**: Strategies 5-7 (SPOKE mappings)
- **Developer 4**: Strategies 9-10 (Advanced multi-source)

Coordinate on shared action development, especially NIGHTINGALE_NMR_MATCH.

## Performance Optimization

### Chunking for Large Datasets
```yaml
- name: cts_bridge_chunked
  action:
    type: METABOLITE_CTS_BRIDGE
    params:
      chunk_size: 1000  # Process in chunks
      parallel_requests: 5  # Parallel CTS calls
      cache_results: true
```

### Caching Strategy
```yaml
parameters:
  cache_dir: "${CACHE_DIR:-/tmp/biomapper/cache}"
  use_cache: true
  cache_ttl_days: 30
```

## Quality Checklist

Before submitting metabolite strategy:

- [ ] Strategy follows naming convention
- [ ] Handles multiple identifier formats
- [ ] HMDB normalization tested
- [ ] CTS bridge has fallback
- [ ] Nightingale matching validated (if applicable)
- [ ] Match rates documented
- [ ] Unit tests cover edge cases
- [ ] Integration test with real subset
- [ ] Performance benchmarks recorded
- [ ] Cache strategy implemented
- [ ] Rate limiting configured
- [ ] Documentation complete

## Next Steps

After metabolite strategies are implemented:
1. Optimize CTS bridge performance
2. Implement local identifier cache
3. Develop lipid-specific strategies
4. Create metabolic pathway mapping strategies
5. Build cross-omics integration strategies