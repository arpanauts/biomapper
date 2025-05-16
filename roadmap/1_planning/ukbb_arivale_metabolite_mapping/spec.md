# UKBB-Arivale Metabolite Mapping: Technical Specification

## Background

This document outlines the technical specifications for extending the Biomapper framework to support metabolite mapping between UKBB and Arivale datasets. Based on the current protein mapping pipeline (Phase 1-3) and lessons learned, we aim to develop a solution that maintains architectural consistency while addressing the unique challenges of metabolite mappings.

## Goals

1. Implement a generalized mapping approach for metabolites that leverages the existing iterative mapping strategy
2. Develop robust fallback mechanisms for cases where direct mapping fails
3. Enhance the output format to accommodate both primary mapping results and fallback results with appropriate provenance
4. Validate the mapping approach across UKBB → Arivale metabolites and UKBB → Arivale clinical labs
5. Establish a foundation for future entity-agnostic mapping capabilities

## Requirements

### Functional Requirements

1. **Entity Type Support**
   - Support metabolite entities from UKBB and Arivale datasets
   - Handle both standardized identifiers (PubChem, ChEBI, HMDB) and less formal identifiers (names, clinical codes)
   - Support structural representations (InChI, SMILES)

2. **Mapping Approaches**
   - **Primary Approach**: Apply the iterative mapping strategy from `/home/ubuntu/biomapper/roadmap/technical_notes/core_mapping_logic/iterative_mapping_strategy.md`
   - **Secondary/Fallback Approaches**: Implement tiered fallback mechanisms for unmapped entities:
     - Translator Name Resolver API
     - UMLS concept mapping
     - RAG-based vector similarity search

3. **File Processing**
   - Process UKBB metabolite data files
   - Process Arivale metabolite data files
   - Process Arivale clinical lab data files
   - Support TSV/CSV formats with appropriate header detection

4. **Output Generation**
   - Generate phase-specific output files consistent with protein mapping
   - Include comprehensive metadata for mapping provenance
   - Implement a confidence scoring system that accounts for mapping method
   - Support a tiered output approach that distinguishes primary vs. fallback results

### Non-Functional Requirements

1. **Performance**
   - Optimize for batch processing of metabolite mappings
   - Implement appropriate retry and error handling for external API calls
   - Support caching of intermediate results to avoid redundant processing

2. **Maintainability**
   - Leverage the existing codebase structure to minimize duplication
   - Ensure proper documentation of metabolite-specific components
   - Implement appropriate unit tests for new components

3. **Extensibility**
   - Design for future integration with `metamapper.db`
   - Support eventual expansion to additional entity types beyond proteins and metabolites
   - Allow for pluggable fallback mechanisms

## Architecture

### Key Components

1. **Script Structure**
   - Extend or adapt existing scripts (`map_ukbb_to_arivale.py`, `phase3_bidirectional_reconciliation.py`) to support metabolite mapping
   - Create new metabolite-specific utility scripts as needed, particularly for fallback mechanism integration

2. **Mapping Clients**
   - `UniChemClient`: Primary client for standard metabolite identifier mapping (e.g., PubChem ↔ ChEBI)
   - `TranslatorNameResolverClient`: Client for resolving metabolite names to standardized identifiers
   - `UMLSClient`: Client for mapping concepts via UMLS
   - `RAGMappingClient`: Vector-based approach for similarity-based mapping

3. **Confidence Scoring System**
   - Implement a weighted scoring approach that considers:
     - Mapping method (iterative mapping > name resolution > RAG)
     - Path length/hop count
     - Bidirectional validation status
     - String similarity metrics (for name-based mappings)

4. **Output Format Extensions**
   - Add columns for fallback method provenance
   - Include confidence scores in output
   - Support tiered result presentation

## Data Sources

1. **UKBB Metabolite Data**
   - Source: `/procedure/data/local_data/HPP_PHENOAI_METADATA/UKBB_Metabolites.tsv` (hypothetical)
   - Key columns: TBD based on file analysis

2. **Arivale Metabolite Data**
   - Source: `/procedure/data/local_data/ARIVALE_SNAPSHOTS/metabolomics_metadata.tsv` (hypothetical)
   - Key columns: TBD based on file analysis

3. **Arivale Clinical Lab Data**
   - Source: `/procedure/data/local_data/ARIVALE_SNAPSHOTS/clinical_lab_metadata.tsv` (hypothetical)
   - Key columns: TBD based on file analysis

## Ontology Types

The following ontology types will be relevant for metabolite mapping:

1. **Primary Identifier Types**
   - `PUBCHEM_CID`
   - `CHEBI_ID`
   - `HMDB_ID`
   - `ARIVALE_METABOLITE_ID`
   - `ARIVALE_CLINICAL_LAB_ID`

2. **Secondary Identifier Types**
   - `KEGG_ID`
   - `INCHI`
   - `INCHI_KEY`
   - `SMILES`
   - `METABOLITE_NAME`
   - `CLINICAL_LAB_CODE`

## Integration Points

1. **Existing Phase 1/2/3 Pipeline**
   - Adapt the existing pipeline components to support metabolite mapping
   - Ensure proper column name handling for metabolite-specific identifiers

2. **Mapping Executor**
   - Leverage the existing `MappingExecutor` class for core mapping logic
   - Implement metabolite-specific configurations and path definitions

3. **Fallback Mechanisms**
   - Define clear integration points for fallback mechanism results
   - Implement a consistent approach for combining results from different sources

## Success Metrics

1. **Mapping Coverage**
   - Target at least 30% successful mapping rate for initial implementation
   - Target 50%+ mapping rate with fallback mechanisms

2. **Result Quality**
   - Validate a sample of mappings for accuracy
   - Ensure confidence scores correlate with actual mapping reliability

3. **Performance**
   - Process complete UKBB-Arivale metabolite mapping within reasonable time constraints
   - Handle batch processing efficiently

## Dependencies

1. **External APIs**
   - UniChem API (for identifier translation)
   - Translator Name Resolver API (for name resolution)
   - UMLS API (for concept mapping)

2. **Internal Components**
   - Existing phase 1/2/3 scripts
   - `MappingExecutor` class
   - Configuration systems

## Risks and Mitigations

1. **API Availability Risks**
   - Risk: External APIs might have rate limits or availability issues
   - Mitigation: Implement robust retry logic, caching, and fallback to alternative sources

2. **Data Quality Risks**
   - Risk: Inconsistent naming conventions or malformed identifiers
   - Mitigation: Implement data cleaning/normalization steps and detailed error logging

3. **Performance Risks**
   - Risk: Vector similarity searches might be computationally expensive
   - Mitigation: Implement efficient indexing and filtering approaches

4. **Architectural Risks**
   - Risk: Changes to support metabolites might impact existing protein mapping
   - Mitigation: Proper encapsulation and extensive testing of shared components

## Timeline Considerations

1. Client Development and Testing: 2-3 weeks
2. Core Mapping Strategy Implementation: 1-2 weeks
3. Fallback Mechanism Integration: 2-3 weeks
4. Output Format Enhancement: 1 week
5. End-to-End Testing and Optimization: 1-2 weeks

Total Estimated Timeline: 7-11 weeks
