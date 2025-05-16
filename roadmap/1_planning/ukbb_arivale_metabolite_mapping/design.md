# UKBB-Arivale Metabolite Mapping: Design Document

## Architecture Overview

This document details the architectural design and implementation approach for the UKBB-Arivale metabolite mapping feature. The design builds upon the existing protein mapping framework while introducing metabolite-specific enhancements and fallback mechanisms.

## Architectural Principles

1. **Entity-Agnostic Core**: Maintain a single iterative mapping strategy that works across entity types
2. **Specialized Clients**: Implement entity-specific mapping clients that conform to common interfaces
3. **Tiered Fallback Approach**: Organize fallback mechanisms in a priority hierarchy
4. **Consistent Output Structure**: Standardize output format while accommodating entity-specific metadata
5. **Unified Confidence Model**: Use a common confidence scoring framework with entity-specific weighting

## Component Design

### 1. Core System Components

#### 1.1 Script Adaptation

The existing three-phase approach will be preserved but adapted for metabolites:

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────────────┐
│  Phase 1:       │     │  Phase 2:       │     │  Phase 3:               │
│  Forward Mapping │────▶│  Reverse Mapping│────▶│  Bidirectional         │
│  (UKBB → Arivale)│     │  (Arivale → UKBB)│     │  Reconciliation        │
└─────────────────┘     └─────────────────┘     └─────────────────────────┘
```

Key modifications to the existing scripts:

- `map_ukbb_to_arivale.py`: 
  - Add support for metabolite column configurations
  - Integrate fallback mechanism invocation for unmapped entities
  - Enhance output to include fallback results and confidence scores

- `phase3_bidirectional_reconciliation.py`:
  - Extend reconciliation logic to handle metabolite-specific many-to-many relationships
  - Fix the existing `is_one_to_many_target` flag bug as part of this implementation
  - Add tiered output generation capabilities

#### 1.2 Configuration Structure

Configuration will be handled through a combination of:

- Script parameters for data paths and runtime options
- Environment variables for API credentials and service URLs
- Internal constants for entity-specific behaviors

```python
# New constants for metabolite mapping
METABOLITE_ID_COLUMN = "metabolite_id"
METABOLITE_NAME_COLUMN = "metabolite_name"
PUBCHEM_ID_COLUMN = "pubchem_cid"
CHEBI_ID_COLUMN = "chebi_id"
INCHI_KEY_COLUMN = "inchi_key"
SMILES_COLUMN = "smiles"

# Fallback mechanism configuration
ENABLE_NAME_RESOLVER = True
ENABLE_UMLS_MAPPING = True
ENABLE_RAG_MAPPING = True
CONFIDENCE_THRESHOLD = 0.7  # Minimum confidence to include in primary output
```

### 2. Mapping Client Implementations

#### 2.1 `UniChemClient`

Handles mapping between standardized chemical identifiers:

```python
class UniChemClient(MappingClient):
    """Client for mapping between chemical identifiers using UniChem API."""
    
    def __init__(self, source_db=None, target_db=None):
        self.source_db = source_db  # e.g., "PUBCHEM", "CHEBI"
        self.target_db = target_db
        self.base_url = "https://www.ebi.ac.uk/unichem/rest/src_compound_id"
        
    async def map_identifiers(self, identifiers, **kwargs):
        """Map chemical identifiers from source to target database."""
        # Implementation details
        
    async def reverse_map_identifiers(self, identifiers, **kwargs):
        """Reverse mapping implementation."""
        # Implementation details
```

#### 2.2 `TranslatorNameResolverClient`

Resolves entity names to standardized identifiers:

```python
class TranslatorNameResolverClient(MappingClient):
    """Client for resolving entity names using Translator Name Resolution API."""
    
    def __init__(self):
        self.base_url = "https://name-resolution-sri.renci.org/lookup"
        
    async def map_identifiers(self, names, **kwargs):
        """Map entity names to standardized identifiers."""
        # Implementation details including:
        # - Batched API calls with retries
        # - Result filtering for metabolites
        # - Confidence scoring based on match quality
        
    async def reverse_map_identifiers(self, identifiers, **kwargs):
        """Not directly supported for name resolution."""
        # Implementation approach
```

#### 2.3 `UMLSClient`

Maps concepts through UMLS:

```python
class UMLSClient(MappingClient):
    """Client for concept mapping via UMLS."""
    
    def __init__(self, api_key=None):
        self.api_key = api_key or os.environ.get("UMLS_API_KEY")
        self.base_url = "https://uts-ws.nlm.nih.gov/rest"
        self.tgt = None  # Ticket granting ticket
        
    async def _get_auth_token(self):
        """Get authentication token for UMLS API."""
        # Implementation details
        
    async def map_identifiers(self, terms, **kwargs):
        """Map terms to UMLS concepts and related identifiers."""
        # Implementation details
        
    async def reverse_map_identifiers(self, identifiers, **kwargs):
        """Map from identifiers to UMLS concepts and related terms."""
        # Implementation details
```

#### 2.4 `RAGMappingClient`

Implements vector similarity search for mapping entities:

```python
class RAGMappingClient(MappingClient):
    """Client for RAG-based mapping using vector similarity."""
    
    def __init__(self, vector_db_path=None, model_name="BAAI/bge-small-en-v1.5"):
        self.vector_db_path = vector_db_path
        self.model_name = model_name
        self.embedding_model = None
        self.vector_db = None
        
    async def _initialize(self):
        """Initialize embedding model and vector database."""
        # Implementation details
        
    async def map_identifiers(self, query_entities, **kwargs):
        """Find similar entities using vector similarity."""
        # Implementation details including:
        # - Query embedding generation
        # - Vector similarity search
        # - Result filtering and ranking
        # - Confidence scoring based on similarity
        
    async def reverse_map_identifiers(self, identifiers, **kwargs):
        """Reverse mapping implementation."""
        # Implementation details
```

### 3. Fallback Orchestration

A `FallbackOrchestrator` class will coordinate the application of fallback mechanisms:

```python
class FallbackOrchestrator:
    """Orchestrates multiple fallback mechanisms for entity mapping."""
    
    def __init__(self, entity_type="metabolite"):
        self.entity_type = entity_type
        self.clients = []
        self.initialize_clients()
        
    def initialize_clients(self):
        """Initialize appropriate clients based on entity type."""
        if self.entity_type == "metabolite":
            if ENABLE_NAME_RESOLVER:
                self.clients.append(TranslatorNameResolverClient())
            if ENABLE_UMLS_MAPPING:
                self.clients.append(UMLSClient())
            if ENABLE_RAG_MAPPING:
                self.clients.append(RAGMappingClient())
                
    async def apply_fallbacks(self, unmapped_entities, target_ontology_type):
        """Apply fallback mechanisms in sequence for unmapped entities."""
        results = {}
        remaining_entities = set(unmapped_entities)
        
        for client in self.clients:
            if not remaining_entities:
                break
                
            client_results = await client.map_identifiers(
                list(remaining_entities),
                target_ontology_type=target_ontology_type
            )
            
            # Process results and update remaining_entities
            # Add client-specific provenance to results
            
        return results
```

### 4. Confidence Scoring System

The confidence scoring system will be implemented as an enhancement to the existing `_cache_results` method in `MappingExecutor`:

```python
def _calculate_confidence_score(self, mapping_result, fallback_source=None):
    """Calculate confidence score for a mapping result."""
    base_score = 0.0
    
    # Factor 1: Mapping method
    if fallback_source is None:
        # Primary mapping via MappingExecutor
        base_score = 0.8
    elif fallback_source == "TranslatorNameResolver":
        base_score = 0.6
    elif fallback_source == "UMLS":
        base_score = 0.5
    elif fallback_source == "RAG":
        base_score = 0.4
    
    # Factor 2: Path length/hop count
    hop_count = mapping_result.get("hop_count", 1)
    hop_penalty = 0.1 * (hop_count - 1)
    
    # Factor 3: Bidirectional validation
    validation_bonus = 0.2 if mapping_result.get("validation_status") == "Validated" else 0.0
    
    # Factor 4: String similarity (for name-based mappings)
    similarity_score = mapping_result.get("similarity_score", 1.0)
    
    # Combine factors (capped at 1.0)
    final_score = min(1.0, max(0.0, base_score - hop_penalty + validation_bonus * similarity_score))
    
    return final_score
```

### 5. Output Format Design

#### 5.1 Enhanced TSV Structure

The output TSV files will maintain the current structure with additional columns:

```
source_id,source_name,target_id,target_name,mapping_status,is_canonical_mapping,is_one_to_many_source,is_one_to_many_target,confidence_score,mapping_method,fallback_source,similarity_score
```

New columns:
- `confidence_score`: Float between 0-1 indicating mapping confidence
- `mapping_method`: String indicating "primary" or "fallback"
- `fallback_source`: String indicating the specific fallback mechanism (if applicable)
- `similarity_score`: Float indicating similarity score (for name/RAG-based mappings)

#### 5.2 Tiered Output Approach

Generate multiple output files for different quality tiers:

1. `primary_mappings.tsv`: High-confidence mappings (confidence ≥ 0.7)
2. `fallback_mappings.tsv`: Lower-confidence mappings (confidence < 0.7)
3. `all_mappings.tsv`: Combined results with clear provenance

#### 5.3 JSON Metadata

Enhanced JSON metadata file to include:

```json
{
  "mapping_session": {
    "timestamp": "2025-05-16T18:30:00Z",
    "source_endpoint": "ukbb_metabolite",
    "target_endpoint": "arivale_metabolite",
    "source_file": "/path/to/ukbb_metabolites.tsv",
    "target_file": "/path/to/arivale_metabolites.tsv"
  },
  "summary_statistics": {
    "total_source_entities": 1000,
    "mapped_entities": 450,
    "mapping_success_rate": 0.45,
    "primary_mappings": 350,
    "fallback_mappings": 100,
    "mapping_method_distribution": {
      "iterative_mapping": 350,
      "name_resolver": 60,
      "umls": 20,
      "rag": 20
    },
    "confidence_distribution": {
      "0.9-1.0": 200,
      "0.8-0.9": 150,
      "0.7-0.8": 50,
      "0.6-0.7": 30,
      "0.5-0.6": 15,
      "0.0-0.5": 5
    }
  }
}
```

### 6. Integration with Existing Pipeline

#### 6.1 Script Modification Approach

The `map_ukbb_to_arivale.py` script will be enhanced but maintain its current structure:

1. Detect entity type based on input file or explicit parameter
2. Load appropriate configuration based on entity type
3. Execute the existing mapping logic with entity-specific clients
4. For unmapped entities, invoke the `FallbackOrchestrator`
5. Combine and format results with confidence scoring
6. Generate appropriate output files

#### 6.2 Phase 3 Reconciliation Integration

The `phase3_bidirectional_reconciliation.py` script will be enhanced to:

1. Support the additional metadata columns for fallback mechanisms
2. Fix the `is_one_to_many_target` flag bug
3. Apply confidence-based filtering during reconciliation
4. Generate tiered output based on confidence thresholds

## Implementation Plan

### Phase 1: Core Infrastructure

1. Fix the `is_one_to_many_target` flag bug in `phase3_bidirectional_reconciliation.py`
2. Implement the confidence scoring system
3. Enhance output format to support tiered results
4. Create unit tests for these components

### Phase 2: Client Development

1. Implement `UniChemClient` for primary metabolite mapping
2. Implement `TranslatorNameResolverClient` for name resolution
3. Implement `UMLSClient` for concept mapping
4. Implement `RAGMappingClient` for similarity search
5. Create unit tests for each client

### Phase 3: Fallback Orchestration

1. Implement the `FallbackOrchestrator` class
2. Create integration tests for fallback orchestration
3. Integrate fallback results with the primary mapping pipeline

### Phase 4: Script Adaptation

1. Enhance `map_ukbb_to_arivale.py` for metabolite mapping
2. Update `phase3_bidirectional_reconciliation.py` for enhanced metadata
3. Create end-to-end tests for metabolite mapping

### Phase 5: Testing and Optimization

1. Benchmark performance with realistic metabolite datasets
2. Optimize bottlenecks identified during testing
3. Validate mapping quality through manual verification of samples

## Design Considerations and Tradeoffs

### Consideration 1: Script Adaptation vs. Complete Rewrite

**Decision**: Adapt existing scripts rather than creating entirely new ones for metabolites.

**Rationale**:
- Maintains consistency with the established workflow
- Reduces duplication and maintenance burden
- Enforces the entity-agnostic design principle

**Tradeoff**:
- May require more complex conditional logic within shared scripts
- Greater risk of regressions in existing functionality

### Consideration 2: Fallback Mechanism Integration

**Decision**: Implement fallback mechanisms as separate clients with a coordinating orchestrator.

**Rationale**:
- Provides clear separation of concerns
- Allows for flexible prioritization and combination of approaches
- Easier to test individual components

**Tradeoff**:
- Requires additional abstraction layer
- May have slight performance overhead

### Consideration 3: Confidence Scoring Approach

**Decision**: Implement a multi-factor weighted scoring system.

**Rationale**:
- Captures nuances of different mapping approaches
- Allows for entity-type-specific weightings
- Provides clear quality signals for downstream consumers

**Tradeoff**:
- Requires calibration and validation
- More complex than simple binary quality indicators

### Consideration 4: Output Format Structure

**Decision**: Enhance existing output format with additional columns and tiered files.

**Rationale**:
- Maintains backward compatibility
- Provides clear provenance for different mapping sources
- Supports filtering by confidence level

**Tradeoff**:
- More complex output structure
- Increased storage requirements for multiple output files

## Technical Debt and Future Enhancements

1. **Integration with `metamapper.db`**:
   - The current design defers full integration with `metamapper.db`
   - Future work should formalize the metabolite ontology types and paths

2. **Advanced Confidence Model**:
   - The current scoring approach could be enhanced with machine learning
   - A training set of verified mappings would enable supervised learning

3. **Expanded Entity Support**:
   - The framework should eventually be extended to additional entity types
   - This will require further abstraction of entity-specific configurations

4. **Performance Optimization**:
   - Large-scale testing may reveal bottlenecks requiring optimization
   - Particularly around vector similarity search and API interactions

5. **Enhanced Visualization**:
   - Develop visualization tools for mapping results and confidence distribution
   - Would aid in quality assessment and parameter tuning

## Conclusion

This design provides a structured approach to extending Biomapper's capabilities to metabolite mapping while maintaining consistency with the existing protein mapping framework. By leveraging the common iterative mapping strategy and adding specialized fallback mechanisms, we can address the unique challenges of metabolite identifiers while building toward a truly entity-agnostic mapping system.
