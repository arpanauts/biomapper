# Biomapper Ontological Resources

This directory contains documentation for the various ontological resources used by Biomapper. These resources provide the foundation for the metadata cache and ontology mapping layer.

## Resource Documentation

| Resource | Description | Primary Entity Types | Key Features |
|----------|-------------|----------------------|-------------|
| [SPOKE](./spoke_ontologies.md) | Comprehensive biomedical knowledge graph integrating 41 databases | Compounds, Genes, Proteins, Diseases, Pathways | Large-scale integration, rich relationships |
| [RaMP DB](./rampdb_ontologies.md) | Rapid Mapping Database for metabolites and pathways | Metabolites, Pathways, Genes | Metabolite-pathway connections, comprehensive IDs |
| [UniChem](./unichem_ontologies.md) | EBI's compound identifier mapping service | Chemical compounds | Structure-based mappings, 40+ sources |
| [ChEBI](./chebi_ontologies.md) | Chemical Entities of Biological Interest ontology | Chemical compounds | Hierarchical classification, roles, relationships |
| [RefMet](./refmet_ontologies.md) | Reference list of Metabolite nomenclature | Metabolites | Standardized naming, chemical classification |
| [Arivale](./arivale_ontologies.md) | Multi-omic data from scientific wellness company | Metabolites, Proteins, Genes, Microbiome | Real-world measurements, multi-omic integration |
| [Extension Graph](./extension_graph_ontologies.md) | Supplementary knowledge graph for Biomapper | Compounds, Assays, Food, Regulatory entities | Custom relationships, FDA UNII data |

## Ontological Coverage

These resources collectively provide mappings for:

- **Metabolites**: HMDB, ChEBI, PubChem, KEGG, InChIKey, DrugBank identifiers
- **Genes**: Entrez, Ensembl, HGNC, Gene Symbol, RefSeq identifiers
- **Proteins**: UniProt, PDB, InterPro identifiers
- **Pathways**: Reactome, KEGG, Gene Ontology, PathwayCommons identifiers
- **Diseases**: MONDO, DOID, MeSH, OMIM, DisGeNET identifiers
- **Anatomy**: UBERON identifiers
- **Food**: FooDB, FoodOn, USDA identifiers
- **Pharmacologic**: ATC, NDC, RxNorm, FDA UNII identifiers

## Resource Integration Strategy

These resources will be integrated into Biomapper's metadata cache through:

1. **Data Extraction**: Extract mappings from each resource using appropriate methods
2. **Schema Mapping**: Normalize data models to fit Biomapper's unified schema
3. **Ontology Alignment**: Resolve conflicts between different ontological systems
4. **Confidence Scoring**: Assign confidence metrics to mappings from different sources
5. **Update Strategy**: Define processes for keeping the cache in sync with source updates

## Next Steps

Based on the documented resources, the following steps are planned:

1. **Schema Design**: Create the database schema for the metadata cache
2. **Extraction Tools**: Develop tools to extract and transform data from each resource
3. **Cache Manager**: Implement the cache manager for coordinating access to mappings
4. **Update Mechanisms**: Create processes for maintaining and updating the cache
5. **API Layer**: Design a unified API for accessing the cache

## Resource Access Documentation

Most of these resources provide APIs or database interfaces that can be used for extracting mappings:

- **SPOKE**: ArangoDB database queries
- **RaMP DB**: R package, SQL database, or REST API
- **UniChem**: REST API, SPARQL endpoint, or direct downloads
- **ChEBI**: Web services (REST/SOAP), OWL ontology downloads
- **RefMet**: Metabolomics Workbench API
- **Arivale**: Proprietary data access methods
- **Extension Graph**: ArangoDB database queries (similar to SPOKE)
