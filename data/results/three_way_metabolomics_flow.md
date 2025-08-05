# Three-Way Metabolomics Mapping Strategy Flow

This flowchart visualizes the strategy defined in `/home/ubuntu/biomapper/configs/three_way_metabolomics_mapping_strategy.yaml` for harmonizing metabolomics data across Israeli10K, UKBB, and Arivale cohorts.

## Key Insight
Israeli10K and UKBB both use the Nightingale NMR platform, providing a strong bridge for direct mapping. Arivale uses a different system but has rich identifier metadata (HMDB, KEGG, PubChem).

## Strategy Flow

```mermaid
flowchart TD
    %% Data Loading Phase
    subgraph "Phase 1: Data Loading"
        LOAD1["LOAD_DATASET_IDENTIFIERS<br/>file: israeli10k_metabolomics_metadata.csv<br/>id_column: tabular_field_name<br/>output_key: israeli10k_data"]
        LOAD2["LOAD_DATASET_IDENTIFIERS<br/>file: UKBB_NMR_Meta.tsv<br/>id_column: title<br/>output_key: ukbb_data"]
        LOAD3["LOAD_DATASET_IDENTIFIERS<br/>file: metabolomics_metadata.tsv<br/>id_column: BIOCHEMICAL_NAME<br/>output_key: arivale_data"]
    end

    %% Nightingale Platform Matching
    subgraph "Phase 2: Nightingale Platform Harmonization"
        NM["NIGHTINGALE_NMR_MATCH<br/>source_key: israeli10k_data<br/>target_key: ukbb_data<br/>threshold: 0.95<br/>output_key: nightingale_matches"]
        LOAD1 --> NM
        LOAD2 --> NM
        BUILD["BUILD_NIGHTINGALE_REFERENCE<br/>matched_pairs: nightingale_matches<br/>output_key: nightingale_reference<br/>export_csv: true"]
        NM --> BUILD
        NM --> UNMATCHED1[Israeli10K Unmatched<br/>452 metabolites]
        NM --> UNMATCHED2[UKBB Unmatched<br/>200 metabolites]
    end

    %% Arivale Tiered Matching
    subgraph "Phase 3: Progressive Enhancement"
        %% Tier 1: Direct Name
        LOAD3 --> BASELINE["BASELINE_FUZZY_MATCH<br/>source_key: arivale_data<br/>target_key: nightingale_reference<br/>source_col: BIOCHEMICAL_NAME<br/>target_col: unified_name<br/>threshold: 0.85"]
        BUILD --> BASELINE
        BASELINE --> MATCHED1[Baseline Matches<br/>~45 percent - 61 metabolites]
        BASELINE --> UNMATCH1[unmatched.baseline.arivale_data<br/>1,237 metabolites]
        
        %% Tier 2: API Enrichment
        UNMATCH1 --> API["CTS_ENRICHED_MATCH<br/>unmatched_key: unmatched.baseline<br/>APIs: CTS, HMDB, PubChem<br/>threshold: 0.80<br/>batch_size: 50"]
        BUILD --> API
        API --> MATCHED2[API Matches<br/>+15 percent - 129 metabolites]
        API --> UNMATCH2[unmatched.api.arivale_data<br/>1,108 metabolites]
        
        %% Tier 3: Semantic/LLM
        UNMATCH2 --> SEMANTIC["SEMANTIC_METABOLITE_MATCH<br/>unmatched_key: unmatched.api<br/>embedding_model: text-ada-002<br/>llm_model: gpt-4<br/>threshold: 0.75"]
        BUILD --> SEMANTIC
        SEMANTIC --> MATCHED3[Semantic Matches<br/>+10 percent - 656 metabolites]
        SEMANTIC --> FINAL_UN[Final Unmatched<br/>452 metabolites]
    end

    %% Combination Phase
    subgraph "Phase 4: Three-Way Integration"
        COMBINE["COMBINE_METABOLITE_MATCHES<br/>nightingale_pairs: nightingale_matches<br/>arivale_tiers: [baseline, api, semantic]<br/>output_key: three_way_matches<br/>track_provenance: true"]
        BUILD --> COMBINE
        MATCHED1 --> COMBINE
        MATCHED2 --> COMBINE
        MATCHED3 --> COMBINE
        
        COMBINE --> THREE[Three-Way Combined<br/>846 total matches<br/>~245 three-way overlaps]
    end

    %% Analysis Phase
    subgraph "Phase 5: Analysis & Reporting"
        OVERLAP["CALCULATE_THREE_WAY_OVERLAP<br/>input_key: three_way_matches<br/>confidence_threshold: 0.8<br/>visualizations: [venn, heatmap, sankey]<br/>output_key: overlap_statistics"]
        THREE --> OVERLAP
        
        REPORT["GENERATE_METABOLOMICS_REPORT<br/>stats_key: overlap_statistics<br/>matches_key: three_way_matches<br/>formats: [md, html, pdf]<br/>sections: [summary, analysis, viz]"]
        OVERLAP --> REPORT
        
        REPORT --> OUTPUT[Final Outputs<br/>Reports + Visualizations<br/>CSV exports]
    end

    %% Styling with dark text
    classDef dataset fill:#e1f5fe,stroke:#01579b,stroke-width:2px,color:#000
    classDef process fill:#f3e5f5,stroke:#4a148c,stroke-width:2px,color:#000
    classDef output fill:#e8f5e9,stroke:#1b5e20,stroke-width:2px,color:#000
    classDef unmatched fill:#ffebee,stroke:#b71c1c,stroke-width:2px,color:#000
    
    class LOAD1,LOAD2,LOAD3 dataset
    class NM,BUILD,BASELINE,API,SEMANTIC,COMBINE,OVERLAP,REPORT process
    class MATCHED1,MATCHED2,MATCHED3,THREE,OUTPUT output
    class UNMATCHED1,UNMATCHED2,UNMATCH1,UNMATCH2,FINAL_UN unmatched
```

## Expected Outcomes

### Match Rates by Stage
- **Israeli10K ↔ UKBB**: ~80-90% (same platform)
- **Arivale → Nightingale**:
  - Tier 1 (Direct): ~45%
  - Tier 2 (API): +15% = 60% cumulative
  - Tier 3 (Semantic): +10% = 70% cumulative

### Three-Way Overlap
The final three-way matches represent metabolites that can be tracked across all three cohorts:
- **High Confidence** (>0.9): Direct Nightingale matches + Tier 1 Arivale
- **Medium Confidence** (0.8-0.9): API-enriched matches
- **Lower Confidence** (0.75-0.8): Semantic/LLM matches

### Key Outputs
1. **Nightingale Reference** (`nightingale_reference.csv`): Unified metabolite names for Israeli10K/UKBB
2. **Three-Way Matches** (tracked with provenance): Complete mapping across all cohorts
3. **Visualization Suite**:
   - 3-way Venn diagram showing overlap
   - Confidence heatmap by metabolite category
   - Sankey diagram showing match provenance
4. **Comprehensive Report**: Analysis of coverage, gaps, and recommendations

## Implementation Status

Currently implemented:
- ✅ Data loading (LOAD_DATASET_IDENTIFIERS)
- ✅ Nightingale matching (NIGHTINGALE_NMR_MATCH) 
- ✅ Reference building (BUILD_NIGHTINGALE_REFERENCE)
- ✅ Direct name matching (BASELINE_FUZZY_MATCH)
- ✅ API enrichment (CTS_ENRICHED_MATCH)
- ✅ Vector similarity (VECTOR_ENHANCED_MATCH)

Not yet implemented:
- ❌ METABOLITE_NAME_MATCH (can use BASELINE_FUZZY_MATCH)
- ❌ METABOLITE_API_ENRICHMENT (partial - CTS only)
- ❌ ENRICHED_METABOLITE_MATCH
- ❌ SEMANTIC_METABOLITE_MATCH (partial - vector search only)
- ❌ COMBINE_METABOLITE_MATCHES
- ❌ CALCULATE_THREE_WAY_OVERLAP
- ❌ GENERATE_METABOLOMICS_REPORT (basic version exists)

## Next Steps

To achieve full three-way mapping:
1. Run the existing progressive enhancement pipeline to validate the approach
2. Implement missing action types or adapt existing ones
3. Execute the full three-way strategy
4. Generate comprehensive overlap analysis and visualizations