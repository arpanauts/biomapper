# Biomapper API Documentation Resources

This directory contains API documentation for the various resources used by Biomapper. These resources provide the foundation for the metadata cache and ontology mapping layer. Each document details the programmatic access methods, entity types, property extraction, and example code for interacting with these resources.

## Resource Documentation

| Resource | API Documentation | Authentication | Entity Types | Key Features | Resource ID |
|----------|------------------|----------------|--------------|-------------|------------|
| [UniChem](./unichem_api_documentation.md) | RESTful API | Not Required | Chemical compounds | Identifier mapping, 40+ source databases | ID 10 |
| [KEGG](./kegg_api_documentation.md) | REST-like API | Not Required | Compounds, Genes, Enzymes, Pathways | Database cross-references, pathway data | ID 9 |
| [RefMet](./refmet_api_documentation.md) | RESTful API | Not Required | Metabolites, pathways | Standardized nomenclature, classifications | ID 11 |
| [ChEBI](./chebi_api_documentation.md) | SOAP Web Services | Not Required | Chemical compounds | Classification hierarchies, chemical roles | ID 5 |
| [RaMP DB](./rampdb_api_documentation.md) | RESTful API | Not Required | Metabolites, Genes, Pathways | Multi-source integration, enrichment analysis | ID 12 |
| [PubChem](./pubchem_api_documentation.md) | PUG REST API | Not Required | Chemical compounds | Structure search, property retrieval | ID 6 |
| SPOKE | ArangoDB queries | N/A (local) | Compounds, Genes, Proteins, Diseases, Pathways | Comprehensive knowledge graph | ID 8 |
| MetabolitesCSV | File-based | N/A (local) | Metabolites | CSV data (proxy for Arivale data) | ID 7 |
| [UniProt](./uniprot_api_documentation.md) | REST API | Not Required | Proteins | ID mapping, sequence search | ID 13 |
| [UMLS](./umls_api_documentation.md) | REST API | Not Required | Medical concepts | Terminology services, concept mapping | ID 14 |

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
- **Chemical Properties**: InChI, InChIKey, SMILES, molecular weight, formula
- **Chemical Classification**: ClassyFire hierarchy, LIPID MAPS classification

## Resource Integration Strategy

These resources will be integrated into Biomapper's metadata cache through:

1. **Data Extraction**: Extract mappings from each resource using appropriate API access methods
2. **Schema Mapping**: Normalize data models to fit Biomapper's unified schema
3. **Ontology Alignment**: Resolve conflicts between different ontological systems
4. **Confidence Scoring**: Assign confidence metrics to mappings from different sources
5. **Update Strategy**: Define processes for keeping the cache in sync with source updates
6. **Property Extraction**: Configure pattern-based extraction of properties from API responses

## Resource Access Methods

The following access methods are implemented for extracting data from these resources:

| Resource | Access Methods | Rate Limits | Response Format | Property Extraction |
|----------|----------------|------------|-----------------|---------------------|
| **UniChem** | REST API | None documented | JSON, XML | JSON Path patterns |
| **KEGG** | REST-like API | 10 req/sec | TXT, JSON | Regex patterns |
| **RefMet** | REST API, Local CSV | None documented | JSON | JSON Path patterns |
| **ChEBI** | SOAP Web Services | None documented | XML | XML Path patterns |
| **RaMP DB** | REST API, R package | None documented | JSON | JSON Path patterns |
| **PubChem** | PUG REST API | 5 req/sec, 400 req/min | JSON, XML, SDF | JSON Path patterns |
| **SPOKE** | ArangoDB queries | N/A (local) | JSON | JSON Path patterns |
| **Extension Graph** | ArangoDB queries | N/A (local) | JSON | JSON Path patterns |
| **UniProt** | REST API | None documented | JSON | JSON Path patterns |
| **UMLS** | REST API | None documented | JSON | JSON Path patterns |

## External Mapping Resources & APIs

Detailed documentation on the external APIs and resources used for mapping:

*   **ChEBI:** [Chemical Entities of Biological Interest API](./chebi_api_documentation.md)
*   **KEGG:** [Kyoto Encyclopedia of Genes and Genomes API](./kegg_api_documentation.md)
*   **PubChem:** [PubChem PUG REST API](./pubchem_api_documentation.md)
*   **RaMP-DB:** [Relational Database of Metabolomics Pathways API](./rampdb_api_documentation.md)
*   **RefMet:** [Reference Metabolomics API](./refmet_api_documentation.md)
*   **UniChem:** [Structure-based Chemical Identifier Mapping API](./unichem_api_documentation.md)
*   **UniProt:** [UniProt REST API (ID Mapping & Search)](./uniprot_api_documentation.md)
*   **UMLS:** [UMLS Terminology Services (UTS) REST API](./umls_api_documentation.md)

## Biomapper-Specific Ontologies & Data Sources

Documentation on ontologies or data formats specific to data sources integrated with Biomapper:

*   **Arivale:** [Arivale Ontology Details](./arivale_ontologies.md)
*   **Extension Graph:** [Extension Graph Ontology Details](./extension_graph_ontologies.md)
*   **SPOKE:** [SPOKE Ontology Details](./spoke_ontologies.md)

## Next Steps

Based on the documented resources, the following steps are planned:

1.  **Implement UniProt Name Client:** Develop a client to query the UniProt search API (`/uniprotkb/search`) to map protein names/symbols to UniProt IDs.
2.  **Implement UMLS Client:** Develop a client to query the UMLS Terminology Services API (`/search`) to map terms to CUIs, handling the necessary authentication.
3.  **Database Integration:** Add `UniProt_NameSearch` and `UMLS_Metathesaurus` as resources in the `metamapper.db`.
4.  **Executor Integration:** Update the `RelationshipMappingExecutor` to dispatch mapping steps to the new UniProt and UMLS clients based on resource ID/name.
5.  **Define Mapping Paths:** Create new `MappingPath` entries in the database that utilize these new resources (e.g., `Endpoint Ontology (Gene Name) -> UniProt_NameSearch -> UniProtKB ID`, `Endpoint Ontology (Term) -> UMLS_Metathesaurus -> CUI`).
