# Develop Protein Mapping Strategies

## Overview

This prompt guides the development of 6 protein mapping strategies for biomapper. These strategies map protein datasets between Arivale, UK Biobank (UKBB), and target ontologies (KG2c and SPOKE) using UniProt identifiers as the primary bridge.

## Prerequisites

Before developing these strategies, ensure the following actions are implemented:
1. `PROTEIN_EXTRACT_UNIPROT_FROM_XREFS` - Extract UniProt IDs from xrefs fields
2. `PROTEIN_NORMALIZE_ACCESSIONS` - Standardize UniProt accession formats
3. `PROTEIN_MULTI_BRIDGE` - Multi-bridge protein resolution

Use the biomapper-action-developer agent to implement these actions first if not available.

## Strategy Naming Convention

Follow the format from `/home/ubuntu/biomapper/configs/STRATEGY_ORGANIZATION_GUIDE.md`:
```
prot_[source]_to_[target]_[bridge]_v1_base.yaml
```

## Strategies to Develop

### 1. Arivale to UKBB Protein Comparison
**File**: `configs/strategies/experimental/prot_arv_ukb_comparison_uniprot_v1_base.yaml`
**Purpose**: Cross-dataset protein comparison between Arivale and UKBB proteomics
**Source Files**: 
- `/procedure/data/local_data/MAPPING_ONTOLOGIES/arivale/proteomics_metadata.tsv`
- `/procedure/data/local_data/MAPPING_ONTOLOGIES/ukbb/UKBB_Protein_Meta.tsv`

**Action Sequence**:
```yaml
steps:
  - name: load_arivale_proteins
    action:
      type: LOAD_DATASET_IDENTIFIERS
      params:
        file_path: "${metadata.source_files[0].path}"
        identifier_column: "uniprot"
        output_key: "arivale_proteins"
  
  - name: load_ukbb_proteins
    action:
      type: LOAD_DATASET_IDENTIFIERS
      params:
        file_path: "${metadata.source_files[1].path}"
        identifier_column: "uniprot"
        output_key: "ukbb_proteins"
  
  - name: normalize_arivale
    action:
      type: PROTEIN_NORMALIZE_ACCESSIONS
      params:
        input_key: "arivale_proteins"
        output_key: "arivale_normalized"
  
  - name: normalize_ukbb
    action:
      type: PROTEIN_NORMALIZE_ACCESSIONS
      params:
        input_key: "ukbb_proteins"
        output_key: "ukbb_normalized"
  
  - name: multi_bridge_resolution
    action:
      type: PROTEIN_MULTI_BRIDGE
      params:
        source_key: "arivale_normalized"
        target_key: "ukbb_normalized"
        bridge_types: ["uniprot", "gene_symbol"]
        output_key: "mapped_proteins"
  
  - name: calculate_overlap
    action:
      type: CALCULATE_SET_OVERLAP
      params:
        dataset1_key: "arivale_normalized"
        dataset2_key: "ukbb_normalized"
        output_key: "overlap_statistics"
  
  - name: export_results
    action:
      type: EXPORT_DATASET
      params:
        dataset_key: "mapped_proteins"
        output_path: "${parameters.output_dir}/protein_comparison.tsv"
```

### 2. Arivale Proteins to KG2c
**File**: `configs/strategies/experimental/prot_arv_to_kg2c_uniprot_v1_base.yaml`
**Purpose**: Map Arivale proteomics data to KG2c protein ontology
**Source Files**:
- `/procedure/data/local_data/MAPPING_ONTOLOGIES/arivale/proteomics_metadata.tsv`
- `/procedure/data/local_data/MAPPING_ONTOLOGIES/kg2.10.2c_ontologies/kg2c_proteins.csv`

**Action Sequence**:
```yaml
steps:
  - name: load_arivale
    action:
      type: LOAD_DATASET_IDENTIFIERS
      params:
        file_path: "${metadata.source_files[0].path}"
        identifier_column: "uniprot"
        output_key: "arivale_proteins"
  
  - name: load_kg2c
    action:
      type: LOAD_DATASET_IDENTIFIERS
      params:
        file_path: "${metadata.target_files[0].path}"
        identifier_column: "xrefs"
        output_key: "kg2c_proteins_raw"
  
  - name: extract_kg2c_uniprot
    action:
      type: PROTEIN_EXTRACT_UNIPROT_FROM_XREFS
      params:
        input_key: "kg2c_proteins_raw"
        xrefs_column: "xrefs"
        remove_isoforms: true
        output_key: "kg2c_proteins"
  
  - name: normalize_arivale
    action:
      type: PROTEIN_NORMALIZE_ACCESSIONS
      params:
        input_key: "arivale_proteins"
        output_key: "arivale_normalized"
  
  - name: filter_kg2c
    action:
      type: FILTER_DATASET
      params:
        input_key: "kg2c_proteins"
        filter_criteria:
          has_uniprot: true
        output_key: "kg2c_filtered"
  
  - name: multi_bridge
    action:
      type: PROTEIN_MULTI_BRIDGE
      params:
        source_key: "arivale_normalized"
        target_key: "kg2c_filtered"
        bridge_types: ["uniprot", "gene_symbol", "ensembl"]
        max_attempts: 3
        output_key: "mapped_proteins"
  
  - name: calculate_overlap
    action:
      type: CALCULATE_SET_OVERLAP
      params:
        dataset1_key: "arivale_normalized"
        dataset2_key: "kg2c_filtered"
        output_key: "overlap_statistics"
  
  - name: export_mapping
    action:
      type: EXPORT_DATASET
      params:
        dataset_key: "mapped_proteins"
        output_path: "${parameters.output_dir}/arivale_kg2c_proteins.tsv"
```

### 3. UKBB Proteins to KG2c
**File**: `configs/strategies/experimental/prot_ukb_to_kg2c_uniprot_v1_base.yaml`
**Purpose**: Map UKBB proteomics data to KG2c protein ontology
**Source Files**:
- `/procedure/data/local_data/MAPPING_ONTOLOGIES/ukbb/UKBB_Protein_Meta.tsv`
- `/procedure/data/local_data/MAPPING_ONTOLOGIES/kg2.10.2c_ontologies/kg2c_proteins.csv`

[Similar structure to strategy #2, with UKBB as source]

### 4. Arivale Proteins to SPOKE
**File**: `configs/strategies/experimental/prot_arv_to_spoke_uniprot_v1_base.yaml`
**Purpose**: Map Arivale proteomics data to SPOKE protein ontology
**Source Files**:
- `/procedure/data/local_data/MAPPING_ONTOLOGIES/arivale/proteomics_metadata.tsv`
- `/procedure/data/local_data/MAPPING_ONTOLOGIES/spoke_ontologies/spoke_proteins.csv`

[Similar structure to strategy #2, with SPOKE as target]

### 5. UKBB Proteins to SPOKE
**File**: `configs/strategies/experimental/prot_ukb_to_spoke_uniprot_v1_base.yaml`
**Purpose**: Map UKBB proteomics data to SPOKE protein ontology
**Source Files**:
- `/procedure/data/local_data/MAPPING_ONTOLOGIES/ukbb/UKBB_Protein_Meta.tsv`
- `/procedure/data/local_data/MAPPING_ONTOLOGIES/spoke_ontologies/spoke_proteins.csv`

[Similar structure to strategy #2, with UKBB source and SPOKE target]

### 6. Multi-Source Protein Harmonization
**File**: `configs/strategies/experimental/prot_multi_to_unified_uniprot_v1_enhanced.yaml`
**Purpose**: Harmonize proteins from multiple sources into unified dataset
**Source Files**:
- `/procedure/data/local_data/MAPPING_ONTOLOGIES/arivale/proteomics_metadata.tsv`
- `/procedure/data/local_data/MAPPING_ONTOLOGIES/ukbb/UKBB_Protein_Meta.tsv`
- `/procedure/data/local_data/MAPPING_ONTOLOGIES/kg2.10.2c_ontologies/kg2c_proteins.csv`
- `/procedure/data/local_data/MAPPING_ONTOLOGIES/spoke_ontologies/spoke_proteins.csv`

**Action Sequence**:
```yaml
steps:
  # Load all sources
  - name: load_arivale
    # ... (as above)
  
  - name: load_ukbb
    # ... (as above)
  
  - name: load_kg2c
    # ... (as above)
  
  - name: load_spoke
    # ... (as above)
  
  # Extract and normalize all
  - name: extract_kg2c_uniprot
    # ... (as above)
  
  - name: extract_spoke_uniprot
    # ... (as above)
  
  - name: normalize_all
    # ... (normalize each dataset)
  
  # Merge all datasets
  - name: merge_datasets
    action:
      type: MERGE_DATASETS
      params:
        dataset_keys: 
          - "arivale_normalized"
          - "ukbb_normalized"
          - "kg2c_normalized"
          - "spoke_normalized"
        merge_strategy: "union"
        deduplicate: true
        output_key: "unified_proteins"
  
  # Calculate multi-way overlaps
  - name: calculate_three_way
    action:
      type: CALCULATE_THREE_WAY_OVERLAP
      params:
        dataset1_key: "arivale_normalized"
        dataset2_key: "ukbb_normalized"
        dataset3_key: "kg2c_normalized"
        output_key: "three_way_stats"
  
  # Export unified dataset
  - name: export_unified
    action:
      type: EXPORT_DATASET
      params:
        dataset_key: "unified_proteins"
        output_path: "${parameters.output_dir}/unified_proteins.tsv"
```

## Metadata Requirements

Each strategy must include comprehensive metadata:

```yaml
metadata:
  # Required fields
  id: "prot_arv_to_kg2c_uniprot_v1_base"
  name: "Arivale Proteins to KG2c via UniProt"
  version: "1.0.0"
  created: "2025-01-08"
  author: "biomapper-team"
  entity_type: "proteins"
  source_dataset: "arivale"
  target_dataset: "kg2c"
  bridge_type: ["uniprot"]
  
  # Quality tracking
  quality_tier: "experimental"
  validation_status: "pending"
  expected_match_rate: 0.85
  actual_match_rate: null
  
  # Data tracking
  source_files:
    - path: "/procedure/data/local_data/MAPPING_ONTOLOGIES/arivale/proteomics_metadata.tsv"
      last_updated: "2024-06-01"
      row_count: 1197
  target_files:
    - path: "/procedure/data/local_data/MAPPING_ONTOLOGIES/kg2.10.2c_ontologies/kg2c_proteins.csv"
      last_updated: "2024-10-01"
      row_count: 45000
  
  # Optional fields
  description: "Maps Arivale proteomics data to KG2c protein ontology using UniProt accessions"
  tags: ["proteomics", "uniprot", "kg2c", "arivale"]
  dependencies: []
  supersedes: null
  citation: null
```

## Testing Requirements

### Unit Tests
Create test files in `tests/unit/configs/strategies/`:

```python
# tests/unit/configs/strategies/test_protein_strategies.py

import pytest
from biomapper_client import BiomapperClient

@pytest.fixture
def client():
    return BiomapperClient()

def test_arivale_kg2c_protein_strategy_loads(client):
    """Test that strategy loads and validates correctly."""
    strategy = client.get_strategy("prot_arv_to_kg2c_uniprot_v1_base")
    assert strategy is not None
    assert strategy.metadata.entity_type == "proteins"

def test_arivale_kg2c_protein_execution(client, sample_protein_data):
    """Test strategy execution with sample data."""
    result = client.execute_strategy(
        "prot_arv_to_kg2c_uniprot_v1_base",
        parameters={"output_dir": "/tmp/test"}
    )
    assert result.success
    assert result.statistics.match_rate >= 0.80
```

### Integration Tests
```python
# tests/integration/strategies/test_protein_mapping_integration.py

def test_full_protein_pipeline(client, real_data_subset):
    """Test complete protein mapping pipeline with real data."""
    # Test each strategy in sequence
    strategies = [
        "prot_arv_to_kg2c_uniprot_v1_base",
        "prot_ukb_to_kg2c_uniprot_v1_base",
        "prot_arv_to_spoke_uniprot_v1_base"
    ]
    
    for strategy_id in strategies:
        result = client.execute_strategy(strategy_id)
        assert result.success
        assert result.statistics.entities_mapped > 0
```

## Validation Criteria

Each strategy must meet these criteria before promotion from experimental:

1. **Functionality**
   - Executes without errors on test data
   - All actions properly registered and available
   - Parameters correctly substituted

2. **Performance**
   - Match rate ≥ 80% for UniProt-based matching
   - Execution time < 60 seconds for standard datasets
   - Memory usage < 2GB for datasets up to 50K entities

3. **Data Quality**
   - Handles missing UniProt IDs gracefully
   - Correctly extracts from compound xrefs fields
   - Normalizes accessions consistently
   - Removes isoforms when specified

4. **Documentation**
   - Complete metadata section
   - Clear action descriptions
   - Test coverage ≥ 80%

## Development Workflow

1. **Create Strategy File**
   ```bash
   touch configs/strategies/experimental/prot_arv_to_kg2c_uniprot_v1_base.yaml
   ```

2. **Add Metadata and Parameters**
   - Copy template from this document
   - Update paths and descriptions
   - Set quality_tier: "experimental"

3. **Define Action Steps**
   - Follow sequences provided above
   - Ensure all actions are implemented
   - Use proper parameter substitution

4. **Write Tests**
   ```bash
   # Create test file
   touch tests/unit/configs/strategies/test_protein_strategies.py
   
   # Run tests
   poetry run pytest tests/unit/configs/strategies/test_protein_strategies.py -xvs
   ```

5. **Validate with Sample Data**
   ```python
   from biomapper_client import BiomapperClient
   
   client = BiomapperClient()
   result = client.execute_strategy(
       "prot_arv_to_kg2c_uniprot_v1_base",
       parameters={"output_dir": "/tmp/validation"}
   )
   print(f"Match rate: {result.statistics.match_rate}")
   ```

6. **Document Results**
   - Update actual_match_rate in metadata
   - Document any issues or limitations
   - Create PR for review

## Common Issues and Solutions

### Issue: Low Match Rates
**Solution**: Check if xrefs extraction is working correctly. May need to adjust PROTEIN_EXTRACT_UNIPROT_FROM_XREFS parameters.

### Issue: Memory Errors with Large Datasets
**Solution**: Implement chunking in PROTEIN_MULTI_BRIDGE action using CHUNK_PROCESSOR utility.

### Issue: Inconsistent Accession Formats
**Solution**: Ensure PROTEIN_NORMALIZE_ACCESSIONS handles all format variations (isoforms, versions, case).

## Parallel Development

These strategies can be developed in parallel by different team members:

- **Developer 1**: Strategies 1-2 (Arivale mappings)
- **Developer 2**: Strategies 3-4 (UKBB mappings)
- **Developer 3**: Strategies 5-6 (SPOKE and multi-source)

Coordinate on shared action development (PROTEIN_EXTRACT_UNIPROT_FROM_XREFS, etc.).

## Quality Checklist

Before submitting strategy for review:

- [ ] Strategy follows naming convention
- [ ] All metadata fields completed
- [ ] Action sequence tested with sample data
- [ ] Match rate meets expectations (≥80%)
- [ ] Unit tests written and passing
- [ ] Integration test with real data subset
- [ ] Documentation in strategy file
- [ ] No hardcoded paths (use parameters)
- [ ] Error handling for missing data
- [ ] Performance benchmarks recorded

## Next Steps

After protein strategies are implemented:
1. Promote validated strategies to production/
2. Create enhanced variants (fuzzy, strict)
3. Develop cross-entity strategies (protein-gene mapping)
4. Create visualization and reporting strategies