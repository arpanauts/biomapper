# ProteinNameMapper Implementation

## Overview

The `ProteinNameMapper` provides mapping functionality for protein names and identifiers across different nomenclature systems. It extends the `AbstractEntityMapper` base class and integrates with the Resource Metadata System to enable intelligent routing of mapping operations.

## Design Goals

1. **Comprehensive Coverage**: Support mapping between major protein identifier systems
2. **Performance Optimization**: Leverage caching and performance metrics for efficient mapping
3. **Extensibility**: Allow for easy addition of new protein data sources
4. **High Accuracy**: Combine multiple resources to improve mapping accuracy
5. **Batch Processing**: Efficiently handle batch mapping operations

## Implementation

```python
class ProteinNameMapper(AbstractEntityMapper):
    """Mapper for protein names and identifiers."""
    
    def __init__(self, db_path=None, config=None):
        """Initialize the protein name mapper."""
        super().__init__("protein", db_path, config)
    
    async def _setup_entity_resources(self):
        """Setup protein-specific resources."""
        # UniProt adapter
        try:
            uniprot_config = self.config.get("uniprot_api", {})
            from biomapper.mapping.adapters.uniprot_adapter import UniProtAdapter
            uniprot_adapter = UniProtAdapter(uniprot_config, "uniprot_api")
            await self.dispatcher.add_resource_adapter("uniprot_api", uniprot_adapter)
        except Exception as e:
            self.logger.warning(f"Failed to initialize UniProt adapter: {e}")
            
        # PDB adapter
        try:
            pdb_config = self.config.get("pdb_api", {})
            from biomapper.mapping.adapters.pdb_adapter import PDBAdapter
            pdb_adapter = PDBAdapter(pdb_config, "pdb_api")
            await self.dispatcher.add_resource_adapter("pdb_api", pdb_adapter)
        except Exception as e:
            self.logger.warning(f"Failed to initialize PDB adapter: {e}")
            
        # InterPro adapter
        try:
            interpro_config = self.config.get("interpro_api", {})
            from biomapper.mapping.adapters.interpro_adapter import InterProAdapter
            interpro_adapter = InterProAdapter(interpro_config, "interpro_api")
            await self.dispatcher.add_resource_adapter("interpro_api", interpro_adapter)
        except Exception as e:
            self.logger.warning(f"Failed to initialize InterPro adapter: {e}")
```

## Key Methods

### Mapping Methods

The `ProteinNameMapper` provides the following key mapping methods:

1. **map_name_to_uniprot**
   ```python
   async def map_name_to_uniprot(self, protein_name, organism="human", confidence_threshold=0.5):
       """
       Map a protein name to UniProt identifier.
       
       Args:
           protein_name: Protein name or gene symbol
           organism: Organism name or taxonomy ID
           confidence_threshold: Minimum confidence score
           
       Returns:
           List of mappings with UniProt IDs and confidence scores
       """
       return await self.map_entity(
           source_id=protein_name,
           source_type="protein_name",
           target_type="uniprot",
           confidence_threshold=confidence_threshold,
           organism=organism
       )
   ```

2. **map_uniprot_to_pdb**
   ```python
   async def map_uniprot_to_pdb(self, uniprot_id, confidence_threshold=0.5):
       """Map a UniProt ID to PDB structure identifiers."""
       return await self.map_entity(
           source_id=uniprot_id,
           source_type="uniprot",
           target_type="pdb",
           confidence_threshold=confidence_threshold
       )
   ```

3. **map_gene_to_protein**
   ```python
   async def map_gene_to_protein(self, gene_symbol, organism="human", confidence_threshold=0.5):
       """Map a gene symbol to protein information."""
       return await self.map_entity(
           source_id=gene_symbol,
           source_type="gene_symbol",
           target_type="uniprot",
           confidence_threshold=confidence_threshold,
           organism=organism
       )
   ```

4. **batch_map_names**
   ```python
   async def batch_map_names(self, protein_names, target_type="uniprot", organism="human", confidence_threshold=0.5):
       """Map multiple protein names in batch."""
       return await self.batch_map_entities(
           source_ids=protein_names,
           source_type="protein_name",
           target_type=target_type,
           confidence_threshold=confidence_threshold,
           organism=organism
       )
   ```

5. **get_protein_metadata**
   ```python
   async def get_protein_metadata(self, identifier, id_type, preferred_resource=None):
       """Get extended metadata for a protein."""
       # Implementation similar to MetaboliteNameMapper's get_metabolite_metadata
       # ...
   ```

### Synchronous Wrappers

For backward compatibility, the mapper includes synchronous wrapper methods:

```python
def map_name_to_uniprot_sync(self, protein_name, organism="human", confidence_threshold=0.5):
    """Synchronous wrapper for map_name_to_uniprot."""
    return self.run_sync(
        self.map_name_to_uniprot, 
        protein_name, 
        organism, 
        confidence_threshold
    )

# Additional synchronous wrappers for other methods...
```

## Resource Adapters

### UniProtAdapter

The UniProt adapter connects the mapper to UniProt web services:

```python
class UniProtAdapter(BaseResourceAdapter):
    """Adapter for UniProt web services."""
    
    def __init__(self, config=None, name="uniprot_api"):
        """Initialize the UniProt adapter."""
        super().__init__(config or {}, name)
        from biomapper.mapping.clients.uniprot_client import UniProtClient
        self.client = UniProtClient(**config or {})
    
    async def connect(self):
        """Connect to the UniProt API."""
        # Most REST APIs don't require explicit connection
        return True
    
    async def map_entity(self, source_id, source_type, target_type, **kwargs):
        """Map entity using UniProt services."""
        organism = kwargs.get("organism", "human")
        
        if source_type == "protein_name" and target_type == "uniprot":
            # Search by protein name
            results = await self.client.search_protein(source_id, organism)
            return [
                {
                    "target_id": r.get("accession"),
                    "confidence": r.get("score", 0.9) / 100,  # Normalize to 0-1
                    "source": self.name,
                    "metadata": {
                        "entry_name": r.get("entry_name"),
                        "protein_name": r.get("protein_name"),
                        "gene_name": r.get("gene_name"),
                        "organism": r.get("organism")
                    }
                }
                for r in results if r.get("accession")
            ]
        
        # Additional mapping logic for other source/target combinations...
        
        # Unsupported mapping type
        return []
```

## Usage Patterns

### Basic Usage

```python
# Initialize the mapper
protein_mapper = ProteinNameMapper()

# Map a protein name to UniProt ID
results = await protein_mapper.map_name_to_uniprot("p53", organism="human")

# Access the results
for result in results:
    print(f"UniProt ID: {result['target_id']}, Confidence: {result['confidence']}")
    for key, value in result.get("metadata", {}).items():
        print(f"  {key}: {value}")
```

### Batch Mapping

```python
# Map multiple protein names in a single operation
protein_names = ["p53", "BRCA1", "EGFR"]
batch_results = await protein_mapper.batch_map_names(protein_names, target_type="uniprot")

# Process the results
for name, mappings in batch_results.items():
    print(f"Protein: {name}")
    for mapping in mappings:
        print(f"  UniProt ID: {mapping['target_id']}, Confidence: {mapping['confidence']}")
```

### With Resource Preferences

```python
# Specify a preferred resource for mapping
results = await protein_mapper.map_name_to_uniprot(
    "insulin", 
    preferred_resource="uniprot_api"
)
```

## Performance Considerations

1. **Resource Prioritization**: Resources are prioritized based on past performance
2. **Caching**: Results are cached to improve future mapping speed
3. **Batch Processing**: Batch operations reduce network overhead
4. **Lazy Initialization**: Resources are only initialized when needed

## Integration with SPOKE

The mapper integrates with the SPOKE knowledge graph through the `SpokeResourceAdapter`:

```python
# The adapter is automatically set up by the AbstractEntityMapper base class
# when the SPOKE configuration is provided:
config = {
    "spoke_graph": {
        "url": "http://localhost:8529",
        "username": "spoke_user",
        "password": "spoke_password",
        "database": "spoke"
    }
}

protein_mapper = ProteinNameMapper(config=config)
```

## Error Handling

The mapper implements robust error handling:

1. **Resource Initialization Failures**: Logs warnings and continues with available resources
2. **Mapping Operation Errors**: Falls back to alternative resources when a mapping operation fails
3. **Validation**: Validates inputs before processing

## Extension Points

The mapper can be extended in several ways:

1. **New Resources**: Additional resources can be added through the `_setup_entity_resources` method
2. **Custom Mappings**: Additional mapping methods can be added for specific use cases
3. **Mapping Pipeline**: The mapping pipeline can be customized through subclassing
