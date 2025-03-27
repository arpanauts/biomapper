# SPOKE Knowledge Graph Ontological Resources

## Overview

SPOKE (Scalable Precision Medicine Open Knowledge Engine) integrates data from 41 specialized biomedical databases into a unified knowledge graph. This document catalogs the ontological identifiers available in SPOKE, their relationships, and how they can be leveraged in Biomapper's metadata cache.

## Node Types and Ontologies

### Compound / Chemical Entities
- **ChEBI**: Chemical Entities of Biological Interest (e.g., CHEBI:15377)
- **HMDB**: Human Metabolome Database IDs (e.g., HMDB0000001)
- **PubChem**: PubChem Compound IDs (e.g., CID123456)
- **DrugBank**: DrugBank IDs (e.g., DB00001)
- **ChEMBL**: ChEMBL IDs for bioactive molecules (e.g., CHEMBL1234)
- **InChIKey**: International Chemical Identifier hashes for unique compound identification

**Source Databases**: ChEMBL, DrugBank, DrugCentral, BindingDB, FooDB

### Gene
- **Entrez Gene**: NCBI gene identifiers (e.g., 672)
- **Ensembl**: Ensembl gene IDs (e.g., ENSG00000139618)
- **HGNC**: Human Gene Nomenclature Committee IDs
- **Gene Symbol**: Standard gene symbols (e.g., BRCA1)

**Source Databases**: Entrez Gene, COSMIC, DisGeNET, DistiLD, OMIM, Bgee, LINCS L1000

### Protein
- **UniProt**: Universal Protein resource accessions (e.g., P04637)
- **PDB**: Protein Data Bank IDs (e.g., 4HHB)
- **InterPro**: Protein family and domain annotations

**Source Databases**: Human Interactome Database, iRefIndex

### Disease
- **MONDO**: Monarch Disease Ontology IDs
- **DOID**: Disease Ontology IDs
- **MeSH**: Medical Subject Headings
- **OMIM**: Online Mendelian Inheritance in Man (e.g., OMIM:143100)
- **DisGeNET**: Disease-gene association database IDs

**Source Databases**: DisGeNET, OMIM, MeSH

### Pathway
- **Reactome**: Reactome pathway database IDs
- **KEGG**: Kyoto Encyclopedia of Genes and Genomes pathway IDs
- **GO**: Gene Ontology terms for biological processes
- **Pathway Commons**: Integrated pathway data
- **PID**: Pathway Interaction Database IDs

**Source Databases**: Reactome, Pathway Commons, Pathway Interaction Database

### Anatomy
- **UBERON**: Unified anatomical structure ontology

### Food
- **FooDB**: Food constituents database IDs
- **FoodOn**: Food ontology terms

**Source Databases**: FooDB

### Pharmacologic
- **ATC**: Anatomical Therapeutic Chemical Classification
- **NDC**: National Drug Code
- **RxNorm**: Normalized names for clinical drugs

**Source Databases**: DrugCentral, PharmacoDB

### Side Effect
- **SIDER**: Side Effect Resource IDs
- **MeSH**: Medical Subject Headings for adverse effects

**Source Databases**: SIDER

## Key Relationships

1. **Compound-Gene Relationships**
   - `INTERACTS_CmG`: Compound interacts with gene
   - `TARGETS_CtG`: Compound targets gene
   
   **Source Databases**: ChEMBL, DrugBank, BindingDB

2. **Gene-Disease Relationships**
   - `ASSOCIATES_DaG`: Disease associated with gene
   - `UPREGULATES_GuD`: Gene upregulates in disease
   - `DOWNREGULATES_GdD`: Gene downregulates in disease
   
   **Source Databases**: DisGeNET, OMIM, COSMIC, DistiLD

3. **Compound-Pathway Relationships**
   - `PARTICIPATES_CpP`: Compound participates in pathway

4. **Gene-Protein Relationships**
   - `EXPRESSES_GeP`: Gene expresses protein

## Data Accessibility

- **Database Type**: ArangoDB
- **Collections**: Nodes (document collection), Edges (edge collection)
- **Node Properties**: Each node contains identifiers in its `properties` field
- **Edge Properties**: Relationships are typed with `label` field

## Query Patterns

Common query patterns for extracting ontological mappings from SPOKE:

1. **Compound Identifier Mapping**:
   ```aql
   FOR node IN Nodes
     FILTER node.type == "Compound" AND node.properties.chebi == "CHEBI:15377"
     RETURN {
       chebi: node.properties.chebi,
       hmdb: node.properties.hmdb,
       pubchem: node.properties.pubchem,
       inchikey: node.properties.inchikey
     }
   ```

2. **Protein to Gene Mapping**:
   ```aql
   FOR edge IN Edges
     FILTER edge.label == "EXPRESSES_GeP"
     LET gene = DOCUMENT(edge._from)
     LET protein = DOCUMENT(edge._to)
     RETURN {
       gene_id: gene.properties.entrez,
       gene_symbol: gene.name,
       uniprot: protein.properties.uniprot
     }
   ```

3. **Disease to Gene Mapping**:
   ```aql
   FOR edge IN Edges
     FILTER edge.label == "ASSOCIATES_DaG"
     LET disease = DOCUMENT(edge._from)
     LET gene = DOCUMENT(edge._to)
     RETURN {
       disease_id: disease.properties.mondo,
       disease_name: disease.name,
       gene_id: gene.properties.entrez,
       gene_symbol: gene.name
     }
   ```

## Metadata Cache Considerations

When designing the metadata cache for SPOKE data:

1. **Primary Keys**: Consider using standard identifiers (CHEBI, Entrez, UniProt) as primary keys
2. **Relationship Tables**: Create mapping tables for each relationship type
3. **Provenance**: Track which SPOKE version was used for each mapping
4. **Confidence**: Include confidence scores from SPOKE when available
5. **Update Strategy**: Consider how to handle updates when SPOKE is updated

## Example Mapping Tables

Here are example table schemas for storing SPOKE mappings:

```sql
-- Compound mappings
CREATE TABLE compound_mappings (
    chebi_id TEXT PRIMARY KEY,
    hmdb_id TEXT,
    pubchem_id TEXT,
    drugbank_id TEXT,
    inchikey TEXT,
    source TEXT DEFAULT 'SPOKE',
    spoke_version TEXT,
    confidence REAL
);

-- Gene to Protein mappings
CREATE TABLE gene_protein_mappings (
    gene_id TEXT,
    gene_symbol TEXT,
    uniprot_id TEXT,
    source TEXT DEFAULT 'SPOKE',
    spoke_version TEXT,
    confidence REAL,
    PRIMARY KEY (gene_id, uniprot_id)
);
```
