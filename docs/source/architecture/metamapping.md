# Metamapping with the Resource Metadata System

## Overview

Metamapping is an advanced feature of Biomapper's Resource Metadata System that enables complex, multi-step mapping between biological ontologies that lack direct connections. When direct mapping from a source ontology to a target ontology is unavailable, metamapping automatically discovers and executes paths through intermediate ontologies.

## Key Concepts

### What is Metamapping?

Metamapping (also called transitive mapping) refers to the process of mapping between two ontologies using one or more intermediate steps:

```
Source Ontology (A) → Intermediate Ontology (B) → Target Ontology (C)
```

For example, if a direct mapping from PubChem to HMDB isn't available, but mappings from PubChem to ChEBI and from ChEBI to HMDB are available, metamapping can combine these:

```
PubChem (CID123456) → ChEBI (CHEBI:15377) → HMDB (HMDB0000122)
```

### Core Components

The metamapping system consists of two main components:

1. **`MetamappingEngine`**: Manages the discovery and execution of mapping paths
2. **`MappingDispatcher`** (enhanced): Integrates metamapping capabilities into the main mapping workflow

## Implementation Details

### Path Discovery Algorithm

Metamapping uses a breadth-first search (BFS) algorithm to find the shortest path between ontologies:

```python
async def find_mapping_path(self, source_type: str, target_type: str):
    """Find a path to map from source_type to target_type."""
    # Get all possible ontology types
    possible_intermediates = self.metadata_manager.get_all_ontology_types()
    
    # Queue for BFS, each entry contains (current_type, path_so_far)
    queue = deque([(source_type, [])])
    visited = {source_type}  # Track visited types to avoid cycles
    
    while queue:
        current_type, path = queue.popleft()
        
        # Check if we've reached the target
        if current_type == target_type and path:
            return path
        
        # If path is already at max length, don't extend further
        if len(path) >= self.max_path_length:
            continue
        
        # Find all possible next steps
        for next_type in possible_intermediates:
            if next_type in visited:
                continue
                
            resources = self.metadata_manager.find_resources_by_capability(
                source_type=current_type,
                target_type=next_type
            )
            
            if resources:
                # Add this step to the path
                new_path = path + [{
                    "source_type": current_type,
                    "target_type": next_type,
                    "resources": resources
                }]
                
                if next_type == target_type:
                    return new_path
                
                queue.append((next_type, new_path))
                visited.add(next_type)
    
    # No path found
    return None
```

This algorithm ensures that:

- The shortest path is found first (fewest number of steps)
- Cycles are avoided by tracking visited ontology types
- Paths longer than a configurable maximum are not explored
- Each step in the path includes the resources capable of performing that mapping

### Executing Multi-Step Mappings

Once a path is discovered, the system executes it step by step:

```python
async def execute_mapping_path(self, source_id, mapping_path, **kwargs):
    """Execute a multi-step mapping path."""
    current_ids = [{"id": source_id, "confidence": 1.0}]
    
    # For each step in the path
    for step in mapping_path:
        source_type = step["source_type"]
        target_type = step["target_type"]
        resources = step["resources"]
        
        # Map current IDs to next step
        next_ids = []
        for id_info in current_ids:
            # Try to map this ID using available resources
            step_results = await self._map_entity_with_resources(
                source_id=id_info["id"],
                source_type=source_type,
                target_type=target_type,
                resources=resources,
                **kwargs
            )
            
            # Accumulate results with compounded confidence
            for result in step_results:
                # Track the mapping path
                path_entry = {
                    "source_id": id_info["id"],
                    "target_id": result["target_id"],
                    "resource": result["source"]
                }
                
                next_ids.append({
                    "id": result["target_id"],
                    # Multiply confidences
                    "confidence": id_info["confidence"] * result["confidence"],
                    "path": id_info.get("path", []) + [path_entry]
                })
        
        # If we couldn't map anything, the path failed
        if not next_ids:
            return []
            
        # Update current IDs for the next step
        current_ids = next_ids
    
    # Format final results
    results = []
    for id_info in current_ids:
        results.append({
            "target_id": id_info["id"],
            "confidence": id_info["confidence"],
            "source": "metamapping",
            "metadata": {"mapping_path": id_info["path"]}
        })
            
    return results
```

Key aspects of execution:

- Each step's results feed into the next step
- Confidence scores are multiplied along the path
- The complete mapping path is preserved in the metadata
- Intermediate results are cached for future use

### Confidence Calculation

Confidence scores in metamapping are calculated using the multiplication principle:

```
path_confidence = confidence_step1 × confidence_step2 × ... × confidence_stepN
```

This approach ensures that:

- Multiple uncertain steps result in lower overall confidence
- A path is only as strong as its weakest link
- Users can set confidence thresholds to filter less reliable mappings

### Caching and Performance Optimization

The metamapping system incorporates several optimizations:

1. **Path Caching**: Discovered paths are cached to avoid repeated searches
2. **Intermediate Result Caching**: Each step's results are saved to the SQLite cache
3. **Complete Path Caching**: The final source→target mapping is also cached
4. **Resource Prioritization**: Resources are prioritized based on past performance

## Example Workflow

### PubChem to HMDB Example

This example demonstrates how metamapping works for a PubChem to HMDB conversion:

1. **Direct Mapping Attempt**:
   ```python
   results = await mapper.map_entity(
       source_id="CID123456", 
       source_type="pubchem", 
       target_type="hmdb"
   )
   ```

2. **Path Discovery** (if direct mapping fails):
   ```
   Path found: pubchem → chebi → hmdb
   ```

3. **First Step Execution**:
   ```
   Map "CID123456" (pubchem) → "CHEBI:15377" (chebi) using PubChemAdapter
   Confidence: 0.95
   ```

4. **Second Step Execution**:
   ```
   Map "CHEBI:15377" (chebi) → "HMDB0000122" (hmdb) using UniChemAdapter
   Confidence: 0.98
   ```

5. **Result Composition**:
   ```
   Final mapping: "CID123456" → "HMDB0000122"
   Combined confidence: 0.95 × 0.98 = 0.931
   ```

6. **Caching**:
   ```
   Cache intermediate: "CID123456" (pubchem) → "CHEBI:15377" (chebi)
   Cache intermediate: "CHEBI:15377" (chebi) → "HMDB0000122" (hmdb)
   Cache complete: "CID123456" (pubchem) → "HMDB0000122" (hmdb)
   ```

### Integration with SPOKE

The SPOKE knowledge graph is particularly valuable for metamapping because:

1. It already contains many entity relationships
2. It can efficiently discover multi-step paths using graph traversal
3. Its graph structure naturally represents the connections between entities

## API Usage

### Basic Usage

```python
from biomapper.mapping import MetaboliteNameMapper

# Initialize with metamapping enabled (default)
mapper = MetaboliteNameMapper()

# This will automatically use metamapping if needed
results = await mapper.map_entity(
    source_id="CID123456",
    source_type="pubchem",
    target_type="hmdb"
)

# Check if result came from metamapping
for result in results:
    if result["source"] == "metamapping":
        print(f"Metamapping path: {result['metadata']['mapping_path']}")
```

### Controlling Metamapping

```python
# Disable metamapping globally
mapper.dispatcher.enable_metamapping = False

# Override for a specific call
results = await mapper.map_entity(
    source_id="CID123456",
    source_type="pubchem",
    target_type="hmdb",
    allow_metamapping=True  # Override global setting
)
```

### Setting Path Length Limits

```python
# Limit maximum path length (default is 3)
mapper.dispatcher.metamapping_engine.max_path_length = 2
```

## Performance Considerations

Metamapping introduces additional computational complexity:

1. **Path Discovery Overhead**: Finding paths requires querying capabilities for many resource combinations
2. **Multiple API Calls**: Each step may involve calls to different resources
3. **Combinatorial Expansion**: Each step might produce multiple IDs that need to be processed

To manage performance:

- The system uses a breadth-first approach to find the shortest path first
- Path length is limited to prevent excessive searches
- Caching of both paths and results improves subsequent requests
- Resource prioritization focuses on the most efficient resources first

## Troubleshooting

Common issues with metamapping:

1. **No Path Found**: Check if the ontologies are connected through any intermediate steps
2. **Low Confidence Results**: Examine the individual step confidences to identify weak links
3. **Performance Issues**: Consider limiting max_path_length or disabling metamapping for time-critical operations

## Future Enhancements

Planned improvements to the metamapping system:

1. **Parallel Path Execution**: Explore multiple paths simultaneously
2. **Weighted Path Selection**: Consider confidence and performance in path ranking
3. **Resource-Specific Parameters**: Allow resources to receive custom parameters for metamapping
4. **Adaptive Learning**: Analyze successful paths to improve future routing decisions
