# RefMet Ontological Resources

## Overview

RefMet (Reference list of Metabolite nomenclature) is a standardized reference nomenclature for both discrete metabolite structures and metabolite species identified in metabolomics experiments. Developed by the Metabolomics Workbench, RefMet addresses the critical need for consistent metabolite naming to enable comparison across different experiments and studies.

### Purpose and Scope

RefMet was created to overcome limitations of using identifiers like PubChem IDs and InChIKeys alone, which can vary depending on salt forms and stereochemical details. It is particularly valuable for metabolite species (especially lipids) that are often reported by MS methods as isobaric mixtures (such as PC 34:1 and TG 54:2) rather than discrete structures.

The database was built from:
- Over 700,000 metabolite names
- Extracted from 3,500+ MS and NMR studies on the Metabolomics Workbench
- Curated specifically for analytical chemistry applications
- Linked to a comprehensive metabolite classification system using LIPID MAPS and ClassyFire

## Available Identifiers and Classification

### Core Identifiers
- **RefMet ID**: Primary identifier (e.g., REFMET:1)
- **RefMet Name**: Standardized metabolite name
- **Systematic Name**: IUPAC or other systematic nomenclature
- **Common Synonyms**: Alternative names
- **Formula**: Molecular formula
- **SMILES**: Simplified molecular-input line-entry system
- **InChIKey**: International Chemical Identifier hash

### Metabolite Classification
- **Main Class**: Primary chemical class (e.g., Fatty Acids, Carbohydrates)
- **Sub Class**: More specific classification
- **Super Class**: Broader classification grouping

### Cross-References to Other Databases
- **HMDB**: Human Metabolome Database IDs
- **KEGG**: KEGG Compound IDs
- **PubChem**: PubChem Compound IDs
- **ChEBI**: Chemical Entities of Biological Interest IDs
- **LIPID MAPS**: Lipid classification IDs
- **CAS**: Chemical Abstracts Service registry numbers
- **MetaCyc**: MetaCyc compound IDs

## Data Structure

RefMet organizes metabolites into a hierarchical classification system:

1. **Super Class**: Broadest level of classification (e.g., Aliphatics)
2. **Main Class**: Primary classification (e.g., Fatty acids)
3. **Sub Class**: Specific subtype (e.g., Monocarboxylic acids)

Each metabolite entry contains:
- Core identifiers and names
- Structural properties
- Classification information
- Cross-references to other databases

## Query Patterns

Typical query patterns for extracting ontological information from RefMet:

1. **Basic Entity Lookup**:
   ```sql
   SELECT * FROM refmet_entities 
   WHERE refmet_id = 'REFMET:1'
   ```

2. **Classification-based Queries**:
   ```sql
   SELECT refmet_id, refmet_name
   FROM refmet_entities
   WHERE main_class = 'Fatty acids'
   AND sub_class = 'Monocarboxylic acids'
   ```

3. **Cross-Reference Mapping**:
   ```sql
   SELECT refmet_id, refmet_name, hmdb_id, pubchem_id
   FROM refmet_entities
   WHERE hmdb_id IS NOT NULL
   ```

4. **Structure-based Queries**:
   ```sql
   SELECT refmet_id, refmet_name
   FROM refmet_entities
   WHERE formula = 'C6H12O6'
   ```

## Metadata Cache Considerations

When designing the metadata cache for RefMet data:

1. **Standardized Names**: Use RefMet names as the standard for metabolite naming
2. **Classification Lookups**: Enable searching by chemical classification
3. **Version Tracking**: Monitor updates to RefMet database
4. **Naming Consistency**: Resolve conflicts between RefMet and other nomenclature sources
5. **Classification Integration**: Map RefMet classifications to other ontologies

## Example Mapping Tables

Example table schemas for storing RefMet data:

```sql
-- Core RefMet entities
CREATE TABLE refmet_entities (
    refmet_id TEXT PRIMARY KEY,
    refmet_name TEXT,
    systematic_name TEXT,
    formula TEXT,
    exact_mass REAL,
    inchikey TEXT,
    smiles TEXT,
    super_class TEXT,
    main_class TEXT,
    sub_class TEXT,
    refmet_version TEXT,
    last_updated DATE
);

-- Cross-references to other databases
CREATE TABLE refmet_xrefs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    refmet_id TEXT REFERENCES refmet_entities(refmet_id),
    database_name TEXT, -- e.g., 'HMDB', 'KEGG', 'PubChem'
    database_id TEXT,
    UNIQUE(refmet_id, database_name, database_id)
);

-- Synonyms for metabolites
CREATE TABLE refmet_synonyms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    refmet_id TEXT REFERENCES refmet_entities(refmet_id),
    synonym TEXT,
    synonym_type TEXT, -- 'common', 'systematic', etc.
    UNIQUE(refmet_id, synonym)
);
```

## Integration with Other Resources

RefMet complements SPOKE, RaMP DB, UniChem, ChEBI, and other resources in these ways:

1. **Metabolite Focus**: Specifically designed for metabolomics research
2. **Standardized Nomenclature**: Provides consistent naming conventions
3. **Chemical Classification**: Organizes metabolites into meaningful chemical classes
4. **Metabolomics Workbench Integration**: Direct connection to experimental metabolomics data
5. **Metabolite Sets**: Groups metabolites by biochemical pathways and functions

## Access Patterns and Tools

RefMet provides multiple access options:

### Web Interfaces
1. **Browse/Search/Download**: Direct access to RefMet database
2. **Classification Viewer**: View RefMet classification hierarchy
3. **Name Conversion Interface**: Map metabolite names to RefMet nomenclature
4. **Core Structures Browser**: View core structures of RefMet sub-classes
5. **Lipid Notation**: Specialized tools for lipid m/z calculation

### Mobile Applications
1. **NMDR Metabolite Summary App**: Search studies by analytical technique, sample source, species, and metabolite class
2. **RefMet Search App**: Search by name and/or neutral mass
3. **RefMet Name Conversion App**: Convert metabolite names to RefMet nomenclature with structure display and m/z calculation
4. **RefMet MS Search App**: Search using m/z values
5. **Lipid Mass/Formula App**: Calculate lipid neutral mass and m/z for over 160 lipid species

### Programmatic Access
1. **R Package**: Available on GitHub for batch conversion and metadata access
   - Map metabolite names to RefMet nomenclature
   - Access RefMet metadata
   - Perform plotting and saving functions
   - Run as Shiny apps on local R installations

2. **Python Script**: Convert metabolite names to RefMet nomenclature
   - REFMET_post.py for batch processing

3. **REST API**: Programmatic access via Metabolomics Workbench

4. **Batch Downloads**: Complete database available for download

5. **SQL Database**: Direct database access for partners

## Use Cases in Biomapper

RefMet is particularly valuable for:

1. **Metabolite Name Standardization**: Providing canonical names for metabolites
2. **Chemical Classification**: Organizing compounds by structural features
3. **Cross-database Mapping**: Connecting metabolite identifiers across resources
4. **Metabolomics Data Integration**: Supporting analysis of metabolomics experiments
5. **Name Resolution**: Disambiguating complex metabolite nomenclature
6. **Lipid Nomenclature**: Handling isobaric mixtures reported in MS data
7. **Meta-Analysis Support**: Facilitating cross-study comparisons 
8. **Systems Biology Applications**: Supporting integration with pathway and network analysis

## Implementation Recommendations

When integrating RefMet into the Biomapper metadata cache:

1. **Name Conversion Pipeline**: Implement the RefMet name conversion functionality using their Python or R tools
2. **Classification Integration**: Store the hierarchical classification from LIPID MAPS and ClassyFire
3. **Completeness Awareness**: Note that RefMet is a work-in-progress and many metabolite names from experiments may not currently map to RefMet identifiers
4. **Mobile-Friendly API**: Consider implementing APIs similar to the mobile applications for enhanced usability
5. **Batch Processing**: Support batch conversion for metabolite name lists

## Citation

The information in this document is derived from the RefMet documentation provided by Metabolomics Workbench.
