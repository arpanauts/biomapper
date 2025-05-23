# Using the TranslatorNameResolverClient

This document provides guidelines and best practices for using the `TranslatorNameResolverClient` in Biomapper.

## Overview

The `TranslatorNameResolverClient` enables mapping of entity names to standardized identifiers using the [Translator Name Resolution API](https://name-resolution-sri.renci.org/) developed by the NCATS Biomedical Data Translator consortium. This client implements the standard `BaseMappingClient` interface for use with the `MappingExecutor`.

## Configuration Options

The client supports several configuration options:

| Option | Description | Default |
|--------|-------------|---------|
| `target_db` | Target database for identifier mapping (e.g., "CHEBI", "PUBCHEM") | (Required) |
| `timeout` | Request timeout in seconds | 30 |
| `max_retries` | Maximum number of retry attempts for failed requests | 3 |
| `backoff_factor` | Exponential backoff factor for retries | 0.5 |
| `match_threshold` | Minimum score threshold for matches | 0.5 |

## Supported Databases

The client can map to the following database identifiers:

| Database | Status | Notes |
|----------|--------|-------|
| CHEBI | ✅ Good | Reliable for metabolites/small molecules |
| PUBCHEM | ✅ Good | Reliable for metabolites/small molecules |
| HMDB | ⚠️ Limited | Less consistent results for metabolites |
| UNIPROT | ✅ Good | Reliable for proteins |
| HGNC | ✅ Good | Reliable for genes |
| DRUGBANK | ⚠️ Limited | Less consistent results for drugs |
| KEGG | ✅ Good | Reliable for metabolites |

## Biolink Types

The client uses Biolink types to filter results. The most commonly used types are:

| Entity Type | Recommended Biolink Type |
|-------------|--------------------------|
| Metabolites | `biolink:SmallMolecule` |
| Proteins | `biolink:Protein` |
| Genes | `biolink:Gene` |
| Drugs | `biolink:Drug` |

## Example Usage

Here's how to use the client for mapping metabolite names to CHEBI identifiers:

```python
import asyncio
from biomapper.mapping.clients.translator_name_resolver_client import TranslatorNameResolverClient

async def map_metabolite_names():
    # Initialize the client
    client = TranslatorNameResolverClient(config={
        "target_db": "CHEBI",
        "match_threshold": 0.5  # Adjust threshold based on needed precision
    })
    
    try:
        # Map metabolite names
        metabolite_names = ["glucose", "cholesterol", "lactate"]
        results = await client.map_identifiers(
            names=metabolite_names,
            target_biolink_type="biolink:SmallMolecule"
        )
        
        # Process results
        for name, (identifiers, confidence) in results.items():
            if identifiers:
                print(f"{name} mapped to {identifiers} with confidence {confidence}")
            else:
                print(f"No mapping found for {name}")
    finally:
        # Always close the client to clean up resources
        await client.close()

# Run the async function
asyncio.run(map_metabolite_names())
```

## Best Practices

Based on testing and evaluation, here are recommended best practices:

1. **Match Threshold Selection**:
   - Use 0.5 as a balanced default threshold
   - Lower to 0.3 for higher recall (more matches, potentially lower precision)
   - Increase to 0.7-0.9 for higher precision (fewer matches, higher confidence)

2. **Database Selection**:
   - For metabolites: CHEBI or PUBCHEM provide the most reliable results
   - For proteins: UNIPROT is recommended
   - For genes: HGNC is recommended

3. **Error Handling**:
   - The client has built-in retry logic with exponential backoff
   - Always use try/except blocks to handle possible exceptions
   - Always close the client using `await client.close()` when finished

4. **Caching**:
   - The client includes built-in caching to improve performance
   - Default cache size is 2048 entries, which can be adjusted in the constructor

5. **Performance Considerations**:
   - Process names in smaller batches (5-10) to avoid overwhelming the API
   - Expect average response times of 1-2 seconds for single name lookups
   - Consider increasing timeouts for batch operations

## Limitations

- Reverse mapping (from IDs to names) is not supported by the API
- Some databases (HMDB, DRUGBANK) have limited coverage
- The API may return multiple matches for a single name
- Match scores are not standardized across different entity types

## Integration with Mapping Pipelines

The `TranslatorNameResolverClient` is designed to work as a fallback mechanism in mapping pipelines, particularly when primary identifier mapping fails.

Example integration in a mapping pipeline:

```python
from biomapper.mapping.clients.translator_name_resolver_client import TranslatorNameResolverClient
from biomapper.core.mapping_executor import MappingExecutor

# Set up primary and fallback clients
primary_client = UniChemClient(config={"target_db": "CHEBI"})
fallback_client = TranslatorNameResolverClient(config={"target_db": "CHEBI"})

# Create mapping executor with fallback
executor = MappingExecutor(
    primary_client=primary_client,
    fallback_clients=[fallback_client],
    fallback_field="name"  # Use the name field for fallback mapping
)

# Execute mapping
results = await executor.execute_mapping(
    source_data=data,
    source_id_field="source_id",
    source_name_field="name",
    target_id_field="target_id"
)
```

## Performance Analysis

Performance testing shows the following average response times:

| Entity Type | Average Response Time |
|-------------|------------------------|
| Metabolites (CHEBI) | 1.3s per name |
| Metabolites (PUBCHEM) | 0.2s per name |
| Proteins (UNIPROT) | 1.6s per name |
| Genes (HGNC) | 1.1s per name |

These timings can vary based on network conditions and API load.