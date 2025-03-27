# UniChem Ontological Resources

## Overview

UniChem is a non-proprietary, large-scale, freely available compound identifier mapping resource developed and maintained by the European Bioinformatics Institute (EBI). It provides cross-references between compound identifiers from various databases, making it an excellent resource for standardizing chemical identifiers.

## Available Sources and Identifiers

UniChem currently maps identifiers from over 50 different sources. When using the UniChem API, it's essential to use the source ID number (not the source name) for queries. The current sources include:

### Primary Sources by ID (critical for API queries)

| Source ID | Source Name | Description | Compound Count |
|-----------|------------|-------------|----------------|
| 1 | ChEMBL | Bioactive drug-like small molecules and bioactivities | 2,473,434 |
| 2 | DrugBank | Drug data with drug target information | 11,919 |
| 3 | PDBe | Protein Data Bank Europe - small molecule ligands | 43,246 |
| 4 | Guide to Pharmacology | IUPHAR/BPS pharmacology database | 8,411 |
| 6 | KEGG | Kyoto Encyclopedia of Genes and Genomes compounds | 14,033 |
| 7 | ChEBI | Chemical Entities of Biological Interest | 142,602 |
| 9 | ZINC | Free database of commercially-available compounds | 16,886,865 |
| 10 | eMolecules | Chemical structure search engine | 5,168,336 |
| 14 | FDA/USP SRS | FDA Substance Registration System (UNII codes) | 86,608 |
| 15 | SureChEMBL | Patent chemistry database | 22,690,940 |
| 17 | PharmGKB | Pharmacogenomics Knowledgebase | 1,691 |
| 18 | HMDB | Human Metabolome Database | 217,733 |
| 21 | BindingDB | Binding affinity database | 1,000,223 |
| 22 | PubChem | PubChem Compounds database | 115,824,355 |
| 25 | LINCS | Library of Integrated Network-based Cellular Signatures | 42,741 |
| 27 | Recon | Biochemical knowledge-base on human metabolism | 1,529 |
| 28 | MolPort | Commercial compound source database | 110,024 |
| 31 | BindingDB | Binding affinity database | 1,000,223 |
| 32 | EPA CompTox | Environmental Protection Agency CompTox Dashboard | 742,310 |
| 33 | LipidMaps | LIPID Metabolites And Pathways Strategy database | 47,866 |
| 34 | DrugCentral | Drug information resource | 4,091 |
| 36 | Metabolights | Database for Metabolomics experiments | 22,227 |
| 37 | Brenda | Enzyme Information system | 149,602 |
| 38 | Rhea | Expert curated resource of biochemical reactions | 8,964 |
| 41 | SwissLipids | Expert curated resource for lipids | 503,725 |
| 45 | DailyMed | Database of marketed drugs in the USA | 2,454 |
| 46 | ClinicalTrials | Intervention names from ClinicalTrials.gov | 5,362 |
| 47 | RxNorm | Normalized names for clinical drugs | 6,497 |

### Most Relevant Sources for Biomapper

Based on our project needs, these sources are particularly valuable:

- **ChEMBL (1)**: Bioactive molecules with activity data (2.4M compounds)
- **PubChem (22)**: Largest chemical database (115.8M compounds)
- **HMDB (18)**: Human metabolome data (217.7K compounds)
- **ChEBI (7)**: Biological interest chemicals (142.6K compounds)
- **DrugBank (2)**: Comprehensive drug information (11.9K compounds)
- **KEGG (6)**: Metabolic pathway compounds (14K compounds)
- **LipidMaps (33)**: Specialized lipid database (47.8K compounds)
- **FDA/USP SRS (14)**: FDA-registered substances with UNIIs (86.6K compounds)

## Data Structure and API Usage

UniChem organizes data through these key concepts:

1. **Source**: A database that provides identifiers (assigned a unique source ID)
2. **InChIKey**: The primary key used for identifying chemical structures
3. **Assignment**: The relationship between a source identifier and an InChIKey
4. **Cross-references**: Mappings between identifiers from different sources

### API Query Requirements

When using the UniChem API, you must use source IDs (numeric) rather than source names. For example:

```python
# Convert a ChEMBL ID to a DrugBank ID
# Note usage of source_id=1 (ChEMBL) and source_id=2 (DrugBank)
url = "https://www.ebi.ac.uk/unichem/rest/src_compound_id/{compound_id}/1/2"

# Get all mappings for a compound from all sources
# Using source_id=1 (ChEMBL)
url = "https://www.ebi.ac.uk/unichem/rest/src_compound_id_all/{compound_id}/1"
```

This numeric source ID requirement is a critical implementation detail that must be incorporated into any UniChem integration code.

## Query Patterns

Typical query patterns for extracting mapping information from UniChem:

1. **Direct Identifier Mapping**:
   ```sql
   -- Convert a ChEMBL ID to a DrugBank ID
   SELECT src_compound_id 
   FROM unichem_mappings 
   WHERE source_id = 2 -- DrugBank
   AND src_compound_id_from = 'CHEMBL25' 
   AND source_id_from = 1 -- ChEMBL
   ```

2. **InChIKey-based Mapping**:
   ```sql
   -- Find all identifiers for a given InChIKey
   SELECT source_id, src_compound_id 
   FROM unichem_assignments
   WHERE inchikey = 'AAOVKJBEBIDNHE-UHFFFAOYSA-N'
   ```

3. **Connectivity Mapping**:
   ```sql
   -- Find compounds with similar connectivity
   SELECT * FROM unichem_connectivity
   WHERE std_inchikey_connectivity = 'AAOVKJBEBIDNHE'
   ```

## Metadata Cache Considerations

When designing the metadata cache for UniChem data:

1. **InChIKey as Hub**: Use the InChIKey as the central hub for connections
2. **Source Prioritization**: Some sources are more authoritative than others
3. **Version Tracking**: UniChem is updated regularly, track which version was used
4. **API vs. Database**: Consider whether to query UniChem live or cache mappings
5. **Structure-based Linkage**: Allow for connections via structural similarity

## Example Mapping Tables

Example table schemas for storing UniChem mappings:

```sql
-- Central compound table
CREATE TABLE compounds (
    inchikey TEXT PRIMARY KEY,
    connectivity_inchikey TEXT, -- First 14 characters of InChIKey
    standard_inchi TEXT,
    created_date DATE,
    last_updated DATE
);

-- Source-specific identifiers
CREATE TABLE compound_identifiers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    inchikey TEXT REFERENCES compounds(inchikey),
    source_id INTEGER, -- UniChem source ID
    source_name TEXT, -- e.g., 'ChEMBL', 'DrugBank'
    compound_id TEXT, -- The identifier in that source
    is_current BOOLEAN DEFAULT 1,
    UNIQUE(inchikey, source_id, compound_id)
);

-- Direct mappings for performance
CREATE TABLE compound_mappings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    from_source_id INTEGER,
    from_compound_id TEXT,
    to_source_id INTEGER,
    to_compound_id TEXT,
    unichem_version TEXT,
    last_updated DATE,
    UNIQUE(from_source_id, from_compound_id, to_source_id)
);
```

## Integration with Other Resources

UniChem complements SPOKE, RaMP DB, and other resources in these ways:

1. **Chemical Structure Focus**: Provides mappings based purely on chemical structure
2. **Broader Source Coverage**: Includes many specialized chemical databases
3. **Regular Updates**: Frequently updated with the latest identifiers
4. **Authoritative Source**: Maintained by EBI, a trusted bioinformatics organization
5. **Unambiguous Mappings**: Uses InChIKey for precise structure-based mappings
6. **Scale**: Contains over 115 million compounds from PubChem alone
7. **Database Size Awareness**: Understanding the size of each source helps with query planning and caching strategies

## Access Patterns

UniChem can be accessed through:

1. **REST API**: Programmatic access via web services at `https://www.ebi.ac.uk/unichem/rest/`
   - Requires numeric source IDs (not names) for all queries
   - Example: `/src_compound_id/{compound_id}/{source_id}/{target_source_id}`

2. **SPARQL Endpoint**: Semantic web query interface

3. **Full Downloads**: Complete data dumps available
   - Consider database size when downloading full dumps (PubChem alone has 115.8M compounds)

4. **Web Interface**: Browser-based query tool at `https://www.ebi.ac.uk/unichem/`

## Implementation Considerations

1. **Source ID Mapping**: Maintain a mapping between source names and their numeric IDs
2. **Database Size Awareness**: Use targeted queries for large sources like PubChem (115M+ compounds)
3. **Rate Limiting**: Implement appropriate rate limiting when making API calls
4. **Caching Strategy**: Cache frequently used mappings to reduce API load
5. **Fallback Strategy**: Implement fallbacks for when the API is unavailable

## Citation

Data about UniChem sources obtained from: https://www.ebi.ac.uk/unichem/sources

## Extension for Unknown Compounds

For compounds not found in UniChem:

1. **Structure-based Matching**: Use InChI/InChIKey to find similar compounds
2. **Partial Matching**: Match on connectivity portion of InChIKey
3. **Name-to-Structure**: Convert names to structures then search
4. **Programmatic Registration**: Submit new compounds to source databases
