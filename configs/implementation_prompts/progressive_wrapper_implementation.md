# Progressive Wrapper Implementation Prompt

## Objective
Create a generic progressive wrapper system that filters out already-matched proteins before each mapping action and manages stage-by-stage statistics.

## Current Context
- Working in `/home/ubuntu/biomapper/biomapper/core/strategy_actions/`
- Using 2025 standardization framework (parameter naming, context handling, etc.)
- Existing actions: `LOAD_DATASET_IDENTIFIERS`, `PARSE_COMPOSITE_IDENTIFIERS`, `PROTEIN_HISTORICAL_RESOLUTION`

## Requirements

### 1. Progressive Wrapper Class
Create `ProgressiveWrapper` that:
- Takes a list of unmatched identifiers
- Tracks which identifiers have been matched at each stage
- Only passes unmatched identifiers to subsequent actions
- Updates `progressive_stats` in execution context

### 2. Context Structure
Implement `progressive_stats` key in context:
```python
context["progressive_stats"] = {
    "stages": {
        1: {"name": "direct_match", "matched": 650, "unmatched": 350, "method": "Direct UniProt", "time": "0.5s"},
        2: {"name": "composite_expansion", "new_matches": 0, "cumulative_matched": 650, "method": "Composite parsing", "time": "0.2s"},
        3: {"name": "historical_resolution", "new_matches": 150, "cumulative_matched": 800, "method": "Historical API", "time": "12.3s"}
    },
    "total_processed": 1000,
    "final_match_rate": 0.80,
    "total_time": "13.0s"
}
```

### 3. API Design
```python
class ProgressiveWrapper:
    def __init__(self, stage_number: int, stage_name: str):
        self.stage_number = stage_number
        self.stage_name = stage_name
    
    async def execute_stage(self, action_instance, params, context):
        # Filter to unmatched only
        # Execute action
        # Update progressive_stats
        # Return results
```

### 4. Integration Points
- Must work with existing `TypedStrategyAction` pattern
- Should use `UniversalContext.wrap(context)` for 2025 standards
- Compatible with current YAML strategy format

### 5. Performance Requirements
- Efficient filtering (avoid O(n²) operations)
- Minimal memory overhead
- Fast set operations for matched/unmatched tracking

## Implementation Steps
1. Create `progressive_wrapper.py` in `utils/` directory
2. Design the wrapper class with proper typing
3. Implement efficient filtering logic
4. Add context statistics management
5. Create unit tests with sample data
6. Test integration with existing actions

## Success Criteria
- ✅ Filters unmatched identifiers efficiently
- ✅ Maintains accurate stage statistics
- ✅ Compatible with existing actions
- ✅ Performance improvement visible (no duplicate work)
- ✅ Clean integration with execution context

## Notes
- Follow 2025 standardization patterns throughout
- Use proper error handling and logging
- Consider memory efficiency for large datasets
- Design for extensibility (easy to add new stages)