# ChEBI API Documentation for Biomapper

## 1. Overview

ChEBI (Chemical Entities of Biological Interest) is a freely available database of molecular entities focused on small chemical compounds maintained by the European Bioinformatics Institute (EMBL-EBI). It provides a structured classification of molecular entities, particularly those with relevance to biological systems.

- **Base URL**: `https://www.ebi.ac.uk/webservices/chebi/2.0/`
- **API Type**: SOAP Web Service
- **WSDL URL**: `https://www.ebi.ac.uk/webservices/chebi/2.0/webservice?wsdl`
- **Authentication**: Not Required
- **Rate Limits**: No documented limits (implement adaptive rate limiting)
- **Response Format**: SOAP XML
- **Request Method**: POST

## 2. Entity Types Supported

- `chemical_entity`: Molecular entities in the ChEBI database

## 3. API Operations and Endpoints

The ChEBI API offers the following main operations:

### 3.1. getLiteEntity

Retrieves a list of "lite" entities containing only the ChEBI ASCII name and ChEBI identifier.

**Parameters**:
- `search`: Search string (accepts wildcard character "*" and unicode characters)
- `searchCategory`: Field to search in (optional, searches all fields if null)
- `maximumResults`: Maximum number of results to return (up to 5000)
- `stars`: Filter by entity status (e.g., "THREE STAR" for manually curated entities)

**Example Request**:
```xml
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:chebi="https://www.ebi.ac.uk/webservices/chebi">
   <soapenv:Header/>
   <soapenv:Body>
      <chebi:getLiteEntity>
         <search>glucose</search>
         <searchCategory>ALL</searchCategory>
         <maximumResults>10</maximumResults>
         <stars>ALL</stars>
      </chebi:getLiteEntity>
   </soapenv:Body>
</soapenv:Envelope>
```

### 3.2. getCompleteEntity

Retrieves the complete entity including synonyms, database links, and chemical structures.

**Parameters**:
- `chebiId`: ChEBI identifier (e.g., "CHEBI:15377" for glucose)

**Example Request**:
```xml
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:chebi="https://www.ebi.ac.uk/webservices/chebi">
   <soapenv:Header/>
   <soapenv:Body>
      <chebi:getCompleteEntity>
         <chebiId>CHEBI:15377</chebiId>
      </chebi:getCompleteEntity>
   </soapenv:Body>
</soapenv:Envelope>
```

### 3.3. getCompleteEntityByList

Retrieves multiple complete entities in a single request.

**Parameters**:
- `listOfChEBIIds`: List of ChEBI identifiers (maximum 50)

**Example Request**:
```xml
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:chebi="https://www.ebi.ac.uk/webservices/chebi">
   <soapenv:Header/>
   <soapenv:Body>
      <chebi:getCompleteEntityByList>
         <listOfChEBIIds>CHEBI:15377</listOfChEBIIds>
         <listOfChEBIIds>CHEBI:17234</listOfChEBIIds>
      </chebi:getCompleteEntityByList>
   </soapenv:Body>
</soapenv:Envelope>
```

### 3.4. getOntologyParents

Retrieves the ontology parents of an entity including the relationship type.

**Parameters**:
- `chebiId`: ChEBI identifier

**Example Request**:
```xml
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:chebi="https://www.ebi.ac.uk/webservices/chebi">
   <soapenv:Header/>
   <soapenv:Body>
      <chebi:getOntologyParents>
         <chebiId>CHEBI:15377</chebiId>
      </chebi:getOntologyParents>
   </soapenv:Body>
</soapenv:Envelope>
```

### 3.5. getOntologyChildren

Retrieves the ontology children of an entity including the relationship type.

**Parameters**:
- `chebiId`: ChEBI identifier

**Example Request**:
```xml
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:chebi="https://www.ebi.ac.uk/webservices/chebi">
   <soapenv:Header/>
   <soapenv:Body>
      <chebi:getOntologyChildren>
         <chebiId>CHEBI:15377</chebiId>
      </chebi:getOntologyChildren>
   </soapenv:Body>
</soapenv:Envelope>
```

### 3.6. getAllOntologyChildrenInPath

Retrieves all ontology children of an entity within a specific path.

**Parameters**:
- `chebiId`: ChEBI identifier
- `relationshipType`: Type of relationship to follow (e.g., "is_a", "has_part")

**Example Request**:
```xml
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:chebi="https://www.ebi.ac.uk/webservices/chebi">
   <soapenv:Header/>
   <soapenv:Body>
      <chebi:getAllOntologyChildrenInPath>
         <chebiId>CHEBI:35366</chebiId>
         <relationshipType>is_a</relationshipType>
      </chebi:getAllOntologyChildrenInPath>
   </soapenv:Body>
</soapenv:Envelope>
```

### 3.7. getStructureSearch

Performs a structural search (substructure, similarity, or identity).

**Parameters**:
- `structure`: Chemical structure (in MDL molfile format)
- `type`: Search type ("SIMILARITY", "SUBSTRUCTURE", or "IDENTITY")
- `threshold`: Similarity threshold (0-100, for similarity searches)
- `maximumResults`: Maximum number of results to return

**Example Request**:
```xml
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:chebi="https://www.ebi.ac.uk/webservices/chebi">
   <soapenv:Header/>
   <soapenv:Body>
      <chebi:getStructureSearch>
         <structure>...</structure>
         <type>SUBSTRUCTURE</type>
         <maximumResults>50</maximumResults>
      </chebi:getStructureSearch>
   </soapenv:Body>
</soapenv:Envelope>
```

### 3.8. getUpdatedPolymer

Retrieves updated information for polymers.

**Parameters**:
- `chebiId`: ChEBI identifier of a polymer

**Example Request**:
```xml
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:chebi="https://www.ebi.ac.uk/webservices/chebi">
   <soapenv:Header/>
   <soapenv:Body>
      <chebi:getUpdatedPolymer>
         <chebiId>CHEBI:77955</chebiId>
      </chebi:getUpdatedPolymer>
   </soapenv:Body>
</soapenv:Envelope>
```

## 4. Search Categories

When using the `getLiteEntity` operation, the following search categories are available:

- `ALL`: Search in all categories
- `CHEBI ID`: Search by ChEBI identifier
- `CHEBI NAME`: Search by ChEBI name
- `DEFINITION`: Search in the entity definition
- `IUPAC NAME`: Search by IUPAC name
- `SYNONYM`: Search in synonyms
- `FORMULA`: Search by chemical formula
- `SMILES`: Search by SMILES notation
- `INCHI`: Search by InChI string
- `INCHI KEY`: Search by InChI key

## 5. Response Data Structure

### 5.1. LiteEntity

Basic information about a ChEBI entity:

```xml
<LiteEntity>
  <chebiId>CHEBI:15377</chebiId>
  <chebiAsciiName>D-glucose</chebiAsciiName>
  <searchScore>...</searchScore>
  <entityStar>3</entityStar>
</LiteEntity>
```

### 5.2. Entity

Complete information about a ChEBI entity:

```xml
<Entity>
  <chebiId>CHEBI:15377</chebiId>
  <chebiAsciiName>D-glucose</chebiAsciiName>
  <definition>A glucose with D-configuration. A pentahydroxyhexanal...</definition>
  <status>CHECKED</status>
  <smiles>C(C1C(C(C(C(O1)O)O)O)O)O</smiles>
  <inchi>InChI=1S/C6H12O6/c7-1-2-3(8)4(9)5(10)6(11)12-2/h2-11H,1H2/t2-,3-,4+,5-,6?/m1/s1</inchi>
  <inchiKey>WQZGKKKJIJFFOK-GASJEMHNSA-N</inchiKey>
  <charge>0</charge>
  <mass>180.06339</mass>
  <monoisotopicMass>180.06339</monoisotopicMass>
  <formulae>C6H12O6</formulae>
  <entityStar>3</entityStar>
  <RegistryNumbers>
    <data>50-99-7</data>
    <type>CAS Registry Number</type>
  </RegistryNumbers>
  <ChemicalStructures>
    <structure>...</structure>
    <type>MOLFILE</type>
    <dimension>2D</dimension>
    <defaultStructure>true</defaultStructure>
  </ChemicalStructures>
  <DatabaseLinks>
    <data>HMDB00122</data>
    <type>HMDB</type>
  </DatabaseLinks>
  <Synonyms>
    <data>Grape sugar</data>
    <type>SYNONYM</type>
    <source>ChEBI</source>
    <languages>en</languages>
  </Synonyms>
</Entity>
```

### 5.3. OntologyDataItem

Information about ontological relationships:

```xml
<OntologyDataItem>
  <chebiId>CHEBI:71358</chebiId>
  <chebiName>aldohexose</chebiName>
  <type>is_a</type>
  <status>CHECKED</status>
  <cyclicRelationship>false</cyclicRelationship>
</OntologyDataItem>
```

## 6. Relationship Types in ChEBI Ontology

ChEBI's ontology includes several types of relationships:

- `is_a`: Subclass relationships (e.g., glucose is_a monosaccharide)
- `has_part`: Structural relationships indicating constituents
- `has_role`: Functional relationships indicating biological/chemical roles
- `has_functional_parent`: Links derivatives to parent molecules
- `is_conjugate_acid_of`/`is_conjugate_base_of`: For acid-base pairs
- `is_tautomer_of`: Links tautomeric forms
- `is_enantiomer_of`: Links stereoisomers
- `has_parent_hydride`: Links to parent hydrocarbon structures

## 7. Property Extraction Configurations in Biomapper

The following property extraction patterns can be used to extract information from ChEBI API responses:

### ChEBI ID
- **Property Name**: `chebi_id`
- **Extraction Method**: `xml_path`
- **Extraction Pattern**: `//chebiId[1]/text()`
- **Sample Data**: Extracts "CHEBI:15377" from the chebiId element

### ChEBI Name
- **Property Name**: `chebi_name`
- **Extraction Method**: `xml_path`
- **Extraction Pattern**: `//chebiAsciiName[1]/text()`
- **Sample Data**: Extracts "D-glucose" from the chebiAsciiName element

### Definition
- **Property Name**: `definition`
- **Extraction Method**: `xml_path`
- **Extraction Pattern**: `//definition[1]/text()`
- **Sample Data**: Extracts the definition text from the definition element

### SMILES
- **Property Name**: `smiles`
- **Extraction Method**: `xml_path`
- **Extraction Pattern**: `//smiles[1]/text()`
- **Sample Data**: Extracts "C(C1C(C(C(C(O1)O)O)O)O)O" from the smiles element

### InChI
- **Property Name**: `inchi`
- **Extraction Method**: `xml_path`
- **Extraction Pattern**: `//inchi[1]/text()`
- **Sample Data**: Extracts the InChI string from the inchi element

### InChI Key
- **Property Name**: `inchikey`
- **Extraction Method**: `xml_path`
- **Extraction Pattern**: `//inchiKey[1]/text()`
- **Sample Data**: Extracts "WQZGKKKJIJFFOK-GASJEMHNSA-N" from the inchiKey element

### Formula
- **Property Name**: `formula`
- **Extraction Method**: `xml_path`
- **Extraction Pattern**: `//formulae[1]/text()`
- **Sample Data**: Extracts "C6H12O6" from the formulae element

### CAS Registry Number
- **Property Name**: `cas_number`
- **Extraction Method**: `xml_path`
- **Extraction Pattern**: `//RegistryNumbers[type="CAS Registry Number"]/data/text()`
- **Sample Data**: Extracts "50-99-7" from the RegistryNumbers element with type "CAS Registry Number"

### Cross-reference to HMDB
- **Property Name**: `hmdb_id`
- **Extraction Method**: `xml_path`
- **Extraction Pattern**: `//DatabaseLinks[type="HMDB"]/data/text()`
- **Sample Data**: Extracts "HMDB00122" from the DatabaseLinks element with type "HMDB"

### Cross-reference to KEGG
- **Property Name**: `kegg_id`
- **Extraction Method**: `xml_path`
- **Extraction Pattern**: `//DatabaseLinks[type="KEGG COMPOUND accession"]/data/text()`
- **Sample Data**: Extracts "C00031" from the DatabaseLinks element with type "KEGG COMPOUND accession"

### Cross-reference to PubChem
- **Property Name**: `pubchem_id`
- **Extraction Method**: `xml_path`
- **Extraction Pattern**: `//DatabaseLinks[type="PubChem"]/data/text()`
- **Sample Data**: Extracts "5793" from the DatabaseLinks element with type "PubChem"

## 8. Programmatic Access Examples

### Python Example Using Suds-Jurko (SOAP Client)

```python
from suds.client import Client

def search_chebi_by_name(name, max_results=10):
    """Search ChEBI database for entities matching a name."""
    wsdl = 'https://www.ebi.ac.uk/webservices/chebi/2.0/webservice?wsdl'
    client = Client(wsdl)
    
    try:
        search_results = client.service.getLiteEntity(name, 'CHEBI NAME', max_results, 'ALL')
        return search_results
    except Exception as e:
        print(f"Error searching ChEBI: {e}")
        return None

def get_complete_entity(chebi_id):
    """Get complete information for a ChEBI entity by ID."""
    wsdl = 'https://www.ebi.ac.uk/webservices/chebi/2.0/webservice?wsdl'
    client = Client(wsdl)
    
    try:
        # Remove 'CHEBI:' prefix if present
        if chebi_id.startswith('CHEBI:'):
            chebi_id = chebi_id
        else:
            chebi_id = f"CHEBI:{chebi_id}"
        
        entity = client.service.getCompleteEntity(chebi_id)
        return entity
    except Exception as e:
        print(f"Error retrieving ChEBI entity: {e}")
        return None

def get_ontology_parents(chebi_id):
    """Get ontology parents for a ChEBI entity."""
    wsdl = 'https://www.ebi.ac.uk/webservices/chebi/2.0/webservice?wsdl'
    client = Client(wsdl)
    
    try:
        if not chebi_id.startswith('CHEBI:'):
            chebi_id = f"CHEBI:{chebi_id}"
        
        parents = client.service.getOntologyParents(chebi_id)
        return parents
    except Exception as e:
        print(f"Error retrieving ontology parents: {e}")
        return None
```

### Using HTTP Requests with XML (Alternative Approach)

```python
import requests
import xml.etree.ElementTree as ET

def search_chebi_soap(name, max_results=10):
    """Search ChEBI database using SOAP request."""
    url = 'https://www.ebi.ac.uk/webservices/chebi/2.0/webservice'
    
    # Prepare SOAP envelope
    soap_envelope = f"""
    <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:chebi="https://www.ebi.ac.uk/webservices/chebi">
       <soapenv:Header/>
       <soapenv:Body>
          <chebi:getLiteEntity>
             <search>{name}</search>
             <searchCategory>CHEBI NAME</searchCategory>
             <maximumResults>{max_results}</maximumResults>
             <stars>ALL</stars>
          </chebi:getLiteEntity>
       </soapenv:Body>
    </soapenv:Envelope>
    """
    
    headers = {
        'Content-Type': 'text/xml;charset=UTF-8',
        'SOAPAction': ''
    }
    
    response = requests.post(url, data=soap_envelope, headers=headers)
    
    if response.status_code == 200:
        # Parse XML response
        root = ET.fromstring(response.content)
        
        # Extract results (namespace handling required)
        ns = {'chebi': 'https://www.ebi.ac.uk/webservices/chebi'}
        entities = root.findall('.//chebi:LiteEntity', ns)
        
        results = []
        for entity in entities:
            chebi_id = entity.find('chebi:chebiId', ns).text
            name = entity.find('chebi:chebiAsciiName', ns).text
            results.append({'chebi_id': chebi_id, 'name': name})
        
        return results
    else:
        print(f"Error: {response.status_code}")
        return None
```

## 9. Common Use Cases

### Finding a Compound by Name or Structure

```python
def find_compound_by_name(name):
    """Find a ChEBI compound by name."""
    results = search_chebi_by_name(name, max_results=5)
    
    if results and hasattr(results, 'ListElement') and len(results.ListElement) > 0:
        # Get complete information for the first result
        chebi_id = results.ListElement[0].chebiId
        return get_complete_entity(chebi_id)
    return None

def classify_compound(chebi_id):
    """Get classification information for a compound."""
    # Get ontology parents to determine classification
    parents = get_ontology_parents(chebi_id)
    
    classifications = []
    if parents and hasattr(parents, 'ListElement'):
        for parent in parents.ListElement:
            classifications.append({
                'chebi_id': parent.chebiId,
                'name': parent.chebiName,
                'relationship': parent.type
            })
    
    return classifications
```

### Cross-referencing with Other Databases

```python
def get_database_references(chebi_id):
    """Extract cross-references to other databases for a ChEBI entity."""
    entity = get_complete_entity(chebi_id)
    
    if not entity or not hasattr(entity, 'DatabaseLinks'):
        return {}
    
    references = {}
    for db_link in entity.DatabaseLinks:
        db_type = db_link.type
        db_id = db_link.data
        
        if db_type not in references:
            references[db_type] = []
        
        references[db_type].append(db_id)
    
    return references
```

### Working with Chemical Classification

```python
def get_all_compounds_in_class(parent_chebi_id, relationship_type="is_a"):
    """Get all compounds in a specific chemical class."""
    wsdl = 'https://www.ebi.ac.uk/webservices/chebi/2.0/webservice?wsdl'
    client = Client(wsdl)
    
    try:
        if not parent_chebi_id.startswith('CHEBI:'):
            parent_chebi_id = f"CHEBI:{parent_chebi_id}"
        
        # Get all children in the specific relationship path
        children = client.service.getAllOntologyChildrenInPath(parent_chebi_id, relationship_type)
        
        compounds = []
        if children and hasattr(children, 'ListElement'):
            for child in children.ListElement:
                compounds.append({
                    'chebi_id': child.chebiId,
                    'name': child.chebiName
                })
        
        return compounds
    except Exception as e:
        print(f"Error retrieving compounds in class: {e}")
        return []
```

## 10. Integration with Biomapper Workflow

### Resource Configuration

In the Biomapper database, ChEBI is configured as resource ID 5:

```python
chebi_resource_id = 5  # ChEBI resource ID in metamapper.db
```

### Mapping Paths

ChEBI serves as a valuable resource in several mapping paths:

1. **NAME → CHEBI → PUBCHEM/HMDB/KEGG/CAS**
   - Maps chemical names to various database identifiers

2. **INCHI/SMILES → CHEBI → NAME/SYNONYM**
   - Maps structural representations to names and synonyms

3. **CHEBI → ONTOLOGY → CLASSIFICATION**
   - Provides chemical classification and hierarchy information

### Error Handling and Retry Strategy

When working with the ChEBI API, implement the following error handling strategy:

```python
import time
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def get_chebi_entity_with_retry(chebi_id):
    """Retrieve ChEBI entity with retry logic."""
    try:
        entity = get_complete_entity(chebi_id)
        return entity
    except Exception as e:
        print(f"Error retrieving ChEBI entity (attempt will be retried): {e}")
        raise
```

## 11. References

- ChEBI Web Services: https://www.ebi.ac.uk/chebi/webServices.do
- ChEBI Ontology: https://www.ebi.ac.uk/chebi/init.do
- ChEBI Software Development Kit: https://github.com/libChEBI
- Hastings, J., et al. (2015). ChEBI in 2016: Improved services and an expanding collection of metabolites. Nucleic Acids Res, 44(D1), D1214-D1219.
