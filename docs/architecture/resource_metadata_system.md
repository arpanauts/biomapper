# Resource Metadata System Architecture

## Executive Summary

This document outlines the architecture for a comprehensive metadata management system within Biomapper. The system aims to capture, store, and leverage rich metadata from various biological entity mapping sources, with particular emphasis on the newly implemented PubChem RAG mapping client and future enhancements. The architecture addresses current gaps in metadata persistence while providing a foundation for advanced features like confidence scoring, result ranking, and provenance tracking.

## 1. Overview

### 1.1 Current State

Biomapper currently calculates rich metadata during mapping execution but has limited persistence and exposure of this information:

- **MappingExecutor** generates detailed metadata including confidence scores, path details, and execution metrics
- **EntityMapping** model has fields for metadata storage but they're not consistently populated
- **API layer** exposes only basic mapping results without detailed metadata
- **PubChemRAGMappingClient** produces similarity scores and embedding metadata that aren't fully utilized

### 1.2 Vision

The Resource Metadata System will provide:

1. **Comprehensive metadata capture** from all mapping sources
2. **Persistent storage** with efficient retrieval mechanisms
3. **Rich integration** with existing Biomapper components
4. **User-facing features** for transparency and decision support
5. **Foundation for advanced capabilities** like ML-based path selection and quality assessment

## 2. Types of Metadata

### 2.1 Resource-Level Metadata

Metadata about mapping resources and their capabilities:

```yaml
ResourceMetadata:
  - resource_id: Unique identifier
  - resource_type: API, Database, RAG, etc.
  - capabilities:
    - supported_entity_types: [Compound, Protein, Gene, etc.]
    - supported_operations: [name_to_id, id_to_id, synonym_search, etc.]
    - performance_characteristics:
      - avg_response_time_ms: float
      - success_rate: float
      - rate_limits: {requests_per_second: int, daily_quota: int}
  - data_quality:
    - last_updated: datetime
    - data_version: string
    - coverage_statistics: {entity_count: int, relationship_count: int}
```

### 2.2 Entity-Level Metadata

Metadata about specific biological entities:

```yaml
EntityMetadata:
  - identifiers:
    - primary_id: {namespace: string, value: string}
    - secondary_ids: [{namespace: string, value: string}]
    - historical_ids: [{namespace: string, value: string, valid_until: datetime}]
  - properties:
    - canonical_name: string
    - synonyms: [string]
    - descriptions: {brief: string, detailed: string}
    - structural_data:  # For compounds
      - molecular_formula: string
      - inchi_key: string
      - smiles: string
      - molecular_weight: float
    - functional_data:  # For proteins/genes
      - organism: string
      - gene_symbols: [string]
      - protein_names: [string]
  - relationships:
    - parent_entities: [{type: string, id: string}]
    - child_entities: [{type: string, id: string}]
    - associated_entities: [{type: string, id: string, relationship: string}]
```

### 2.3 Mapping-Level Metadata

Metadata about specific mapping operations:

```yaml
MappingMetadata:
  - execution_metadata:
    - timestamp: datetime
    - execution_id: uuid
    - user_context: {session_id: string, request_id: string}
    - execution_time_ms: float
  - provenance:
    - mapping_path: {path_id: string, steps: [step_details]}
    - resources_used: [resource_id]
    - transformations_applied: [transformation_type]
  - quality_metrics:
    - confidence_score: float  # 0.0-1.0
    - confidence_factors:
      - method_reliability: float
      - data_freshness: float
      - path_directness: float
    - validation_status: {status: string, validator: string, timestamp: datetime}
  - rag_specific:  # For RAG-based mappings
    - similarity_score: float
    - embedding_model: string
    - statistical_significance: {p_value: float, method: string}
    - top_k_alternatives: [{id: string, score: float}]
  - llm_metadata:  # When LLM is used
    - model_used: string
    - prompt_template: string
    - justification: string
    - token_usage: {prompt: int, completion: int}
```

### 2.4 Performance Metadata

System performance and usage metrics:

```yaml
PerformanceMetadata:
  - query_metrics:
    - query_hash: string
    - frequency: int
    - avg_response_time: float
    - cache_hit_rate: float
  - resource_metrics:
    - resource_id: string
    - total_requests: int
    - success_count: int
    - error_types: {type: count}
    - avg_latency_by_operation: {operation: latency_ms}
  - system_metrics:
    - daily_request_count: int
    - unique_entities_mapped: int
    - cache_effectiveness: float
```

## 3. Storage Strategy

### 3.1 Database Schema Extensions

#### 3.1.1 Enhanced EntityMapping Model

Extend the existing `EntityMapping` table in `mapping_cache.db`:

```sql
-- Keep existing fields and add:
ALTER TABLE entity_mapping ADD COLUMN entity_metadata JSON;
ALTER TABLE entity_mapping ADD COLUMN quality_metrics JSON;
ALTER TABLE entity_mapping ADD COLUMN rag_metadata JSON;
ALTER TABLE entity_mapping ADD COLUMN llm_metadata JSON;

-- Create indexes for common queries
CREATE INDEX idx_confidence_score ON entity_mapping(confidence_score);
CREATE INDEX idx_mapping_timestamp ON entity_mapping(created_at);
CREATE INDEX idx_source_type_confidence ON entity_mapping(source_type, confidence_score);
```

#### 3.1.2 New Tables in metamapper.db

```sql
-- Resource performance tracking
CREATE TABLE resource_performance (
    id INTEGER PRIMARY KEY,
    resource_id TEXT NOT NULL,
    metric_type TEXT NOT NULL,
    metric_value REAL,
    metric_metadata JSON,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (resource_id) REFERENCES resource(id)
);

-- Entity metadata cache
CREATE TABLE entity_metadata_cache (
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    metadata_type TEXT NOT NULL,
    metadata_value JSON,
    source_resource TEXT,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (entity_type, entity_id, metadata_type)
);

-- Mapping provenance details
CREATE TABLE mapping_provenance (
    mapping_id TEXT PRIMARY KEY,
    execution_id TEXT NOT NULL,
    full_provenance JSON NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 3.2 Metadata Storage Patterns

#### 3.2.1 Immediate Storage
Critical metadata stored immediately during mapping execution:
- Confidence scores
- Mapping path details
- Execution timestamps
- Basic quality metrics

#### 3.2.2 Deferred Enrichment
Resource-intensive metadata populated asynchronously:
- Detailed entity properties from APIs
- LLM-generated justifications
- Cross-reference validation results
- Statistical significance calculations

#### 3.2.3 Cached Aggregations
Frequently accessed aggregated metadata:
- Resource performance statistics
- Entity mapping success rates
- Common mapping patterns

## 4. Access and Integration

### 4.1 MappingExecutor Integration

Enhance `MappingExecutor` to:

```python
class EnhancedMappingExecutor:
    def __init__(self, metadata_manager: MetadataManager):
        self.metadata_manager = metadata_manager
        # ... existing initialization
    
    def execute_mapping(self, request: MappingRequest) -> MappingResult:
        # Existing mapping logic
        result = self._execute_path(path, request)
        
        # New: Capture and persist metadata
        metadata = self._extract_metadata(result, path, execution_context)
        self.metadata_manager.persist_mapping_metadata(metadata)
        
        # New: Enrich result with cached entity metadata
        enriched_result = self.metadata_manager.enrich_result(result)
        
        return enriched_result
```

### 4.2 Metadata Manager Component

New component for centralized metadata operations:

```python
class MetadataManager:
    """Manages all metadata operations across Biomapper"""
    
    def __init__(self, cache_db: Session, metamapper_db: Session):
        self.cache_db = cache_db
        self.metamapper_db = metamapper_db
        self.enrichment_queue = Queue()
    
    def persist_mapping_metadata(self, metadata: MappingMetadata):
        """Store mapping metadata with appropriate storage strategy"""
        
    def enrich_result(self, result: MappingResult) -> EnrichedMappingResult:
        """Add cached entity metadata to mapping result"""
        
    def get_resource_metrics(self, resource_id: str) -> ResourceMetrics:
        """Retrieve performance metrics for a resource"""
        
    def schedule_enrichment(self, entity_type: str, entity_id: str):
        """Queue entity for background metadata enrichment"""
```

### 4.3 API Layer Enhancements

Extend API models to expose metadata:

```python
class EnrichedMappingResult(BaseModel):
    # Existing fields
    source_id: str
    target_id: str
    confidence: float
    
    # New metadata fields
    metadata: Dict[str, Any] = Field(default_factory=dict)
    quality_metrics: QualityMetrics
    provenance: MappingProvenance
    alternatives: List[AlternativeMapping] = []
    
class QualityMetrics(BaseModel):
    confidence_score: float
    confidence_factors: Dict[str, float]
    validation_status: Optional[ValidationStatus]
    
class MappingProvenance(BaseModel):
    path_id: str
    path_name: str
    resources_used: List[str]
    execution_time_ms: float
```

## 5. RAG-Specific Metadata Integration

### 5.1 PubChemRAGMappingClient Metadata

The current client produces valuable metadata that should be captured:

```python
class RAGMetadataExtractor:
    def extract_from_rag_result(self, rag_result: Dict) -> RAGMetadata:
        return RAGMetadata(
            query_embedding=rag_result.get('query_embedding'),
            similarity_scores=rag_result.get('scores', []),
            embedding_model=self.embedding_model_name,
            vector_dimension=self.vector_dimension,
            search_parameters={
                'top_k': self.top_k,
                'score_threshold': self.score_threshold
            }
        )
```

### 5.2 Enhanced RAG Metadata (Future)

Following the advanced RAG planning design:

```python
class EnhancedRAGMetadata:
    # Enriched compound data from PubChem API
    compound_details: CompoundDetails
    
    # Statistical significance of similarity
    statistical_analysis: StatisticalAnalysis
    
    # LLM-generated insights
    llm_justification: LLMJustification
    
    # Alternative matches with scores
    alternatives: List[ScoredAlternative]
```

## 6. User-Facing Features

### 6.1 Transparency Features

- **Confidence Visualization**: Show confidence scores with breakdown by factors
- **Provenance Tracking**: Display complete mapping path with resources used
- **Alternative Suggestions**: Present top-k alternative mappings with scores

### 6.2 Reporting Capabilities

- **Mapping Quality Report**: Aggregate statistics on mapping success rates
- **Resource Performance Dashboard**: Visualize resource availability and performance
- **Audit Trail**: Complete history of mapping decisions with metadata

### 6.3 API Endpoints

New endpoints for metadata access:

```yaml
/api/v1/mappings/{mapping_id}/metadata:
  GET: Retrieve full metadata for a mapping
  
/api/v1/entities/{entity_type}/{entity_id}/metadata:
  GET: Retrieve cached entity metadata
  
/api/v1/resources/{resource_id}/metrics:
  GET: Retrieve resource performance metrics
  
/api/v1/mappings/explain:
  POST: Get detailed explanation for a mapping result
```

## 7. Implementation Roadmap

### Phase 1: Foundation (Weeks 1-2)
1. Implement database schema changes
2. Create `MetadataManager` component
3. Update `MappingExecutor` to capture basic metadata
4. Implement metadata persistence for existing fields

### Phase 2: RAG Integration (Weeks 3-4)
1. Extract and store RAG-specific metadata
2. Implement similarity score persistence
3. Add statistical significance calculations
4. Create metadata enrichment for PubChem compounds

### Phase 3: API Enhancement (Weeks 5-6)
1. Extend API models with metadata fields
2. Implement new metadata endpoints
3. Add metadata filtering and querying capabilities
4. Create basic visualization components

### Phase 4: Advanced Features (Weeks 7-8)
1. Implement LLM-based justification generation
2. Add background enrichment workers
3. Create performance monitoring dashboards
4. Implement metadata-based result ranking

### Phase 5: Optimization (Weeks 9-10)
1. Add caching layers for frequently accessed metadata
2. Optimize database queries with proper indexing
3. Implement metadata archival strategies
4. Performance tune the entire system

## 8. Scalability Considerations

### 8.1 Storage Management
- Implement metadata TTL policies
- Use JSON column compression where supported
- Archive old metadata to separate tables
- Implement selective metadata capture based on importance

### 8.2 Performance Optimization
- Cache frequently accessed metadata in Redis
- Use database connection pooling
- Implement batch operations for metadata writes
- Create materialized views for common aggregations

### 8.3 Maintenance Strategy
- Regular metadata quality audits
- Automated cleanup of orphaned metadata
- Performance metric monitoring and alerting
- Schema migration tools for metadata evolution

## 9. Security and Privacy

### 9.1 Access Control
- Role-based access to sensitive metadata
- Audit logging for metadata access
- Encryption for sensitive fields

### 9.2 Data Retention
- Configurable retention policies by metadata type
- GDPR-compliant data deletion capabilities
- Anonymization options for analytics

## 10. Future Enhancements

### 10.1 Machine Learning Integration
- Use metadata for training mapping quality predictors
- Implement adaptive path selection based on historical success
- Anomaly detection for mapping quality issues

### 10.2 Advanced Analytics
- Mapping pattern discovery
- Resource reliability scoring
- Entity relationship inference from mapping patterns

### 10.3 External Integrations
- Export metadata to data warehouses
- Integration with monitoring systems (Prometheus, Grafana)
- Webhook notifications for metadata events

## 11. Conclusion

The Resource Metadata System will transform Biomapper from a simple mapping tool to an intelligent, transparent, and auditable biological entity resolution platform. By capturing, storing, and leveraging rich metadata, the system will enable better decision-making, improved mapping quality, and enhanced user trust in the results.

The phased implementation approach ensures that value is delivered incrementally while building toward a comprehensive metadata management solution. Starting with the foundation of proper storage and basic capture, the system will evolve to include advanced features like LLM-based explanations and ML-driven optimizations.

This architecture provides the flexibility to adapt to new metadata sources and use cases while maintaining performance and scalability for production workloads.