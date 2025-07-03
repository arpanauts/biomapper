# Protein Mapping Tutorial

This tutorial demonstrates how to map protein identifiers and names using Biomapper's protein-specific strategies.

## Overview

Protein mapping is one of the most common use cases for Biomapper. This tutorial covers:
- Mapping protein names to UniProt IDs
- Converting between different protein identifier systems
- Handling protein synonyms and aliases
- Using protein-specific mapping strategies

## Prerequisites

```python
import asyncio
from biomapper.core import MappingExecutor, MappingExecutorBuilder
from biomapper.core.models import DatabaseConfig, CacheConfig
```

## Basic Protein Mapping

### Setup

First, initialize the mapping executor:

```python
async def setup_executor():
    # Configure the executor
    db_config = DatabaseConfig(url="sqlite+aiosqlite:///data/protein_mapping.db")
    cache_config = CacheConfig(backend="memory", ttl=3600)
    
    # Build and initialize
    executor = MappingExecutorBuilder.create(
        db_config=db_config,
        cache_config=cache_config
    )
    await executor.initialize()
    
    return executor
```

### Example 1: Simple Protein Name Mapping

Map common protein names to UniProt identifiers:

```python
async def map_protein_names():
    executor = await setup_executor()
    
    try:
        # Common protein names
        protein_names = [
            "BRCA1",
            "p53",
            "Insulin",
            "Hemoglobin alpha",
            "EGFR"
        ]
        
        # Execute mapping
        result = await executor.execute(
            entity_names=protein_names,
            entity_type="protein"
        )
        
        # Display results
        for mapping in result.mappings:
            print(f"{mapping.query_id} -> {mapping.mapped_id} "
                  f"(confidence: {mapping.confidence:.2f})")
                  
    finally:
        await executor.shutdown()
```

### Example 2: Using Protein-Specific YAML Strategy

Create a comprehensive protein mapping strategy:

```yaml
# configs/strategies/protein_comprehensive.yaml
name: protein_comprehensive_mapping
version: "1.0"
entity_type: protein
description: Comprehensive protein mapping with multiple fallback options

actions:
  - type: LOAD_INPUT_DATA
    name: load_proteins
    config:
      source_field: entities
      
  - type: API_RESOLVER
    name: uniprot_direct
    config:
      api_endpoint: uniprot
      search_fields: ["gene_name", "protein_name"]
      confidence_threshold: 0.9
      
  - type: API_RESOLVER
    name: uniprot_synonym_search
    config:
      api_endpoint: uniprot
      search_fields: ["synonyms", "alternative_names"]
      only_unmapped: true
      confidence_threshold: 0.8
      
  - type: UNIPROT_HISTORICAL_RESOLVER
    name: historical_lookup
    config:
      only_unmapped: true
      include_deleted: true
      
  - type: SAVE_RESULTS
    name: save_mappings
    config:
      output_format: json
      include_metadata: true
      include_confidence: true
```

Execute the strategy:

```python
async def use_protein_strategy():
    executor = await setup_executor()
    
    try:
        # Load protein list
        proteins = [
            "BRCA1",
            "BRCA2", 
            "MLH1",
            "MSH2",
            "TP53",
            "PTEN",
            "APC",
            "KRAS"
        ]
        
        # Execute comprehensive strategy
        result = await executor.execute_yaml_strategy(
            strategy_file="configs/strategies/protein_comprehensive.yaml",
            input_data={
                "entities": proteins,
                "entity_type": "protein"
            },
            options={
                "include_isoforms": True,
                "species": "human"
            }
        )
        
        # Process results
        if result.success:
            mappings = result.data.get("mappings", [])
            print(f"Successfully mapped {len(mappings)} proteins")
            
            # Show detailed results
            for mapping in mappings:
                print(f"\nProtein: {mapping['query_id']}")
                print(f"  UniProt ID: {mapping['mapped_id']}")
                print(f"  Confidence: {mapping['confidence']}")
                print(f"  Source: {mapping['source']}")
                if 'metadata' in mapping:
                    print(f"  Full Name: {mapping['metadata'].get('protein_name')}")
                    
    finally:
        await executor.shutdown()
```

### Example 3: Cross-Database Protein Mapping

Map proteins across different databases:

```python
async def cross_database_mapping():
    executor = await setup_executor()
    
    try:
        # Define cross-reference strategy
        strategy = {
            "name": "protein_cross_reference",
            "actions": [
                {
                    "type": "LOAD_INPUT_DATA",
                    "name": "load_proteins"
                },
                {
                    "type": "API_RESOLVER", 
                    "name": "get_uniprot",
                    "config": {
                        "api_endpoint": "uniprot",
                        "return_cross_references": True
                    }
                },
                {
                    "type": "CROSS_REFERENCE_MAPPER",
                    "name": "map_to_other_dbs",
                    "config": {
                        "target_databases": ["RefSeq", "Ensembl", "PDB", "STRING"],
                        "include_all_matches": True
                    }
                }
            ]
        }
        
        # Execute cross-database mapping
        proteins = ["P04637", "P38398", "Q13315"]  # UniProt IDs
        
        result = await executor.execute_custom_strategy(
            strategy=strategy,
            entity_names=proteins,
            context={"entity_type": "protein"}
        )
        
        # Display cross-references
        for mapping in result.mappings:
            print(f"\nUniProt: {mapping.query_id}")
            if mapping.cross_references:
                for db, ids in mapping.cross_references.items():
                    print(f"  {db}: {', '.join(ids)}")
                    
    finally:
        await executor.shutdown()
```

### Example 4: Handling Protein Complexes and Families

```python
async def map_protein_families():
    executor = await setup_executor()
    
    try:
        # Protein family and complex names
        protein_groups = [
            "Hemoglobin",
            "Cytochrome c oxidase",
            "RNA polymerase II",
            "Proteasome",
            "Histone H3"
        ]
        
        # Use a strategy that handles protein families
        result = await executor.execute_yaml_strategy(
            strategy_file="configs/strategies/protein_family_mapping.yaml",
            input_data={
                "entities": protein_groups,
                "entity_type": "protein",
                "mapping_mode": "family"
            }
        )
        
        # Process family mappings
        if result.success:
            for family_result in result.data.get("family_mappings", []):
                print(f"\nProtein Family: {family_result['query']}")
                print(f"  Family ID: {family_result['family_id']}")
                print(f"  Members: {len(family_result['members'])}")
                for member in family_result['members'][:5]:  # Show first 5
                    print(f"    - {member['id']}: {member['name']}")
                if len(family_result['members']) > 5:
                    print(f"    ... and {len(family_result['members']) - 5} more")
                    
    finally:
        await executor.shutdown()
```

## Advanced Topics

### Protein Isoform Handling

```python
async def handle_isoforms():
    """Map proteins including their isoforms."""
    executor = await setup_executor()
    
    try:
        # Configure to include isoforms
        result = await executor.execute(
            entity_names=["BRCA1", "TP53"],
            entity_type="protein",
            options={
                "include_isoforms": True,
                "isoform_format": "full"  # or "canonical_only"
            }
        )
        
        for mapping in result.mappings:
            print(f"\nProtein: {mapping.query_id}")
            print(f"  Canonical: {mapping.mapped_id}")
            if mapping.isoforms:
                print(f"  Isoforms: {', '.join(mapping.isoforms)}")
                
    finally:
        await executor.shutdown()
```

### Species-Specific Mapping

```python
async def species_specific_mapping():
    """Map proteins for specific species."""
    executor = await setup_executor()
    
    try:
        proteins = ["insulin", "albumin", "myoglobin"]
        
        # Map for multiple species
        for species in ["human", "mouse", "rat"]:
            print(f"\n{species.upper()} proteins:")
            
            result = await executor.execute(
                entity_names=proteins,
                entity_type="protein",
                options={
                    "species": species,
                    "species_id": {
                        "human": 9606,
                        "mouse": 10090,
                        "rat": 10116
                    }[species]
                }
            )
            
            for mapping in result.mappings:
                if mapping.mapped_id:
                    print(f"  {mapping.query_id} -> {mapping.mapped_id}")
                    
    finally:
        await executor.shutdown()
```

## Best Practices

1. **Use appropriate confidence thresholds**: Protein mapping often requires high confidence (>0.9) for critical applications

2. **Handle synonyms**: Protein names can vary significantly (e.g., "p53" vs "TP53" vs "tumor protein p53")

3. **Consider species**: Always specify species when known to avoid cross-species mappings

4. **Use comprehensive strategies**: Combine multiple data sources for better coverage

5. **Cache results**: Protein mappings are relatively stable, so caching can significantly improve performance

## Common Issues and Solutions

### Issue 1: Ambiguous Protein Names
```python
# Solution: Use additional context
result = await executor.execute(
    entity_names=["CAT"],  # Could be Catalase or something else
    entity_type="protein",
    options={
        "context": "enzyme",
        "species": "human",
        "preferred_name": "Catalase"
    }
)
```

### Issue 2: Obsolete Identifiers
```python
# Solution: Use historical resolver
result = await executor.execute_yaml_strategy(
    strategy_file="configs/strategies/protein_with_history.yaml",
    input_data={"entities": ["P12345_RETIRED"]},
    options={"include_obsolete": True}
)
```

### Issue 3: Performance with Large Lists
```python
# Solution: Use batch processing
import pandas as pd

async def batch_process_proteins(protein_list, batch_size=100):
    executor = await setup_executor()
    all_results = []
    
    try:
        for i in range(0, len(protein_list), batch_size):
            batch = protein_list[i:i+batch_size]
            result = await executor.execute(
                entity_names=batch,
                entity_type="protein"
            )
            all_results.extend(result.mappings)
            
        return all_results
        
    finally:
        await executor.shutdown()
```

## Next Steps

- Learn about [YAML Strategy Development](yaml_mapping_strategies.md) for custom protein mapping workflows
- Explore [Multi-Provider Integration](multi_provider.md) for combining multiple protein databases
- Check the [API Documentation](../api/README.md) for building protein mapping services