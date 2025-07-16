# Graph Cross-Reference Resolver

## Overview

The Graph Cross-Reference Resolver uses Neo4j to build and query a knowledge graph of biological entity relationships. This enables efficient resolution of complex cross-references, discovery of indirect mappings, and analysis of relationship patterns across different databases.

## Architecture

### Graph Schema

```cypher
// Node types
(:BiologicalEntity {
    id: String,              // Primary identifier
    type: String,            // protein, gene, metabolite, etc.
    source: String,          // Database source
    name: String,
    description: String,
    created_at: DateTime,
    updated_at: DateTime
})

(:Identifier {
    value: String,           // The identifier value
    type: String,            // Identifier type (UNIPROT, ENSEMBL, etc.)
    is_primary: Boolean
})

(:Database {
    name: String,            // Database name
    version: String,
    url: String
})

(:Ontology {
    id: String,              // Ontology ID
    name: String,
    namespace: String
})

// Relationship types
(:BiologicalEntity)-[:HAS_IDENTIFIER]->(:Identifier)
(:BiologicalEntity)-[:MAPS_TO {confidence: Float}]->(:BiologicalEntity)
(:BiologicalEntity)-[:IS_SYNONYM_OF]->(:BiologicalEntity)
(:BiologicalEntity)-[:BELONGS_TO]->(:Ontology)
(:Identifier)-[:FROM_DATABASE]->(:Database)
(:BiologicalEntity)-[:HAS_PROPERTY {key: String, value: String}]->()
```

### Core Components

```python
from typing import List, Dict, Any, Optional, Set, Tuple
from pydantic import BaseModel, Field
from neo4j import AsyncGraphDatabase, AsyncSession
import asyncio
from datetime import datetime

class GraphNode(BaseModel):
    """Represents a node in the graph."""
    id: str
    type: str
    source: str
    properties: Dict[str, Any] = Field(default_factory=dict)

class GraphRelationship(BaseModel):
    """Represents a relationship in the graph."""
    from_id: str
    to_id: str
    type: str
    properties: Dict[str, Any] = Field(default_factory=dict)

class CrossReferenceResult(BaseModel):
    """Result from cross-reference resolution."""
    query_id: str
    query_type: str
    mappings: List[Dict[str, Any]]
    paths: List[List[str]] = Field(default_factory=list)
    confidence_scores: Dict[str, float] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class GraphCrossReferenceResolver:
    """Resolver for biological cross-references using Neo4j."""
    
    def __init__(self, uri: str, auth: Tuple[str, str]):
        self.driver = AsyncGraphDatabase.driver(uri, auth=auth)
        self._session_pool: List[AsyncSession] = []
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
    
    async def close(self):
        """Close driver and sessions."""
        for session in self._session_pool:
            await session.close()
        await self.driver.close()
    
    async def build_entity_subgraph(
        self,
        entity_data: List[Dict[str, Any]],
        batch_size: int = 1000
    ) -> Dict[str, Any]:
        """Build subgraph from entity data."""
        async with self.driver.session() as session:
            nodes_created = 0
            relationships_created = 0
            
            # Process in batches
            for i in range(0, len(entity_data), batch_size):
                batch = entity_data[i:i + batch_size]
                
                # Create nodes and relationships
                result = await session.execute_write(
                    self._create_entity_batch,
                    batch
                )
                
                nodes_created += result["nodes_created"]
                relationships_created += result["relationships_created"]
            
            # Create indexes for performance
            await self._create_indexes(session)
            
            return {
                "nodes_created": nodes_created,
                "relationships_created": relationships_created,
                "batch_size": batch_size
            }
    
    async def _create_entity_batch(self, tx, batch: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create batch of entities in transaction."""
        # Create entities
        create_query = """
        UNWIND $batch as entity
        MERGE (e:BiologicalEntity {id: entity.id})
        SET e.type = entity.type,
            e.source = entity.source,
            e.name = entity.name,
            e.updated_at = datetime()
        
        WITH e, entity
        UNWIND entity.identifiers as identifier
        MERGE (i:Identifier {value: identifier.value, type: identifier.type})
        MERGE (e)-[:HAS_IDENTIFIER]->(i)
        
        WITH e, entity
        UNWIND entity.xrefs as xref
        MERGE (x:BiologicalEntity {id: xref.id})
        MERGE (e)-[r:MAPS_TO]->(x)
        SET r.confidence = xref.confidence
        """
        
        result = await tx.run(create_query, batch=batch)
        summary = await result.consume()
        
        return {
            "nodes_created": summary.counters.nodes_created,
            "relationships_created": summary.counters.relationships_created
        }
    
    async def _create_indexes(self, session: AsyncSession):
        """Create database indexes."""
        indexes = [
            "CREATE INDEX IF NOT EXISTS FOR (e:BiologicalEntity) ON (e.id)",
            "CREATE INDEX IF NOT EXISTS FOR (e:BiologicalEntity) ON (e.type)",
            "CREATE INDEX IF NOT EXISTS FOR (i:Identifier) ON (i.value)",
            "CREATE INDEX IF NOT EXISTS FOR (i:Identifier) ON (i.type)"
        ]
        
        for index_query in indexes:
            await session.run(index_query)
    
    async def resolve_cross_reference(
        self,
        identifier: str,
        identifier_type: Optional[str] = None,
        target_types: Optional[List[str]] = None,
        max_hops: int = 3
    ) -> CrossReferenceResult:
        """Resolve cross-references for an identifier."""
        async with self.driver.session() as session:
            # Build match clause
            match_clause = "MATCH (start:BiologicalEntity)"
            if identifier_type:
                match_clause = """
                MATCH (start:BiologicalEntity)-[:HAS_IDENTIFIER]->(i:Identifier)
                WHERE i.value = $identifier AND i.type = $identifier_type
                """
            else:
                match_clause = """
                MATCH (start:BiologicalEntity)
                WHERE start.id = $identifier
                   OR EXISTS {
                       (start)-[:HAS_IDENTIFIER]->(i:Identifier)
                       WHERE i.value = $identifier
                   }
                """
            
            # Build path query
            path_query = f"""
            {match_clause}
            CALL {{
                WITH start
                MATCH path = (start)-[:MAPS_TO*1..{max_hops}]-(target:BiologicalEntity)
                {"WHERE target.type IN $target_types" if target_types else ""}
                RETURN target, path, 
                       reduce(conf = 1.0, r in relationships(path) | conf * r.confidence) as path_confidence
                ORDER BY path_confidence DESC
                LIMIT 100
            }}
            RETURN start, collect(DISTINCT {{
                target: target,
                path: [n in nodes(path) | n.id],
                confidence: path_confidence,
                hops: length(path)
            }}) as mappings
            """
            
            params = {
                "identifier": identifier,
                "identifier_type": identifier_type,
                "target_types": target_types
            }
            
            result = await session.run(path_query, **params)
            record = await result.single()
            
            if not record:
                return CrossReferenceResult(
                    query_id=identifier,
                    query_type=identifier_type or "unknown",
                    mappings=[]
                )
            
            start_node = record["start"]
            mappings = record["mappings"]
            
            # Process mappings
            processed_mappings = []
            confidence_scores = {}
            paths = []
            
            for mapping in mappings:
                target = mapping["target"]
                target_id = target["id"]
                
                processed_mappings.append({
                    "id": target_id,
                    "type": target.get("type"),
                    "name": target.get("name"),
                    "source": target.get("source"),
                    "hops": mapping["hops"],
                    "confidence": mapping["confidence"]
                })
                
                confidence_scores[target_id] = mapping["confidence"]
                paths.append(mapping["path"])
            
            return CrossReferenceResult(
                query_id=identifier,
                query_type=start_node.get("type", "unknown"),
                mappings=processed_mappings,
                paths=paths,
                confidence_scores=confidence_scores,
                metadata={
                    "max_hops": max_hops,
                    "total_mappings": len(processed_mappings)
                }
            )
    
    async def find_mapping_paths(
        self,
        from_id: str,
        to_id: str,
        max_paths: int = 5
    ) -> List[Dict[str, Any]]:
        """Find all paths between two entities."""
        async with self.driver.session() as session:
            query = """
            MATCH (from:BiologicalEntity {id: $from_id}),
                  (to:BiologicalEntity {id: $to_id})
            MATCH path = allShortestPaths((from)-[:MAPS_TO*]-(to))
            WITH path, 
                 reduce(conf = 1.0, r in relationships(path) | conf * r.confidence) as confidence
            ORDER BY confidence DESC
            LIMIT $max_paths
            RETURN [n in nodes(path) | {
                id: n.id,
                type: n.type,
                name: n.name
            }] as nodes,
            [r in relationships(path) | {
                type: type(r),
                confidence: r.confidence
            }] as relationships,
            confidence,
            length(path) as path_length
            """
            
            result = await session.run(
                query,
                from_id=from_id,
                to_id=to_id,
                max_paths=max_paths
            )
            
            paths = []
            async for record in result:
                paths.append({
                    "nodes": record["nodes"],
                    "relationships": record["relationships"],
                    "confidence": record["confidence"],
                    "length": record["path_length"]
                })
            
            return paths
    
    async def analyze_entity_connectivity(
        self,
        entity_id: str,
        depth: int = 2
    ) -> Dict[str, Any]:
        """Analyze connectivity patterns for an entity."""
        async with self.driver.session() as session:
            query = """
            MATCH (e:BiologicalEntity {id: $entity_id})
            CALL {
                WITH e
                MATCH (e)-[:MAPS_TO*1..$depth]-(connected)
                RETURN connected.type as type, 
                       connected.source as source,
                       count(DISTINCT connected) as count
            }
            WITH e, collect({type: type, source: source, count: count}) as connections
            CALL {
                WITH e
                MATCH (e)-[:HAS_IDENTIFIER]->(i:Identifier)
                RETURN collect({type: i.type, value: i.value}) as identifiers
            }
            RETURN e.id as id,
                   e.type as type,
                   e.name as name,
                   identifiers,
                   connections,
                   size(connections) as total_connections
            """
            
            result = await session.run(
                query,
                entity_id=entity_id,
                depth=depth
            )
            
            record = await result.single()
            if not record:
                return {"error": f"Entity {entity_id} not found"}
            
            return dict(record)
    
    async def merge_duplicate_entities(
        self,
        duplicate_groups: List[List[str]]
    ) -> Dict[str, Any]:
        """Merge duplicate entities in the graph."""
        async with self.driver.session() as session:
            merged_count = 0
            
            for group in duplicate_groups:
                if len(group) < 2:
                    continue
                
                primary_id = group[0]
                duplicate_ids = group[1:]
                
                merge_query = """
                MATCH (primary:BiologicalEntity {id: $primary_id})
                UNWIND $duplicate_ids as dup_id
                MATCH (duplicate:BiologicalEntity {id: dup_id})
                
                // Transfer relationships
                CALL {
                    WITH primary, duplicate
                    MATCH (duplicate)-[r:HAS_IDENTIFIER]->(i)
                    MERGE (primary)-[:HAS_IDENTIFIER]->(i)
                }
                CALL {
                    WITH primary, duplicate
                    MATCH (duplicate)-[r:MAPS_TO]->(target)
                    WHERE target.id <> primary.id
                    MERGE (primary)-[new_r:MAPS_TO]->(target)
                    SET new_r.confidence = 
                        CASE WHEN new_r.confidence IS NULL 
                        THEN r.confidence 
                        ELSE (new_r.confidence + r.confidence) / 2 
                        END
                }
                
                // Delete duplicate
                DETACH DELETE duplicate
                
                RETURN count(duplicate) as merged
                """
                
                result = await session.run(
                    merge_query,
                    primary_id=primary_id,
                    duplicate_ids=duplicate_ids
                )
                
                summary = await result.single()
                merged_count += summary["merged"]
            
            return {
                "groups_processed": len(duplicate_groups),
                "entities_merged": merged_count
            }
```

## Integration with Actions

```python
@register_action("RESOLVE_CROSS_REFERENCES")
class ResolveCrossReferencesAction(TypedStrategyAction[ResolveParams, ResolveResult]):
    
    def __init__(self):
        super().__init__()
        self.resolver = None
    
    async def initialize(self, context: StrategyExecutionContext):
        """Initialize graph connection."""
        config = context.config.get("neo4j", {})
        self.resolver = GraphCrossReferenceResolver(
            uri=config.get("uri", "bolt://localhost:7687"),
            auth=(config.get("user", "neo4j"), config.get("password"))
        )
    
    async def execute_typed(
        self,
        params: ResolveParams,
        context: StrategyExecutionContext
    ) -> ResolveResult:
        """Resolve cross-references using graph."""
        
        # Build graph if needed
        if params.build_graph:
            build_result = await self.resolver.build_entity_subgraph(
                params.entity_data,
                batch_size=params.batch_size
            )
            context.logger.info(f"Built graph: {build_result}")
        
        # Resolve identifiers
        results = []
        for identifier in params.identifiers:
            result = await self.resolver.resolve_cross_reference(
                identifier=identifier.value,
                identifier_type=identifier.type,
                target_types=params.target_types,
                max_hops=params.max_hops
            )
            results.append(result)
        
        # Analyze connectivity if requested
        connectivity_analysis = {}
        if params.analyze_connectivity:
            for result in results[:10]:  # Limit analysis
                if result.mappings:
                    analysis = await self.resolver.analyze_entity_connectivity(
                        result.query_id
                    )
                    connectivity_analysis[result.query_id] = analysis
        
        return ResolveResult(
            resolved_count=len(results),
            resolutions=results,
            connectivity_analysis=connectivity_analysis,
            graph_stats=await self._get_graph_stats()
        )
    
    async def cleanup(self):
        """Clean up resources."""
        if self.resolver:
            await self.resolver.close()
```

## Query Examples

### Find All Protein Mappings

```cypher
// Find all mappings for a UniProt accession
MATCH (p:BiologicalEntity)-[:HAS_IDENTIFIER]->(i:Identifier {value: 'P04637', type: 'UNIPROT'})
MATCH (p)-[:MAPS_TO*1..2]-(mapped:BiologicalEntity)
WHERE mapped.type = 'protein'
RETURN DISTINCT mapped.id, mapped.source, mapped.name
ORDER BY mapped.source
```

### Discover Indirect Relationships

```cypher
// Find metabolites connected to a gene through proteins
MATCH (g:BiologicalEntity {type: 'gene', id: 'ENSG00000141510'})
MATCH path = (g)-[:MAPS_TO*2..4]-(m:BiologicalEntity {type: 'metabolite'})
WHERE ALL(r in relationships(path) WHERE r.confidence > 0.7)
RETURN m.id, m.name, 
       [n in nodes(path) | n.id + ' (' + n.type + ')'] as path_nodes,
       reduce(conf = 1.0, r in relationships(path) | conf * r.confidence) as path_confidence
ORDER BY path_confidence DESC
```

### Identify Hub Entities

```cypher
// Find highly connected entities (potential key nodes)
MATCH (e:BiologicalEntity)
WITH e, size((e)-[:MAPS_TO]-()) as degree
WHERE degree > 50
RETURN e.id, e.type, e.name, degree
ORDER BY degree DESC
LIMIT 20
```

## Performance Optimizations

### Batch Processing

```python
class BatchGraphBuilder:
    """Optimized batch builder for large datasets."""
    
    async def build_from_stream(
        self,
        data_stream: AsyncIterator[Dict[str, Any]],
        resolver: GraphCrossReferenceResolver,
        batch_size: int = 5000
    ):
        """Build graph from streaming data."""
        batch = []
        total_processed = 0
        
        async for record in data_stream:
            batch.append(record)
            
            if len(batch) >= batch_size:
                await resolver.build_entity_subgraph(batch, batch_size=1000)
                total_processed += len(batch)
                batch = []
                
                # Log progress
                if total_processed % 50000 == 0:
                    logger.info(f"Processed {total_processed:,} entities")
        
        # Process remaining
        if batch:
            await resolver.build_entity_subgraph(batch, batch_size=1000)
            total_processed += len(batch)
        
        return total_processed
```

### Caching Layer

```python
class CachedGraphResolver:
    """Graph resolver with Redis caching."""
    
    def __init__(self, resolver: GraphCrossReferenceResolver, redis_client):
        self.resolver = resolver
        self.redis = redis_client
        self.cache_ttl = 3600  # 1 hour
    
    async def resolve_cross_reference(self, identifier: str, **kwargs) -> CrossReferenceResult:
        """Resolve with caching."""
        cache_key = f"xref:{identifier}:{hash(frozenset(kwargs.items()))}"
        
        # Check cache
        cached = await self.redis.get(cache_key)
        if cached:
            return CrossReferenceResult.parse_raw(cached)
        
        # Resolve
        result = await self.resolver.resolve_cross_reference(identifier, **kwargs)
        
        # Cache result
        await self.redis.setex(
            cache_key,
            self.cache_ttl,
            result.json()
        )
        
        return result
```

## Configuration

```yaml
graph_resolver:
  neo4j:
    uri: "bolt://localhost:7687"
    user: "neo4j"
    password: "${NEO4J_PASSWORD}"
    max_connection_lifetime: 3600
    max_connection_pool_size: 50
  
  resolution:
    default_max_hops: 3
    confidence_threshold: 0.5
    batch_size: 5000
  
  caching:
    enabled: true
    ttl: 3600
    redis_url: "redis://localhost:6379"
```

## Benefits

1. **Complex Relationship Discovery**: Find indirect mappings through multiple hops
2. **Confidence Scoring**: Path-based confidence calculation
3. **Performance**: Graph queries outperform relational joins for connected data
4. **Flexibility**: Easy to add new relationship types and properties
5. **Visualization**: Graph structure enables intuitive visualization

## Next Steps

- Implement graph embedding for similarity search
- Add temporal versioning for historical analysis
- Create graph-based validation rules
- Build interactive visualization interface
- Develop graph-based machine learning features