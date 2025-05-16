# UKBB-Arivale Metabolite Mapping

## Feature Overview
This feature extends the Biomapper mapping capabilities from proteins to metabolites, implementing a consistent approach for mapping UKBB metabolite data to Arivale metabolites and clinical lab results. By leveraging the existing iterative mapping strategy while adding metabolite-specific fallback mechanisms, we will create a robust solution that handles the increased complexity of metabolite mapping.

## Background and Motivation
The Biomapper project has successfully established a foundation for protein mapping between UKBB and Arivale datasets using a three-phase approach (forward mapping, reverse mapping, and bidirectional reconciliation). Metabolites represent the next critical biological entity type to support, but they present unique challenges:

1. Greater identifier complexity and heterogeneity (structural representations like InChI/SMILES alongside traditional identifiers)
2. Less standardized naming conventions
3. More complex many-to-many relationships
4. Fewer universally adopted identifier systems compared to proteins

Building on our successful protein mapping framework while addressing these challenges will significantly enhance Biomapper's utility for comprehensive biological data integration.

## Key Components
1. **Core Iterative Mapping Strategy Implementation**
   - Reuse of existing phase1/2/3 scripts with metabolite-specific configurations
   - UniChem client integration for primary chemical identifier mapping

2. **Fallback Mechanism Framework**
   - Translator Name Resolver client
   - UMLS mapping client
   - RAG-based approach with Qdrant/FastEmbed vector database

3. **Enhanced Output Generation**
   - Extended reconciliation format with fallback method provenance
   - Confidence scoring system
   - Tiered output approach (primary vs. fallback results)

4. **Validation and Quality Assessment**
   - Cross-validation metrics for metabolite mappings
   - Performance analysis of different mapping approaches

## Documents in this Folder
- [Specification](./spec.md) - Detailed technical specifications
- [Design](./design.md) - Architecture and implementation design
- [Task List](./task_list.md) - Implementation breakdown (added when moved to in-progress)

## Related Documents
- [Iterative Mapping Strategy](/home/ubuntu/biomapper/roadmap/technical_notes/core_mapping_logic/iterative_mapping_strategy.md)
- [Phase 3 Bidirectional Reconciliation](/home/ubuntu/biomapper/scripts/phase3_bidirectional_reconciliation.py)
- [UKBB-Arivale Protein Mapping](/home/ubuntu/biomapper/scripts/map_ukbb_to_arivale.py)

## Key Stakeholders
- Data scientists requiring integrated UKBB-Arivale datasets
- Developers maintaining the Biomapper framework
- Researchers examining metabolomic data relationships
