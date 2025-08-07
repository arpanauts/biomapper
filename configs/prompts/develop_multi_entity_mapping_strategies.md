# Develop Multi-Entity Mapping Strategies

## Overview

This prompt guides the development of advanced multi-entity mapping strategies for biomapper. These strategies combine proteins, metabolites, and chemistry tests in complex workflows for comprehensive multi-omics analysis and cross-entity harmonization.

## Prerequisites

Before developing these strategies, ensure all entity-specific actions are implemented:

**Protein Actions:**
- `PROTEIN_EXTRACT_UNIPROT_FROM_XREFS`
- `PROTEIN_NORMALIZE_ACCESSIONS`
- `PROTEIN_MULTI_BRIDGE`

**Metabolite Actions:**
- `METABOLITE_EXTRACT_IDENTIFIERS`
- `METABOLITE_NORMALIZE_HMDB`
- `METABOLITE_CTS_BRIDGE`
- `NIGHTINGALE_NMR_MATCH`

**Chemistry Actions:**
- `CHEMISTRY_EXTRACT_LOINC`
- `CHEMISTRY_FUZZY_TEST_MATCH`
- `CHEMISTRY_VENDOR_HARMONIZATION`

**Cross-Entity Actions:**
- `SEMANTIC_METABOLITE_MATCH`
- `CALCULATE_THREE_WAY_OVERLAP`
- `GENERATE_METABOLOMICS_REPORT`

## Strategy Naming Convention

For multi-entity strategies:
```
multi_[sources]_to_[target]_[analysis_type]_v1_[variant].yaml
```

## Complex Multi-Entity Strategies

### 1. Comprehensive Multi-Omics Harmonization
**File**: `configs/strategies/experimental/multi_arv_ukb_isr_comprehensive_v1_advanced.yaml`
**Purpose**: Complete harmonization of proteins, metabolites, and chemistry across all sources
**Source Files**: All Arivale, UKBB, and Israeli10k datasets

**Action Sequence**:
```yaml
metadata:
  id: "multi_arv_ukb_isr_comprehensive_v1_advanced"
  name: "Comprehensive Multi-Omics Harmonization"
  version: "1.0.0"
  created: "2025-01-08"
  author: "biomapper-team"
  entity_type: ["proteins", "metabolites", "chemistry"]
  source_dataset: ["arivale", "ukbb", "israeli10k"]
  target_dataset: "unified"
  bridge_type: ["uniprot", "hmdb", "loinc", "semantic"]
  
  quality_tier: "experimental"
  validation_status: "pending"
  expected_match_rate: 0.65  # Lower for multi-entity
  
  source_files:
    # Arivale
    - path: "/procedure/data/local_data/MAPPING_ONTOLOGIES/arivale/proteomics_metadata.tsv"
      entity: "proteins"
    - path: "/procedure/data/local_data/MAPPING_ONTOLOGIES/arivale/metabolomics_metadata.tsv"
      entity: "metabolites"
    - path: "/procedure/data/local_data/MAPPING_ONTOLOGIES/arivale/chemistries_metadata.tsv"
      entity: "chemistry"
    # UKBB
    - path: "/procedure/data/local_data/MAPPING_ONTOLOGIES/ukbb/UKBB_Protein_Meta.tsv"
      entity: "proteins"
    - path: "/procedure/data/local_data/MAPPING_ONTOLOGIES/ukbb/UKBB_NMR_Meta.tsv"
      entity: "metabolites"
    # Israeli10k
    - path: "/procedure/data/local_data/MAPPING_ONTOLOGIES/israeli10k/israeli10k_metabolomics_metadata.csv"
      entity: "metabolites"
    - path: "/procedure/data/local_data/MAPPING_ONTOLOGIES/israeli10k/israeli10k_lipidomics_metadata.csv"
      entity: "metabolites"
    - path: "/procedure/data/local_data/MAPPING_ONTOLOGIES/israeli10k/israeli10k_chemistries_metadata.csv"
      entity: "chemistry"

parameters:
  output_dir: "${OUTPUT_DIR:-/tmp/biomapper/outputs}"
  enable_semantic_matching: true
  cross_entity_analysis: true
  generate_report: true

steps:
  # === PROTEIN PROCESSING ===
  - name: load_arivale_proteins
    action:
      type: LOAD_DATASET_IDENTIFIERS
      params:
        file_path: "${metadata.source_files[0].path}"
        identifier_column: "uniprot"
        output_key: "arv_proteins_raw"
  
  - name: load_ukbb_proteins
    action:
      type: LOAD_DATASET_IDENTIFIERS
      params:
        file_path: "${metadata.source_files[3].path}"
        identifier_column: "uniprot"
        output_key: "ukb_proteins_raw"
  
  - name: normalize_all_proteins
    action:
      type: PROTEIN_NORMALIZE_ACCESSIONS
      params:
        input_keys: ["arv_proteins_raw", "ukb_proteins_raw"]
        output_key: "proteins_normalized"
  
  # === METABOLITE PROCESSING ===
  - name: load_arivale_metabolites
    action:
      type: LOAD_DATASET_IDENTIFIERS
      params:
        file_path: "${metadata.source_files[1].path}"
        identifier_column: "metabolite_id"
        output_key: "arv_metabolites_raw"
  
  - name: load_ukbb_nmr
    action:
      type: LOAD_DATASET_IDENTIFIERS
      params:
        file_path: "${metadata.source_files[4].path}"
        identifier_column: "biomarker"
        output_key: "ukb_nmr_raw"
  
  - name: load_israeli10k_metabolites
    action:
      type: LOAD_DATASET_IDENTIFIERS
      params:
        file_path: "${metadata.source_files[5].path}"
        identifier_column: "hmdb_id"
        output_key: "isr_metab_raw"
  
  - name: load_israeli10k_lipids
    action:
      type: LOAD_DATASET_IDENTIFIERS
      params:
        file_path: "${metadata.source_files[6].path}"
        identifier_column: "lipid_id"
        output_key: "isr_lipid_raw"
  
  - name: extract_all_metabolite_ids
    action:
      type: METABOLITE_EXTRACT_IDENTIFIERS
      params:
        input_keys: ["arv_metabolites_raw", "ukb_nmr_raw", "isr_metab_raw", "isr_lipid_raw"]
        extract_hmdb: true
        extract_inchikey: true
        output_key: "metabolites_extracted"
  
  - name: nightingale_process_ukbb
    action:
      type: NIGHTINGALE_NMR_MATCH
      params:
        input_key: "ukb_nmr_raw"
        biomarker_column: "biomarker"
        output_key: "ukb_nmr_matched"
  
  - name: normalize_all_metabolites
    action:
      type: METABOLITE_NORMALIZE_HMDB
      params:
        input_keys: ["metabolites_extracted", "ukb_nmr_matched"]
        output_key: "metabolites_normalized"
  
  # === CHEMISTRY PROCESSING ===
  - name: load_arivale_chemistry
    action:
      type: LOAD_DATASET_IDENTIFIERS
      params:
        file_path: "${metadata.source_files[2].path}"
        identifier_column: "test_name"
        output_key: "arv_chemistry_raw"
  
  - name: load_israeli10k_chemistry
    action:
      type: LOAD_DATASET_IDENTIFIERS
      params:
        file_path: "${metadata.source_files[7].path}"
        identifier_column: "test_id"
        output_key: "isr_chemistry_raw"
  
  - name: extract_all_loinc
    action:
      type: CHEMISTRY_EXTRACT_LOINC
      params:
        input_keys: ["arv_chemistry_raw", "isr_chemistry_raw"]
        output_key: "chemistry_loinc"
  
  - name: harmonize_chemistry_vendors
    action:
      type: CHEMISTRY_VENDOR_HARMONIZATION
      params:
        input_key: "chemistry_loinc"
        vendors: ["arivale", "israeli10k"]
        output_key: "chemistry_harmonized"
  
  # === CROSS-ENTITY INTEGRATION ===
  - name: merge_all_entities
    action:
      type: MERGE_DATASETS
      params:
        dataset_keys:
          - "proteins_normalized"
          - "metabolites_normalized"
          - "chemistry_harmonized"
        merge_strategy: "entity_aware"
        maintain_entity_types: true
        output_key: "multi_omics_merged"
  
  - name: calculate_entity_overlaps
    action:
      type: CALCULATE_THREE_WAY_OVERLAP
      params:
        dataset1_key: "proteins_normalized"
        dataset2_key: "metabolites_normalized"
        dataset3_key: "chemistry_harmonized"
        output_key: "entity_overlap_stats"
  
  - name: semantic_cross_entity_matching
    action:
      type: SEMANTIC_METABOLITE_MATCH
      params:
        source_key: "multi_omics_merged"
        enable_cross_entity: true
        model: "biobert"
        context: "multi_omics"
        output_key: "semantic_enhanced"
  
  - name: generate_comprehensive_report
    action:
      type: GENERATE_METABOLOMICS_REPORT
      params:
        dataset_key: "semantic_enhanced"
        report_type: "multi_omics"
        include_statistics: true
        include_visualizations: true
        include_entity_breakdown: true
        output_path: "${parameters.output_dir}/multi_omics_report.html"
  
  - name: export_unified_dataset
    action:
      type: EXPORT_DATASET
      params:
        dataset_key: "semantic_enhanced"
        output_path: "${parameters.output_dir}/unified_multi_omics.tsv"
        include_metadata: true
        partition_by_entity: true
```

### 2. Protein-Metabolite Pathway Analysis
**File**: `configs/strategies/experimental/multi_prot_met_pathway_analysis_v1_base.yaml`
**Purpose**: Analyze protein-metabolite relationships for pathway enrichment
**Focus**: Integration of proteins and metabolites for biological pathway analysis

**Action Sequence**:
```yaml
steps:
  # Load proteins and metabolites
  # ... (similar loading steps)
  
  - name: protein_metabolite_association
    action:
      type: PROTEIN_METABOLITE_ASSOCIATION
      params:
        protein_key: "proteins_normalized"
        metabolite_key: "metabolites_normalized"
        association_database: "string_db"
        min_confidence: 0.7
        output_key: "protein_metabolite_pairs"
  
  - name: pathway_enrichment
    action:
      type: PATHWAY_ENRICHMENT_ANALYSIS
      params:
        input_key: "protein_metabolite_pairs"
        pathway_database: "kegg"
        enrichment_method: "hypergeometric"
        fdr_threshold: 0.05
        output_key: "enriched_pathways"
  
  - name: generate_pathway_report
    action:
      type: GENERATE_PATHWAY_REPORT
      params:
        dataset_key: "enriched_pathways"
        include_visualizations: true
        output_path: "${parameters.output_dir}/pathway_analysis.html"
```

### 3. Clinical Chemistry to Metabolomics Bridge
**File**: `configs/strategies/experimental/multi_chem_met_clinical_bridge_v1_experimental.yaml`
**Purpose**: Bridge clinical chemistry tests with metabolomics data
**Focus**: Connect routine clinical labs with detailed metabolomics

**Action Sequence**:
```yaml
steps:
  # Load chemistry and metabolites
  # ... (loading steps)
  
  - name: chemistry_metabolite_mapping
    action:
      type: CHEMISTRY_METABOLITE_BRIDGE
      params:
        chemistry_key: "chemistry_harmonized"
        metabolite_key: "metabolites_normalized"
        mapping_rules:
          glucose: ["glucose", "glucose-6-phosphate"]
          cholesterol: ["cholesterol", "LDL", "HDL", "VLDL"]
          triglycerides: ["triglycerides", "fatty acids"]
        output_key: "chem_met_bridge"
  
  - name: clinical_correlation_analysis
    action:
      type: CLINICAL_CORRELATION_ANALYSIS
      params:
        input_key: "chem_met_bridge"
        correlation_method: "spearman"
        min_correlation: 0.6
        output_key: "clinical_correlations"
  
  - name: generate_clinical_report
    action:
      type: GENERATE_CLINICAL_REPORT
      params:
        dataset_key: "clinical_correlations"
        include_clinical_relevance: true
        output_path: "${parameters.output_dir}/clinical_bridge_report.html"
```

### 4. Longitudinal Multi-Omics Tracking
**File**: `configs/strategies/experimental/multi_longitudinal_tracking_v1_advanced.yaml`
**Purpose**: Track changes in multi-omics data over time
**Focus**: Temporal analysis of proteins, metabolites, and chemistry

**Action Sequence**:
```yaml
parameters:
  timepoints: ["baseline", "3_months", "6_months", "12_months"]
  
steps:
  # Load data for each timepoint
  - name: load_timepoint_data
    action:
      type: LOAD_LONGITUDINAL_DATA
      params:
        timepoints: "${parameters.timepoints}"
        entity_types: ["proteins", "metabolites", "chemistry"]
        output_key: "longitudinal_data"
  
  - name: temporal_alignment
    action:
      type: TEMPORAL_ALIGNMENT
      params:
        input_key: "longitudinal_data"
        alignment_method: "subject_id"
        handle_missing: "interpolate"
        output_key: "aligned_data"
  
  - name: change_detection
    action:
      type: LONGITUDINAL_CHANGE_DETECTION
      params:
        input_key: "aligned_data"
        change_threshold: 1.5  # fold change
        statistical_test: "paired_t_test"
        fdr_correction: true
        output_key: "significant_changes"
  
  - name: trajectory_clustering
    action:
      type: TRAJECTORY_CLUSTERING
      params:
        input_key: "significant_changes"
        clustering_method: "kmeans"
        n_clusters: 5
        output_key: "trajectory_clusters"
  
  - name: generate_longitudinal_report
    action:
      type: GENERATE_LONGITUDINAL_REPORT
      params:
        dataset_key: "trajectory_clusters"
        include_trajectories: true
        include_heatmaps: true
        output_path: "${parameters.output_dir}/longitudinal_report.html"
```

### 5. Disease-Specific Multi-Omics Integration
**File**: `configs/strategies/experimental/multi_disease_integration_v1_specialized.yaml`
**Purpose**: Integrate multi-omics data for specific disease analysis
**Focus**: Disease biomarker discovery across entity types

**Action Sequence**:
```yaml
parameters:
  disease_focus: "type_2_diabetes"
  control_group: "healthy_controls"
  
steps:
  # Load case and control data
  - name: load_disease_data
    action:
      type: LOAD_DISEASE_COHORT_DATA
      params:
        disease: "${parameters.disease_focus}"
        controls: "${parameters.control_group}"
        entity_types: ["proteins", "metabolites", "chemistry"]
        output_key: "disease_cohort_data"
  
  - name: differential_analysis
    action:
      type: MULTI_OMICS_DIFFERENTIAL_ANALYSIS
      params:
        input_key: "disease_cohort_data"
        comparison: "disease_vs_control"
        statistical_methods:
          proteins: "limma"
          metabolites: "metaboanalyst"
          chemistry: "mann_whitney"
        output_key: "differential_results"
  
  - name: biomarker_selection
    action:
      type: BIOMARKER_SELECTION
      params:
        input_key: "differential_results"
        selection_method: "random_forest"
        cross_validation_folds: 5
        max_features: 50
        output_key: "selected_biomarkers"
  
  - name: biomarker_validation
    action:
      type: BIOMARKER_VALIDATION
      params:
        input_key: "selected_biomarkers"
        validation_cohort: "independent_cohort"
        performance_metrics: ["auc", "sensitivity", "specificity"]
        output_key: "validated_biomarkers"
  
  - name: generate_disease_report
    action:
      type: GENERATE_DISEASE_REPORT
      params:
        dataset_key: "validated_biomarkers"
        disease: "${parameters.disease_focus}"
        include_roc_curves: true
        include_biomarker_panels: true
        output_path: "${parameters.output_dir}/disease_biomarkers.html"
```

## Advanced Features for Multi-Entity Strategies

### Cross-Entity Correlation Matrix
```yaml
- name: cross_entity_correlation
  action:
    type: CROSS_ENTITY_CORRELATION
    params:
      entities:
        proteins: "proteins_normalized"
        metabolites: "metabolites_normalized"
        chemistry: "chemistry_harmonized"
      correlation_method: "spearman"
      min_correlation: 0.5
      adjust_for_covariates: ["age", "sex", "bmi"]
      output_key: "correlation_matrix"
```

### Network Analysis
```yaml
- name: multi_omics_network
  action:
    type: BUILD_MULTI_OMICS_NETWORK
    params:
      nodes:
        proteins: "proteins_normalized"
        metabolites: "metabolites_normalized"
        chemistry: "chemistry_harmonized"
      edges:
        protein_protein: "string_db"
        metabolite_metabolite: "metaboanalyst"
        cross_entity: "correlation_based"
      network_metrics: ["centrality", "clustering", "modules"]
      output_key: "omics_network"
```

### Machine Learning Integration
```yaml
- name: ml_integration
  action:
    type: MULTI_OMICS_ML_PIPELINE
    params:
      features: "multi_omics_merged"
      target: "clinical_outcome"
      models:
        - "random_forest"
        - "xgboost"
        - "neural_network"
      feature_selection: "recursive_elimination"
      cross_validation: "stratified_kfold"
      output_key: "ml_predictions"
```

## Testing Multi-Entity Strategies

### Unit Tests
```python
# tests/unit/configs/strategies/test_multi_entity_strategies.py

import pytest
from biomapper_client import BiomapperClient

@pytest.fixture
def client():
    return BiomapperClient()

def test_multi_omics_strategy_loads(client):
    """Test multi-omics strategy loads correctly."""
    strategy = client.get_strategy("multi_arv_ukb_isr_comprehensive_v1_advanced")
    assert strategy is not None
    assert len(strategy.metadata.entity_type) == 3

def test_entity_integration(client, sample_multi_omics_data):
    """Test integration across entity types."""
    result = client.execute_strategy(
        "multi_arv_ukb_isr_comprehensive_v1_advanced",
        parameters={"cross_entity_analysis": True}
    )
    assert result.success
    assert result.statistics.entities_integrated == 3

def test_pathway_enrichment(client, protein_metabolite_data):
    """Test pathway enrichment analysis."""
    result = client.execute_strategy(
        "multi_prot_met_pathway_analysis_v1_base"
    )
    assert result.success
    assert len(result.enriched_pathways) > 0
```

### Integration Tests
```python
# tests/integration/strategies/test_multi_entity_integration.py

def test_full_multi_omics_pipeline(client, real_multi_omics_data):
    """Test complete multi-omics integration pipeline."""
    result = client.execute_strategy(
        "multi_arv_ukb_isr_comprehensive_v1_advanced"
    )
    assert result.success
    assert result.statistics.total_entities > 0
    assert result.report_generated

def test_longitudinal_tracking(client, longitudinal_data):
    """Test longitudinal multi-omics tracking."""
    result = client.execute_strategy(
        "multi_longitudinal_tracking_v1_advanced",
        parameters={"timepoints": ["t0", "t1", "t2"]}
    )
    assert result.success
    assert result.statistics.trajectories_identified > 0
```

## Validation Criteria for Multi-Entity Strategies

1. **Data Integration Quality**
   - Entity alignment correct
   - No data loss during merging
   - Metadata preserved

2. **Cross-Entity Analysis**
   - Correlations computed correctly
   - Network connections valid
   - Pathway enrichment significant

3. **Performance Metrics**
   - Execution time < 5 minutes for standard datasets
   - Memory usage < 4GB
   - Parallel processing utilized

4. **Statistical Validity**
   - Multiple testing correction applied
   - Appropriate statistical tests used
   - Confidence intervals reported

5. **Biological Relevance**
   - Known associations recovered
   - Pathway enrichment makes biological sense
   - Biomarkers have literature support

## Common Challenges and Solutions

### Challenge: Entity Alignment
**Solution**: Use common identifiers or bridge databases (e.g., UniProt for proteins, HMDB for metabolites).

### Challenge: Scale Differences
**Solution**: Normalize each entity type appropriately before integration (z-score, quantile normalization).

### Challenge: Missing Data
**Solution**: Implement imputation strategies appropriate for each entity type.

### Challenge: Computational Complexity
**Solution**: Use chunking, parallel processing, and efficient data structures.

### Challenge: Biological Interpretation
**Solution**: Include pathway analysis, GO enrichment, and literature mining.

## Quality Checklist for Multi-Entity Strategies

- [ ] All entity types properly loaded
- [ ] Entity-specific normalization applied
- [ ] Cross-entity bridges implemented
- [ ] Integration preserves data integrity
- [ ] Statistical analysis appropriate
- [ ] Pathway/network analysis included
- [ ] Visualization components working
- [ ] Report generation successful
- [ ] Performance optimized
- [ ] Memory usage acceptable
- [ ] Error handling comprehensive
- [ ] Documentation complete
- [ ] Biological validation performed

## Advanced Development Topics

### 1. Graph Neural Networks
Implement GNN-based approaches for multi-omics integration:
```yaml
- name: gnn_integration
  action:
    type: GRAPH_NEURAL_NETWORK_INTEGRATION
    params:
      graph_structure: "omics_network"
      node_features: "multi_omics_features"
      architecture: "graph_attention_network"
      output_key: "gnn_embeddings"
```

### 2. Causal Inference
Add causal analysis capabilities:
```yaml
- name: causal_analysis
  action:
    type: CAUSAL_INFERENCE_ANALYSIS
    params:
      variables: "multi_omics_merged"
      method: "pc_algorithm"
      significance_level: 0.05
      output_key: "causal_network"
```

### 3. Single-Cell Integration
Extend to single-cell multi-omics:
```yaml
- name: single_cell_integration
  action:
    type: SINGLE_CELL_MULTI_OMICS
    params:
      modalities: ["scRNA-seq", "scATAC-seq", "scProteomics"]
      integration_method: "seurat_v4"
      output_key: "integrated_single_cell"
```

## Next Steps

After implementing multi-entity strategies:
1. Develop disease-specific pipelines
2. Create interactive visualization dashboards
3. Implement real-time analysis capabilities
4. Build automated interpretation systems
5. Develop clinical decision support tools
6. Create multi-omics data lakes
7. Implement federated learning approaches
8. Build API endpoints for external integration