# RaMP DB Ontological Resources

## Overview

RaMP DB (Rapid Mapping Database) is a database that integrates metabolite, gene, and pathway data from multiple sources into one unified repository. RaMP-DB 2.0 combines data from HMDB v5.0, KEGG, Reactome v81, and WikiPathways v20220710, providing comprehensive mapping functionality to connect different identifiers for metabolites, genes, and pathways.

## Available Ontologies and Identifiers

### Metabolite Identifiers
RaMP-DB 2.0 supports the following identifier types for metabolites:
- **HMDB**: Human Metabolome Database IDs (e.g., HMDB0000001)
- **PubChem**: PubChem Compound IDs (e.g., CID123456)
- **ChEBI**: Chemical Entities of Biological Interest (e.g., CHEBI:15377)
- **KEGG**: Kyoto Encyclopedia of Genes and Genomes Compound IDs (e.g., C00001)
- **CAS**: Chemical Abstracts Service Registry Numbers
- **WikiData**: WikiData identifiers
- **ChemSpider**: ChemSpider identifiers
- **SwissLipids**: SwissLipids database identifiers
- **LIPID MAPS**: LIPID MAPS Structure Database identifiers
- **LipidBank**: LipidBank identifiers
- **PlantFA**: Plant fatty acid database identifiers
- **InChIKey**: International Chemical Identifier hashes
- **SMILES**: Simplified molecular-input line-entry system strings

### Pathway Identifiers
- **KEGG Pathway**: KEGG pathway IDs (363 pathways)
- **Reactome**: Reactome pathway IDs (2,583 pathways in v81)
- **WikiPathways**: Community pathway database IDs (1,272 pathways in v20220710)
- **HMDB Pathways**: Pathway information from HMDB v5.0 (49,613 pathways)

### Gene/Protein Identifiers
RaMP-DB 2.0 supports the following identifier types for genes/proteins:
- **Entrez Gene**: NCBI gene identifiers
- **ENSEMBL**: Ensembl gene IDs
- **UniProt**: Universal Protein resource accessions
- **Gene Symbol**: Standard gene symbols
- **HMDB**: HMDB protein identifiers
- **NCBIprotein**: NCBI protein identifiers
- **EN**: Ensembl identifiers
- **WikiData**: WikiData identifiers
- **ChEBI**: ChEBI identifiers (for some proteins)

### Chemical Classification
RaMP-DB 2.0 includes chemical classification data:
- **ClassyFire Taxonomy**: Chemical class, superclass, and subclass
- **LIPID MAPS Classification**: Lipid classification hierarchy

## Data Structure and Content

RaMP-DB 2.0 contains comprehensive biological entity data with the following statistics:

### Entity Counts
- **Distinct metabolites**: 256,086 metabolites
- **Distinct genes/enzymes**: 15,827 genes
- **Distinct pathways**: 53,831 pathways
- **Metabolite-pathway mappings**: 412,775 mappings
- **Gene-pathway mappings**: 401,303 mappings
- **Metabolic enzyme/metabolite mutual reaction relationships**: 1,541,996 relationships
- **Functional ontologies**: 699 succinct functional ontologies from HMDB v5.0

RaMP DB's main tables and their relationships:

1. **Analytes**: Contains metabolites and genes
2. **Pathways**: Contains pathway information
3. **Analyte-Pathway Mappings**: Links analytes to pathways
4. **ID Mappings**: Connects different identifiers for the same entity
5. **Chemical Properties**: 256,592 compounds with chemical properties
   - From HMDB v5.0: 217,776 compounds
   - From ChEBI (release 212): 13,066 compounds
   - From LIPID MAPS (July 2022): 44,981 compounds

## Entity Resolution and Data Quality

RaMP-DB 2.0 implements a sophisticated approach to entity resolution across different databases:

1. **ID-based Entity Resolution**: Initially groups entities based on shared IDs across databases
2. **Mismapping Detection**: Implements a molecular weight heuristic to flag potential mismappings
3. **Manual Curation**: Flagged mismappings are manually investigated and corrected
4. **Error Prevention**: 955 distinct metabolites with incorrect associations were identified and curated
5. **Persistent Corrections**: Mismappings are recorded to automatically correct future database updates

### Database Content Overlap

- 43% of metabolites (109,754) are found in only one source database (99% from HMDB)
- Of metabolites with pathway associations, 23% (12,966) have pathway mappings from only one source
- Only 5% of genes/proteins (686) are unique to a single source database

## Query Patterns

RaMP-DB 2.0 allows users to input mixed ID types in batch queries. Typical query patterns include:

1. **Metabolite ID Mapping**:
   ```sql
   SELECT source_id, target_id 
   FROM metabolite_mapping 
   WHERE source_type = 'hmdb' AND target_type = 'chebi'
   ```

2. **Metabolite to Pathway Mapping**:
   ```sql
   SELECT pathway_id, pathway_name 
   FROM pathway_mapping 
   WHERE metabolite_id = 'hmdb:HMDB0000001'
   ```

3. **Gene to Pathway Mapping**:
   ```sql
   SELECT pathway_id, pathway_name 
   FROM pathway_mapping 
   WHERE gene_id = 'entrez:5243'
   ```

**Note**: ID types must be prepended to the ID for queries (e.g., `hmdb:HMDB0000064`).

## Metadata Cache Considerations

When designing the metadata cache for RaMP DB data:

1. **Preferred IDs**: HMDB IDs are often used as the primary identifier for metabolites
2. **Cross-References**: Store multiple identifier mappings (HMDB→ChEBI, HMDB→KEGG, etc.)
3. **Pathway Connections**: Store analyte-pathway relationships
4. **Source Database**: Track which original database provided each mapping
5. **Mismapping Prevention**: Implement molecular weight validation to prevent propagating errors
6. **Chemical Classification**: Include ClassyFire taxonomy and LIPID MAPS classifications
7. **Functional Ontologies**: Include the 699 functional ontologies from HMDB
8. **Updates**: Consider how to manage updates as RaMP DB is periodically refreshed
9. **ID Type Standardization**: Support the RaMP prefix notation (e.g., `hmdb:HMDB0000064`)

## Example Mapping Tables

Example table schemas for storing RaMP DB mappings:

```sql
-- Metabolite mappings
CREATE TABLE metabolite_mappings (
    hmdb_id TEXT PRIMARY KEY,
    chebi_id TEXT,
    kegg_id TEXT,
    pubchem_id TEXT,
    cas_rn TEXT,
    inchikey TEXT,
    common_name TEXT,
    source TEXT DEFAULT 'RaMP DB',
    ramp_version TEXT,
    last_updated DATE
);

-- Metabolite to pathway mappings
CREATE TABLE metabolite_pathway_mappings (
    metabolite_id TEXT,
    pathway_id TEXT,
    pathway_name TEXT,
    pathway_source TEXT, -- KEGG, Reactome, etc.
    source TEXT DEFAULT 'RaMP DB',
    ramp_version TEXT,
    PRIMARY KEY (metabolite_id, pathway_id)
);
```

## Integration with Other Resources

RaMP DB complements SPOKE and other resources in these ways:

1. **Enhanced Metabolite Coverage**: More comprehensive metabolite identifier mappings
2. **Pathway Annotations**: Rich pathway information not fully captured in SPOKE
3. **Metabolic Process Focus**: Specific emphasis on metabolic processes
4. **Different Source Databases**: Incorporates some sources not present in SPOKE

## Access Patterns

RaMP DB can be accessed through:

1. **Direct Database Access**: SQL queries to the database
2. **R Package**: R interface for querying RaMP DB
3. **Web Interface**: Browser-based access
4. **Custom API**: Programmatic access via REST API

## Citation

This documentation includes information from:

Palmer A, Maker G, Coffman A, Broadhurstm D, Pavlovskiy K, Jones DP, Wishart D, Jones CMA, Kelly RS, Johnson CH, McConn B, Uppal K, Walker DI. RaMP-DB 2.0: an enhanced metabolite, gene and pathway database with accurate ID mapping for multi-omics analyses. Bioinformatics. 2023 Jan 1;39(1):btad012. doi: 10.1093/bioinformatics/btad012. PMID: 36759745; PMCID: PMC9825745.
