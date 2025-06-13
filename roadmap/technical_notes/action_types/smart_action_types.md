# Smart Action Types: A Technical Concept Report and Roadmap

## Executive Summary

This document proposes an evolution of biomapper's action type system from atomic, single-purpose actions to "smart actions" that can handle the complex realities of bioinformatics data. Smart actions would provide conditional logic, composite identifier handling, and many-to-many mapping awareness while maintaining backward compatibility with existing configurations.

**Key Finding**: While smart actions represent the ideal architecture, the implementation complexity and risk to existing pipelines suggest a phased approach starting with enhanced atomic actions is more pragmatic.

## 1. Current State Analysis

### 1.1 Existing Architecture

The current biomapper system uses atomic action types:
- `CONVERT_IDENTIFIERS_LOCAL` - Local data conversion within an endpoint
- `EXECUTE_MAPPING_PATH` - Run a predefined mapping sequence
- `FILTER_IDENTIFIERS_BY_TARGET_PRESENCE` - Filter by target dataset presence
- `MATCH_SHARED_ONTOLOGY` - Direct ontology matching

Each action:
- Maps to a specific class in `/biomapper/core/strategy_actions/`
- Receives parameters from YAML configurations stored in `metamapper.db`
- Executes a single, well-defined operation
- Returns structured results with provenance

### 1.2 Current Database Schema

```sql
-- Simplified view of current schema
CREATE TABLE mapping_strategies (
    id INTEGER PRIMARY KEY,
    name VARCHAR NOT NULL,
    entity_type VARCHAR,
    description TEXT,
    default_source_ontology_type VARCHAR,
    default_target_ontology_type VARCHAR
);

CREATE TABLE mapping_strategy_steps (
    id INTEGER PRIMARY KEY,
    mapping_strategy_id INTEGER REFERENCES mapping_strategies(id),
    step_id VARCHAR NOT NULL,
    step_order INTEGER NOT NULL,
    description TEXT,
    action_type VARCHAR NOT NULL,  -- Simple string like 'CONVERT_IDENTIFIERS_LOCAL'
    action_parameters JSON          -- Basic parameters as JSON
);
```

### 1.3 Limitations of Current Approach

1. **No Composite Identifier Handling** - Q14213_Q8NEV9 treated as opaque string
2. **Limited Many-to-Many Support** - Handled but not optimized
3. **No Conditional Logic** - Cannot branch based on data characteristics
4. **Redundant Processing** - Cannot intelligently skip already-matched identifiers
5. **Fixed Behavior** - Actions cannot adapt based on parameters

## 2. Smart Actions Concept

### 2.1 Definition

Smart actions are higher-level operations that:
- Encapsulate multiple atomic operations
- Make decisions based on data characteristics
- Handle bioinformatics-specific patterns (composites, M2M)
- Optimize processing through intelligent routing
- Maintain detailed provenance of all decisions

### 2.2 Example Smart Actions

#### SMART_DIRECT_MATCH
```yaml
action:
  type: "SMART_DIRECT_MATCH"
  parameters:
    # Composite handling
    composite_handling: "split_and_match"  # or "match_whole", "both"
    composite_delimiter: "_"
    
    # Matching behavior
    match_mode: "many_to_many"  # or "one_to_one", "first_only"
    match_direction: "bidirectional"  # or "forward", "reverse"
    
    # Post-processing
    post_match: "remove_exact"  # or "tag_only", "keep_all"
    track_unmatched: true
    
    # Optimization hints
    use_index: true
    batch_size: 1000
```

#### PROCESS_UNMATCHED
```yaml
action:
  type: "PROCESS_UNMATCHED"
  parameters:
    # Resolution strategy
    strategy: "uniprot_api"  # or "fuzzy_match", "synonym_lookup"
    
    # Handling options
    include_previously_matched: false
    max_attempts: 3
    fallback_strategy: "keep_original"
    
    # API-specific settings
    api_batch_size: 100
    rate_limit: 5  # requests per second
```

#### INTELLIGENT_FILTER
```yaml
action:
  type: "INTELLIGENT_FILTER"
  parameters:
    # Filter criteria
    filter_by: "target_presence"
    
    # Composite awareness
    composite_mode: "any_component"  # or "all_components", "whole_only"
    
    # Performance optimization
    pre_filter_exact_matches: true
    use_bloom_filter: true
    
    # Tracking
    save_filtered_out: true
    filtered_out_path: "context.filtered_identifiers"
```

### 2.3 Benefits

1. **Reduced Strategy Complexity** - Fewer steps needed in YAML
2. **Better Performance** - Intelligent routing and caching
3. **Improved Maintainability** - Business logic in code, not YAML
4. **Enhanced Debugging** - Detailed decision tracking
5. **Future-Proof** - Easy to add new behaviors via parameters

## 3. Required Changes

### 3.1 Database Schema Evolution

#### Option A: Minimal Changes (Recommended for Phase 1)
```sql
-- Add version to strategy for compatibility detection
ALTER TABLE mapping_strategies ADD COLUMN strategy_version VARCHAR DEFAULT '1.0';

-- Add schema validation for parameters
ALTER TABLE mapping_strategy_steps ADD COLUMN parameter_schema JSON;

-- Add execution metadata
ALTER TABLE mapping_strategy_steps ADD COLUMN execution_hints JSON;
```

#### Option B: Full Smart Action Support (Future)
```sql
-- New table for smart action definitions
CREATE TABLE smart_action_types (
    id INTEGER PRIMARY KEY,
    name VARCHAR NOT NULL UNIQUE,
    version VARCHAR NOT NULL,
    parameter_schema JSON NOT NULL,
    description TEXT,
    category VARCHAR,  -- 'matching', 'filtering', 'resolution', etc.
    is_composite BOOLEAN DEFAULT FALSE  -- Can contain other actions
);

-- Enhanced step definition
CREATE TABLE mapping_strategy_steps_v2 (
    id INTEGER PRIMARY KEY,
    mapping_strategy_id INTEGER REFERENCES mapping_strategies(id),
    step_id VARCHAR NOT NULL,
    step_order INTEGER NOT NULL,
    description TEXT,
    action_type_id INTEGER REFERENCES smart_action_types(id),
    action_parameters JSON,
    conditional_logic JSON,  -- When to execute this step
    error_handling JSON,     -- What to do on failure
    performance_hints JSON   -- Caching, batching, etc.
);

-- Execution tracking
CREATE TABLE smart_action_executions (
    id INTEGER PRIMARY KEY,
    strategy_execution_id INTEGER,
    step_id VARCHAR,
    action_type VARCHAR,
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    input_count INTEGER,
    output_count INTEGER,
    decisions_made JSON,  -- Tracking conditional logic
    performance_metrics JSON
);
```

### 3.2 YAML Configuration Changes

#### Current Format
```yaml
steps:
  - step_id: "S1_CONVERT"
    action:
      type: "CONVERT_IDENTIFIERS_LOCAL"
      endpoint_context: "SOURCE"
      output_ontology_type: "PROTEIN_UNIPROTKB_AC_ONTOLOGY"
```

#### Smart Action Format
```yaml
version: "2.0"  # Strategy version for compatibility
steps:
  - step_id: "S1_SMART_MATCH"
    action:
      type: "SMART_DIRECT_MATCH"
      version: "1.0"  # Action version
      parameters:
        # Required parameters with schema validation
        source_ontology: "${source.primary_ontology}"
        target_ontology: "PROTEIN_UNIPROTKB_AC_ONTOLOGY"
        
        # Composite handling
        composite:
          enabled: true
          delimiter: "_"
          strategy: "split_and_match"
        
        # Matching configuration
        matching:
          mode: "many_to_many"
          direction: "bidirectional"
          exact_match_first: true
        
        # Post-processing
        post_process:
          remove_matched: true
          save_unmatched_to: "context.unmatched_ids"
          
      # Conditional execution (future)
      conditions:
        - execute_if: "context.total_identifiers > 1000"
        - skip_if: "context.previous_step.match_rate > 0.95"
        
      # Error handling
      on_error:
        strategy: "continue"  # or "abort", "retry"
        fallback_action: "CONVERT_IDENTIFIERS_LOCAL"
```

### 3.3 MappingExecutor Architecture Changes

#### Current Architecture
```python
# Simple dispatch in MappingExecutor
if action_type == "CONVERT_IDENTIFIERS_LOCAL":
    action = ConvertIdentifiersLocalAction(session)
    result = await action.execute(...)
```

#### Smart Action Architecture
```python
# Enhanced MappingExecutor with smart action support
class MappingExecutor:
    def __init__(self):
        self.action_registry = SmartActionRegistry()
        self.execution_context = ExecutionContext()
        
    async def execute_smart_action(
        self,
        action_type: str,
        action_params: Dict[str, Any],
        context: ExecutionContext
    ) -> ActionResult:
        # Get action class with version support
        action_class = self.action_registry.get_action(
            action_type, 
            version=action_params.get('version', 'latest')
        )
        
        # Validate parameters against schema
        validated_params = action_class.validate_parameters(action_params)
        
        # Create action instance with context injection
        action = action_class(
            session=self.session,
            context=context,
            metrics_collector=self.metrics
        )
        
        # Execute with comprehensive error handling
        try:
            result = await action.execute(
                identifiers=context.current_identifiers,
                parameters=validated_params
            )
            
            # Update context for next steps
            context.update_from_result(result)
            
            return result
            
        except ActionExecutionError as e:
            return await self._handle_action_error(e, action_params)
```

#### Smart Action Base Class
```python
class SmartActionBase(ABC):
    """Base class for all smart actions."""
    
    # Class-level configuration
    parameter_schema = {}  # JSON Schema for validation
    supports_composite = True
    supports_many_to_many = True
    
    def __init__(self, session, context, metrics_collector):
        self.session = session
        self.context = context
        self.metrics = metrics_collector
        
    @classmethod
    def validate_parameters(cls, params: Dict) -> Dict:
        """Validate parameters against schema."""
        # Use jsonschema or similar
        validate(params, cls.parameter_schema)
        return params
        
    @abstractmethod
    async def execute(
        self, 
        identifiers: List[str], 
        parameters: Dict[str, Any]
    ) -> ActionResult:
        """Execute the smart action."""
        pass
        
    # Helper methods for common patterns
    async def _handle_composites(
        self, 
        identifiers: List[str], 
        strategy: str
    ) -> List[str]:
        """Common composite handling logic."""
        if strategy == "split_and_match":
            return self._split_composite_identifiers(identifiers)
        # ... other strategies
        
    async def _perform_matching(
        self,
        source_ids: List[str],
        target_endpoint: Endpoint,
        mode: str
    ) -> Dict[str, List[str]]:
        """Common matching logic with different modes."""
        # Implementation based on mode
        pass
```

## 4. Implementation Roadmap

### Phase 1: Enhanced Atomic Actions (Months 1-2)
**Goal**: Add smart parameters to existing actions without breaking changes

1. **Week 1-2**: Design parameter schemas for existing actions
2. **Week 3-4**: Implement parameter validation in action classes
3. **Week 5-6**: Add composite identifier handling to CONVERT_IDENTIFIERS_LOCAL
4. **Week 7-8**: Testing and documentation

**Deliverables**:
- Enhanced action classes with optional smart parameters
- Documentation on new parameter options
- Test suite covering new behaviors

### Phase 2: Smart Action Prototypes (Months 3-4)
**Goal**: Implement 2-3 smart actions alongside atomic actions

1. **Week 1-2**: Implement SMART_DIRECT_MATCH action
2. **Week 3-4**: Implement PROCESS_UNMATCHED action
3. **Week 5-6**: Create migration tools for existing strategies
4. **Week 7-8**: Performance testing and optimization

**Deliverables**:
- Working smart action implementations
- Migration guide and tools
- Performance benchmarks

### Phase 3: Full Integration (Months 5-6)
**Goal**: Complete smart action system with full backward compatibility

1. **Week 1-2**: Database schema migration
2. **Week 3-4**: Update populate_metamapper_db.py for new schemas
3. **Week 5-6**: Implement conditional logic and error handling
4. **Week 7-8**: Production rollout with feature flags

**Deliverables**:
- Complete smart action system
- Migrated production strategies
- Monitoring and metrics dashboard

## 5. Risk Assessment and Mitigation

### 5.1 Technical Risks

**Risk**: Breaking existing pipelines
- **Mitigation**: Strict backward compatibility, extensive testing, feature flags

**Risk**: Performance degradation from added complexity
- **Mitigation**: Profiling, caching, optional smart features

**Risk**: Increased debugging difficulty
- **Mitigation**: Comprehensive logging, execution tracking, debugging tools

### 5.2 Operational Risks

**Risk**: User confusion with new configuration options
- **Mitigation**: Clear documentation, migration tools, examples

**Risk**: Database migration failures
- **Mitigation**: Reversible migrations, backups, staged rollout

## 6. Alternative Approach: Incremental Enhancement

Given the complexity, an alternative approach is to incrementally enhance atomic actions:

1. **Add optional parameters** to existing actions (no schema changes)
2. **Create composite actions** that chain atomic actions (no new action types)
3. **Use context passing** for state between actions
4. **Defer database changes** until patterns are proven

This approach:
- Minimizes risk
- Allows learning from usage patterns
- Provides value immediately
- Delays major architectural changes

## 7. Recommendation

**Short term (Next 3 months)**: 
- Proceed with incremental enhancement of atomic actions
- Add composite handling and M2M awareness as optional parameters
- Gather metrics on usage patterns

**Medium term (3-6 months)**:
- Design smart actions based on learned patterns
- Prototype with select use cases
- Plan database migration strategy

**Long term (6-12 months)**:
- Implement full smart action system if justified by usage
- Migrate existing strategies gradually
- Deprecate redundant atomic actions

## 8. Conclusion

Smart actions represent a significant evolution in biomapper's capability to handle complex bioinformatics data. However, the implementation complexity and risk to existing systems suggest a measured approach. By starting with enhanced atomic actions and gradually introducing smart capabilities, we can deliver value while learning what features are truly needed.

The key insight is that bioinformatics data complexity (composites, M2M, deprecated IDs) is not going away - our system must evolve to handle it elegantly. Smart actions provide a path forward that balances power with maintainability.

## Appendix A: Example Smart Action Implementation

```python
class SmartDirectMatchAction(SmartActionBase):
    """Intelligent direct matching with composite and M2M awareness."""
    
    parameter_schema = {
        "type": "object",
        "properties": {
            "composite_handling": {
                "type": "string",
                "enum": ["split_and_match", "match_whole", "both"]
            },
            "match_mode": {
                "type": "string", 
                "enum": ["many_to_many", "one_to_one", "first_only"]
            },
            "post_match": {
                "type": "string",
                "enum": ["remove_exact", "tag_only", "keep_all"]
            }
        },
        "required": ["match_mode"]
    }
    
    async def execute(
        self, 
        identifiers: List[str], 
        parameters: Dict[str, Any]
    ) -> ActionResult:
        # Step 1: Handle composites if configured
        processed_ids = identifiers
        if parameters.get('composite_handling') == 'split_and_match':
            processed_ids = await self._handle_composites(
                identifiers, 
                'split_and_match'
            )
            
        # Step 2: Perform matching based on mode
        matches = await self._perform_matching(
            processed_ids,
            self.context.target_endpoint,
            parameters['match_mode']
        )
        
        # Step 3: Post-process based on configuration
        if parameters.get('post_match') == 'remove_exact':
            remaining = self._remove_exact_matches(identifiers, matches)
            self.context.unmatched_identifiers = remaining
            
        # Build comprehensive result
        return ActionResult(
            input_count=len(identifiers),
            output_count=len(matches),
            matched_identifiers=matches,
            unmatched_identifiers=remaining,
            provenance=self._build_provenance(identifiers, matches),
            metrics={
                'composite_ids_processed': len(processed_ids) - len(identifiers),
                'match_rate': len(matches) / len(identifiers) if identifiers else 0
            }
        )
```

## Appendix B: Migration Example

Current atomic strategy:
```yaml
steps:
  - step_id: "S1"
    action:
      type: "CONVERT_IDENTIFIERS_LOCAL"
      endpoint_context: "SOURCE"
      output_ontology_type: "PROTEIN_UNIPROTKB_AC_ONTOLOGY"
  - step_id: "S2"
    action:
      type: "FILTER_IDENTIFIERS_BY_TARGET_PRESENCE"
      endpoint_context: "TARGET"
      ontology_type_to_match: "PROTEIN_UNIPROTKB_AC_ONTOLOGY"
```

Migrated to smart actions:
```yaml
version: "2.0"
steps:
  - step_id: "S1_SMART"
    action:
      type: "SMART_DIRECT_MATCH"
      parameters:
        source_ontology: "UKBB_PROTEIN_ASSAY_ID_ONTOLOGY"
        target_ontology: "PROTEIN_UNIPROTKB_AC_ONTOLOGY"
        composite_handling: "split_and_match"
        match_mode: "many_to_many"
        post_match: "remove_exact"
        auto_filter: true  # Combines conversion and filtering
```

This reduces 2 steps to 1 while handling more edge cases.