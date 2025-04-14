# RaMP DB API Documentation for Biomapper

## 1. Overview

RaMP DB (Rapid Mapping Database) is a comprehensive, integrated database that combines metabolite, gene, and pathway data from multiple sources. It provides extensive mapping functionality to connect identifiers across different biological databases and offers pathway and chemical enrichment analyses.

- **Base URL**: `https://rampdb.nih.gov/api`
- **Authentication**: Not Required
- **Rate Limits**: No documented limits (implement adaptive rate limiting)
- **Response Format**: JSON
- **Request Method**: GET
- **Current Version**: RaMP 3.0

## 2. Data Sources Integrated

RaMP DB integrates data from multiple key resources:

- **HMDB** (Human Metabolome Database v5.0): Primary source for metabolite information
- **KEGG** (Kyoto Encyclopedia of Genes and Genomes): Metabolic pathways and compounds
- **Reactome** (v81): Pathway database of biological processes
- **WikiPathways** (v20220710): Community pathway database
- **ChEBI**: Chemical Entities of Biological Interest
- **LIPID MAPS**: Comprehensive lipid database
- **Rhea**: Annotated database of biochemical reactions

## 3. Entity Types Supported

RaMP DB supports multiple entity types:

- `metabolite`: Chemical compounds (>200,000 entries)
- `gene`: Genes and proteins (~16,000 entries) 
- `pathway`: Biological pathways (>53,000 entries)
- `class`: Chemical classifications (from ClassyFire and LIPID MAPS)
- `ontology`: Biological ontologies (699 functional ontologies)

## 4. API Endpoints

### 4.1. Metabolite Queries

#### Get Metabolite by ID
```
GET /metabolite/{id_type}/{id}
```

Retrieves information about a specific metabolite.

**Parameters**:
- `id_type`: Identifier type (hmdb, pubchem, chebi, kegg, cas, inchikey)
- `id`: The identifier value

**Example**:
```
GET /metabolite/hmdb/HMDB0000001
```

#### Get Metabolite ID Mappings
```
GET /metabolite/{id_type}/{id}/mappings
```

Retrieves all identifier mappings for a specific metabolite.

**Parameters**:
- `id_type`: Source identifier type
- `id`: The source identifier value

**Example**:
```
GET /metabolite/hmdb/HMDB0000001/mappings
```

#### Get Metabolite Classification
```
GET /metabolite/{id_type}/{id}/class
```

Retrieves chemical classification information for a metabolite.

**Parameters**:
- `id_type`: Identifier type
- `id`: The identifier value

**Example**:
```
GET /metabolite/hmdb/HMDB0000001/class
```

#### Get Metabolite Properties
```
GET /metabolite/{id_type}/{id}/properties
```

Retrieves chemical properties for a metabolite (formula, MW, SMILES, etc.).

**Parameters**:
- `id_type`: Identifier type
- `id`: The identifier value

**Example**:
```
GET /metabolite/hmdb/HMDB0000001/properties
```

### 4.2. Gene/Protein Queries

#### Get Gene by ID
```
GET /gene/{id_type}/{id}
```

Retrieves information about a specific gene.

**Parameters**:
- `id_type`: Identifier type (entrez, ensembl, uniprot, symbol)
- `id`: The identifier value

**Example**:
```
GET /gene/entrez/5243
```

#### Get Gene ID Mappings
```
GET /gene/{id_type}/{id}/mappings
```

Retrieves all identifier mappings for a specific gene.

**Parameters**:
- `id_type`: Source identifier type
- `id`: The source identifier value

**Example**:
```
GET /gene/entrez/5243/mappings
```

### 4.3. Pathway Queries

#### Get Pathway by ID
```
GET /pathway/{id_type}/{id}
```

Retrieves information about a specific pathway.

**Parameters**:
- `id_type`: Identifier type (kegg, reactome, wiki, hmdb)
- `id`: The identifier value

**Example**:
```
GET /pathway/kegg/hsa00010
```

#### Get All Pathways for Source
```
GET /pathway/source/{source_name}
```

Retrieves all pathways from a specific source database.

**Parameters**:
- `source_name`: Source database name (kegg, reactome, wiki, hmdb)

**Example**:
```
GET /pathway/source/reactome
```

### 4.4. Analyte-Pathway Mappings

#### Get Pathways for Metabolite
```
GET /metabolite/{id_type}/{id}/pathways
```

Retrieves all pathways associated with a specific metabolite.

**Parameters**:
- `id_type`: Identifier type
- `id`: The identifier value

**Example**:
```
GET /metabolite/hmdb/HMDB0000001/pathways
```

#### Get Pathways for Gene
```
GET /gene/{id_type}/{id}/pathways
```

Retrieves all pathways associated with a specific gene.

**Parameters**:
- `id_type`: Identifier type
- `id`: The identifier value

**Example**:
```
GET /gene/entrez/5243/pathways
```

#### Get Metabolites in Pathway
```
GET /pathway/{id_type}/{id}/metabolites
```

Retrieves all metabolites associated with a specific pathway.

**Parameters**:
- `id_type`: Pathway database identifier
- `id`: The pathway identifier

**Example**:
```
GET /pathway/kegg/hsa00010/metabolites
```

#### Get Genes in Pathway
```
GET /pathway/{id_type}/{id}/genes
```

Retrieves all genes associated with a specific pathway.

**Parameters**:
- `id_type`: Pathway database identifier
- `id`: The pathway identifier

**Example**:
```
GET /pathway/kegg/hsa00010/genes
```

### 4.5. Reaction Queries

#### Get Metabolite-Gene Reactions
```
GET /metabolite/{id_type}/{id}/reactions
```

Retrieves all reactions (and associated genes) for a specific metabolite.

**Parameters**:
- `id_type`: Identifier type
- `id`: The identifier value

**Example**:
```
GET /metabolite/hmdb/HMDB0000001/reactions
```

#### Get Gene-Metabolite Reactions
```
GET /gene/{id_type}/{id}/reactions
```

Retrieves all reactions (and associated metabolites) for a specific gene.

**Parameters**:
- `id_type`: Identifier type
- `id`: The identifier value

**Example**:
```
GET /gene/entrez/5243/reactions
```

### 4.6. Batch Queries

#### Batch Metabolite Query
```
POST /batch/metabolites
```

Retrieves information for multiple metabolites in a single request.

**Request Body**:
```json
{
  "ids": [
    {"type": "hmdb", "id": "HMDB0000001"},
    {"type": "hmdb", "id": "HMDB0000002"},
    {"type": "kegg", "id": "C00031"}
  ],
  "return": ["pathways", "mappings", "properties"]
}
```

#### Batch Pathway Enrichment
```
POST /batch/pathway-enrichment
```

Performs pathway enrichment analysis on a list of analytes.

**Request Body**:
```json
{
  "metabolites": [
    {"type": "hmdb", "id": "HMDB0000001"},
    {"type": "hmdb", "id": "HMDB0000002"}
  ],
  "genes": [
    {"type": "entrez", "id": "5243"},
    {"type": "entrez", "id": "5230"}
  ],
  "background": "measured",
  "pvalueCutoff": 0.05,
  "sources": ["kegg", "reactome"]
}
```

## 5. Response Data Structure

### 5.1. Metabolite Object

```json
{
  "id": "HMDB0000001",
  "name": "1-Methylhistidine",
  "formula": "C7H11N3O2",
  "source": "hmdb",
  "mappings": {
    "hmdb": "HMDB0000001",
    "pubchem": "92105",
    "chebi": "CHEBI:50599",
    "kegg": "C01152",
    "inchikey": "BRMWTNUJHUMWMS-LURJTMIESA-N"
  },
  "properties": {
    "mw": 169.0851,
    "smiles": "CN1C=NC(C[C@H](N)C(O)=O)=C1",
    "inchi": "InChI=1S/C7H11N3O2/c1-10-3-9-5(10)2-4(8)6(11)12/h3-4H,2,8H2,1H3,(H,11,12)/t4-/m0/s1",
    "formula": "C7H11N3O2"
  },
  "classification": {
    "super_class": "Organic acids and derivatives",
    "main_class": "Carboxylic acids and derivatives",
    "sub_class": "Amino acids, peptides, and analogues"
  },
  "ontologies": [
    {"type": "biofluid", "value": "Blood"},
    {"type": "biofluid", "value": "Urine"}
  ]
}
```

### 5.2. Gene Object

```json
{
  "id": "5243",
  "symbol": "ABCB1",
  "name": "ATP binding cassette subfamily B member 1",
  "source": "entrez",
  "mappings": {
    "entrez": "5243",
    "ensembl": "ENSG00000085563",
    "uniprot": "P08183"
  }
}
```

### 5.3. Pathway Object

```json
{
  "id": "hsa00010",
  "name": "Glycolysis / Gluconeogenesis",
  "source": "kegg",
  "url": "https://www.genome.jp/pathway/hsa00010",
  "gene_count": 68,
  "metabolite_count": 29
}
```

### 5.4. Pathway Enrichment Result

```json
{
  "pathways": [
    {
      "id": "hsa00010",
      "name": "Glycolysis / Gluconeogenesis",
      "source": "kegg",
      "pvalue": 0.00123,
      "fdr": 0.0234,
      "overlapping_metabolites": ["HMDB0000122", "HMDB0000131"],
      "overlapping_genes": ["5230", "5236"]
    }
  ],
  "parameters": {
    "pvalueCutoff": 0.05,
    "background": "measured",
    "sources": ["kegg", "reactome"]
  }
}
```

## 6. Property Extraction Configurations in Biomapper

The following property extraction patterns can be used to extract information from RaMP DB API responses:

### Metabolite ID
- **Property Name**: `rampdb_metabolite_id`
- **Extraction Method**: `json_path`
- **Extraction Pattern**: `$.id`
- **Sample Data**: Extracts "HMDB0000001" from the id field

### Metabolite Name
- **Property Name**: `rampdb_metabolite_name`
- **Extraction Method**: `json_path`
- **Extraction Pattern**: `$.name`
- **Sample Data**: Extracts "1-Methylhistidine" from the name field

### PubChem ID Mapping
- **Property Name**: `pubchem_id`
- **Extraction Method**: `json_path`
- **Extraction Pattern**: `$.mappings.pubchem`
- **Sample Data**: Extracts "92105" from the mappings.pubchem field

### HMDB ID Mapping
- **Property Name**: `hmdb_id`
- **Extraction Method**: `json_path`
- **Extraction Pattern**: `$.mappings.hmdb`
- **Sample Data**: Extracts "HMDB0000001" from the mappings.hmdb field

### ChEBI ID Mapping
- **Property Name**: `chebi_id`
- **Extraction Method**: `json_path`
- **Extraction Pattern**: `$.mappings.chebi`
- **Sample Data**: Extracts "CHEBI:50599" from the mappings.chebi field

### KEGG ID Mapping
- **Property Name**: `kegg_id`
- **Extraction Method**: `json_path`
- **Extraction Pattern**: `$.mappings.kegg`
- **Sample Data**: Extracts "C01152" from the mappings.kegg field

### Chemical Formula
- **Property Name**: `formula`
- **Extraction Method**: `json_path`
- **Extraction Pattern**: `$.properties.formula`
- **Sample Data**: Extracts "C7H11N3O2" from the properties.formula field

### SMILES
- **Property Name**: `smiles`
- **Extraction Method**: `json_path`
- **Extraction Pattern**: `$.properties.smiles`
- **Sample Data**: Extracts "CN1C=NC(C[C@H](N)C(O)=O)=C1" from the properties.smiles field

### InChI Key
- **Property Name**: `inchikey`
- **Extraction Method**: `json_path`
- **Extraction Pattern**: `$.mappings.inchikey`
- **Sample Data**: Extracts "BRMWTNUJHUMWMS-LURJTMIESA-N" from the mappings.inchikey field

### Chemical Class
- **Property Name**: `chemical_class`
- **Extraction Method**: `json_path`
- **Extraction Pattern**: `$.classification.main_class`
- **Sample Data**: Extracts "Carboxylic acids and derivatives" from the classification.main_class field

## 7. Common Use Cases with Code Examples

### Mapping Metabolite IDs Across Databases

```python
import requests
import json

def map_metabolite_ids(id_type, id_value):
    """
    Map a metabolite ID to equivalent IDs in other databases.
    
    Parameters:
    id_type (str): Type of input ID (hmdb, chebi, pubchem, kegg)
    id_value (str): The ID value
    
    Returns:
    dict: A dictionary of mapped IDs across databases
    """
    url = f"https://rampdb.nih.gov/api/metabolite/{id_type}/{id_value}/mappings"
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error: {response.status_code}")
            return None
    except Exception as e:
        print(f"Exception: {str(e)}")
        return None

# Example usage
hmdb_id = "HMDB0000122"  # Glucose
mappings = map_metabolite_ids("hmdb", hmdb_id)
print(json.dumps(mappings, indent=2))
```

### Finding Pathways for a Metabolite

```python
import requests

def get_metabolite_pathways(id_type, id_value):
    """
    Get all pathways associated with a metabolite.
    
    Parameters:
    id_type (str): Type of input ID (hmdb, chebi, pubchem, kegg)
    id_value (str): The ID value
    
    Returns:
    list: A list of pathway objects
    """
    url = f"https://rampdb.nih.gov/api/metabolite/{id_type}/{id_value}/pathways"
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error: {response.status_code}")
            return None
    except Exception as e:
        print(f"Exception: {str(e)}")
        return None

# Example usage
hmdb_id = "HMDB0000122"  # Glucose
pathways = get_metabolite_pathways("hmdb", hmdb_id)

# Summarize pathway sources
pathway_sources = {}
for pathway in pathways:
    source = pathway["source"]
    if source in pathway_sources:
        pathway_sources[source] += 1
    else:
        pathway_sources[source] = 1

print("Pathway sources distribution:")
for source, count in pathway_sources.items():
    print(f"  {source}: {count} pathways")
```

### Performing Batch Pathway Enrichment Analysis

```python
import requests
import json

def perform_pathway_enrichment(metabolites=None, genes=None, pvalue_cutoff=0.05, sources=None):
    """
    Perform pathway enrichment analysis on a list of metabolites and/or genes.
    
    Parameters:
    metabolites (list): List of metabolite identifier dictionaries with 'type' and 'id'
    genes (list): List of gene identifier dictionaries with 'type' and 'id'
    pvalue_cutoff (float): P-value cutoff for significance
    sources (list): List of pathway databases to use (kegg, reactome, wiki, hmdb)
    
    Returns:
    dict: Enrichment analysis results
    """
    url = "https://rampdb.nih.gov/api/batch/pathway-enrichment"
    
    if metabolites is None:
        metabolites = []
    
    if genes is None:
        genes = []
    
    if sources is None:
        sources = ["kegg", "reactome", "wiki", "hmdb"]
    
    payload = {
        "metabolites": metabolites,
        "genes": genes,
        "background": "measured",
        "pvalueCutoff": pvalue_cutoff,
        "sources": sources
    }
    
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error: {response.status_code}")
            return None
    except Exception as e:
        print(f"Exception: {str(e)}")
        return None

# Example usage
metabolites = [
    {"type": "hmdb", "id": "HMDB0000122"},  # Glucose
    {"type": "hmdb", "id": "HMDB0000190"},  # Lactate
    {"type": "hmdb", "id": "HMDB0000161"}   # Alanine
]

genes = [
    {"type": "entrez", "id": "5230"},  # PGK1
    {"type": "entrez", "id": "5232"},  # PGK2
    {"type": "entrez", "id": "2821"}   # GPI
]

enrichment_results = perform_pathway_enrichment(
    metabolites=metabolites,
    genes=genes,
    sources=["kegg", "reactome"]
)

# Print top enriched pathways
if enrichment_results and "pathways" in enrichment_results:
    print("Top enriched pathways:")
    for i, pathway in enumerate(enrichment_results["pathways"][:5]):
        print(f"{i+1}. {pathway['name']} ({pathway['source']})")
        print(f"   p-value: {pathway['pvalue']:.6f}, FDR: {pathway['fdr']:.6f}")
```

### Retrieving Chemical Class Information

```python
import requests

def get_metabolite_classification(id_type, id_value):
    """
    Get chemical classification information for a metabolite.
    
    Parameters:
    id_type (str): Type of input ID (hmdb, chebi, pubchem, kegg)
    id_value (str): The ID value
    
    Returns:
    dict: Chemical classification information
    """
    url = f"https://rampdb.nih.gov/api/metabolite/{id_type}/{id_value}/class"
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error: {response.status_code}")
            return None
    except Exception as e:
        print(f"Exception: {str(e)}")
        return None

# Example usage
hmdb_id = "HMDB0000122"  # Glucose
classification = get_metabolite_classification("hmdb", hmdb_id)
print(json.dumps(classification, indent=2))
```

## 8. Integration with Biomapper Workflow

### Resource Configuration

In the Biomapper database, RaMP DB is configured as resource ID 12:

```python
rampdb_resource_id = 12  # RaMP DB resource ID in metamapper.db
```

### Mapping Paths

RaMP DB serves as a valuable resource in several mapping paths:

1. **NAME → RAMPDB → HMDB/PUBCHEM/CHEBI/KEGG**
   - Standardizes metabolite names and maps to ontological database IDs

2. **HMDB/PUBCHEM → RAMPDB → PATHWAY**
   - Maps compound IDs to pathway memberships

3. **HMDB/PUBCHEM → RAMPDB → CLASSIFICATION**
   - Maps compound IDs to chemical classifications

4. **GENE/PROTEIN → RAMPDB → PATHWAY**
   - Maps genes/proteins to pathway memberships

5. **METABOLITE → RAMPDB → GENE/PROTEIN**
   - Maps metabolites to enzymes via reaction relationships

### Error Handling and Retry Strategy

When working with the RaMP DB API, implement the following error handling strategy:

```python
import time
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def query_rampdb_with_retry(url, method="get", json_data=None):
    """
    Query RaMP DB API with retry logic.
    
    Parameters:
    url (str): API endpoint URL
    method (str): HTTP method (get or post)
    json_data (dict): JSON payload for POST requests
    
    Returns:
    dict: API response data
    """
    import requests
    
    try:
        if method.lower() == "get":
            response = requests.get(url, timeout=30)
        elif method.lower() == "post":
            response = requests.post(url, json=json_data, timeout=30)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error {response.status_code} from RaMP DB API: {response.text}")
            raise Exception(f"API returned error {response.status_code}")
    except requests.exceptions.Timeout:
        print("Request timed out, will retry...")
        raise
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {str(e)}")
        raise
```

## 9. Data Statistics and Coverage

RaMP DB 3.0 provides extensive coverage of biological entities:

- **Metabolites**: >200,000 distinct compounds
- **Genes/Proteins**: ~16,000 entries
- **Pathways**: >53,000 from multiple sources
- **Metabolite-Pathway Mappings**: >412,000 associations
- **Gene-Pathway Mappings**: >401,000 associations
- **Reaction Relationships**: >1.5 million metabolite-enzyme relationships
- **Ontologies**: 699 functional ontologies from HMDB v5.0

## 10. References

- RaMP DB Website: https://rampdb.nih.gov/
- RaMP DB API: https://rampdb.nih.gov/api
- GitHub Repository: https://github.com/ncats/RaMP-DB
- Palmer A, et al. (2023). RaMP-DB 2.0: an enhanced metabolite, gene and pathway database with accurate ID mapping for multi-omics analyses. Bioinformatics, 39(1), btad012. PMID: 36759745
- API Documentation: https://rampdb.nih.gov/api/docs (if available)
