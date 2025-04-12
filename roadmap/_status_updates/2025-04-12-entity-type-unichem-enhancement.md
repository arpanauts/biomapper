# Entity Type Expansion and UniChem Enhancement

## 1. Recent Accomplishments

- Added entity_type column to the resources table in metamapper.db to support different entity types (metabolite, protein, gene, etc.)
- Properly categorized existing resources with appropriate entity types (metabolites for most resources, "all" for SPOKE)
- Added entity_type column to property_extraction_configs table to enable entity-specific property extractions
- Enhanced UniChem client with 13 additional chemical database sources, significantly expanding mapping capabilities:
  - Added support for LIPID MAPS, ZINC, ChemSpider, Atlas Chemical Database, Guide to Pharmacology
  - Added CAS Registry Numbers, BindingDB, MolPort, EPA CompTox, BRENDA Database
  - Added MetaboLights and Selleck Chemicals
- Created a mapping_paths_history system to track the evolution of mapping paths over time
- Implemented database triggers for automatic logging of mapping path changes
- Added utility functions for analyzing mapping path performance and history

## 2. Current Project State

- The metamapper.db database schema now supports entity type differentiation, enabling expansion beyond metabolites
- UniChem integration has been significantly enhanced with 13 new chemical database sources
- A total of 22 property extraction configurations now exist for UniChem, covering a wide range of chemical databases
- The mapping path history system is in place to track changes to mapping paths over time
- All 8 configured resources (ChEBI, PubChem, MetabolitesCSV, SPOKE, KEGG, UniChem, RefMet, RaMP-DB) have been properly categorized by entity type
- The core mapping framework is now poised for expansion to protein entities while maintaining strong metabolite mapping capabilities
- Database tools are now available for examining how mapping paths evolve and which ones perform best

## 3. Technical Context

### Entity Type Implementation
- Added "entity_type" column to resources table with default value "metabolite"
- Established a controlled set of entity types: metabolite, protein, gene, disease, pathway, and all
- Most resources tagged as "metabolite", while SPOKE is tagged as "all" to reflect its heterogeneous nature
- Property extraction configurations now include entity type, enabling property-specific filtering
- This design allows for implicit entity type handling based on ontology types (e.g., UniProt → protein, PubChem → metabolite)

### UniChem Enhancements
- Extended property extraction configurations for 13 additional UniChem sources
- Updated the UniChem client SOURCE_IDS mapping to include the new source IDs
- Enhanced _process_compound_result and _get_empty_result methods to handle new sources
- Maintained backward compatibility with existing mappings
- Each new source has its own JSON path extraction pattern for reliable property extraction

### Mapping Path History System
- Created mapping_paths_history table to track the creation, updates, and deletion of mapping paths
- Implemented database triggers to automatically log mapping path changes:
  - trg_mapping_paths_after_insert: Records new mapping paths
  - trg_mapping_paths_after_update: Records updates to existing paths
  - trg_mapping_paths_after_delete: Records when paths are deleted
- Added utility functions for analyzing mapping path evolution:
  - log_mapping_path_change: Manually log changes with specific reasons
  - get_mapping_path_history: Retrieve history for specific paths or types
  - get_path_evolution: Track how source→target mappings evolved over time
  - compare_path_versions: Compare different versions of the same path

## 4. Next Steps

- Create mapping paths that leverage the newly added UniChem sources:
  - Establish direct paths for high-value conversions (e.g., LIPID MAPS → CHEBI)
  - Add multi-step paths that utilize intermediate IDs (e.g., NAME → ChemSpider → PUBCHEM)
  - Create paths specifically for lipid compounds via LIPID MAPS

- Test the expanded UniChem integration:
  - Verify extraction success for each new property
  - Measure mapping success rates across different source databases
  - Identify which new sources provide the highest mapping value

- Begin protein entity type implementation:
  - Add UniProt as a protein-specific resource
  - Create property extraction configurations for protein properties
  - Establish initial mapping paths for protein identifiers

- Implement the SQLite mapping cache:
  - Design schema that aligns with the entity-type expanded architecture
  - Focus on caching high-value mappings first
  - Connect the cache with the mapping_paths_history system for performance analysis

## 5. Open Questions & Considerations

- What's the optimal strategy for creating mapping paths that leverage the 13 new UniChem sources?
  - Should we create paths for all possible combinations, or focus on high-value mappings?
  - What metrics should we use to determine "high-value" in this context?

- How should we handle potential inconsistencies in identifier mappings across different sources?
  - For example, if LIPID MAPS and ChemSpider disagree on a mapping to PubChem
  - Should we implement a voting or confidence-scoring mechanism?

- Do we need to create entity-specific mapping dispatcher logic?
  - Current implicit approach relies on ontology types naturally mapping to entity types
  - As we add more entities, will this approach scale or do we need explicit dispatcher logic?

- How should we approach the protein entity implementation?
  - Should we prioritize UniProt or PDB as the primary protein database?
  - What are the most valuable protein identifier cross-references to implement first?

- Should we consider performance implications of the mapping_paths_history system?
  - Database triggers add overhead to mapping path operations
  - For production environments, would a scheduled batch logging approach be more efficient?
