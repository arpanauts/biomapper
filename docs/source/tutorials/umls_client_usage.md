# Using the UMLS Client in Biomapper

This document provides guidelines and best practices for using the UMLS clients in Biomapper.

## Overview

Biomapper provides two implementations of UMLS clients for name resolution:

1. **UMLSClient**: The full-featured client that attempts to resolve names to specific database identifiers via the UMLS Terminology Services API.
2. **UMLSClientSimplified**: A simplified client that maps names to UMLS Concept Unique Identifiers (CUIs) only.

Both clients implement the standard `BaseMappingClient` interface and can be used with `MappingExecutor` for entity mapping.

## Authentication

Both clients use direct API key authentication with the UMLS API. To use these clients, you need a UMLS API key:

1. Sign up for a UMLS account at [https://uts.nlm.nih.gov/uts/](https://uts.nlm.nih.gov/uts/)
2. After approval, log in to the UTS website
3. Navigate to "My Profile" > "API Keys"
4. Generate a new API key

The API key can be provided in three ways:
- Directly in the client configuration: `config={"api_key": "your_umls_api_key"}`
- As an environment variable: `export UMLS_API_KEY="your_umls_api_key"`
- In the `.env` file in the project root

## UMLSClientSimplified

### Overview

The `UMLSClientSimplified` provides a lightweight implementation that maps entity names to UMLS Concept Unique Identifiers (CUIs). It's more reliable but provides less specific mappings than the full `UMLSClient`.

### Configuration

```python
from biomapper.mapping.clients.umls_client_simplified import UMLSClientSimplified

# Initialize the client
client = UMLSClientSimplified(config={
    "api_key": "your_umls_api_key",  # Required
    "target_db": "CHEBI",  # Optional but recommended
    "timeout": 30,  # Optional (default: 30 seconds)
    "max_retries": 3  # Optional (default: 3)
})
```

### Usage Example

```python
import asyncio
from biomapper.mapping.clients.umls_client_simplified import UMLSClientSimplified

async def map_metabolite_names():
    # Initialize the client
    client = UMLSClientSimplified(config={
        "api_key": "your_umls_api_key",
        "target_db": "CHEBI"
    })
    
    try:
        # Map metabolite names
        metabolite_names = ["glucose", "cholesterol", "lactate"]
        results = await client.map_identifiers(terms=metabolite_names)
        
        # Process results
        for name, (cuis, confidence) in results.items():
            if cuis:
                print(f"{name} mapped to CUIs: {cuis} with confidence {confidence}")
            else:
                print(f"No mapping found for {name}")
    finally:
        # Always close the client to clean up resources
        await client.close()

# Run the async function
asyncio.run(map_metabolite_names())
```

### Pros and Cons

Pros:
- More reliable and faster than the full UMLSClient
- Good for getting UMLS CUIs for entity names
- Simple implementation with fewer API calls

Cons:
- Returns UMLS CUIs rather than specific database identifiers
- Less specific than the full UMLSClient
- Limited filtering capabilities

## UMLSClient (Full Implementation)

### Overview

The `UMLSClient` is a full-featured implementation that attempts to map entity names to specific database identifiers via the UMLS Terminology Services API. It's more comprehensive but less reliable due to the complexity of the UMLS API.

> **Note**: The full UMLSClient implementation may experience timeout issues with the UMLS API, especially when mapping multiple terms. Use with caution.

### Configuration

```python
from biomapper.mapping.clients.umls_client import UMLSClient

# Initialize the client
client = UMLSClient(config={
    "api_key": "your_umls_api_key",  # Required
    "target_db": "CHEBI",  # Required for mapping to specific identifiers
    "timeout": 30,  # Optional (default: 30 seconds)
    "max_retries": 3  # Optional (default: 3)
})
```

### Known Issues

The full UMLSClient implementation attempts to perform the following multi-step process:
1. Search for the term in UMLS
2. Get detailed information about each matching concept
3. Get atoms (source-asserted identifiers) for each concept
4. Extract target database identifiers from the atoms

Steps 2-4 can be very slow and may cause timeouts, especially when mapping multiple terms. We recommend using the simplified client for most use cases.

## Integration with Mapping Pipelines

Both clients can be integrated into mapping pipelines using `MappingExecutor`:

```python
from biomapper.mapping.clients.umls_client_simplified import UMLSClientSimplified
from biomapper.core.mapping_executor import MappingExecutor

# Initialize the client
client = UMLSClientSimplified(config={
    "api_key": "your_umls_api_key",
    "target_db": "CHEBI"
})

# Create mapping executor
executor = MappingExecutor(
    primary_client=client,
    source_id_field="source_id",
    source_name_field="name",
    target_id_field="target_id"
)

# Execute mapping
results = await executor.execute_mapping(source_data=data)
```

## Supported Target Databases

Both clients support the following target databases:

| Database | UMLS Source Abbreviation |
|----------|--------------------------|
| PUBCHEM | PUBCHEM |
| CHEBI | CHEBI |
| HMDB | HMDB |
| KEGG | KEGG |
| DRUGBANK | DRUGBANKID |
| MESH | MSH |

## Performance Considerations

- The simplified client is much faster and more reliable than the full client
- Both clients implement caching to improve performance for repeated queries
- Process entities in batches to optimize throughput
- Implement appropriate error handling and retry logic in your application

## When to Use Each Client

- Use `UMLSClientSimplified` when:
  - You need UMLS CUIs for entity names
  - Performance and reliability are priorities
  - You don't need specific database identifiers

- Use `UMLSClient` when:
  - You need specific database identifiers for entity names
  - You can tolerate potential timeouts and slower performance
  - You have a smaller number of terms to map

For most use cases, we recommend using the `UMLSClientSimplified` or the `TranslatorNameResolverClient` instead of the full `UMLSClient`.

## Additional Resources

- [UMLS Terminology Services API Documentation](https://documentation.uts.nlm.nih.gov/rest/home.html)
- [UMLS Account Registration](https://uts.nlm.nih.gov/uts/signup-login)