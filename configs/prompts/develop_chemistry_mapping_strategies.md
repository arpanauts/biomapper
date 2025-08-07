# Develop Chemistry Mapping Strategies

## Overview

This prompt guides the development of 5 clinical chemistry/laboratory test mapping strategies for biomapper. These strategies map chemistry datasets between Arivale, Israeli10k, UK Biobank, and SPOKE clinical labs using LOINC codes and fuzzy test name matching.

## Prerequisites

Before developing these strategies, ensure the following actions are implemented:
1. `CHEMISTRY_EXTRACT_LOINC` - Extract LOINC codes from various formats
2. `CHEMISTRY_FUZZY_TEST_MATCH` - Fuzzy matching for test names
3. `CHEMISTRY_VENDOR_HARMONIZATION` - Handle vendor-specific variations
4. `SEMANTIC_METABOLITE_MATCH` - Semantic matching for chemistry-metabolite bridge

Use the biomapper-action-developer agent to implement these actions first if not available.

## Strategy Naming Convention

Follow the format from `/home/ubuntu/biomapper/configs/STRATEGY_ORGANIZATION_GUIDE.md`:
```
chem_[source]_to_[target]_[bridge]_v1_base.yaml
```

## Strategies to Develop

### 1. Arivale Chemistries to SPOKE Clinical Labs
**File**: `configs/strategies/experimental/chem_arv_to_spoke_loinc_v1_base.yaml`
**Purpose**: Map Arivale chemistry tests to SPOKE clinical labs via LOINC
**Source Files**:
- `/procedure/data/local_data/MAPPING_ONTOLOGIES/arivale/chemistries_metadata.tsv`
- `/procedure/data/local_data/MAPPING_ONTOLOGIES/spoke_ontologies/spoke_clinical_labs.csv`

**Action Sequence**:
```yaml
steps:
  - name: load_arivale_chemistry
    action:
      type: LOAD_DATASET_IDENTIFIERS
      params:
        file_path: "${metadata.source_files[0].path}"
        identifier_column: "test_name"
        output_key: "arivale_chemistry_raw"
  
  - name: load_spoke_labs
    action:
      type: LOAD_DATASET_IDENTIFIERS
      params:
        file_path: "${metadata.target_files[0].path}"
        identifier_column: "loinc_code"
        output_key: "spoke_labs_raw"
  
  - name: extract_arivale_loinc
    action:
      type: CHEMISTRY_EXTRACT_LOINC
      params:
        input_key: "arivale_chemistry_raw"
        test_name_column: "test_name"
        loinc_column: "loinc_code"
        vendor: "arivale"
        output_key: "arivale_chemistry"
  
  - name: extract_spoke_loinc
    action:
      type: CHEMISTRY_EXTRACT_LOINC
      params:
        input_key: "spoke_labs_raw"
        loinc_column: "loinc_code"
        validate_format: true
        output_key: "spoke_labs"
  
  - name: filter_valid_loinc
    action:
      type: FILTER_DATASET
      params:
        input_key: "spoke_labs"
        filter_criteria:
          has_valid_loinc: true
          loinc_pattern: "^\\d{1,5}-\\d$"
        output_key: "spoke_filtered"
  
  - name: fuzzy_test_match
    action:
      type: CHEMISTRY_FUZZY_TEST_MATCH
      params:
        source_key: "arivale_chemistry"
        target_key: "spoke_filtered"
        test_name_column: "test_name"
        match_threshold: 0.85
        use_synonyms: true
        synonym_file: "/procedure/data/local_data/references/lab_test_synonyms.csv"
        output_key: "fuzzy_matched"
  
  - name: calculate_overlap
    action:
      type: CALCULATE_SET_OVERLAP
      params:
        dataset1_key: "arivale_chemistry"
        dataset2_key: "spoke_filtered"
        output_key: "overlap_statistics"
  
  - name: export_mapping
    action:
      type: EXPORT_DATASET
      params:
        dataset_key: "fuzzy_matched"
        output_path: "${parameters.output_dir}/arivale_spoke_chemistry.tsv"
```

### 2. Israeli10k Chemistries to SPOKE Clinical Labs
**File**: `configs/strategies/experimental/chem_isr_to_spoke_loinc_v1_base.yaml`
**Purpose**: Map Israeli10k chemistry tests to SPOKE with vendor harmonization
**Source Files**:
- `/procedure/data/local_data/MAPPING_ONTOLOGIES/israeli10k/israeli10k_chemistries_metadata.csv`
- `/procedure/data/local_data/MAPPING_ONTOLOGIES/spoke_ontologies/spoke_clinical_labs.csv`

**Action Sequence**:
```yaml
steps:
  - name: load_israeli10k_chemistry
    action:
      type: LOAD_DATASET_IDENTIFIERS
      params:
        file_path: "${metadata.source_files[0].path}"
        identifier_column: "test_id"
        output_key: "israeli10k_chemistry_raw"
  
  - name: load_spoke_labs
    # ... (as above)
  
  - name: extract_israeli10k_loinc
    action:
      type: CHEMISTRY_EXTRACT_LOINC
      params:
        input_key: "israeli10k_chemistry_raw"
        test_id_column: "test_id"
        test_name_column: "test_name_hebrew"
        vendor: "israeli10k"
        translate_hebrew: true
        output_key: "israeli10k_chemistry"
  
  - name: extract_spoke_loinc
    # ... (as above)
  
  - name: vendor_harmonization
    action:
      type: CHEMISTRY_VENDOR_HARMONIZATION
      params:
        input_key: "israeli10k_chemistry"
        vendor: "israeli10k"
        harmonization_rules:
          glucose: ["glucose", "blood sugar", "GLU"]
          cholesterol: ["cholesterol", "CHOL", "total cholesterol"]
          hemoglobin: ["hemoglobin", "HGB", "Hb"]
        output_key: "israeli10k_harmonized"
  
  - name: fuzzy_test_match
    action:
      type: CHEMISTRY_FUZZY_TEST_MATCH
      params:
        source_key: "israeli10k_harmonized"
        target_key: "spoke_filtered"
        test_name_column: "harmonized_name"
        match_threshold: 0.80  # Lower threshold for cross-vendor
        use_abbreviations: true
        output_key: "fuzzy_matched"
  
  - name: calculate_overlap
    # ... (as above)
  
  - name: export_mapping
    # ... (as above)
```

### 3. Israeli10k Metabolomics to SPOKE Clinical Labs (Semantic Bridge)
**File**: `configs/strategies/experimental/chem_isr_metab_to_spoke_semantic_v1_experimental.yaml`
**Purpose**: Bridge metabolomics to clinical labs using semantic matching
**Source Files**:
- `/procedure/data/local_data/MAPPING_ONTOLOGIES/israeli10k/israeli10k_metabolomics_metadata.csv`
- `/procedure/data/local_data/MAPPING_ONTOLOGIES/spoke_ontologies/spoke_clinical_labs.csv`

**Action Sequence**:
```yaml
steps:
  - name: load_israeli10k_metabolomics
    action:
      type: LOAD_DATASET_IDENTIFIERS
      params:
        file_path: "${metadata.source_files[0].path}"
        identifier_column: "metabolite_name"
        output_key: "israeli10k_metabolites"
  
  - name: load_spoke_labs
    # ... (as above)
  
  - name: extract_chemistry_related
    action:
      type: CHEMISTRY_EXTRACT_LOINC
      params:
        input_key: "spoke_labs_raw"
        filter_chemistry_related: true
        chemistry_categories:
          - "glucose metabolism"
          - "lipid panel"
          - "amino acids"
        output_key: "chemistry_labs"
  
  - name: fuzzy_metabolite_match
    action:
      type: CHEMISTRY_FUZZY_TEST_MATCH
      params:
        source_key: "israeli10k_metabolites"
        target_key: "chemistry_labs"
        metabolite_to_test_mapping: true
        mapping_rules:
          glucose: ["glucose", "blood sugar"]
          cholesterol: ["total cholesterol", "LDL", "HDL"]
          triglycerides: ["triglycerides", "TG"]
        output_key: "metabolite_chemistry_fuzzy"
  
  - name: semantic_bridge
    action:
      type: SEMANTIC_METABOLITE_MATCH
      params:
        source_key: "metabolite_chemistry_fuzzy"
        target_key: "chemistry_labs"
        model: "biobert"
        context: "clinical_chemistry"
        threshold: 0.75
        output_key: "semantic_matched"
  
  - name: calculate_overlap
    # ... (as above)
  
  - name: export_mapping
    # ... (as above)
```

### 4. UKBB NMR to SPOKE Clinical Labs
**File**: `configs/strategies/experimental/chem_ukb_nmr_to_spoke_nightingale_v1_base.yaml`
**Purpose**: Map UKBB NMR biomarkers to clinical labs via Nightingale
**Source Files**:
- `/procedure/data/local_data/MAPPING_ONTOLOGIES/ukbb/UKBB_NMR_Meta.tsv`
- `/procedure/data/local_data/MAPPING_ONTOLOGIES/spoke_ontologies/spoke_clinical_labs.csv`

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
  
  - name: load_spoke_labs
    # ... (as above)
  
  - name: extract_clinical_biomarkers
    action:
      type: CHEMISTRY_EXTRACT_LOINC
      params:
        input_key: "ukbb_nmr_raw"
        biomarker_column: "biomarker"
        filter_clinical_only: true
        clinical_markers:
          - "Total_C"
          - "LDL_C"
          - "HDL_C"
          - "Triglycerides"
          - "Glucose"
        output_key: "clinical_biomarkers"
  
  - name: nightingale_to_loinc
    action:
      type: NIGHTINGALE_NMR_MATCH
      params:
        input_key: "clinical_biomarkers"
        biomarker_column: "biomarker"
        target_format: "loinc"
        reference_file: "/procedure/data/local_data/references/nightingale_loinc_mapping.csv"
        output_key: "nightingale_loinc"
  
  - name: fuzzy_test_match
    action:
      type: CHEMISTRY_FUZZY_TEST_MATCH
      params:
        source_key: "nightingale_loinc"
        target_key: "spoke_labs"
        use_loinc_primary: true
        fallback_to_name: true
        output_key: "matched_labs"
  
  - name: calculate_overlap
    # ... (as above)
  
  - name: export_mapping
    # ... (as above)
```

### 5. Multi-Source Chemistry Harmonization
**File**: `configs/strategies/experimental/chem_multi_to_unified_loinc_v1_comprehensive.yaml`
**Purpose**: Harmonize chemistry tests from multiple sources
**Source Files**:
- `/procedure/data/local_data/MAPPING_ONTOLOGIES/arivale/chemistries_metadata.tsv`
- `/procedure/data/local_data/MAPPING_ONTOLOGIES/ukbb/UKBB_NMR_Meta.tsv`
- `/procedure/data/local_data/MAPPING_ONTOLOGIES/israeli10k/israeli10k_chemistries_metadata.csv`

**Action Sequence**:
```yaml
steps:
  # Load all three sources
  - name: load_arivale
    action:
      type: LOAD_DATASET_IDENTIFIERS
      params:
        file_path: "${metadata.source_files[0].path}"
        identifier_column: "test_name"
        output_key: "arivale_raw"
  
  - name: load_ukbb
    action:
      type: LOAD_DATASET_IDENTIFIERS
      params:
        file_path: "${metadata.source_files[1].path}"
        identifier_column: "biomarker"
        output_key: "ukbb_raw"
  
  - name: load_israeli10k
    action:
      type: LOAD_DATASET_IDENTIFIERS
      params:
        file_path: "${metadata.source_files[2].path}"
        identifier_column: "test_id"
        output_key: "israeli10k_raw"
  
  # Extract LOINC from each source
  - name: extract_arivale_loinc
    action:
      type: CHEMISTRY_EXTRACT_LOINC
      params:
        input_key: "arivale_raw"
        vendor: "arivale"
        output_key: "arivale_loinc"
  
  - name: extract_ukbb_loinc
    action:
      type: CHEMISTRY_EXTRACT_LOINC
      params:
        input_key: "ukbb_raw"
        vendor: "ukbb_nmr"
        use_nightingale_mapping: true
        output_key: "ukbb_loinc"
  
  - name: extract_israeli10k_loinc
    action:
      type: CHEMISTRY_EXTRACT_LOINC
      params:
        input_key: "israeli10k_raw"
        vendor: "israeli10k"
        output_key: "israeli10k_loinc"
  
  # Vendor harmonization for each
  - name: harmonize_arivale
    action:
      type: CHEMISTRY_VENDOR_HARMONIZATION
      params:
        input_key: "arivale_loinc"
        vendor: "arivale"
        output_key: "arivale_harmonized"
  
  - name: harmonize_ukbb
    action:
      type: CHEMISTRY_VENDOR_HARMONIZATION
      params:
        input_key: "ukbb_loinc"
        vendor: "ukbb"
        output_key: "ukbb_harmonized"
  
  - name: harmonize_israeli10k
    action:
      type: CHEMISTRY_VENDOR_HARMONIZATION
      params:
        input_key: "israeli10k_loinc"
        vendor: "israeli10k"
        output_key: "israeli10k_harmonized"
  
  # Cross-vendor fuzzy matching
  - name: cross_vendor_fuzzy
    action:
      type: CHEMISTRY_FUZZY_TEST_MATCH
      params:
        source_datasets:
          - "arivale_harmonized"
          - "ukbb_harmonized"
          - "israeli10k_harmonized"
        cross_match: true
        match_threshold: 0.75
        output_key: "cross_matched"
  
  # Merge all datasets
  - name: merge_datasets
    action:
      type: MERGE_DATASETS
      params:
        dataset_keys:
          - "arivale_harmonized"
          - "ukbb_harmonized"
          - "israeli10k_harmonized"
        merge_strategy: "union"
        deduplicate_by: "loinc_code"
        output_key: "unified_chemistry"
  
  # Export unified dataset
  - name: export_unified
    action:
      type: EXPORT_DATASET
      params:
        dataset_key: "unified_chemistry"
        output_path: "${parameters.output_dir}/unified_chemistry_tests.tsv"
        include_source_mapping: true
```

## Metadata Requirements

Each strategy must include comprehensive metadata:

```yaml
metadata:
  # Required fields
  id: "chem_arv_to_spoke_loinc_v1_base"
  name: "Arivale Chemistry to SPOKE Labs via LOINC"
  version: "1.0.0"
  created: "2025-01-08"
  author: "biomapper-team"
  entity_type: "chemistry"
  source_dataset: "arivale"
  target_dataset: "spoke"
  bridge_type: ["loinc", "fuzzy"]
  
  # Quality tracking
  quality_tier: "experimental"
  validation_status: "pending"
  expected_match_rate: 0.70  # Lower due to vendor variations
  actual_match_rate: null
  
  # Data tracking
  source_files:
    - path: "/procedure/data/local_data/MAPPING_ONTOLOGIES/arivale/chemistries_metadata.tsv"
      last_updated: "2024-06-01"
      row_count: 89
      vendor: "arivale"
  target_files:
    - path: "/procedure/data/local_data/MAPPING_ONTOLOGIES/spoke_ontologies/spoke_clinical_labs.csv"
      last_updated: "2024-10-01"
      row_count: 15000
      standard: "loinc"
  
  # Optional fields
  description: "Maps Arivale chemistry tests to SPOKE clinical labs using LOINC codes and fuzzy name matching"
  tags: ["chemistry", "loinc", "clinical_labs", "arivale", "spoke"]
  dependencies: []
  supersedes: null
  citation: null
  
  # Chemistry-specific metadata
  test_categories:
    - "metabolic_panel"
    - "lipid_panel"
    - "complete_blood_count"
    - "liver_function"
    - "kidney_function"
```

## Special Considerations for Chemistry Tests

### 1. LOINC Code Variations
LOINC codes have specific format requirements:
- Standard format: 12345-6 (numeric with check digit)
- May be missing or incorrect in source data
- Need validation and correction

### 2. Vendor-Specific Test Names
Different vendors use different naming conventions:
- Arivale: "Glucose, Serum"
- LabCorp: "GLUCOSE"
- Quest: "Glucose (Fasting)"
- Israeli10k: May have Hebrew names

### 3. Units and Reference Ranges
Chemistry tests have unit variations:
- Glucose: mg/dL vs mmol/L
- Cholesterol: mg/dL vs mmol/L
- Need unit harmonization for comparison

### 4. Test Panel Groupings
Many tests are part of panels:
- Basic Metabolic Panel (BMP)
- Comprehensive Metabolic Panel (CMP)
- Lipid Panel
- Need to handle both individual tests and panels

### 5. Fuzzy Matching Challenges
Test names have many variations:
- Abbreviations: "GLU" vs "Glucose"
- Synonyms: "Blood Sugar" vs "Glucose"
- Modifiers: "Fasting Glucose" vs "Random Glucose"

## Testing Requirements

### Unit Tests
```python
# tests/unit/configs/strategies/test_chemistry_strategies.py

import pytest
from biomapper_client import BiomapperClient

@pytest.fixture
def client():
    return BiomapperClient()

def test_arivale_spoke_chemistry_loads(client):
    """Test strategy loads and validates."""
    strategy = client.get_strategy("chem_arv_to_spoke_loinc_v1_base")
    assert strategy is not None
    assert strategy.metadata.entity_type == "chemistry"

def test_loinc_extraction(client, sample_chemistry_data):
    """Test LOINC code extraction."""
    result = client.execute_strategy(
        "chem_arv_to_spoke_loinc_v1_base",
        parameters={"output_dir": "/tmp/test"}
    )
    assert result.success
    assert result.statistics.valid_loinc_codes > 0

def test_vendor_harmonization(client, multi_vendor_data):
    """Test cross-vendor harmonization."""
    result = client.execute_strategy(
        "chem_multi_to_unified_loinc_v1_comprehensive",
        parameters={"output_dir": "/tmp/test"}
    )
    assert result.success
    assert result.statistics.vendors_harmonized == 3

def test_fuzzy_matching_accuracy(client, test_name_variations):
    """Test fuzzy matching handles variations."""
    result = client.execute_strategy(
        "chem_isr_to_spoke_loinc_v1_base",
        parameters={"match_threshold": 0.8}
    )
    assert result.statistics.fuzzy_match_rate >= 0.65
```

### Integration Tests
```python
# tests/integration/strategies/test_chemistry_mapping_integration.py

def test_multi_source_chemistry_pipeline(client, real_chemistry_subset):
    """Test complete chemistry harmonization pipeline."""
    result = client.execute_strategy(
        "chem_multi_to_unified_loinc_v1_comprehensive"
    )
    assert result.success
    assert result.statistics.total_unique_tests > 0
    assert result.statistics.cross_vendor_matches > 0

def test_semantic_bridge_chemistry(client, metabolite_chemistry_data):
    """Test semantic bridge from metabolites to chemistry."""
    result = client.execute_strategy(
        "chem_isr_metab_to_spoke_semantic_v1_experimental"
    )
    assert result.success
    assert result.statistics.semantic_matches > 0
```

## Validation Criteria

Chemistry strategies have specific validation requirements:

1. **LOINC Validation**
   - Correct LOINC format (12345-6)
   - Valid check digits
   - Appropriate LOINC codes for test types

2. **Vendor Harmonization**
   - Consistent test name mapping
   - Unit conversion accuracy
   - Reference range alignment

3. **Fuzzy Matching Quality**
   - Handles abbreviations correctly
   - Synonym recognition works
   - Modifier handling appropriate

4. **Match Rates**
   - Direct LOINC matching: ≥ 60%
   - Fuzzy name matching: ≥ 70%
   - Combined approach: ≥ 75%
   - Semantic bridge: ≥ 40% (experimental)

## Common Issues and Solutions

### Issue: Invalid LOINC Formats
**Solution**: Implement LOINC validation and correction in CHEMISTRY_EXTRACT_LOINC.

### Issue: Hebrew/Non-English Test Names
**Solution**: Use translation service or mapping table for Israeli10k data.

### Issue: Unit Mismatches
**Solution**: Implement unit conversion in CHEMISTRY_VENDOR_HARMONIZATION.

### Issue: Panel vs Individual Tests
**Solution**: Expand panels to individual tests for matching, then re-group.

### Issue: Low Fuzzy Match Rates
**Solution**: Tune threshold, expand synonym dictionary, handle abbreviations.

## Parallel Development

Chemistry strategies can be developed by team members:

- **Developer 1**: Strategies 1-2 (LOINC-based matching)
- **Developer 2**: Strategy 3 (Semantic bridge)
- **Developer 3**: Strategies 4-5 (NMR and multi-source)

Coordinate on CHEMISTRY_VENDOR_HARMONIZATION implementation.

## Performance Optimization

### Synonym Caching
```yaml
- name: fuzzy_match_cached
  action:
    type: CHEMISTRY_FUZZY_TEST_MATCH
    params:
      cache_synonyms: true
      synonym_cache_file: "/tmp/synonym_cache.pkl"
```

### Batch Processing
```yaml
- name: batch_loinc_extraction
  action:
    type: CHEMISTRY_EXTRACT_LOINC
    params:
      batch_size: 100
      parallel_workers: 4
```

## Vendor-Specific Configurations

### Arivale
```yaml
vendor_config:
  arivale:
    test_name_column: "test_name"
    unit_column: "units"
    loinc_column: "loinc_code"
    name_format: "Test, Specimen"
```

### Israeli10k
```yaml
vendor_config:
  israeli10k:
    test_id_column: "test_id"
    hebrew_name_column: "test_name_hebrew"
    english_name_column: "test_name_english"
    requires_translation: true
```

### UKBB NMR
```yaml
vendor_config:
  ukbb_nmr:
    biomarker_column: "biomarker"
    uses_nightingale: true
    clinical_subset: ["Total_C", "LDL_C", "HDL_C", "Triglycerides"]
```

## Quality Checklist

Before submitting chemistry strategy:

- [ ] Strategy follows naming convention
- [ ] LOINC extraction validated
- [ ] Vendor harmonization tested
- [ ] Fuzzy matching tuned
- [ ] Unit handling correct
- [ ] Panel expansion works
- [ ] Match rates documented
- [ ] Synonym dictionary updated
- [ ] Translation handling (if needed)
- [ ] Unit tests comprehensive
- [ ] Integration test with real data
- [ ] Performance acceptable
- [ ] Documentation complete

## Next Steps

After chemistry strategies are implemented:
1. Expand synonym dictionaries
2. Improve vendor harmonization rules
3. Develop panel-aware strategies
4. Create reference range normalization
5. Build longitudinal test tracking strategies