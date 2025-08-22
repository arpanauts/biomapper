# Protein Dataset Mapping to KG2c Strategy Documentation

## Overview
This document details the comprehensive strategy for mapping two protein datasets (Arivale proteomics and UK Biobank proteins) to KG2c protein entities using UniProt identifiers as the primary linking mechanism.

## Datasets

### 1. Arivale Proteomics Dataset
- **Location**: `/procedure/data/local_data/MAPPING_ONTOLOGIES/arivale/proteomics_metadata.tsv`
- **Format**: Tab-separated values with header metadata
- **Key Columns**:
  - `uniprot`: UniProt identifier (primary key for matching)
  - `name`: Protein assay name
  - `panel`: Assay panel grouping
  - `gene_name`: Associated gene symbol
  - `gene_description`: Gene functional description
  - `gene_id`: Ensembl gene ID
  - `transcript_id`: Ensembl transcript IDs
  - `protein_id`: Ensembl protein IDs
- **Data Quality**: 
  - Contains 1197 protein entries
  - UniProt IDs are generally well-formatted
  - Some entries may have obsolete UniProt IDs

### 2. UK Biobank (UKBB) Protein Dataset
- **Location**: `/procedure/data/local_data/MAPPING_ONTOLOGIES/ukbb/UKBB_Protein_Meta.tsv`
- **Format**: Tab-separated values
- **Key Columns**:
  - `UniProt`: UniProt identifier (primary key)
  - `Assay`: Protein assay name (often contains gene symbol)
  - `Panel`: Clinical panel grouping (e.g., Oncology, Neurology)
- **Data Quality**:
  - Clean, well-curated UniProt IDs
  - Organized by clinical panels
  - Expected high match rate with KG2c

### 3. KG2c Protein Dataset
- **Location**: `/procedure/data/local_data/MAPPING_ONTOLOGIES/kg2.10.2c_ontologies/kg2c_proteins.csv`
- **Format**: Comma-separated values
- **Key Columns**:
  - `id`: KG2c entity identifier
  - `name`: Protein/entity name
  - `category`: Biolink category (mostly "biolink:Protein")
  - `description`: Detailed description
  - `synonyms`: Alternative names (pipe-separated)
  - `xrefs`: Cross-references including UniProt IDs
- **UniProt Format**: UniProt IDs appear as `UniProtKB:XXXXX` in the xrefs column
- **Data Characteristics**:
  - Large file with comprehensive protein information
  - Multiple cross-references per protein
  - Some entries may have multiple UniProt IDs

## Mapping Strategy

### Phase 1: Data Loading and Validation
- Load all three datasets with appropriate column selection
- Validate data types and handle missing values
- Track initial data quality metrics

### Phase 2: UniProt ID Extraction and Normalization
- **KG2c Processing**:
  - Extract UniProt IDs from xrefs column using regex: `UniProtKB:([A-Z0-9]+)`
  - Handle multiple UniProt IDs per KG2c entry
  - Create expanded mapping table
  
- **Source Dataset Processing**:
  - Normalize UniProt IDs (uppercase, trim whitespace)
  - Remove isoform suffixes (e.g., P12345-1 → P12345)
  - Validate UniProt format using regex patterns

### Phase 3: Direct UniProt Matching
- Perform inner join on normalized UniProt IDs
- Track match rates and cardinality (one-to-one, one-to-many)
- Analyze coverage by panel (for UKBB)

### Phase 4: Handle Unmatched Proteins
- Identify proteins without direct matches
- Attempt resolution via UniProt API for:
  - Obsolete accessions
  - Secondary accessions
  - Cross-referenced identifiers

### Phase 5: Secondary Matching
- Match resolved proteins with KG2c
- Gene-based fallback matching for remaining unmatched
- Combine all successful matches

### Phase 6: Quality Assessment and Reporting
- Calculate Jaccard similarity and overlap coefficients
- Assess mapping cardinality
- Generate comprehensive HTML reports
- Export results in multiple formats

## Implementation Details

### YAML Strategy Files Created

1. **arivale_to_kg2c_proteins.yaml**
   - Location: `/home/ubuntu/biomapper/configs/strategies/arivale_to_kg2c_proteins.yaml`
   - Expected match rate: 80-90%
   - Includes UniProt resolution for obsolete IDs
   - Comprehensive error handling and metrics

2. **ukbb_to_kg2c_proteins.yaml**
   - Location: `/home/ubuntu/biomapper/configs/strategies/ukbb_to_kg2c_proteins.yaml`
   - Expected match rate: 85-95%
   - Panel-specific coverage analysis
   - Gene-based fallback matching

### Key Action Types Used

1. **LOAD_DATASET_IDENTIFIERS**: Initial data loading with validation
2. **CUSTOM_TRANSFORM**: UniProt extraction and normalization
3. **MERGE_DATASETS**: Primary and secondary matching
4. **FILTER_DATASET**: Identifying unmatched entries
5. **MERGE_WITH_UNIPROT_RESOLUTION**: API-based ID resolution
6. **CALCULATE_SET_OVERLAP**: Statistical analysis
7. **EXPORT_DATASET**: Multi-format output
8. **GENERATE_REPORT**: HTML report generation

### Output Structure

Each strategy produces:
- `*_matched.tsv`: Successfully mapped protein pairs
- `*_unmatched.tsv`: Proteins requiring manual review
- `panel_coverage.tsv`: Panel-specific statistics (UKBB only)
- `mapping_statistics.json`: Comprehensive metrics
- `mapping_report.html`: Visual summary report

## Execution Instructions

### Running the Strategies

```bash
# Using biomapper CLI
biomapper execute-strategy arivale_to_kg2c_proteins
biomapper execute-strategy ukbb_to_kg2c_proteins

# Using Python client
from biomapper_client import BiomapperClient

client = BiomapperClient()
client.execute_strategy("ARIVALE_TO_KG2C_PROTEINS")
client.execute_strategy("UKBB_TO_KG2C_PROTEINS")
```

### Monitoring Progress

- Strategies include checkpointing after each phase
- Progress can be monitored via API endpoints
- Failed jobs can be resumed from last checkpoint

### Parameter Overrides

Both strategies support parameter overrides:

```python
client.execute_strategy(
    "ARIVALE_TO_KG2C_PROTEINS",
    parameters={
        "output_dir": "/custom/output/path",
        "min_confidence": 0.95,
        "include_obsolete": True
    }
)
```

## Expected Outcomes

### Success Metrics
- **Arivale → KG2c**: 80-90% match rate expected
- **UKBB → KG2c**: 85-95% match rate expected
- Low API error rates (<100 errors)
- Comprehensive coverage across clinical panels

### Common Issues and Solutions

1. **Low Match Rates**:
   - Check UniProt ID formats in source data
   - Verify KG2c xrefs extraction logic
   - Consider enabling obsolete ID resolution

2. **API Rate Limiting**:
   - Adjust batch_size parameter (default: 1000)
   - Implement exponential backoff
   - Use local UniProt cache if available

3. **Memory Issues**:
   - Process in smaller batches
   - Enable checkpointing
   - Use filtering to reduce dataset size

## Quality Assurance

### Validation Steps

1. **Pre-execution**:
   - Verify file paths exist
   - Check column names match expected
   - Validate sufficient disk space for outputs

2. **During execution**:
   - Monitor checkpoint progress
   - Check intermediate metrics
   - Validate UniProt API connectivity

3. **Post-execution**:
   - Review match rates against expectations
   - Examine unmatched proteins for patterns
   - Validate output file integrity

### Testing Recommendations

1. **Development Testing**:
   ```bash
   # Create test subsets
   head -100 arivale/proteomics_metadata.tsv > test_arivale.tsv
   head -100 ukbb/UKBB_Protein_Meta.tsv > test_ukbb.tsv
   
   # Run strategies with test data
   biomapper execute-strategy test_arivale_to_kg2c
   ```

2. **Validation Testing**:
   - Manually verify 10-20 matches
   - Check edge cases (obsolete IDs, multiple mappings)
   - Validate panel coverage calculations

## Future Enhancements

### Planned Improvements

1. **Additional Matching Strategies**:
   - Gene symbol matching
   - Protein name similarity
   - Sequence-based alignment

2. **Performance Optimizations**:
   - Parallel processing for API calls
   - Caching layer for repeated lookups
   - Vectorized operations for large datasets

3. **Enhanced Reporting**:
   - Interactive visualization dashboards
   - Detailed unmapped protein analysis
   - Cross-dataset comparison reports

### Integration Opportunities

1. **Downstream Analysis**:
   - Pathway enrichment using matched proteins
   - Disease association analysis
   - Cross-cohort protein comparisons

2. **Data Quality Improvements**:
   - Automated UniProt update detection
   - Version tracking for KG2c updates
   - Confidence scoring for matches

## Appendix

### UniProt ID Format Patterns

```regex
# Standard UniProt Accession
^[OPQ][0-9][A-Z0-9]{3}[0-9]$

# UniProt Accession (extended)
^[A-NR-Z][0-9]([A-Z][A-Z0-9]{2}[0-9]){1,2}$

# With isoform
^[A-Z][0-9][A-Z0-9]{3}[0-9]-\d+$
```

### KG2c xrefs Parsing Example

```python
import re

def extract_uniprot_from_xrefs(xrefs_string):
    """Extract all UniProt IDs from KG2c xrefs field"""
    if not xrefs_string:
        return []
    
    # Pattern: UniProtKB:XXXXX
    pattern = r'UniProtKB:([A-Z0-9]+)'
    matches = re.findall(pattern, xrefs_string)
    
    return list(set(matches))  # Remove duplicates
```

### Biomapper Action Registry

The strategies use self-registering actions from:
- `biomapper/core/strategy_actions/`
- Actions register via `@register_action` decorator
- No manual registration required

---

*Document Version: 1.0.0*  
*Last Updated: 2025-08-06*  
*Author: BiomapperStrategyAssistant*