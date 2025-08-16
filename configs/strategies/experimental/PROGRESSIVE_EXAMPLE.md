# Progressive Protein Mapping - Example Output

## Waterfall Progression

```
100% |
     |
 90% |                                    ┌─────── 89% FINAL
     |                              ┌─────┤ (+2%)
 80% |                    ┌─────────┤     └─ Similarity
     |          ┌─────────┤ (+5%)   └─ Ensembl  
 70% |          │ (+15%)  └─ Gene Symbol
     | ┌────────┤
 60% | │  65%   └─ Historical Resolution
     | │ Direct
 50% | │ Match
     | │
 40% | │
     |─┴────────┬─────────┬─────────┬─────────┬─────────
       Stage 1   Stage 2   Stage 3   Stage 4   Stage 5
```

## Sample Provenance Output

| Source_ID | Target_ID | Match_Method | Confidence | Stage | Details |
|-----------|-----------|--------------|------------|-------|---------|
| P12345 | P12345 | direct_uniprot_match | 1.00 | 1 | Exact match |
| P00001 | P00001 | direct_uniprot_match | 1.00 | 1 | Exact match |
| Q99999 | P88888 | uniprot_historical_api | 0.95 | 2 | Q99999 superseded by P88888 (2019) |
| O12345 | P54321 | uniprot_historical_api | 0.90 | 2 | O12345 merged into P54321 |
| P11111 | Q22222 | gene_symbol_bridge | 0.85 | 3 | Both map to gene CDK2 |
| A00001 | B00001 | ensembl_bridge | 0.80 | 4 | Both map to ENSP00000123456 |
| X99999 | Y88888 | similarity_match | 0.70 | 5 | 95% name similarity: "PROTEIN_KINASE_A" |

## Progressive Statistics Report

```json
{
  "progressive_mapping_summary": {
    "stage_1_direct": {
      "matched": 650,
      "unmatched": 350,
      "match_rate": "65.0%",
      "method": "Direct UniProt comparison",
      "computation_time": "0.5s"
    },
    "stage_2_historical": {
      "new_matches": 150,
      "cumulative_matched": 800,
      "cumulative_rate": "80.0%",
      "improvement": "+15.0%",
      "resolution_breakdown": {
        "superseded": 85,
        "secondary": 40,
        "merged": 25
      },
      "api_calls": 35,
      "computation_time": "12.3s"
    },
    "stage_3_gene_symbol": {
      "new_matches": 50,
      "cumulative_matched": 850,
      "cumulative_rate": "85.0%",
      "improvement": "+5.0%",
      "bridge_confidence_avg": 0.85,
      "computation_time": "3.2s"
    },
    "stage_4_ensembl": {
      "new_matches": 20,
      "cumulative_matched": 870,
      "cumulative_rate": "87.0%",
      "improvement": "+2.0%",
      "bridge_confidence_avg": 0.80,
      "computation_time": "2.1s"
    },
    "stage_5_similarity": {
      "new_matches": 20,
      "cumulative_matched": 890,
      "cumulative_rate": "89.0%",
      "improvement": "+2.0%",
      "similarity_threshold": 0.95,
      "computation_time": "5.5s"
    }
  },
  "final_summary": {
    "total_source_proteins": 1000,
    "total_matched": 890,
    "final_match_rate": "89.0%",
    "total_improvement": "+24.0%",
    "total_computation_time": "23.6s",
    "unmapped_proteins": 110,
    "provenance_distribution": {
      "direct_match": 650,
      "historical_resolution": 150,
      "gene_symbol_bridge": 50,
      "ensembl_bridge": 20,
      "similarity_match": 20
    }
  },
  "unmapped_analysis": {
    "total": 110,
    "reasons": {
      "novel_proteins": 45,
      "species_specific": 30,
      "obsolete_no_replacement": 20,
      "low_confidence_excluded": 15
    }
  }
}
```

## Benefits of Progressive Approach

### 1. **Complete Audit Trail**
Every match has documented provenance - critical for:
- Scientific reproducibility
- Regulatory compliance
- Quality assurance
- Debugging

### 2. **Performance Optimization**
- Skip expensive operations for already-matched proteins
- API calls only for unresolved proteins
- Progressive filtering reduces computation

### 3. **Quality Metrics**
- Confidence score per match
- Know which matches are most reliable
- Can filter by confidence threshold

### 4. **Improvement Visibility**
- See exactly how much each method contributes
- Identify which techniques work best for your data
- Optimize strategy order based on results

### 5. **Troubleshooting**
- Immediately see where matches fail
- Understand why proteins remain unmapped
- Target improvements to specific stages

## Example Use Cases

### Research Publication
"We achieved 89% protein mapping between datasets through progressive enhancement:
- 65% direct UniProt matching
- +15% through historical ID resolution
- +5% via gene symbol bridging
- +2% through Ensembl identifiers
- +2% using high-confidence similarity matching"

### Clinical Validation
"All protein mappings traceable:
- 73% high-confidence (direct + historical)
- 16% medium-confidence (gene/Ensembl bridge)
- 2% similarity-based (manual review recommended)"

### Performance Report
"Progressive approach avoided 350 unnecessary API calls by matching 65% directly, reducing processing time by 70%"