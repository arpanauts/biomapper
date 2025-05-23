# Name Resolution Clients for Biomapper

This guide provides instructions for using and testing the name resolution clients in Biomapper. These clients enable mapping between entity names and standardized identifiers, with a focus on metabolites/compounds.

## Available Clients

Biomapper provides two primary name resolution clients:

1. **TranslatorNameResolverClient**: Uses the Translator Name Resolution API developed by the NCATS Biomedical Data Translator consortium.
2. **UMLSClient**: Uses the UMLS Terminology Services (UTS) REST API.

Both clients implement the standard `BaseMappingClient` interface and can be used with `MappingExecutor` for entity mapping.

## TranslatorNameResolverClient

### Overview

The `TranslatorNameResolverClient` provides name-to-identifier mapping through the SRI Name Resolution API. It's particularly useful as a fallback mechanism when primary identifier mapping fails.

### Configuration

```python
from biomapper.mapping.clients.translator_name_resolver_client import TranslatorNameResolverClient

# Initialize the client
client = TranslatorNameResolverClient(config={
    "target_db": "CHEBI",  # Required
    "match_threshold": 0.5,  # Optional (default: 0.5)
    "timeout": 30,  # Optional (default: 30 seconds)
    "max_retries": 3  # Optional (default: 3)
})
```

### Testing the Client

We provide a test script to verify the client's functionality:

```bash
# Basic testing
python scripts/test_translator_name_resolver.py

# Comprehensive testing with different entity types and configurations
python scripts/test_translator_name_resolver_comprehensive.py
```

No API key is required for the Translator Name Resolution API, making it easy to test and integrate.

## UMLSClient

### Overview

The `UMLSClient` provides mapping between entity names and UMLS Concept Unique Identifiers (CUIs), which can then be linked to various source terminologies. It's particularly useful for more complex mappings that benefit from UMLS's rich terminology integration.

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

### Getting a UMLS API Key

To use the `UMLSClient`, you need a UMLS API key:

1. Sign up for a UMLS account at [https://uts.nlm.nih.gov/uts/](https://uts.nlm.nih.gov/uts/)
2. After approval, log in to the UTS website
3. Navigate to "My Profile" > "API Keys"
4. Generate a new API key

### Setting Up the API Key

Set the UMLS API key as an environment variable:

```bash
# For temporary use
export UMLS_API_KEY="your_umls_api_key"

# For permanent use, add to your shell profile (.bashrc, .zshrc, etc.)
echo 'export UMLS_API_KEY="your_umls_api_key"' >> ~/.bashrc
source ~/.bashrc
```

### Testing the Client

We provide a test script to verify the client's functionality:

```bash
# Set the API key if not already in your environment
export UMLS_API_KEY="your_umls_api_key"

# Run the test script
python scripts/test_umls_client.py
```

## Integrating with Mapping Pipelines

Both clients can be integrated into mapping pipelines using `MappingExecutor`:

```python
from biomapper.mapping.clients.translator_name_resolver_client import TranslatorNameResolverClient
from biomapper.mapping.clients.umls_client import UMLSClient
from biomapper.core.mapping_executor import MappingExecutor

# Choose primary and fallback clients based on your needs
primary_client = TranslatorNameResolverClient(config={"target_db": "CHEBI"})
fallback_client = UMLSClient(config={"target_db": "CHEBI", "api_key": "your_umls_api_key"})

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

## Client Selection Guidelines

When choosing between these clients, consider:

1. **API Access**: The TranslatorNameResolverClient doesn't require authentication, while UMLSClient requires a UMLS API key.
2. **Coverage**: UMLSClient typically has broader coverage due to UMLS's extensive terminology integration.
3. **Performance**: TranslatorNameResolverClient is generally faster and has better caching.
4. **Specificity**: UMLSClient provides more detailed semantic type filtering, which can be valuable for specialized domains.

For most general-purpose metabolite name resolution tasks, the TranslatorNameResolverClient is recommended as the primary client due to its simplicity and performance.

## Performance Considerations

- Both clients implement caching to improve performance for repeated queries
- UMLSClient is generally slower due to its multi-step lookup process (search → concept details → atoms)
- Process entities in batches to optimize throughput
- Implement appropriate error handling and retry logic in your application

## Additional Resources

- [Translator Name Resolution API Documentation](https://name-resolution-sri.renci.org/)
- [UMLS Terminology Services API Documentation](https://documentation.uts.nlm.nih.gov/rest/home.html)
- [UMLS Account Registration](https://uts.nlm.nih.gov/uts/signup-login)