# RefMet/Metabolomics Workbench API Documentation for Biomapper

## 1. Overview

RefMet (Reference list of Metabolite nomenclature) is a standardized reference nomenclature for metabolites developed by the Metabolomics Workbench. It provides consistent naming for both discrete metabolite structures and metabolite species identified in metabolomics experiments, enabling comparison across different studies.

- **Base URL**: `https://www.metabolomicsworkbench.org/rest`
- **Authentication**: Not Required
- **Rate Limits**: No documented limits (implement adaptive rate limiting)
- **Response Format**: JSON, TXT
- **Request Method**: GET

## 2. Entity Types Supported

- `metabolite` (discrete compounds and lipid species)

## 3. API Structure and Contexts

The Metabolomics Workbench REST API is organized into multiple contexts, with RefMet being one of them:

```
https://www.metabolomicsworkbench.org/rest/<context>/<input specification>/<output specification>
```

where:
- `<context>` determines the type of data to access
- `<input specification>` consists of two required parameters: `<input item>/<input value>`
- `<output specification>` consists of one or two parameters: `<output item>/[<output format>]`

Available contexts include:
- `refmet`: RefMet standardized nomenclature
- `compound`: Metabolite structures database
- `study`: Studies in Metabolomics Workbench
- `gene`: Gene data
- `protein`: Protein data
- `moverz`: m/z value information
- `exactmass`: Exact mass information

## 4. RefMet Context API Endpoints

### Get All RefMet Entries
```
https://www.metabolomicsworkbench.org/rest/refmet/all
```
Returns all entries in the RefMet database (note: very large response).

### Get RefMet Entry by Name
```
https://www.metabolomicsworkbench.org/rest/refmet/name/<compound_name>/all
```
Returns all available information for the specified RefMet name.

**Example**:
```bash
curl -X GET "https://www.metabolomicsworkbench.org/rest/refmet/name/Cholesterol/all"
```

### Match Input Name to RefMet Standardized Name
```
https://www.metabolomicsworkbench.org/rest/refmet/match/<input_name>
```
Attempts to convert an input name to standardized RefMet nomenclature.

**Example**:
```bash
curl -X GET "https://www.metabolomicsworkbench.org/rest/refmet/match/LysoPC16:0"
```

### Search by Formula
```
https://www.metabolomicsworkbench.org/rest/refmet/formula/<formula>/all
```
Returns all RefMet entries with the specified molecular formula.

**Example**:
```bash
curl -X GET "https://www.metabolomicsworkbench.org/rest/refmet/formula/C27H46O/all"
```

### Search by Classification
```
https://www.metabolomicsworkbench.org/rest/refmet/main_class/<class_name>/all
```
Returns all RefMet entries in the specified main class.

**Example**:
```bash
curl -X GET "https://www.metabolomicsworkbench.org/rest/refmet/main_class/Sterols/all"
```

## 5. Compound Context API Endpoints

The compound context provides access to the Metabolomics Workbench Metabolite Database:

### Get Compound by Registry Number
```
https://www.metabolomicsworkbench.org/rest/compound/regno/<regno>/all
```
Returns all information for a compound with the specified registry number.

**Example**:
```bash
curl -X GET "https://www.metabolomicsworkbench.org/rest/compound/regno/34361/all"
```

### Get Compound by External ID
```
https://www.metabolomicsworkbench.org/rest/compound/<id_type>/<id>/all
```
Where `<id_type>` can be: pubchem_cid, hmdb_id, kegg_id, chebi_id, or inchi_key

**Example**:
```bash
curl -X GET "https://www.metabolomicsworkbench.org/rest/compound/hmdb_id/HMDB0000012/all"
```

### Get Compound Structure
```
https://www.metabolomicsworkbench.org/rest/compound/regno/<regno>/molfile
```
Returns the chemical structure as a molfile.

**Example**:
```bash
curl -X GET "https://www.metabolomicsworkbench.org/rest/compound/regno/34361/molfile"
```

## 6. Study Context API Endpoints

The study context provides access to studies in the Metabolomics Workbench:

### Get Study Summary
```
https://www.metabolomicsworkbench.org/rest/study/study_id/<study_id>/summary
```
Returns summary information for the specified study.

**Example**:
```bash
curl -X GET "https://www.metabolomicsworkbench.org/rest/study/study_id/ST000001/summary"
```

### Get Metabolites in Study
```
https://www.metabolomicsworkbench.org/rest/study/study_id/<study_id>/metabolites
```
Returns metabolites and annotations detected in the specified study.

**Example**:
```bash
curl -X GET "https://www.metabolomicsworkbench.org/rest/study/study_id/ST000009/metabolites"
```

## 7. Response Formats and Data Structure

### RefMet Entry Structure
A typical RefMet entry includes:

```json
{
  "refmet_name": "Cholesterol",
  "regno": 11,
  "pubchem_cid": 5997,
  "inchi_key": "HVYWMOMLDIMFJA-DPAQBDIFSA-N",
  "exactmass": 386.3549,
  "formula": "C27H46O",
  "sys_name": "cholest-5-en-3beta-ol",
  "main_class": "Sterols",
  "sub_class": "Cholesterol and derivatives",
  "synonyms": [
    "Cholest-5-en-3-ol",
    "5-Cholesten-3beta-ol",
    "(3beta)-Cholest-5-en-3-ol"
  ]
}
```

### RefMet Classification Hierarchy
RefMet organizes metabolites into a three-level hierarchy:

1. **Super Class**: Broadest level (e.g., Sterol Lipids)
2. **Main Class**: Primary classification (e.g., Sterols)
3. **Sub Class**: Specific subtype (e.g., Cholesterol and derivatives)

## 8. Property Extraction Configurations in Biomapper

The following property extraction patterns can be used to extract information from RefMet API responses:

### RefMet Name
- **Property Name**: `refmet_name`
- **Extraction Method**: `json_path`
- **Extraction Pattern**: `$.refmet_name`
- **Sample Data**: Extracts "Cholesterol" from the refmet_name field

### InChIKey
- **Property Name**: `inchikey`
- **Extraction Method**: `json_path`
- **Extraction Pattern**: `$.inchi_key`
- **Sample Data**: Extracts "HVYWMOMLDIMFJA-DPAQBDIFSA-N" from the inchi_key field

### PubChem ID
- **Property Name**: `pubchem_id`
- **Extraction Method**: `json_path`
- **Extraction Pattern**: `$.pubchem_cid`
- **Sample Data**: Extracts "5997" from the pubchem_cid field

### Chemical Formula
- **Property Name**: `formula`
- **Extraction Method**: `json_path`
- **Extraction Pattern**: `$.formula`
- **Sample Data**: Extracts "C27H46O" from the formula field

### HMDB ID
- **Property Name**: `hmdb_id`
- **Extraction Method**: `json_path`
- **Extraction Pattern**: `$.hmdb_id`
- **Sample Data**: Extracts "HMDB0000289" from the hmdb_id field

### KEGG ID
- **Property Name**: `kegg_id`
- **Extraction Method**: `json_path`
- **Extraction Pattern**: `$.kegg_id`
- **Sample Data**: Extracts "C00366" from the kegg_id field

### ChEBI ID
- **Property Name**: `chebi_id`
- **Extraction Method**: `json_path`
- **Extraction Pattern**: `$.chebi_id`
- **Sample Data**: Extracts "17775" from the chebi_id field

## 9. Multi-level Fallback Strategy

The RefMet client in Biomapper implements a three-level fallback strategy:

1. **Local CSV file**: Primary data source (`data/refmet/refmet.csv`)
   - Contains ~187,000 entries for faster and more reliable lookups
   - Avoids API rate limiting and connection issues

2. **REST API endpoints**: Secondary option with "refmet" context
   - Used when entries are not found in the local CSV
   - Provides access to the most up-to-date data

3. **Legacy database endpoints**: Last resort
   - Used for backward compatibility
   - May provide access to older entries

## 10. Common Use Cases

### Convert Non-standard Metabolite Name to RefMet Standard
```python
async def standardize_metabolite_name(input_name):
    """Convert an input metabolite name to RefMet standard nomenclature."""
    # Try to match the input name to a standard RefMet name
    response = await refmet_client.match_name(input_name)
    
    if response and 'refmet_name' in response:
        return response['refmet_name']
    return None
```

### Get Cross-Reference IDs for a Metabolite
```python
async def get_metabolite_cross_references(refmet_name):
    """Get all cross-reference IDs for a metabolite by RefMet name."""
    # Get complete RefMet entry
    response = await refmet_client.get_metabolite_by_name(refmet_name)
    
    if not response:
        return None
    
    # Extract available cross-references
    cross_refs = {}
    for id_type in ['pubchem_cid', 'hmdb_id', 'kegg_id', 'chebi_id']:
        if id_type in response and response[id_type]:
            cross_refs[id_type] = response[id_type]
    
    return cross_refs
```

### Classification-Based Retrieval
```python
async def get_metabolites_by_class(main_class):
    """Get all metabolites in a specific chemical class."""
    response = await refmet_client.get_metabolites_by_class(main_class)
    
    metabolites = []
    if response:
        for entry in response:
            metabolites.append({
                'name': entry.get('refmet_name'),
                'sub_class': entry.get('sub_class'),
                'formula': entry.get('formula')
            })
    
    return metabolites
```

## 11. Error Handling

Common errors when working with the RefMet API:

- **Entity Not Found**: Empty response when a metabolite isn't in the database
- **Malformed Requests**: Incorrect URL structure
- **Server Errors**: Occasional 500-series errors
- **Timeout Issues**: Some queries may take a long time to process

Recommended error handling approach:
```python
try:
    response = await refmet_client.get_metabolite_by_name(name)
    if not response:
        # Fall back to local CSV lookup
        response = refmet_client.lookup_in_local_csv(name)
except Exception as e:
    logger.error(f"Error querying RefMet API: {e}")
    # Implement exponential backoff and retry
```

## 12. URL Construction Issues

The status updates mention issues with RefMet URL construction that need fixing:

```
Current error: 404 Client Error: Not Found for url: 
https://www.metabolomicsworkbench.org/databases/refmet/refmet/name/1/all
```

The URL appears to have duplicate segments ("refmet/refmet"). Correct format should be:
```
https://www.metabolomicsworkbench.org/rest/refmet/name/Cholesterol/all
```

## 13. Integration with Biomapper Workflow

### Mapping Paths
RefMet serves as a valuable resource in many mapping paths:

1. **NAME → REFMET → PUBCHEM/HMDB/KEGG**
   - Standardizes metabolite names and maps to ontological database IDs

2. **CHEBI/PUBCHEM → REFMET → CLASSIFICATION**
   - Maps compound IDs to chemical classifications

3. **NAME → REFMET → FORMULA/INCHIKEY**
   - Provides structural information from non-standard names

### Breadth-First Search Context
In Biomapper's breadth-first search approach:

- RefMet provides standardized metabolite names as a central hub
- It offers connections to multiple ontological databases (HMDB, KEGG, PubChem, ChEBI)
- The local CSV file (~187,000 entries) provides efficient first-pass lookups

## 14. References

- Metabolomics Workbench REST API Documentation: https://www.metabolomicsworkbench.org/tools/mw_rest.php
- RefMet Portal: https://www.metabolomicsworkbench.org/databases/refmet/
- Metabolomics Workbench: https://www.metabolomicsworkbench.org/
