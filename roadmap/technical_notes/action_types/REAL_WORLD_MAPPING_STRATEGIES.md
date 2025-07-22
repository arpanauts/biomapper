# Real-World Mapping Strategies

This document captures practical mapping strategies for proteins, metabolites, and clinical labs, described in natural language. These examples will drive the design of MVP action types.

## Protein Mappings (9 Examples)

All protein mappings follow the same pattern: compare UniProt values with historical resolution to handle obsolete/updated accessions.

**Important Column Naming Conventions:**
- Arivale, HPA, QIN: column named `uniprot` (lowercase)
- UK Biobank: column named `UniProt` (capitalized)
- SPOKE proteins: `identifier` column contains bare UniProt accessions (e.g., "P00519")
  - ~86% of entries have UniProt IDs (18,843 out of 21,824 total)
  - Also available in `source` column as URLs: http://www.uniprot.org/uniprot/[ID].fasta
- KG2C proteins: `id` column with "UniProtKB:" prefix (e.g., "UniProtKB:P68431")
  - ~32% of entries are UniProt proteins (85,711 out of 266,488 total)
  - Also may have UniProt cross-references in `xrefs` column

## General Protein Mapping Approach

For all 9 protein mappings, the process follows these steps:

1. **Load datasets** with appropriate column mapping
   - Handle different column names (`uniprot`, `UniProt`, `identifier`, `id`)
   - Expand composite IDs (e.g., "Q14213_Q8NEV9") in ALL datasets
   - Strip prefixes where needed (KG2C: "UniProtKB:P68431" → "P68431")
   - Filter KG2C to only UniProtKB entries

2. **Resolve historical IDs** via UniProt API
   - Handle obsolete, secondary, and demerged accessions
   - Track confidence scores for each resolution
   - Maintain both original and resolved IDs

3. **Compare datasets**
   - Match on resolved UniProt accessions
   - Calculate overlap statistics
   - Track which proteins map between datasets

4. **Generate comprehensive reports**
   - Mapping results with all metadata preserved
   - Statistics by categories (e.g., UKBB Panel, HPA organ)
   - Lists of unique proteins to each dataset
   - Confidence scores from historical resolution

### 1. UKBB → HPA (UK Biobank → Human Protein Atlas)
- UKBB: `UniProt` column, may have composites, includes Panel metadata
- HPA: `uniprot` column, may have composites, includes organ metadata
- Goal: Find proteins measured in both platforms, analyze by panel/organ

### 2. UKBB → QIN (UK Biobank → Quantitative Imaging Network)
- UKBB: `UniProt` column, may have composites, includes Panel metadata
- QIN: `uniprot` column, may have composites
- Goal: Identify proteins relevant to quantitative imaging biomarkers

### 3. HPA → QIN (Human Protein Atlas → Quantitative Imaging Network)
- HPA: `uniprot` column, may have composites, includes organ metadata
- QIN: `uniprot` column, may have composites
- Goal: Connect tissue-specific proteins to imaging biomarkers

### 4. Arivale → SPOKE
- Arivale: `uniprot` column, may have composites, includes clinical metadata
- SPOKE: `identifier` column, may have composites (~86% have UniProt)
- Goal: Map clinical proteomics to biomedical knowledge graph

### 5. Arivale → KG2C
- Arivale: `uniprot` column, may have composites
- KG2C: `id` column with "UniProtKB:" prefix, filter to ~85K UniProt entries
- Goal: Connect clinical proteins to comprehensive knowledge graph

### 6. Arivale → UKBB
- Arivale: `uniprot` column, may have composites
- UKBB: `UniProt` column, may have composites, includes Panel metadata
- Goal: Compare clinical cohort proteins with population study

### 7. UKBB → KG2C
- UKBB: `UniProt` column, may have composites, includes Panel metadata
- KG2C: `id` column with "UniProtKB:" prefix, filter to ~85K UniProt entries
- Goal: Enrich population proteins with knowledge graph annotations

### 8. UKBB → SPOKE
- UKBB: `UniProt` column, may have composites, includes Panel metadata
- SPOKE: `identifier` column, may have composites (~86% have UniProt)
- Goal: Connect population proteomics to biomedical relationships

### 9. HPA → SPOKE
- HPA: `uniprot` column, may have composites, includes organ metadata
- SPOKE: `identifier` column, may have composites (~86% have UniProt)
- Goal: Link tissue-specific proteins to disease networks

## Action Types Required for Protein Mappings

Based on the 9 protein mapping scenarios above, we need these MVP actions:

1. **LOAD_DATASET_IDENTIFIERS**
   - Handle different column names via configuration
   - Expand composite IDs (underscore-separated)
   - Strip prefixes (e.g., "UniProtKB:" → bare accession)
   - Filter by ID type (e.g., only UniProtKB entries from KG2C)

2. **RESOLVE_CROSS_REFERENCES** (UniProt Historical)
   - Batch API calls to UniProt
   - Handle obsolete, secondary, demerged accessions
   - Track resolution confidence
   - Cache results for efficiency

3. **MERGE_DATASETS**
   - Join on resolved UniProt accessions
   - Preserve all metadata columns
   - Handle column name conflicts

4. **CALCULATE_SET_OVERLAP**
   - Compare UniProt sets between datasets
   - Generate intersection/unique lists
   - Calculate statistics (Jaccard, percentages)

5. **AGGREGATE_STATISTICS**
   - Group by metadata (Panel, organ, etc.)
   - Count proteins per category
   - Generate summary metrics

6. **FILTER_ROWS**
   - Filter by confidence scores or other criteria
   - Support multiple conditions with AND/OR logic
   - Preserve filtered-out rows separately (optional)

7. **GENERATE_MAPPING_REPORT**
   - Export to Excel with multiple sheets
   - Include mapping results and statistics
   - Preserve all metadata for downstream analysis

## YAML Strategy Patterns

Based on the protein mapping requirements, here's the standard YAML structure:

```yaml
name: SOURCE_TARGET_PROTEIN_MAPPING
version: "1.0.0"
description: Clear description of mapping purpose

config:
  source_file: "/path/to/source.csv"
  target_file: "/path/to/target.csv"
  output_dir: "/results/protein_mappings/source_target/"

steps:
  # 1. Load source with composite handling
  # 2. Load target with composite handling  
  # 3. Resolve source historical IDs
  # 4. Resolve target historical IDs
  # 5. Merge on resolved IDs
  # 6. Calculate overlap statistics
  # 7. Aggregate by metadata categories
  # 8. Filter (optional)
  # 9. Generate comprehensive report
```

Key patterns:
- Always expand composites during load
- Always resolve historical IDs before comparison
- Preserve all metadata through the pipeline
- Generate multi-sheet Excel reports with statistics

## Metabolite Mappings (3 Examples)

### 1. UKBB NMR Metabolomics → HMDB
*Status: Ready to document*

### 2. Arivale Metabolomics → KEGG Compounds
*Status: Ready to document*

### 3. Cross-Reference Metabolites (HMDB ↔ CHEBI ↔ PubChem)
*Status: Ready to document*

## Clinical Labs Mappings (3 Examples)

### 1. Function Health Tests → LOINC Codes
*Status: Ready to document*

### 2. Arivale Chemistry Tests → SPOKE Clinical Labs
*Status: Ready to document*

### 3. Lab Test Harmonization Across Providers
*Status: Ready to document*

---

## Notes on API Integration (Concern #1)

### UniProt Historical Resolution Parser
For RESOLVE_CROSS_REFERENCES with UniProt:

```python
# Expected API response structure
{
  "results": [{
    "primaryAccession": "P12345",  # Current primary
    "secondaryAccessions": ["Q99999"],  # Secondary IDs
    "obsolete": false,
    "demerged": [],
    "confidence": 1.0
  }]
}

# Parser should handle:
1. Direct matches (ID unchanged)
2. Secondary → Primary mappings  
3. Obsolete → Current mappings
4. Demerged entries (one ID split into multiple)
5. Not found (return original with confidence 0)
```

### Parser Interface
```python
def parse_uniprot_response(response: Dict, query_id: str) -> Dict:
    return {
        'resolved_id': str,      # Current primary accession
        'confidence': float,     # 0.0 to 1.0
        'resolution_type': str,  # 'direct', 'secondary', 'obsolete', 'demerged'
        'notes': str            # Any warnings or details
    }
```

## Notes on Complex Merges (Concern #2)

### Handling Expanded Composite IDs
After expanding composites, we may have many-to-many relationships:

```
Original:
UKBB: Assay="EBI3", UniProt="Q14213_Q8NEV9"
HPA: gene="IL27", uniprot="Q14213_Q6UWB1"  

After expansion:
UKBB: EBI3 → Q14213
      EBI3 → Q8NEV9
HPA:  IL27 → Q14213  (matches!)
      IL27 → Q6UWB1

Merge should preserve the relationship context.
```

### Column Conflict Resolution
Standard pattern for protein mappings:
- Keep join column once (they're equal by definition)
- Suffix other conflicts with _source and _target
- Preserve all metadata columns

## Notes on Report Generation (Concern #3)

### Standard Excel Layout for Protein Mappings

**Sheet 1: "All_Mappings"**
- All rows from outer join
- Columns: UniProt_Current, Assay, Panel (UKBB), gene, organ (HPA)
- Include resolution confidence scores
- Flag rows present in both/only one dataset

**Sheet 2: "Overlapping_Only"**
- Filter to proteins in both datasets
- Same columns as Sheet 1
- Sorted by confidence scores

**Sheet 3: "Statistics_By_Category"**
- Aggregated counts by Panel × organ
- Pivot table format
- Include percentage calculations

**Sheet 4: "Summary"**
- Total proteins per dataset
- Overlap statistics (count, percentage, Jaccard)
- Confidence score distribution
- Venn diagram data
- Processing metadata (files, timestamps, parameters)

**Sheet 5: "Unique_to_UKBB"** / **"Unique_to_HPA"**
- Proteins found only in one dataset
- Include all metadata for further investigation