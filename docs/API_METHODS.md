# API Client Methods Reference

This document provides a comprehensive reference for all API client methods used in the biomapper system. It serves as the authoritative source for method signatures and usage.

## UniProtHistoricalResolverClient
**Location**: `biomapper.mapping.clients.uniprot_historical_resolver_client`

Client for resolving UniProt identifiers including historical IDs

### Methods:

- `async map_identifiers(source_identifiers, target_ontology_type=None, mapping_params=None) -> Dict[str, Any]`
  - Map protein identifiers to UniProt accessions
  - Required parameters:
    - `source_identifiers`: List of protein identifiers to map
  - Optional parameters:
    - `target_ontology_type`: Target ontology type for mapping
    - `mapping_params`: Additional mapping parameters

- `async resolve_batch(protein_ids, include_metadata=None) -> Dict[str, Any]`
  - Resolve a batch of protein IDs
  - Required parameters:
    - `protein_ids`: List of protein IDs to resolve
  - Optional parameters:
    - `include_metadata`: Whether to include additional metadata

- `async _fetch_uniprot_search_results(query) -> Dict[str, Any]`
  - Execute search query against UniProt REST API
  - Required parameters:
    - `query`: Search query string

## ChemblAPIClient
**Location**: `biomapper.mapping.clients.chembl_api_client`

Client for ChEMBL compound database

### Methods:

- `search_compounds(query, limit=None, filters=None) -> List[Dict[str, Any]]`
  - Search for compounds in ChEMBL
  - Required parameters:
    - `query`: Search query string
  - Optional parameters:
    - `limit`: Maximum number of results to return
    - `filters`: Additional search filters

- `get_compound_by_id(chembl_id) -> Dict[str, Any]`
  - Get compound details by ChEMBL ID
  - Required parameters:
    - `chembl_id`: ChEMBL identifier

## PubChemAPIClient
**Location**: `biomapper.mapping.clients.pubchem_api_client`

Client for PubChem compound database

### Methods:

- `get_compound(cid, namespace=None, domain=None) -> Dict[str, Any]`
  - Get compound information by CID
  - Required parameters:
    - `cid`: PubChem compound identifier
  - Optional parameters:
    - `namespace`: Namespace for the query
    - `domain`: Domain for the query

- `search_by_name(name, max_results=None) -> List[Dict[str, Any]]`
  - Search compounds by name
  - Required parameters:
    - `name`: Compound name to search
  - Optional parameters:
    - `max_results`: Maximum number of results

## HMDBAPIClient
**Location**: `biomapper.mapping.clients.hmdb_api_client`

Client for Human Metabolome Database

### Methods:

- `get_metabolite(hmdb_id) -> Dict[str, Any]`
  - Get metabolite information by HMDB ID
  - Required parameters:
    - `hmdb_id`: HMDB identifier

- `search_metabolites(query, search_type=None, limit=None) -> List[Dict[str, Any]]`
  - Search metabolites in HMDB
  - Required parameters:
    - `query`: Search query
  - Optional parameters:
    - `search_type`: Type of search to perform
    - `limit`: Maximum number of results

## Usage Examples

### UniProt Resolution

```python
from biomapper.mapping.clients.uniprot_historical_resolver_client import UniProtHistoricalResolverClient
from biomapper.core.standards.api_validator import APIMethodValidator

# Create client
client = UniProtHistoricalResolverClient()

# Validate method exists before use
APIMethodValidator.validate_method_exists(client, 'map_identifiers')

# Use the validated method
result = await client.map_identifiers(
    source_identifiers=['P12345', 'Q67890'],
    target_ontology_type='uniprot'
)
```

### Error Handling with Validation

```python
from biomapper.core.standards.api_validator import APIMethodValidator

try:
    # This will fail with a helpful error message
    APIMethodValidator.validate_method_exists(client, 'get_uniprot_data')
except AttributeError as e:
    print(e)
    # Output: Method 'get_uniprot_data' not found on UniProtHistoricalResolverClient
    # Did you mean one of: ['map_identifiers', 'resolve_batch']?
```

### Using the Registry

```python
from biomapper.core.standards.api_registry import APIClientRegistry

# Get client specification
spec = APIClientRegistry.get_client_spec('uniprot')

# Validate client implementation
results = APIClientRegistry.validate_client('uniprot', client)

# Get method signature
method_spec = APIClientRegistry.get_method_signature('uniprot', 'map_identifiers')
```

## Common Issues and Solutions

### Issue: Method Name Mismatch
**Problem**: Code expects `get_uniprot_data` but actual method is `map_identifiers`

**Solution**: Use the APIMethodValidator to detect and suggest correct method names:
```python
validator = APIMethodValidator()
validator.validate_method_exists(client, 'get_uniprot_data')
# Raises: AttributeError with suggestion for 'map_identifiers'
```

### Issue: Wrong Method Signature
**Problem**: Calling method with wrong parameters

**Solution**: Use wrapper with validation:
```python
wrapped_method = APIMethodValidator.create_method_wrapper(
    client, 'map_identifiers'
)
# Now calls are validated and errors are descriptive
```

### Issue: Silent Failures
**Problem**: Method doesn't exist but fails silently

**Solution**: Always validate before use:
```python
# Add to action initialization
APIMethodValidator.validate_client_interface(
    client,
    required_methods=['map_identifiers', 'resolve_batch'],
    optional_methods=['_fetch_uniprot_search_results']
)
```

## Best Practices

1. **Always validate methods at initialization**: Check that required methods exist when creating action instances
2. **Use the registry for documentation**: Keep the registry updated with new clients and methods
3. **Wrap methods for production**: Use `create_method_wrapper` for automatic validation and logging
4. **Handle async methods properly**: Remember that many API methods are async
5. **Provide clear error messages**: Use the validator's suggestions to help developers

## Adding New API Clients

To add a new API client to the registry:

```python
from biomapper.core.standards.api_registry import ClientSpec, MethodSpec, APIClientRegistry

new_client = ClientSpec(
    name='my_api',
    class_name='MyAPIClient',
    module_path='biomapper.mapping.clients.my_api_client',
    description='My custom API client',
    methods={
        'fetch_data': MethodSpec(
            name='fetch_data',
            params=['query'],
            optional_params=['limit'],
            returns='List[Dict[str, Any]]',
            description='Fetch data from my API',
            async_method=True
        )
    }
)

APIClientRegistry.register_client(new_client)
```

## Maintenance

This documentation is generated from the APIClientRegistry. To update:

```python
from biomapper.core.standards.api_registry import APIClientRegistry

# Generate updated documentation
doc = APIClientRegistry.generate_documentation()
print(doc)
```