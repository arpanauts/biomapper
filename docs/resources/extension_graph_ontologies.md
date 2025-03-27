# Extension Graph Ontological Resources

## Overview

The Extension Graph is a supplementary knowledge graph that complements SPOKE by providing additional biological entity relationships that may not be present in SPOKE. As outlined in Biomapper's hybrid architecture, the Extension Graph uses the same ArangoDB technology as SPOKE but contains custom data curated specifically for Biomapper's needs, such as FDA UNII data and other specialized ontologies.

## Purpose and Scope

The Extension Graph serves several key purposes:

1. **Fill SPOKE Gaps**: Provide ontological mappings for entities not covered in SPOKE
2. **Incorporate Proprietary Data**: Store mappings that may not be publicly available
3. **Support Custom Relationships**: Create application-specific relationships between entities
4. **Enable Rapid Updates**: Allow additions without waiting for SPOKE release cycles
5. **Preserve SPOKE Independence**: Function when SPOKE is unavailable or deprecated

## Node Types and Ontologies

### Compound / Chemical Entities
- **FDA UNII**: FDA Unique Ingredient Identifiers
- **EPA CompTox**: EPA's Computational Toxicology identifiers
- **eCFR**: Electronic Code of Federal Regulations identifiers
- **EU EINECS**: European Inventory of Existing Commercial Chemical Substances
- **Custom Compounds**: Proprietary or application-specific compounds

### Genes and Proteins
- **RefSeq**: NCBI Reference Sequence identifiers
- **HGNC**: HUGO Gene Nomenclature Committee identifiers
- **MGI**: Mouse Genome Informatics identifiers (for model organism mapping)
- **Regulatory Elements**: Promoters, enhancers, and other regulatory regions

### Assays and Measurements
- **LOINC**: Logical Observation Identifiers Names and Codes
- **CDISC**: Clinical Data Interchange Standards Consortium terms
- **Instrument-specific Codes**: Identifiers for specific analytical platforms
- **Units of Measurement**: UCUM and other measurement unit standards

### Food and Nutrition
- **FoodData Central**: USDA food composition identifiers
- **LanguaL**: Food description thesaurus codes
- **Supplement Facts**: Dietary supplement ingredients and formulations
- **Brand-specific Products**: Commercial food and supplement products

## Relationships and Mappings

The Extension Graph contains these key relationship types:

1. **equivalentTo**: Identity mappings between identifiers from different systems
2. **similarTo**: High-confidence similarity relationships (not exact equivalence)
3. **measurementOf**: Links between assays/measurements and the entities they detect
4. **regulatedBy**: Regulatory relationships for genes, compounds, or products
5. **foundIn**: Source relationships for compounds (e.g., compounds found in foods)

## Data Structure

The Extension Graph follows ArangoDB's structure:

- **Nodes Collection**: Contains document entities with:
  - `type`: Entity type (Compound, Gene, Assay, etc.)
  - `name`: Human-readable name
  - `properties`: Map of typed properties, including external identifiers

- **Edges Collection**: Contains relationships with:
  - `label`: Relationship type (equivalentTo, similarTo, etc.)
  - `from` and `to`: References to source and target nodes
  - `properties`: Additional relationship metadata, including confidence scores

## Query Patterns

Example AQL queries for the Extension Graph:

1. **FDA UNII to Other Identifiers**:
   ```aql
   FOR node IN Nodes
     FILTER node.type == "Compound" AND node.properties.unii != null
     RETURN {
       unii: node.properties.unii,
       chebi: node.properties.chebi,
       inchikey: node.properties.inchikey,
       name: node.name
     }
   ```

2. **Food to Compound Mapping**:
   ```aql
   FOR edge IN Edges
     FILTER edge.label == "foundIn"
     LET compound = DOCUMENT(edge._from)
     LET food = DOCUMENT(edge._to)
     RETURN {
       compound_id: compound.properties.identifier,
       compound_name: compound.name,
       food_id: food.properties.identifier,
       food_name: food.name
     }
   ```

3. **Assay to Metabolite Mapping**:
   ```aql
   FOR edge IN Edges
     FILTER edge.label == "measurementOf"
     LET assay = DOCUMENT(edge._from)
     LET metabolite = DOCUMENT(edge._to)
     RETURN {
       assay_id: assay.properties.loinc,
       assay_name: assay.name,
       metabolite_id: metabolite.properties.hmdb,
       metabolite_name: metabolite.name
     }
   ```

## Metadata Cache Considerations

When designing the metadata cache for Extension Graph data:

1. **Layered Priorities**: Define clear precedence when conflicts arise with SPOKE
2. **Provenance Tracking**: Mark which mappings came from the Extension Graph
3. **Confidence Scoring**: Include confidence metrics for each mapping
4. **Transparency**: Make clear which mappings are curated vs. automatically generated
5. **Versioning**: Track versions of the Extension Graph to manage updates

## Example Mapping Tables

Example table schemas for storing Extension Graph mappings:

```sql
-- FDA UNII compound mappings
CREATE TABLE unii_mappings (
    unii_id TEXT PRIMARY KEY,
    compound_name TEXT,
    chebi_id TEXT,
    pubchem_id TEXT,
    inchikey TEXT,
    source TEXT DEFAULT 'Extension Graph',
    confidence REAL,
    last_updated DATE
);

-- Food compound mappings
CREATE TABLE food_compound_mappings (
    food_id TEXT,
    compound_id TEXT,
    relationship_type TEXT, -- e.g., 'foundIn', 'metabolizedTo'
    amount TEXT, -- e.g., '2mg/100g'
    source TEXT DEFAULT 'Extension Graph',
    confidence REAL,
    PRIMARY KEY (food_id, compound_id, relationship_type)
);

-- Assay mappings
CREATE TABLE assay_entity_mappings (
    assay_id TEXT, -- e.g., LOINC code
    entity_id TEXT, -- e.g., HMDB ID
    entity_type TEXT, -- e.g., 'Metabolite', 'Protein'
    measurement_type TEXT, -- e.g., 'concentration', 'activity'
    units TEXT,
    source TEXT DEFAULT 'Extension Graph',
    PRIMARY KEY (assay_id, entity_id)
);
```

## Current Development Status

The Extension Graph is under active development with these priorities:

1. **FDA UNII Integration**: Complete set of FDA ingredient identifiers with mappings
2. **Assay Standardization**: Mapping between commercial lab tests and biological entities
3. **Food-Compound Relationships**: Detailed mapping of food ingredients to compounds
4. **Custom Ontologies**: Specialized ontologies for Biomapper's specific domains
5. **Client Applications**: Connectors that leverage the Extension Graph for mapping

## Comparison with SPOKE

Extension Graph differs from SPOKE in several important ways:

| Feature | Extension Graph | SPOKE |
|---------|----------------|-------|
| Focus | Application-specific gaps | Comprehensive biomedical knowledge |
| Update Cycle | Rapid, as-needed | Periodic releases |
| Data Sources | Custom, proprietary, specialized | Established public databases |
| Access Control | Can include restricted data | Primarily public data |
| Size | Targeted, focused | Large-scale (43M+ nodes) |
| Integration | Tightly coupled with Biomapper | General-purpose resource |

## Integration Strategy

The Extension Graph integrates with other resources through:

1. **Unified Schema**: Follows the same schema patterns as SPOKE
2. **Transparent Layering**: Clear indication of which graph provided mappings
3. **Fallback Chains**: Automatic use when primary sources lack mappings
4. **Bidirectional Synchronization**: Periodic reconciliation with SPOKE updates
5. **Configuration-driven Integration**: Easy enabling/disabling via configuration
