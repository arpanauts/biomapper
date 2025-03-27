# ChEBI Ontological Resources

## Overview

ChEBI (Chemical Entities of Biological Interest) is a freely available database of molecular entities focused on small chemical compounds. It provides a structured classification of molecular entities, particularly those with relevance to biological systems. This document catalogs the ontological information available in ChEBI that can be leveraged in Biomapper's metadata cache.

## Available Identifiers and Classification

### Core Identifiers
- **ChEBI ID**: Primary identifier (e.g., CHEBI:15377 for glucose)
- **IUPAC Name**: Systematic chemical name
- **Synonyms**: Common names and alternative nomenclature
- **InChI**: International Chemical Identifier
- **InChIKey**: Hashed version of InChI for easier searching
- **SMILES**: Simplified molecular-input line-entry system
- **Formula**: Molecular formula

### Classification Hierarchies
- **Chemical Structure**: Based on structural features
- **Role**: Biological role, application, etc.
- **Subatomic Particle**: Fundamental particles
- **Chemical Entity**: General classification

### Cross-References to Other Databases
- **CAS Registry**: Chemical Abstracts Service registry numbers
- **KEGG COMPOUND**: KEGG compound IDs
- **HMDB**: Human Metabolome Database IDs
- **PubChem**: PubChem Compound IDs
- **DrugBank**: DrugBank IDs
- **MetaCyc**: MetaCyc compound IDs
- **LIPID MAPS**: Lipid classification IDs
- **UniProt**: Protein cross-references
- **Rhea**: Biochemical reactions database
- **Patents**: Patent cross-references

## Ontological Structure

ChEBI's ontology is organized into three main relationship types:

1. **is_a**: Subclass relationships (e.g., glucose is_a monosaccharide)
2. **has_part**: Structural relationships indicating constituents
3. **has_role**: Functional relationships indicating biological/chemical roles

Additional relationships include:

- **has_functional_parent**
- **is_conjugate_acid_of**
- **is_conjugate_base_of**
- **is_tautomer_of**
- **is_enantiomer_of**
- **has_parent_hydride**

## Query Patterns

Typical query patterns for extracting ontological information from ChEBI:

1. **Basic Entity Lookup**:
   ```sql
   SELECT * FROM chebi_entities 
   WHERE chebi_id = 'CHEBI:15377'
   ```

2. **Ontological Relationships**:
   ```sql
   SELECT child_id, relationship_type
   FROM chebi_ontology
   WHERE parent_id = 'CHEBI:15377'
   ```

3. **Database Cross-References**:
   ```sql
   SELECT database_name, database_id
   FROM chebi_database_refs
   WHERE chebi_id = 'CHEBI:15377'
   ```

4. **Structural Classification**:
   ```sql
   -- Find all monosaccharides
   SELECT chebi_id, name
   FROM chebi_entities
   JOIN chebi_ontology ON chebi_entities.chebi_id = chebi_ontology.child_id
   WHERE parent_id = 'CHEBI:35366' -- Monosaccharide
   AND relationship_type = 'is_a'
   ```

## Metadata Cache Considerations

When designing the metadata cache for ChEBI data:

1. **Primary Keys**: Use ChEBI IDs as primary keys
2. **Ontological Relationships**: Store relationships for classification-based queries
3. **Structural Properties**: Cache structural information for similarity searches
4. **Release Versioning**: Track ChEBI release versions used for each entry
5. **Update Strategy**: Plan for regular updates as ChEBI releases new versions

## Example Mapping Tables

Example table schemas for storing ChEBI data:

```sql
-- Core ChEBI entities
CREATE TABLE chebi_entities (
    chebi_id TEXT PRIMARY KEY,
    name TEXT,
    definition TEXT,
    iupac_name TEXT,
    formula TEXT,
    inchi TEXT,
    inchikey TEXT,
    smiles TEXT,
    mass REAL,
    charge INTEGER,
    chebi_version TEXT,
    last_updated DATE
);

-- Cross-references to other databases
CREATE TABLE chebi_xrefs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chebi_id TEXT REFERENCES chebi_entities(chebi_id),
    database_name TEXT, -- e.g., 'HMDB', 'KEGG', 'PubChem'
    database_id TEXT,
    UNIQUE(chebi_id, database_name, database_id)
);

-- Ontological relationships
CREATE TABLE chebi_ontology (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    parent_id TEXT REFERENCES chebi_entities(chebi_id),
    child_id TEXT REFERENCES chebi_entities(chebi_id),
    relationship_type TEXT, -- 'is_a', 'has_part', 'has_role', etc.
    UNIQUE(parent_id, child_id, relationship_type)
);
```

## Integration with Other Resources

ChEBI complements SPOKE, RaMP DB, UniChem, and other resources in these ways:

1. **Authoritative Chemical Classifications**: Provides structured classification not present in other databases
2. **Biological Roles**: Annotates chemicals with biological roles and applications
3. **Comprehensive Cross-References**: Links to numerous specialized chemical databases
4. **Structural Relationships**: Connects compounds based on chemical structure
5. **Manually Curated Data**: Maintained by expert curators ensuring high data quality

## Access Patterns

ChEBI can be accessed through:

1. **Web Service**: REST and SOAP API
2. **SPARQL Endpoint**: For semantic web queries
3. **Full Downloads**: Monthly releases available in various formats
4. **OntoBee**: Linked open data representation
5. **Web Interface**: Browser-based search and navigation
