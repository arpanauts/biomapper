# UniChem API Documentation for Biomapper

## 1. Overview

UniChem is a non-proprietary, large-scale, freely available compound identifier mapping resource developed and maintained by the European Bioinformatics Institute (EBI). It provides cross-references between compound identifiers from various databases, making it an excellent resource for standardizing chemical identifiers.

- **Base URL**: 
  - Modern API (v1): `https://www.ebi.ac.uk/unichem/beta/api/v1`
  - Legacy API: `https://www.ebi.ac.uk/unichem/rest`
- **Authentication**: Not Required
- **Rate Limits**: Standard EBI fair usage policy (implement adaptive rate limiting with random jitter)
- **Response Format**: JSON
- **Request Method**: Modern API uses POST; legacy API uses GET

## 2. Entity Types Supported

- `metabolite` (chemical compounds)

## 3. API Endpoints

### Modern API (v1)

#### Get Compound Information
- **URL**: `/compounds`
- **Method**: POST
- **Headers**:
  - `accept: application/json`
  - `Content-Type: application/json`
- **Request Body**:
```json
{
  "compound": "RYYVLZVUVIJVGH-UHFFFAOYSA-N",
  "sourceID": 1,
  "type": "inchikey"
}
```
- **Request Parameters**:
  - `compound`: Identifier for the compound (InChIKey, SMILES, etc.)
  - `sourceID`: Source database ID (optional)
  - `type`: Type of identifier (inchikey, smiles, inchi, compound_id)
- **Sample Request**:
```bash
curl -X POST "https://www.ebi.ac.uk/unichem/beta/api/v1/compounds" \
     -H "accept: application/json" \
     -H "Content-Type: application/json" \
     -d '{ "compound": "RYYVLZVUVIJVGH-UHFFFAOYSA-N", "sourceID": 1, "type": "inchikey"}'
```
- **Sample Response**:
```json
{
  "compound": {
    "inchi": "InChI=1S/C9H8O4/c1-6(10)13-8-5-3-2-4-7(8)9(11)12/h2-5H,1H3,(H,11,12)",
    "inchikey": "RYYVLZVUVIJVGH-UHFFFAOYSA-N"
  },
  "sources": [
    {
      "id": 1,
      "name": "chembl",
      "compoundId": "CHEMBL25",
      "url": "https://www.ebi.ac.uk/chembl/compound/inspect/CHEMBL25"
    },
    {
      "id": 2,
      "name": "drugbank",
      "compoundId": "DB00945",
      "url": "https://www.drugbank.ca/drugs/DB00945"
    },
    {
      "id": 7,
      "name": "chebi",
      "compoundId": "15365",
      "url": "https://www.ebi.ac.uk/chebi/searchId.do?chebiId=CHEBI:15365"
    },
    {
      "id": 22,
      "name": "pubchem",
      "compoundId": "2244",
      "url": "https://pubchem.ncbi.nlm.nih.gov/compound/2244"
    }
  ]
}
```

### Legacy API (still supported)

#### InChIKey Search
- **URL**: `/src_compound_id/{compound_id}/src_id/{src_id}`
- **Method**: GET
- **Parameters**:
  - `compound_id`: Compound ID in the source database
  - `src_id`: Source database ID
- **Sample Request**:
```bash
curl -X GET "https://www.ebi.ac.uk/unichem/rest/src_compound_id/CHEMBL25/src_id/1"
```

#### Mapping Between Sources
- **URL**: `/src_compound_id/{identifier}/src_id/{src_id}/dst_id/{dst_id}`
- **Method**: GET
- **Parameters**:
  - `identifier`: Compound ID in the source database
  - `src_id`: Source database ID
  - `dst_id`: Destination database ID
- **Sample Request**:
```bash
curl -X GET "https://www.ebi.ac.uk/unichem/rest/src_compound_id/CHEMBL25/src_id/1/dst_id/2"
```

## 4. Available Sources and Identifiers

UniChem currently maps identifiers from over 50 different sources. When using the UniChem API, it's essential to use the source ID number (not the source name) for queries. Below is the complete list of available sources from the UniChem metadata (as of March 27, 2025):

| Source ID | Source Name | Description | Compound Count |
|-----------|------------|-------------|----------------|
| 1 | ChEMBL | Bioactive drug-like small molecules and bioactivities | 2,473,434 |
| 2 | DrugBank | Drug data with drug target information | 11,919 |
| 3 | PDBe | Protein Data Bank Europe - small molecule ligands | 43,246 |
| 4 | Guide to Pharmacology | IUPHAR/BPS pharmacology database | 8,411 |
| 5 | PubChem ('Drugs of the Future' subset) | A subset from the original depositor 'drugs of the future' | 5,646 |
| 6 | KEGG | Kyoto Encyclopedia of Genes and Genomes compounds | 14,033 |
| 7 | ChEBI | Chemical Entities of Biological Interest | 142,602 |
| 8 | NIH Clinical Collection | Molecules with history in human clinical trials | 719 |
| 9 | ZINC | Free database of commercially-available compounds | 16,886,865 |
| 10 | eMolecules | Chemical structure search engine | 5,168,336 |
| 12 | Gene Expression Atlas | Meta-analysis based summary statistics | 676 |
| 14 | FDA/USP SRS | FDA Substance Registration System (UNII codes) | 86,608 |
| 15 | SureChEMBL | Patent chemistry database | 22,690,940 |
| 17 | PharmGKB | Pharmacogenomics Knowledgebase | 1,691 |
| 18 | HMDB | Human Metabolome Database | 217,733 |
| 20 | Selleck | Biochemical products supplier | 1,890 |
| 21 | PubChem ('Thomson Pharma' subset) | From original depositor 'Thomson Pharma' | 3,858,588 |
| 22 | PubChem Compounds | Normalized PubChem compounds (CIDs) | 115,824,355 |
| 23 | Mcule | Online drug discovery platform | 32,919,693 |
| 24 | NMRShiftDB | NMR database for organic structures | 257,882 |
| 25 | LINCS | Library of Integrated Network-based Cellular Signatures | 42,741 |
| 26 | ACToR | Aggregated Computational Toxicology Resource | 411,229 |
| 27 | Recon | Biochemical knowledge-base on human metabolism | 1,529 |
| 28 | MolPort | Database for commercial sources of compounds | 110,024 |
| 29 | Nikkaji | The Japan Chemical Substance Dictionary | 3,439,411 |
| 31 | BindingDB | Database of measured binding affinities | 1,000,223 |
| 32 | EPA CompTox | Environmental Protection Agency CompTox Dashboard | 742,310 |
| 33 | LipidMaps | LIPID Metabolites And Pathways Strategy database | 47,866 |
| 34 | DrugCentral | Online drug information resource | 4,091 |
| 35 | Carotenoid Database | Information on naturally occurring carotenoids | 7 |
| 36 | Metabolights | Database for Metabolomics experiments | 22,227 |
| 37 | Brenda | Enzyme Information system | 149,602 |
| 38 | Rhea | Expert curated resource of biochemical reactions | 8,964 |
| 39 | ChemicalBook | Knowledge-base of chemicals | 141,931 |
| 41 | SwissLipids | Expert curated resource for lipids | 503,725 |
| 45 | DailyMed | Database of marketed drugs in the USA | 2,454 |
| 46 | ClinicalTrials | Intervention names from ClinicalTrials.gov | 5,362 |
| 47 | RxNorm | Normalized names for clinical drugs | 6,497 |
| 48 | MedChemExpress | Chemical supplier of Inhibitors and Agonists | 23,468 |
| 49 | Probes And Drugs | Data from the Probes and Drugs group | 126,060 |
| 50 | CCDC | CSD structures from Cambridge Crystallographic Data Centre | 235,341 |

### Most Relevant Sources for Biomapper

Based on our project needs, these sources are particularly valuable:

- **ChEMBL (1)**: Bioactive molecules with activity data (2.4M compounds)
- **PubChem (22)**: Largest chemical database (115.8M compounds)
- **HMDB (18)**: Human metabolome data (217.7K compounds)
- **ChEBI (7)**: Biological interest chemicals (142.6K compounds)
- **DrugBank (2)**: Comprehensive drug information (11.9K compounds)
- **KEGG (6)**: Metabolic pathway compounds (14K compounds)

## 5. Property Extraction Configurations in Biomapper

Each property extraction configuration in the metamapper database defines how to extract specific identifiers from UniChem API responses.

### ChEBI ID
- **Property Name**: `chebi_id`
- **Extraction Method**: `json_path`
- **Extraction Pattern**: `$.sources[?(@.id==7)].compoundId`
- **Sample Data**: ChEBI ID "15365" is extracted when src_id is 7

### PubChem ID
- **Property Name**: `pubchem_id`
- **Extraction Method**: `json_path`
- **Extraction Pattern**: `$.sources[?(@.id==22)].compoundId`
- **Sample Data**: PubChem ID "2244" is extracted when src_id is 22

### ChEMBL ID
- **Property Name**: `chembl_id`
- **Extraction Method**: `json_path`
- **Extraction Pattern**: `$.sources[?(@.id==1)].compoundId`
- **Sample Data**: ChEMBL ID "CHEMBL25" is extracted when src_id is 1

### DrugBank ID
- **Property Name**: `drugbank_id`
- **Extraction Method**: `json_path`
- **Extraction Pattern**: `$.sources[?(@.id==2)].compoundId`
- **Sample Data**: DrugBank ID "DB00945" is extracted when src_id is 2

### KEGG ID
- **Property Name**: `kegg_id`
- **Extraction Method**: `json_path`
- **Extraction Pattern**: `$.sources[?(@.id==6)].compoundId`
- **Sample Data**: KEGG ID extracted when src_id is 6

### InChI
- **Property Name**: `inchi`
- **Extraction Method**: `json_path`
- **Extraction Pattern**: `$.compound.inchi`
- **Sample Data**: InChI string extracted from compound object

### InChIKey
- **Property Name**: `inchikey`
- **Extraction Method**: `json_path`
- **Extraction Pattern**: `$.compound.inchikey`
- **Sample Data**: InChIKey string extracted from compound object

### Additional Ontological Databases
Recent enhancements to the UniChem client have added 13 additional ontological databases:

| Source Name | Property Name | Description |
|-------------|--------------|-------------|
| LIPID MAPS | `lipidmaps_ids` | LIPID Metabolites And Pathways Strategy database |
| ZINC | `zinc_ids` | Free database of commercially-available compounds |
| ChemSpider | `chemspider_ids` | Royal Society of Chemistry's chemical structure database |
| Atlas | `atlas_ids` | Atlas Chemical Database |
| Guide to Pharmacology | `gtopdb_ids` | IUPHAR/BPS pharmacology database |
| eMolecules | `emolecules_ids` | Chemical structure search engine |
| CAS | `cas_ids` | CAS Registry Numbers |
| BindingDB | `bindingdb_ids` | Binding affinity database |
| MolPort | `molport_ids` | Commercial compound source database |
| EPA CompTox | `comptox_ids` | Environmental Protection Agency CompTox Dashboard |
| BRENDA | `brenda_ids` | Enzyme Information system |
| MetaboLights | `metabolights_ids` | Database for Metabolomics experiments |
| Selleck | `selleck_ids` | Selleck Chemicals |

Each of these has a corresponding property extraction configuration for reliable extraction from UniChem API responses.

## 6. Common Use Cases

### Map ChEBI ID to PubChem ID
```python
async def map_chebi_to_pubchem(chebi_id):
    # Assuming unichem_client is properly initialized
    payload = {
        "compound": chebi_id,
        "sourceID": 7,  # ChEBI source ID
        "type": "compound_id"
    }
    result = await unichem_client.post_compound_info(payload)
    
    # Extract PubChem ID if available
    pubchem_sources = [s for s in result.get("sources", []) if s.get("id") == 22]
    if pubchem_sources:
        return pubchem_sources[0].get("compoundId")
    return None
```

### Get All Available Mappings for an InChIKey
```python
async def get_all_mappings(inchikey):
    payload = {
        "compound": inchikey,
        "type": "inchikey"
    }
    result = await unichem_client.post_compound_info(payload)
    
    # Create dictionary of all source mappings
    mappings = {}
    for source in result.get("sources", []):
        mappings[source.get("name")] = source.get("compoundId")
    
    return mappings
```

## 7. Error Handling

- **Not Found**: Returns empty array for sources, check if sources array is empty
- **Invalid Source ID**: Returns error message in JSON response
- **Server Error**: Handle HTTP 500 errors with exponential backoff retry
- **Rate Limiting**: Implement adaptive sleep based on response times with random jitter

## 8. Integration with Metamapper

- **Resource ID**: 10
- **Entity Type**: metabolite
- **Available Ontologies**: Over 50 chemical compound databases including ChEMBL, DrugBank, ChEBI, PubChem, KEGG, HMDB, and LipidMaps

## 9. Data Structure and Concepts

UniChem organizes data through these key concepts:

1. **Source**: A database that provides identifiers (assigned a unique source ID)
2. **InChIKey**: The primary key used for identifying chemical structures
3. **Assignment**: The relationship between a source identifier and an InChIKey
4. **Cross-references**: Mappings between identifiers from different sources

## 10. Implementation Considerations

1. **Source ID Mapping**: Maintain a mapping between source names and their numeric IDs
2. **Database Size Awareness**: Use targeted queries for large sources like PubChem (115M+ compounds)
3. **Rate Limiting**: Implement appropriate rate limiting when making API calls
4. **Caching Strategy**: Cache frequently used mappings to reduce API load
5. **Fallback Strategy**: Implement fallbacks for when the API is unavailable

## 11. Integration with Biomapper Workflow

### Mapping Paths
UniChem is a central component in many mapping paths within Biomapper. Common paths include:

1. **NAME → PUBCHEM/CHEBI → INCHI/INCHIKEY**
   - Converts raw compound names to standardized identifiers

2. **PUBCHEM → KEGG → PATHWAY**
   - Links compounds to metabolic pathways

3. **PUBCHEM/CHEBI → HMDB → GENE**
   - Connects compounds to related genes

### Breadth-First Search Context
In the context of Biomapper's breadth-first search approach for finding optimal mapping paths:

- UniChem serves as a central hub with connections to many ontological databases
- It often provides the shortest path (fewest hops) between different identifier systems
- The high number of available sources makes it valuable for the first or second step in many mapping paths

## 12. API Updates and Versioning

UniChem has moved from a GET method to a POST method for their modern API. The legacy GET API is still supported for backward compatibility. When implementing:

1. Prefer the modern POST API for new development
2. Use the legacy API only when required for specific integration points

## 13. References

- Official UniChem API Documentation: https://chembl.gitbook.io/unichem/api
- UniChem Source Information: https://www.ebi.ac.uk/unichem/sources
- Interactive API Documentation: https://www.ebi.ac.uk/unichem/beta/api/docs
