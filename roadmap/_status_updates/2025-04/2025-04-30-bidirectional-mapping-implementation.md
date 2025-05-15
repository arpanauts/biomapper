# Bidirectional Mapping Implementation Status

## Overview

We have successfully implemented bidirectional mapping in the Biomapper framework, allowing for efficient mapping between UKBB and Arivale protein identifiers in both directions. This enhances the framework's flexibility and completeness, addressing a key requirement from the MVP roadmap.

## Key Accomplishments

1. **Bidirectional Path Finding**
   - Implemented `ReversiblePath` wrapper class to allow executing paths in reverse direction
   - Extended the `_find_mapping_paths` method to support bidirectional search
   - Added special handling for reversed path execution in `_execute_mapping_step`

2. **Metadata Enhancement**
   - Added critical metadata fields to `EntityMapping` model:
     - `confidence_score`: Float value indicating mapping reliability
     - `hop_count`: Number of steps in the mapping path
     - `mapping_direction`: String indicating "forward" or "reverse" direction
     - `mapping_path_details`: JSON field with detailed path information

3. **Confidence Scoring System**
   - Implemented a comprehensive confidence scoring algorithm in `_calculate_confidence_score`
   - Factors considered: hop count, path name, resource type, and mapping direction
   - Reverse mappings receive a slight confidence penalty to prioritize forward mappings

4. **CSV Output Enhancement**
   - Fixed the CSV output in `map_ukbb_to_arivale.py` to include all metadata
   - Removed filtering for forward mappings to include both directions
   - Enhanced the database query to retrieve appropriate metadata
   - Added logging to track directional mapping counts

5. **Database Migration and Updates**
   - Created a utility script `update_entity_mapping_metadata.py` to ensure all existing mappings have proper metadata
   - Added explicit testing for reverse mapping with `test_explicit_reverse_mapping.py`

## Current Status

The bidirectional mapping functionality is fully implemented and tested. The system now:

1. Attempts forward mappings first (UKBB → Arivale)
2. If no forward paths are found, attempts reverse mappings (Arivale → UKBB)
3. Stores appropriate metadata for all mappings
4. Outputs comprehensive CSV reports with full provenance information

This implementation addresses several key items from the MVP roadmap:
- Bidirectional Mapping Support: ✅ Completed
- Enhanced Metadata Tracking: ✅ Completed
- Confidence Scoring System: ✅ Completed
- EntityMapping Schema Enhancement: ✅ Completed
- Bidirectional Path Finding: ✅ Completed
- Comprehensive Reporting: ✅ Completed

## Technical Details

### 1. ReversiblePath Wrapper

The `ReversiblePath` wrapper class provides a clean, non-invasive way to execute paths in reverse direction without modifying the core `MappingPath` model. It overrides key properties to support path reversal:

```python
class ReversiblePath:
    """Wrapper to allow executing a path in reverse direction."""
    
    def __init__(self, original_path, is_reverse=False):
        self.original_path = original_path
        self.is_reverse = is_reverse
        
    @property
    def steps(self):
        if not self.is_reverse:
            return self.original_path.steps
        else:
            # Return steps in reverse order
            return sorted(self.original_path.steps, key=lambda s: -s.step_order)
```

### 2. Reverse Step Execution

Added specialized step execution logic to handle reversed paths:

```python
async def _execute_mapping_step(self, step, input_values, is_reverse=False):
    # ...
    if not is_reverse:
        # Normal forward execution
        return await client_instance.map_identifiers(input_values)
    else:
        # Reverse execution - try specialized reverse method first
        if hasattr(client_instance, "reverse_map_identifiers"):
            return await client_instance.reverse_map_identifiers(input_values)
            
        # Fall back to inverting the results of forward mapping
        # ...
```

### 3. Confidence Scoring

Implemented a nuanced confidence scoring system that considers multiple factors:

```python
def _calculate_confidence_score(self, path_log, processed_target_ids, path_details=None, is_reverse=False):
    # Base score starts at 0.7
    base_score = 0.7
    
    # Factor 1: Number of results - prefer single, definitive mappings
    # ...
    
    # Factor 2: Path length (hop count) - shorter paths are preferred
    # ...
    
    # Factor 3: Resource type - some resources are more trustworthy
    # ...
    
    # Factor 4: Direction - reverse mappings are slightly less preferred
    direction_score = -0.05 if is_reverse else 0.0
```

### 4. Database Schema Updates

Enhanced the EntityMapping model with new metadata fields:

```sql
-- Added to entity_mappings table
confidence_score FLOAT,
hop_count INTEGER,
mapping_direction TEXT,
mapping_path_details TEXT  -- JSON field
```

## Next Steps

While the bidirectional mapping functionality is now complete, the following items remain on the roadmap:

1. Move `PathLogMappingAssociation` to `cache_models.py` for better code organization
2. Implement alternative path strategy for improved mapping coverage
3. Add ID normalization support for handling outdated or merged identifiers
4. Create schema for alternative identifiers

## Conclusion

The implementation of bidirectional mapping represents a significant enhancement to the Biomapper framework, providing more comprehensive and robust mapping capabilities. The system can now efficiently map identifiers in both directions, with proper metadata and confidence scoring, addressing key requirements from the MVP roadmap.