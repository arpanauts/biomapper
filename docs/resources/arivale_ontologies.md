# Arivale Ontological Resources

## Overview

Arivale was a scientific wellness company that collected comprehensive multi-omic data from participants, including metabolomics, genomics, proteomics, and microbiome data. This document catalogs the ontological identifiers and relationships available in the Arivale dataset that can be leveraged in Biomapper's metadata cache.

## Available Data Types and Identifiers

### Metabolomics
- **Metabolite Names**: Common and systematic names for metabolites
- **HMDB IDs**: Human Metabolome Database identifiers
- **PubChem CIDs**: PubChem Compound IDs
- **CAS Numbers**: Chemical Abstract Service numbers
- **KEGG IDs**: KEGG identifiers
- **Internal Arivale IDs**: Proprietary identifiers used in Arivale datasets

### Genomics
- **SNP IDs**: Single Nucleotide Polymorphism identifiers (rs numbers)
- **Gene Symbols**: Human gene names
- **Ensembl IDs**: Ensembl genome database identifiers
- **Chromosomal Positions**: Genomic coordinates

### Proteomics
- **Protein Names**: Common protein names
- **UniProt IDs**: Universal Protein Resource accessions
- **SomaLogic Aptamer IDs**: Specific to SomaLogic proteomics platform
- **Entrez Gene IDs**: NCBI gene identifiers associated with proteins

### Microbiome
- **Taxonomic IDs**: NCBI taxonomy identifiers
- **OTU IDs**: Operational Taxonomic Unit identifiers
- **Species Names**: Scientific names of microbial species
- **Functional Pathways**: KEGG or MetaCyc pathway identifiers

## Data Structure and Relationships

The Arivale dataset contains these key relationships:

1. **Metabolite-Gene Associations**: Links between metabolites and genes based on known biochemical pathways
2. **SNP-Phenotype Associations**: Connections between genetic variants and clinical measurements
3. **Protein-Disease Relationships**: Associations between protein levels and disease states
4. **Microbiome-Metabolite Correlations**: Relationships between gut microbes and blood metabolites

## Metadata Cache Considerations

When designing the metadata cache for Arivale data:

1. **Multi-omic Integration**: Create cross-references between different omic data types
2. **Longitudinal Data**: Account for multiple measurements over time
3. **Privacy Considerations**: Ensure proper de-identification of personal data
4. **Provenance Tracking**: Maintain information about data sources and processing methods
5. **Measurement Context**: Store information about measurement platforms and techniques

## Example Mapping Tables

Example table schemas for storing Arivale mappings:

```sql
-- Metabolite mappings
CREATE TABLE arivale_metabolite_mappings (
    arivale_id TEXT PRIMARY KEY,
    metabolite_name TEXT,
    hmdb_id TEXT,
    pubchem_id TEXT,
    inchikey TEXT,
    measurement_platform TEXT,
    confidence REAL
);

-- SNP-Gene mappings
CREATE TABLE arivale_snp_mappings (
    rs_id TEXT PRIMARY KEY,
    gene_symbol TEXT,
    ensembl_id TEXT,
    chromosome TEXT,
    position INTEGER,
    reference_allele TEXT,
    alternate_allele TEXT
);

-- Protein mappings
CREATE TABLE arivale_protein_mappings (
    somalogic_id TEXT PRIMARY KEY,
    protein_name TEXT,
    uniprot_id TEXT,
    entrez_gene_id TEXT,
    gene_symbol TEXT,
    confidence REAL
);
```

## Integration with Other Resources

Arivale data complements SPOKE, RaMP DB, and other resources in these ways:

1. **Real-world Measurements**: Contains actual measurements from human participants
2. **Multi-omic Correlations**: Provides relationships between different types of biological entities
3. **Temporal Dimension**: Includes longitudinal data over multiple timepoints
4. **Phenotype Connections**: Links biological measurements to health outcomes
5. **Novel Associations**: Contains correlations that may not be present in literature-based resources

## Unique Features and Challenges

Arivale data presents some unique characteristics:

1. **Proprietary Identifiers**: Some identifiers may be specific to Arivale platforms
2. **Data Gaps**: Not all participants have all data types
3. **Batch Effects**: Measurements taken at different times may have technical variations
4. **Privacy Constraints**: Stricter usage limitations compared to public databases
5. **Context Dependency**: Measurements are affected by participant demographics and behaviors

## Recommended Usage in Metadata Cache

For optimal use of Arivale data in the metadata cache:

1. **Standardize Identifiers**: Map Arivale-specific IDs to standard ontologies
2. **Prioritize High-confidence Associations**: Focus on strongest and most replicated relationships
3. **Link to External Knowledge**: Connect Arivale observations to literature-based relationships
4. **Maintain Context**: Preserve information about measurement conditions
5. **Extract Generalized Patterns**: Identify recurring relationships that transcend individual variations
