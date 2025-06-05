# SPOKE Nodes Parser - Implementation Feedback

**Date:** 2025-06-03
**Prompt ID:** 2025-06-03-222827-parse-spoke-nodes
**Script Location:** `/home/ubuntu/biomapper/scripts/utils/parse_spoke_nodes.py`

## Schema Discovery Results

Based on analysis of the SPOKE v6 data file (`/home/ubuntu/data/spokeV6.jsonl`), the following schema was discovered:

### Data Structure
- **Format:** JSONL (JSON Lines) - one JSON object per line
- **Primary object type:** Nodes (with `"type": "node"`)
- **Total unique entity types:** 16 different labels found

### Top-Level JSON Fields
1. **type**: Always "node" for node entries
2. **id**: Numeric string identifier for the node
3. **labels**: Array containing entity type(s) (typically single value)
4. **properties**: Object containing all entity-specific attributes

### Entity Distribution (from full file scan)
```
Protein         4,070,297
Compound        2,358,629
Location           61,689
Gene               20,647
Anatomy            15,404
Variant            12,327
Disease            11,347
EC                  8,360
ClinicalLab         1,694
Symptom             1,681
Pathway               316
Organism               56
Reaction               37
CellType                6
ProteinDomain           2
SideEffect              1
```

### Key Property Fields by Entity Type

#### Protein
- **identifier**: UniProt accession (primary ID)
- **name**: Protein name with organism suffix
- **description**: Functional description
- **refseq**: RefSeq identifiers (list)
- **chembl_id**: ChEMBL identifier
- **EC**: EC numbers (list)
- **gene**: Associated gene identifiers (list)
- **org_name**: Organism name
- **reviewed**: Review status from UniProt

#### Compound
- **identifier**: InChIKey (primary ID)
- **name**: Chemical name
- **smiles**: SMILES string representation
- **standardized_smiles**: Canonical SMILES
- **synonyms**: Alternative names (list)
- **pubchem_compound_ids**: PubChem CIDs (list)
- **pdb_ligand_ids**: PDB ligand identifiers (list)

#### Gene
- **identifier**: Entrez Gene ID (numeric)
- **name**: Gene symbol
- **description**: Gene description
- **ensembl**: Ensembl gene identifier
- **synonyms**: Alternative gene symbols (list)
- **chromosome**: Chromosome location

#### Disease
- **identifier**: Disease Ontology ID (DOID)
- **name**: Disease name
- **omim_list**: OMIM identifiers (list)
- **mesh_list**: MeSH identifiers (list)

#### Anatomy
- **identifier**: UBERON ontology ID
- **name**: Anatomical structure name
- **mesh_id**: MeSH identifier
- **bto**: BRENDA Tissue Ontology IDs (list)

## Script Design Decisions

### 1. Entity Mapping
The script maps SPOKE labels directly to output files without attempting Biolink normalization, as SPOKE uses its own entity type vocabulary:
- `Protein` → `spoke_proteins.csv`
- `Compound` → `spoke_metabolites.csv` (semantic mapping to metabolites)
- `Gene` → `spoke_genes.csv`
- `Disease` → `spoke_diseases.csv`
- And additional types as found in the data

### 2. Field Extraction Strategy
- **ID field**: Uses `properties.identifier` when available, falls back to top-level `id`
- **Name field**: Extracted from `properties.name`
- **Description**: Extracted from `properties.description` when present
- **Synonyms**: Looks for both `synonyms` and `synonym` fields
- **Cross-references**: Entity-specific extraction logic for different xref types

### 3. Cross-Reference Handling
The script builds structured xrefs based on entity type:
- **Proteins**: RefSeq, ChEMBL, EC numbers
- **Compounds**: PubChem CIDs, PDB ligand IDs
- **Genes**: Ensembl IDs
- **Diseases**: OMIM, MeSH
- **Anatomy**: MeSH, BTO

### 4. Data Processing Approach
- **Streaming**: Processes file line-by-line to handle large size efficiently
- **Error handling**: Captures and reports JSON parsing errors without failing
- **Progress reporting**: Updates every 100,000 nodes processed
- **CSV encoding**: UTF-8 with proper handling of special characters

## Assumptions Made

1. **Primary identifiers**: The `identifier` field in properties contains the primary ID for each entity
2. **Single labels**: Most nodes have a single label (entity type)
3. **Missing fields**: Empty strings used for missing optional fields
4. **List delimiters**: Pipe character (|) for multiple values within a field, semicolon (;) for sub-items

## Potential Issues/Limitations

1. **Memory usage**: While streaming helps, the CSV writers remain open throughout processing
2. **Error recovery**: JSON parsing errors on individual lines are skipped but may indicate data quality issues
3. **Field variations**: Some entities may have additional useful fields not captured in the current extraction
4. **Large file processing**: The full extraction may take considerable time given 6.5M+ nodes

## Execution Summary

### To run schema discovery:
```bash
python /home/ubuntu/biomapper/scripts/utils/parse_spoke_nodes.py --explore
```

### To run full extraction:
```bash
python /home/ubuntu/biomapper/scripts/utils/parse_spoke_nodes.py
```

The script will:
1. Create the output directory if it doesn't exist
2. Generate separate CSV files for each entity type
3. Report progress during processing
4. Provide a summary of entities extracted

## Script Status

✅ **Ready for USER testing**

The script has been created and is ready for execution. It includes both schema exploration and full extraction capabilities as requested.