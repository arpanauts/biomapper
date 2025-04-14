# KEGG API Documentation for Biomapper

## 1. Overview

KEGG (Kyoto Encyclopedia of Genes and Genomes) is a comprehensive database resource for understanding high-level functions and utilities of biological systems. It provides a REST-style API for programmatic access to its diverse datasets including metabolites, pathways, genes, and reactions.

- **Base URL**: `https://rest.kegg.jp`
- **Authentication**: Not Required
- **Rate Limits**: 3 requests per second (very strict, requires proper rate limiting)
- **Response Format**: Text (tab-delimited, flat file, or image/binary)
- **Request Method**: GET

## 2. Entity Types Supported

- `metabolite` (compounds and glycans)
- `protein` (genes and orthologs)
- `pathway` (metabolic and signaling pathways)
- `reaction` (biochemical reactions)
- `disease` (human diseases)
- `drug` (pharmaceutical compounds)

## 3. API Endpoints and Operations

KEGG API provides 7 main operations:

### INFO - Get Database Information

```
https://rest.kegg.jp/info/<database>
```

Returns information about the specified database.

**Parameters**:
- `database`: Name of the KEGG database (compound, pathway, etc.)

**Example**:
```bash
curl -X GET "https://rest.kegg.jp/info/compound"
```

### LIST - List Database Entries

```
https://rest.kegg.jp/list/<database>
```

Returns a list of all entries in the specified database.

**Parameters**:
- `database`: Name of the KEGG database

**Example**:
```bash
curl -X GET "https://rest.kegg.jp/list/compound"
```

### FIND - Search for Entries

```
https://rest.kegg.jp/find/<database>/<query>
```

Searches for entries in the specified database matching the query.

**Parameters**:
- `database`: Name of the KEGG database
- `query`: Search term or pattern

**Example**:
```bash
curl -X GET "https://rest.kegg.jp/find/compound/glucose"
```

### GET - Retrieve Entry Data

```
https://rest.kegg.jp/get/<dbentries>[/<option>]
```

Retrieves detailed information for specified database entries.

**Parameters**:
- `dbentries`: Database entry identifiers (can be multiple, separated by +)
- `option`: Format options like mol, image, etc. (optional)

**Example**:
```bash
curl -X GET "https://rest.kegg.jp/get/C00031"  # Get glucose compound data
curl -X GET "https://rest.kegg.jp/get/C00031/image"  # Get glucose structure image
```

### CONV - Convert Identifiers

```
https://rest.kegg.jp/conv/<target_db>/<source_db>
```

Converts identifiers between KEGG and outside databases.

**Parameters**:
- `target_db`: Target database for conversion
- `source_db`: Source database

**Example**:
```bash
curl -X GET "https://rest.kegg.jp/conv/compound/pubchem"  # Convert PubChem IDs to KEGG
```

### LINK - Find Related Entries

```
https://rest.kegg.jp/link/<target_db>/<source_db>
```

Finds related entries between KEGG databases.

**Parameters**:
- `target_db`: Target database to link to
- `source_db`: Source database to link from

**Example**:
```bash
curl -X GET "https://rest.kegg.jp/link/pathway/compound"  # Find pathways containing specific compounds
```

### DDI - Drug-Drug Interactions

```
https://rest.kegg.jp/ddi/<dbentry>
```

Retrieves drug-drug interaction information.

**Parameters**:
- `dbentry`: Drug database entry identifier

**Example**:
```bash
curl -X GET "https://rest.kegg.jp/ddi/D00564"  # Get interactions for drug D00564
```

## 4. Database Identifier Formats

KEGG uses specific identifier formats for different data types:

| Entity Type | Prefix | Example ID | Format |
|-------------|--------|------------|--------|
| Compound | C | C00031 | C followed by 5 digits |
| Glycan | G | G00001 | G followed by 5 digits |
| Reaction | R | R00010 | R followed by 5 digits |
| Enzyme | ec | ec:1.1.1.1 | Enzyme Commission number |
| Pathway | map/[org] | map00010, hsa00010 | map or org code + 5 digits |
| KO (Orthology) | K | K00001 | K followed by 5 digits |
| Gene | [org]: | hsa:10458 | org code + : + gene identifier |
| Drug | D | D00001 | D followed by 5 digits |
| Disease | H | H00001 | H followed by 5 digits |

## 5. Understanding KEGG Compound Data Format

KEGG compound entries are returned in a flat file format with specific sections:

```
ENTRY       C00031                      Compound
NAME        D-Glucose
            Grape sugar
            Dextrose
FORMULA     C6H12O6
EXACT_MASS  180.0634
MOL_WEIGHT  180.1559
DBLINKS     PubChem: 5793
            ChEBI: 17634
            HMDB: HMDB0000122
PATHWAY     map00010  Glycolysis / Gluconeogenesis
            map00030  Pentose phosphate pathway
            map00500  Starch and sucrose metabolism
ENZYME      1.1.1.47  Glucose 1-dehydrogenase
            1.1.3.4   Glucose oxidase
BRITE       DBGET: C00031
///
```

Key sections for property extraction include:
- **ENTRY**: KEGG compound ID
- **NAME**: Compound names (multiple entries possible)
- **FORMULA**: Molecular formula
- **EXACT_MASS**: Exact mass
- **MOL_WEIGHT**: Molecular weight
- **DBLINKS**: Links to other databases (PubChem, ChEBI, HMDB, etc.)
- **PATHWAY**: Associated metabolic pathways
- **ENZYME**: Related enzymes

## 6. Property Extraction Configurations in Biomapper

The following property extraction patterns are used to extract information from KEGG compound entries:

### KEGG ID
- **Property Name**: `kegg_id`
- **Extraction Method**: `regex`
- **Extraction Pattern**: `ENTRY\\s+(C\\d{5})`
- **Sample Data**: Extracts "C00031" from the ENTRY line

### Compound Name
- **Property Name**: `compound_name`
- **Extraction Method**: `regex`
- **Extraction Pattern**: `NAME\\s+([^\\n]+)`
- **Sample Data**: Extracts "D-Glucose" from the NAME line

### Molecular Formula
- **Property Name**: `formula`
- **Extraction Method**: `regex`
- **Extraction Pattern**: `FORMULA\\s+([^\\n]+)`
- **Sample Data**: Extracts "C6H12O6" from the FORMULA line

### Molecular Weight
- **Property Name**: `molecular_weight`
- **Extraction Method**: `regex`
- **Extraction Pattern**: `MOL_WEIGHT\\s+([\\d\\.]+)`
- **Sample Data**: Extracts "180.1559" from the MOL_WEIGHT line

### ChEBI ID
- **Property Name**: `chebi_id`
- **Extraction Method**: `regex`
- **Extraction Pattern**: `ChEBI:\\s+(\\d+)`
- **Sample Data**: Extracts "17634" from the DBLINKS section

### HMDB ID
- **Property Name**: `hmdb_id`
- **Extraction Method**: `regex`
- **Extraction Pattern**: `HMDB:\\s+(HMDB\\d+)`
- **Sample Data**: Extracts "HMDB0000122" from the DBLINKS section

### PubChem ID
- **Property Name**: `pubchem_id`
- **Extraction Method**: `regex`
- **Extraction Pattern**: `PubChem:\\s+(\\d+)`
- **Sample Data**: Extracts "5793" from the DBLINKS section

## 7. Common Use Cases

### Get Compound Information by KEGG ID
```python
async def get_compound_by_kegg_id(kegg_id):
    # Assuming kegg_client is properly initialized
    compound_data = await kegg_client.get_compound(kegg_id)
    
    # Extract properties using regex patterns
    properties = {}
    properties['kegg_id'] = kegg_id
    
    # Extract name
    name_match = re.search(r'NAME\s+([^\n]+)', compound_data)
    if name_match:
        properties['name'] = name_match.group(1).strip()
    
    # Extract formula
    formula_match = re.search(r'FORMULA\s+([^\n]+)', compound_data)
    if formula_match:
        properties['formula'] = formula_match.group(1).strip()
    
    # Extract database links
    chebi_match = re.search(r'ChEBI:\s+(\d+)', compound_data)
    if chebi_match:
        properties['chebi_id'] = chebi_match.group(1).strip()
    
    return properties
```

### Find Pathways Associated with a Compound
```python
async def find_pathways_for_compound(kegg_id):
    # Use LINK operation to find related pathways
    pathway_data = await kegg_client.link("pathway", kegg_id)
    
    # Parse tab-delimited response
    pathways = []
    for line in pathway_data.strip().split('\n'):
        if line:
            compound_id, pathway_id = line.split('\t')
            pathways.append(pathway_id)
    
    return pathways
```

### Convert Between KEGG and ChEBI IDs
```python
async def convert_kegg_to_chebi(kegg_id):
    # Find compound entry data
    compound_data = await kegg_client.get_compound(kegg_id)
    
    # Extract ChEBI ID using regex
    chebi_match = re.search(r'ChEBI:\s+(\d+)', compound_data)
    if chebi_match:
        return f"CHEBI:{chebi_match.group(1)}"
    return None
```

## 8. Error Handling

- **HTTP Status Codes**:
  - 200: Success
  - 400: Bad request (syntax error, wrong database name)
  - 404: Not found

- **Common Errors**:
  - Rate limiting issues (exceeding 3 requests/second)
  - Entity not found in database
  - Malformed query parameters

- **Best Practices**:
  - Implement proper rate limiting (3 req/sec maximum)
  - Add small random jitter between requests
  - Use exponential backoff for retries
  - Verify entry existence before detailed queries

## 9. Rate Limiting Implementation

KEGG strictly enforces a rate limit of 3 requests per second. The following implementation is recommended:

```python
import asyncio
import random
import time
from functools import wraps

class KEGGRateLimiter:
    def __init__(self, requests_per_second=3):
        self.requests_per_second = requests_per_second
        self.interval = 1.0 / requests_per_second
        self.last_request_time = 0
    
    async def wait(self):
        """Wait until we can make another request."""
        current_time = time.time()
        elapsed = current_time - self.last_request_time
        
        if elapsed < self.interval:
            # Add small jitter (0-50ms) to avoid synchronized requests
            jitter = random.uniform(0, 0.05)
            sleep_time = self.interval - elapsed + jitter
            await asyncio.sleep(sleep_time)
        
        self.last_request_time = time.time()

def rate_limited(func):
    """Decorator to apply rate limiting to a function."""
    limiter = KEGGRateLimiter(requests_per_second=3)
    
    @wraps(func)
    async def wrapper(*args, **kwargs):
        await limiter.wait()
        return await func(*args, **kwargs)
    
    return wrapper
```

## 10. Integration with Biomapper Workflow

### Mapping Paths
KEGG serves as a key resource in many mapping paths within Biomapper, particularly for metabolite pathway associations:

1. **KEGG → ChEBI/PubChem/HMDB**
   - Extracts ontological database IDs from KEGG entries

2. **NAME → KEGG → PATHWAY**
   - Maps compound names to associated metabolic pathways

3. **CHEBI/PUBCHEM → KEGG → ENZYME**
   - Connects compounds to enzymes that act on them

### Breadth-First Search Context
In the context of Biomapper's breadth-first search approach:

- KEGG provides connections between compounds and biological functions (pathways, enzymes)
- It serves as an intermediate step in many mapping paths
- Its rich property extraction allows for multiple types of entity associations

## 11. References

- Official KEGG API Documentation: https://www.kegg.jp/kegg/rest/keggapi.html
- KEGG Database Categories: https://www.kegg.jp/kegg/kegg2.html
- KEGG Entry Format: https://www.kegg.jp/kegg/docs/dbentry.html
