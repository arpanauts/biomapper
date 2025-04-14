# PubChem API Documentation for Biomapper

## 1. Overview

PubChem is an open chemistry database at the National Institutes of Health (NIH). It contains information on chemical structures, identifiers, biological properties, and bioactivity data for over 111 million compounds. This documentation outlines how to access PubChem data programmatically using the PUG (Power User Gateway) REST API.

- **Base URL**: `https://pubchem.ncbi.nlm.nih.gov/rest/pug`
- **Authentication**: Not Required
- **Rate Limits**: 5 requests per second; 400 requests per minute
- **Response Formats**: JSON, XML, SDF, CSV, ASNT, PNG, TXT
- **Request Method**: GET/POST

## 2. Entity Types Supported

PubChem organizes its data into several distinct entity types:

- `compound`: Chemical substance entries (CID)
- `substance`: Depositor-submitted chemical information (SID)
- `assay`: Bioactivity data (AID)
- `gene`: Gene targets (GeneID)
- `protein`: Protein targets (ProteinID)
- `pathway`: Biological pathways
- `cell`: Cell line information
- `taxonomy`: Taxonomic classification of tested species
- `patent`: Patent information for compounds

## 3. PUG REST URL Structure

The PUG REST API follows this general URL pattern:

```
https://pubchem.ncbi.nlm.nih.gov/rest/pug/<input specification>/<operation specification>/[<output specification>][?<operation control>]
```

Where:
- `<input specification>` identifies the records to use
- `<operation specification>` identifies the operation to perform
- `<output specification>` identifies the output format (defaults to JSON)
- `<operation control>` specifies additional parameters

## 4. Input Specification

The input specification follows this pattern:

```
<domain>/<namespace>/<identifiers>
```

Where:
- `<domain>` is the data domain (compound, substance, assay, etc.)
- `<namespace>` is the type of identifier (cid, sid, name, smiles, etc.)
- `<identifiers>` are the actual identifiers (comma-separated or as a range)

### 4.1. Common Domain/Namespace Combinations:

#### Compound Identifiers
- `compound/cid/1,2,3`: Retrieve compounds by PubChem Compound IDs
- `compound/name/aspirin`: Retrieve compound by name
- `compound/smiles/CCO`: Retrieve compound by SMILES notation
- `compound/inchi/InChI=1S/CH4/h1H4`: Retrieve compound by InChI
- `compound/inchikey/VNWKTOKETHGBQD-UHFFFAOYSA-N`: Retrieve compound by InChIKey
- `compound/formula/C6H12O6`: Retrieve compounds by molecular formula

#### Substance Identifiers
- `substance/sid/1,2,3`: Retrieve substances by PubChem Substance IDs
- `substance/sourceid/DS_*/1,2,3`: Retrieve substances by source database IDs

#### Assay Identifiers
- `assay/aid/1,2,3`: Retrieve assays by PubChem Assay IDs
- `assay/type/confirmatory`: Retrieve assays by type

#### Other Domains
- `protein/accession/P12345`: Retrieve protein by accession
- `gene/geneid/1,2,3`: Retrieve genes by Gene IDs
- `pathway/accession/123`: Retrieve pathway by accession
- `taxonomy/taxid/9606`: Retrieve taxonomic information by taxonomy ID

## 5. Operation Specification

The operation specification defines what data to retrieve for the input records:

### 5.1. Record Operations

- `record`: Retrieve full record data
- `property`: Retrieve specific properties
- `synonyms`: Retrieve name synonyms
- `description`: Retrieve textual descriptions
- `classification`: Retrieve classification hierarchy
- `xrefs`: Retrieve cross-references to other databases
- `sids`: Retrieve substance IDs for a compound
- `cids`: Retrieve compound IDs for a substance
- `aids`: Retrieve assay IDs for a compound or substance

### 5.2. Structure Operations

- `substructure`: Perform substructure search
- `superstructure`: Perform superstructure search
- `similarity`: Perform similarity search
- `identity`: Find identical structures

### 5.3. Assay Operations

- `assaysummary`: Retrieve assay summaries
- `concise`: Retrieve concise assay data
- `doseresponse`: Retrieve dose-response data
- `targets`: Retrieve target information

## 6. Output Specification

The output format can be specified as:

- `JSON` (default): JavaScript Object Notation
- `XML`: Extensible Markup Language
- `SDF`: Structure Data Format
- `ASNT/ASNT.txt`: ASNT text format
- `CSV/CSV.txt`: Comma-separated values
- `PNG`: Image format for structure diagrams
- `TXT`: Plain text format

## 7. Common API Endpoints and Examples

### 7.1. Compound Retrieval

#### Get Compound by CID
```
https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/2244/JSON
```
Retrieves full compound record for aspirin (CID 2244) in JSON format.

#### Get Multiple Compounds
```
https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/2244,2245,2246/JSON
```
Retrieves full compound records for multiple CIDs.

#### Get Compound by Name
```
https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/aspirin/JSON
```
Retrieves compound record for aspirin by name.

#### Get Compound by SMILES
```
https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/smiles/CC(=O)OC1=CC=CC=C1C(=O)O/JSON
```
Retrieves compound record for aspirin by SMILES notation.

### 7.2. Property Retrieval

#### Get Selected Properties
```
https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/2244/property/MolecularFormula,MolecularWeight,InChIKey/JSON
```
Retrieves specific properties for aspirin.

#### Get All Properties
```
https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/2244/property/MolecularFormula,XLogP,TPSA,HBondDonorCount,HBondAcceptorCount,RotatableBondCount,HeavyAtomCount,IsomericSMILES,InChI,InChIKey,IUPACName,Title,ExactMass,MonoisotopicMass,ComplexityScore,CanonicalSMILES/JSON
```
Retrieves comprehensive property set for aspirin.

#### Get Chemical Structure
```
https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/2244/PNG
```
Retrieves chemical structure diagram for aspirin as a PNG image.

### 7.3. Cross-Reference Retrieval

#### Get Synonyms
```
https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/2244/synonyms/JSON
```
Retrieves all synonyms for aspirin.

#### Get Substance IDs
```
https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/2244/sids/JSON
```
Retrieves all substance IDs associated with aspirin.

#### Get Database Cross-References
```
https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/2244/xrefs/RegistryID/JSON
```
Retrieves external database identifiers for aspirin.

### 7.4. Structure Searches

#### Similarity Search
```
https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/similarity/smiles/CC(=O)OC1=CC=CC=C1C(=O)O/JSON?Threshold=90
```
Finds compounds with ≥90% similarity to aspirin.

#### Substructure Search
```
https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/substructure/smiles/C(=O)O/JSON
```
Finds compounds containing the carboxyl group.

### 7.5. Classification and Relationships

#### Get Classification
```
https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/2244/classification/JSON
```
Retrieves classification hierarchies for aspirin.

#### Get Related Compounds
```
https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/2244/cids/JSON?cids_type=same_connectivity
```
Retrieves compounds with the same connectivity as aspirin.

### 7.6. Assay Data

#### Get Bioactivity Data
```
https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/2244/assaysummary/JSON
```
Retrieves summaries of bioactivity assays for aspirin.

#### Get Active Assays
```
https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/2244/aids/JSON?aid_type=active
```
Retrieves assay IDs where aspirin showed activity.

## 8. Response Data Structure

### 8.1. Compound Record (JSON)

```json
{
  "PC_Compounds": [
    {
      "id": {"id": {"cid": 2244}},
      "atoms": {...},
      "bonds": {...},
      "coords": [...],
      "charge": 0,
      "props": [
        {
          "urn": {"label": "Molecular Formula", "name": "MolecularFormula"},
          "value": {"sval": "C9H8O4"}
        },
        {
          "urn": {"label": "Molecular Weight", "name": "MolecularWeight"},
          "value": {"fval": 180.16}
        },
        {
          "urn": {"label": "InChI", "name": "InChI"},
          "value": {"sval": "InChI=1S/C9H8O4/c1-6(10)13-8-5-3-2-4-7(8)9(11)12/h2-5H,1H3,(H,11,12)"}
        },
        {
          "urn": {"label": "InChIKey", "name": "InChIKey"},
          "value": {"sval": "BSYNRYMUTXBXSQ-UHFFFAOYSA-N"}
        },
        {
          "urn": {"label": "IUPAC Name", "name": "IUPACName"},
          "value": {"sval": "2-acetyloxybenzoic acid"}
        },
        {
          "urn": {"label": "SMILES", "name": "CanonicalSMILES"},
          "value": {"sval": "CC(=O)OC1=CC=CC=C1C(=O)O"}
        }
      ]
    }
  ]
}
```

### 8.2. Property Data (JSON)

```json
{
  "PropertyTable": {
    "Properties": [
      {
        "CID": 2244,
        "MolecularFormula": "C9H8O4",
        "MolecularWeight": 180.16,
        "InChIKey": "BSYNRYMUTXBXSQ-UHFFFAOYSA-N"
      }
    ]
  }
}
```

### 8.3. Synonym Data (JSON)

```json
{
  "InformationList": {
    "Information": [
      {
        "CID": 2244,
        "Synonym": [
          "Aspirin",
          "Acetylsalicylic acid",
          "2-Acetoxybenzoic acid",
          "ASA",
          "Acetylsalicylate"
        ]
      }
    ]
  }
}
```

## 9. Property Extraction Configurations in Biomapper

The following property extraction patterns can be used to extract information from PubChem API responses:

### 9.1. Compound ID (CID)
- **Property Name**: `pubchem_cid`
- **Extraction Method**: `json_path`
- **Extraction Pattern**: `$.PropertyTable.Properties[0].CID`
- **Sample Data**: Extracts "2244" from the CID field

### 9.2. Molecular Formula
- **Property Name**: `formula`
- **Extraction Method**: `json_path`
- **Extraction Pattern**: `$.PropertyTable.Properties[0].MolecularFormula`
- **Sample Data**: Extracts "C9H8O4" from the MolecularFormula field

### 9.3. Molecular Weight
- **Property Name**: `molecular_weight`
- **Extraction Method**: `json_path`
- **Extraction Pattern**: `$.PropertyTable.Properties[0].MolecularWeight`
- **Sample Data**: Extracts 180.16 from the MolecularWeight field

### 9.4. InChI
- **Property Name**: `inchi`
- **Extraction Method**: `json_path`
- **Extraction Pattern**: `$.PropertyTable.Properties[0].InChI`
- **Sample Data**: Extracts "InChI=1S/C9H8O4/c1-6(10)13-8-5-3-2-4-7(8)9(11)12/h2-5H,1H3,(H,11,12)" from the InChI field

### 9.5. InChI Key
- **Property Name**: `inchikey`
- **Extraction Method**: `json_path`
- **Extraction Pattern**: `$.PropertyTable.Properties[0].InChIKey`
- **Sample Data**: Extracts "BSYNRYMUTXBXSQ-UHFFFAOYSA-N" from the InChIKey field

### 9.6. IUPAC Name
- **Property Name**: `iupac_name`
- **Extraction Method**: `json_path`
- **Extraction Pattern**: `$.PropertyTable.Properties[0].IUPACName`
- **Sample Data**: Extracts "2-acetyloxybenzoic acid" from the IUPACName field

### 9.7. SMILES
- **Property Name**: `smiles`
- **Extraction Method**: `json_path`
- **Extraction Pattern**: `$.PropertyTable.Properties[0].CanonicalSMILES`
- **Sample Data**: Extracts "CC(=O)OC1=CC=CC=C1C(=O)O" from the CanonicalSMILES field

### 9.8. Synonyms (First Name)
- **Property Name**: `name`
- **Extraction Method**: `json_path`
- **Extraction Pattern**: `$.InformationList.Information[0].Synonym[0]`
- **Sample Data**: Extracts "Aspirin" from the first Synonym entry

## 10. Python Example Code

### 10.1. Basic Compound Retrieval

```python
import requests
import json
import time

def get_pubchem_compound(identifier, id_type="cid", properties=None):
    """
    Retrieve compound information from PubChem.
    
    Parameters:
    identifier (str): The compound identifier
    id_type (str): Identifier type (cid, name, smiles, inchi, inchikey, formula)
    properties (list): List of properties to retrieve
    
    Returns:
    dict: The compound data
    """
    base_url = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
    
    if properties:
        # Get specific properties
        url = f"{base_url}/compound/{id_type}/{identifier}/property/{','.join(properties)}/JSON"
    else:
        # Get full record
        url = f"{base_url}/compound/{id_type}/{identifier}/JSON"
    
    try:
        response = requests.get(url)
        # Implement rate limiting
        time.sleep(0.2)  # Ensures we don't exceed 5 requests per second
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error: {response.status_code}")
            print(response.text)
            return None
    except Exception as e:
        print(f"Exception: {str(e)}")
        return None

# Example usage
cid = "2244"  # Aspirin
properties = ["MolecularFormula", "MolecularWeight", "InChIKey", "CanonicalSMILES"]
result = get_pubchem_compound(cid, properties=properties)
print(json.dumps(result, indent=2))
```

### 10.2. Batch Property Retrieval

```python
def get_batch_properties(cids, properties):
    """
    Retrieve properties for multiple compounds in batch.
    
    Parameters:
    cids (list): List of PubChem CIDs
    properties (list): List of properties to retrieve
    
    Returns:
    dict: Properties for each compound
    """
    base_url = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
    
    # Join CIDs with commas
    cid_string = ",".join(map(str, cids))
    
    # Join properties with commas
    property_string = ",".join(properties)
    
    url = f"{base_url}/compound/cid/{cid_string}/property/{property_string}/JSON"
    
    try:
        response = requests.get(url)
        time.sleep(0.2)  # Rate limiting
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error: {response.status_code}")
            print(response.text)
            return None
    except Exception as e:
        print(f"Exception: {str(e)}")
        return None

# Example usage
cids = ["2244", "2662", "1983"]  # Aspirin, Caffeine, Acetaminophen
properties = ["MolecularFormula", "MolecularWeight", "InChIKey"]
batch_results = get_batch_properties(cids, properties)
print(json.dumps(batch_results, indent=2))
```

### 10.3. Compound Search by Name

```python
def search_compound_by_name(name):
    """
    Search for compounds matching a name.
    
    Parameters:
    name (str): Compound name to search for
    
    Returns:
    dict: Matching compounds
    """
    base_url = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
    
    url = f"{base_url}/compound/name/{name}/cids/JSON"
    
    try:
        response = requests.get(url)
        time.sleep(0.2)  # Rate limiting
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error: {response.status_code}")
            print(response.text)
            return None
    except Exception as e:
        print(f"Exception: {str(e)}")
        return None

# Example usage
name = "glucose"
search_results = search_compound_by_name(name)
print(json.dumps(search_results, indent=2))

# Retrieve properties for the first match
if search_results and "IdentifierList" in search_results:
    first_cid = search_results["IdentifierList"]["CID"][0]
    properties = ["MolecularFormula", "MolecularWeight", "InChIKey", "IUPACName"]
    compound_data = get_pubchem_compound(first_cid, properties=properties)
    print(json.dumps(compound_data, indent=2))
```

### 10.4. Similarity Search

```python
def similarity_search(smiles, threshold=90, max_records=10):
    """
    Find compounds similar to a given structure.
    
    Parameters:
    smiles (str): SMILES notation of the query structure
    threshold (int): Similarity threshold (1-100)
    max_records (int): Maximum number of records to return
    
    Returns:
    dict: Similar compounds
    """
    base_url = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
    
    url = f"{base_url}/compound/similarity/smiles/{smiles}/cids/JSON"
    params = {
        "Threshold": threshold,
        "MaxRecords": max_records
    }
    
    try:
        response = requests.get(url, params=params)
        time.sleep(0.2)  # Rate limiting
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error: {response.status_code}")
            print(response.text)
            return None
    except Exception as e:
        print(f"Exception: {str(e)}")
        return None

# Example usage
smiles = "CC(=O)OC1=CC=CC=C1C(=O)O"  # Aspirin
similar_compounds = similarity_search(smiles, threshold=85)
print(json.dumps(similar_compounds, indent=2))
```

## 11. Common Use Cases

### 11.1. Metabolite Identification

```python
def identify_metabolite(inchikey):
    """
    Identify a metabolite by its InChIKey.
    
    Parameters:
    inchikey (str): InChIKey of the metabolite
    
    Returns:
    dict: Metabolite identification information
    """
    base_url = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
    
    # Check if compound exists with this InChIKey
    url = f"{base_url}/compound/inchikey/{inchikey}/cids/JSON"
    
    try:
        response = requests.get(url)
        time.sleep(0.2)  # Rate limiting
        
        if response.status_code != 200:
            print(f"Error: InChIKey not found: {inchikey}")
            return None
        
        cid_data = response.json()
        if "IdentifierList" not in cid_data or "CID" not in cid_data["IdentifierList"]:
            print(f"No CID found for InChIKey: {inchikey}")
            return None
        
        cid = cid_data["IdentifierList"]["CID"][0]
        
        # Get properties
        properties = ["MolecularFormula", "MolecularWeight", "IUPACName", 
                      "CanonicalSMILES", "InChI", "XLogP", "TPSA"]
        
        properties_url = f"{base_url}/compound/cid/{cid}/property/{','.join(properties)}/JSON"
        prop_response = requests.get(properties_url)
        time.sleep(0.2)  # Rate limiting
        
        if prop_response.status_code != 200:
            print(f"Error retrieving properties for CID: {cid}")
            return None
        
        property_data = prop_response.json()
        
        # Get synonyms
        synonyms_url = f"{base_url}/compound/cid/{cid}/synonyms/JSON"
        syn_response = requests.get(synonyms_url)
        time.sleep(0.2)  # Rate limiting
        
        synonyms = []
        if syn_response.status_code == 200:
            synonym_data = syn_response.json()
            if "InformationList" in synonym_data and "Information" in synonym_data["InformationList"]:
                synonyms = synonym_data["InformationList"]["Information"][0].get("Synonym", [])
        
        # Combine all data
        result = {
            "cid": cid,
            "properties": property_data["PropertyTable"]["Properties"][0],
            "synonyms": synonyms[:10]  # First 10 synonyms
        }
        
        return result
    except Exception as e:
        print(f"Exception: {str(e)}")
        return None

# Example usage
inchikey = "BSYNRYMUTXBXSQ-UHFFFAOYSA-N"  # Aspirin
metabolite_info = identify_metabolite(inchikey)
print(json.dumps(metabolite_info, indent=2))
```

### 11.2. Chemical Identifier Conversion

```python
def convert_identifiers(identifier, from_type, to_types):
    """
    Convert between different chemical identifiers.
    
    Parameters:
    identifier (str): The source identifier
    from_type (str): Type of the source identifier (cid, name, smiles, inchi, inchikey)
    to_types (list): List of target identifier types
    
    Returns:
    dict: Converted identifiers
    """
    base_url = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
    
    # First convert to CID
    url = f"{base_url}/compound/{from_type}/{identifier}/cids/JSON"
    
    try:
        response = requests.get(url)
        time.sleep(0.2)  # Rate limiting
        
        if response.status_code != 200:
            print(f"Error: Could not convert {from_type} to CID")
            return None
        
        cid_data = response.json()
        if "IdentifierList" not in cid_data or "CID" not in cid_data["IdentifierList"]:
            print(f"No CID found for {from_type}: {identifier}")
            return None
        
        cid = cid_data["IdentifierList"]["CID"][0]
        
        # Get all requested properties
        properties_url = f"{base_url}/compound/cid/{cid}/property/{','.join(to_types)}/JSON"
        prop_response = requests.get(properties_url)
        time.sleep(0.2)  # Rate limiting
        
        if prop_response.status_code != 200:
            print(f"Error retrieving properties for CID: {cid}")
            return None
        
        conversion_result = {
            "source": {
                "type": from_type,
                "value": identifier
            },
            "cid": cid,
            "conversions": prop_response.json()["PropertyTable"]["Properties"][0]
        }
        
        return conversion_result
    except Exception as e:
        print(f"Exception: {str(e)}")
        return None

# Example usage
name = "glucose"
target_properties = ["CanonicalSMILES", "InChI", "InChIKey", "IUPACName"]
conversion = convert_identifiers(name, "name", target_properties)
print(json.dumps(conversion, indent=2))
```

## 12. Integration with Biomapper Workflow

### 12.1. Resource Configuration

In the Biomapper database, PubChem is configured as resource ID 6:

```python
pubchem_resource_id = 6  # PubChem resource ID in metamapper.db
```

### 12.2. Mapping Paths

PubChem serves as a valuable resource in several mapping paths:

1. **NAME → PUBCHEM → STRUCTURE**
   - Maps chemical names to structural representations (SMILES, InChI, etc.)

2. **PUBCHEM → XREFS → KEGG/CHEBI/HMDB**
   - Maps PubChem IDs to other database identifiers

3. **STRUCTURE → PUBCHEM → NAME**
   - Maps structural representations to standardized names

4. **PUBCHEM → CLASSIFICATION → FUNCTION**
   - Provides chemical classification and functional information

### 12.3. Error Handling and Retry Strategy

When working with the PubChem API, implement the following error handling strategy:

```python
import time
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def query_pubchem_with_retry(url, params=None):
    """
    Query PubChem API with retry logic.
    
    Parameters:
    url (str): API endpoint URL
    params (dict): Optional query parameters
    
    Returns:
    dict: API response data
    """
    import requests
    
    try:
        response = requests.get(url, params=params, timeout=30)
        
        # Implement rate limiting
        time.sleep(0.25)  # Ensures we don't exceed 5 requests per second
        
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 429:
            print("Rate limit exceeded, retrying after delay...")
            raise Exception("Rate limit exceeded")
        elif response.status_code == 404:
            print(f"Resource not found: {url}")
            return None
        else:
            print(f"Error {response.status_code} from PubChem API: {response.text}")
            raise Exception(f"API returned error {response.status_code}")
    except requests.exceptions.Timeout:
        print("Request timed out, will retry...")
        raise
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {str(e)}")
        raise
```

## 13. References

- PubChem PUG REST Documentation: https://pubchem.ncbi.nlm.nih.gov/docs/pug-rest
- PubChem PUG REST Tutorial: https://pubchem.ncbi.nlm.nih.gov/docs/pug-rest-tutorial
- Full Record Retrieval: https://pubchem.ncbi.nlm.nih.gov/docs/pug-rest#section=Full-record-Retrieval
- PubChem Programmatic Access: https://pubchem.ncbi.nlm.nih.gov/docs/programmatic-access
- PubChemPy Python Library: https://pubchempy.readthedocs.io/
