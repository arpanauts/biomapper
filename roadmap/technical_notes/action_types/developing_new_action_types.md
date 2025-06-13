# Developing New Action Types: A Comprehensive Guide

## Overview

Action types are the building blocks of biomapper's mapping strategies. Each action type represents a specific operation that can be performed on identifiers during the mapping process. This guide provides a systematic approach to developing new action types.

## Architecture Overview

### Current Structure
```
biomapper/
├── core/
│   └── strategy_actions/
│       ├── __init__.py
│       ├── base.py                        # BaseStrategyAction abstract class
│       ├── convert_identifiers_local.py   # Example action implementation
│       ├── execute_mapping_path.py        # Example action implementation
│       └── filter_by_target_presence.py   # Example action implementation
tests/
└── unit/
    └── core/
        └── strategy_actions/
            ├── test_convert_identifiers_local.py
            ├── test_execute_mapping_path.py
            └── test_filter_by_target_presence.py
```

### Key Design Principles

1. **Modular Design** - Each action type is a separate module
2. **Minimal MappingExecutor Modification** - Only add action to dispatch logic
3. **Consistent Interface** - All actions inherit from `BaseStrategyAction`
4. **Comprehensive Testing** - Each action has dedicated unit tests
5. **Context Awareness** - Actions can read/write to shared context

## Step-by-Step Development Process

### Step 1: Plan the Action Type

Before coding, answer these questions:

1. **What problem does this action solve?**
   - Example: "Handle bidirectional matching with tracking"

2. **What are the inputs and outputs?**
   - Input: List of identifiers, ontology types, endpoints
   - Output: Matched identifiers, unmatched tracking, provenance

3. **What parameters will it need?**
   ```yaml
   parameters:
     match_mode: "many_to_many"  # or "one_to_one"
     track_unmatched: true
     composite_handling: "split_and_match"
   ```

4. **How does it handle edge cases?**
   - Empty inputs
   - Composite identifiers
   - Many-to-many relationships
   - Missing data

### Step 2: Create the Action Module

Create a new file in `/biomapper/core/strategy_actions/`:

```python
# bidirectional_match.py
"""Bidirectional matching with composite and M2M awareness."""

import logging
from typing import Dict, Any, List, Optional
from collections import defaultdict

from .base import BaseStrategyAction
from biomapper.db.models import Endpoint

logger = logging.getLogger(__name__)


class BidirectionalMatchAction(BaseStrategyAction):
    """
    Perform bidirectional matching between source and target endpoints.
    
    This action:
    - Handles composite identifiers by default
    - Supports many-to-many mappings
    - Tracks matched and unmatched identifiers
    - Provides detailed provenance
    """
    
    def __init__(self, session):
        """Initialize with database session."""
        self.session = session
        
    async def execute(
        self,
        current_identifiers: List[str],
        current_ontology_type: str,
        action_params: Dict[str, Any],
        source_endpoint: Endpoint,
        target_endpoint: Endpoint,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute bidirectional matching.
        
        Required parameters:
            - source_ontology: Ontology type in source endpoint
            - target_ontology: Ontology type in target endpoint
            - match_mode: "many_to_many" or "one_to_one"
            
        Optional parameters:
            - composite_handling: How to handle composite IDs
            - track_unmatched: Whether to save unmatched IDs
            - save_matched_to: Context key for matched IDs
            - save_unmatched_source_to: Context key for unmatched source
            - save_unmatched_target_to: Context key for unmatched target
        """
        # Validate required parameters
        source_ontology = action_params.get('source_ontology')
        target_ontology = action_params.get('target_ontology')
        match_mode = action_params.get('match_mode', 'many_to_many')
        
        if not source_ontology or not target_ontology:
            raise ValueError("source_ontology and target_ontology are required")
            
        # Extract optional parameters
        composite_handling = action_params.get('composite_handling', 'split_and_match')
        track_unmatched = action_params.get('track_unmatched', True)
        
        logger.info(
            f"Performing bidirectional match: {source_ontology} <-> {target_ontology}"
        )
        
        # Implementation details...
        # 1. Load data from both endpoints
        # 2. Handle composites if needed
        # 3. Perform matching based on mode
        # 4. Track results
        
        return {
            'input_identifiers': current_identifiers,
            'output_identifiers': matched_ids,
            'output_ontology_type': current_ontology_type,  # Unchanged
            'provenance': provenance_records,
            'details': {
                'action': 'BIDIRECTIONAL_MATCH',
                'match_mode': match_mode,
                'total_matched': len(matched_ids),
                'unmatched_source': len(unmatched_source),
                'unmatched_target': len(unmatched_target)
            }
        }
```

### Step 3: Register the Action

#### Update __init__.py
Add your action to `/biomapper/core/strategy_actions/__init__.py`:

```python
from .base import BaseStrategyAction
from .convert_identifiers_local import ConvertIdentifiersLocalAction
from .execute_mapping_path import ExecuteMappingPathAction
from .filter_by_target_presence import FilterByTargetPresenceAction
from .bidirectional_match import BidirectionalMatchAction  # NEW

__all__ = [
    "ConvertIdentifiersLocalAction",
    "ExecuteMappingPathAction", 
    "FilterByTargetPresenceAction",
    "BidirectionalMatchAction",  # NEW
]
```

#### Update MappingExecutor Dispatch Logic
Add your action to the dispatch logic in `/biomapper/core/mapping_executor.py`:

Find the section around line 3470:
```python
# Route to appropriate action handler
if action_type == "CONVERT_IDENTIFIERS_LOCAL":
    action = ConvertIdentifiersLocalAction(session)
elif action_type == "EXECUTE_MAPPING_PATH":
    action = ExecuteMappingPathAction(session)
elif action_type == "FILTER_IDENTIFIERS_BY_TARGET_PRESENCE":
    action = FilterByTargetPresenceAction(session)
elif action_type == "BIDIRECTIONAL_MATCH":  # NEW
    action = BidirectionalMatchAction(session)  # NEW
else:
    raise ConfigurationError(f"Unknown action type: {action_type}")
```

Note: This is the only modification needed to MappingExecutor. In the future, we may implement dynamic action loading to eliminate this step.

### Step 4: Create Comprehensive Tests

Create `/tests/unit/core/strategy_actions/test_bidirectional_match.py`:

```python
"""Tests for bidirectional match action."""

import pytest
from unittest.mock import Mock, AsyncMock
from biomapper.core.strategy_actions.bidirectional_match import BidirectionalMatchAction


class TestBidirectionalMatchAction:
    """Test cases for bidirectional matching."""
    
    @pytest.fixture
    def action(self, mock_session):
        """Create action instance with mocked session."""
        return BidirectionalMatchAction(session=mock_session)
        
    @pytest.fixture
    def basic_params(self):
        """Basic valid parameters."""
        return {
            'source_ontology': 'PROTEIN_UNIPROTKB_AC_ONTOLOGY',
            'target_ontology': 'PROTEIN_UNIPROTKB_AC_ONTOLOGY',
            'match_mode': 'many_to_many'
        }
        
    async def test_simple_matching(self, action, basic_params, mock_endpoints):
        """Test basic identifier matching."""
        # Arrange
        input_ids = ['P12345', 'Q67890']
        
        # Act
        result = await action.execute(
            current_identifiers=input_ids,
            current_ontology_type='PROTEIN_UNIPROTKB_AC_ONTOLOGY',
            action_params=basic_params,
            source_endpoint=mock_endpoints['source'],
            target_endpoint=mock_endpoints['target'],
            context={}
        )
        
        # Assert
        assert result['input_identifiers'] == input_ids
        assert len(result['output_identifiers']) > 0
        assert 'provenance' in result
        
    async def test_composite_handling(self, action, basic_params):
        """Test handling of composite identifiers."""
        # Test with composite IDs like 'P12345_Q67890'
        pass
        
    async def test_many_to_many_mapping(self, action, basic_params):
        """Test many-to-many relationship handling."""
        pass
        
    async def test_unmatched_tracking(self, action, basic_params):
        """Test that unmatched IDs are properly tracked."""
        pass
        
    async def test_missing_parameters(self, action):
        """Test error handling for missing required parameters."""
        with pytest.raises(ValueError, match="required"):
            await action.execute(
                current_identifiers=['P12345'],
                current_ontology_type='SOME_ONTOLOGY',
                action_params={},  # Missing required params
                source_endpoint=Mock(),
                target_endpoint=Mock(),
                context={}
            )
```

### Step 5: Integration Testing

Create integration tests that use the action in a real strategy:

```python
# tests/integration/test_bidirectional_strategy.py
async def test_ukbb_hpa_bidirectional_strategy(mapping_executor):
    """Test full bidirectional mapping strategy."""
    strategy = {
        'name': 'TEST_BIDIRECTIONAL',
        'steps': [{
            'step_id': 'S1',
            'action': {
                'type': 'BIDIRECTIONAL_MATCH',
                'source_ontology': 'PROTEIN_UNIPROTKB_AC_ONTOLOGY',
                'target_ontology': 'PROTEIN_UNIPROTKB_AC_ONTOLOGY',
                'match_mode': 'many_to_many'
            }
        }]
    }
    
    result = await mapping_executor.execute_strategy(
        strategy=strategy,
        input_identifiers=['P12345', 'Q67890']
    )
    
    assert result['success']
    assert len(result['mapped']) > 0
```

### Step 6: Documentation

1. **Add to ACTION_TYPES_REFERENCE.md**:
   ```markdown
   ## BIDIRECTIONAL_MATCH
   
   Performs intelligent bidirectional matching between endpoints.
   
   **Features:**
   - Composite identifier handling
   - Many-to-many relationship support
   - Unmatched tracking
   - Detailed provenance
   
   **Parameters:**
   - `source_ontology` (required): Ontology type in source
   - `target_ontology` (required): Ontology type in target
   - `match_mode`: "many_to_many" or "one_to_one"
   - `composite_handling`: How to handle composite IDs
   - `track_unmatched`: Whether to track unmatched IDs
   ```

2. **Update strategy examples** to show usage

### Step 7: Code Review Checklist

Before submitting:

- [ ] Action follows the `BaseStrategyAction` interface
- [ ] All parameters are validated
- [ ] Error handling is comprehensive
- [ ] Logging is informative but not excessive
- [ ] Tests cover happy path and edge cases
- [ ] Documentation is complete
- [ ] Code follows project style guidelines
- [ ] Performance is acceptable for large datasets

## Common Patterns

### Pattern 1: Context-Aware Actions

Actions can read from and write to the shared context:

```python
# Read from context
previous_unmatched = context.get('unmatched_ids', [])

# Write to context
if track_unmatched:
    context_key = action_params.get('save_unmatched_to', 'unmatched_ids')
    context[context_key] = unmatched_ids
```

### Pattern 2: Composite Identifier Handling

Standard approach for composites:

```python
def _expand_composites(self, identifiers: List[str], delimiter: str = '_') -> List[str]:
    """Expand composite identifiers into components."""
    expanded = []
    for id in identifiers:
        if delimiter in id:
            components = id.split(delimiter)
            expanded.extend(components)
        expanded.append(id)  # Keep original too
    return list(set(expanded))  # Remove duplicates
```

### Pattern 3: Many-to-Many Mapping

Use defaultdict for M2M relationships:

```python
from collections import defaultdict

# Build mapping
mapping = defaultdict(list)
for source_id, target_id in matches:
    mapping[source_id].append(target_id)
```

## Testing Strategy

### Unit Tests (Required)
- Test each action in isolation
- Mock database and endpoints
- Cover all parameter combinations
- Test error conditions

### Integration Tests (Recommended)
- Test action within a strategy
- Use test data files
- Verify end-to-end behavior
- Check performance with realistic data

### Property-Based Tests (Advanced)
```python
from hypothesis import given, strategies as st

@given(
    identifiers=st.lists(st.text(min_size=1), min_size=1),
    composite_prob=st.floats(0, 1)
)
def test_composite_handling_properties(identifiers, composite_prob):
    """Test that composite handling preserves certain properties."""
    # Property: Expansion never loses identifiers
    # Property: Original IDs always included
    pass
```

## Performance Considerations

1. **Lazy Loading** - Only load data columns you need
2. **Batch Processing** - Process identifiers in batches
3. **Caching** - Use context to cache expensive operations
4. **Early Exit** - Return early if no work to do

```python
# Example: Early exit
if not current_identifiers:
    return {
        'input_identifiers': [],
        'output_identifiers': [],
        'provenance': [],
        'details': {'action': 'BIDIRECTIONAL_MATCH', 'skipped': 'empty_input'}
    }
```

## Debugging Tips

1. **Comprehensive Logging**:
   ```python
   logger.debug(f"Processing {len(identifiers)} identifiers")
   logger.info(f"Matched {matched_count}/{total_count} identifiers")
   logger.warning(f"No matches found for {unmatched_count} identifiers")
   ```

2. **Detailed Provenance**:
   ```python
   provenance.append({
       'action': 'BIDIRECTIONAL_MATCH',
       'timestamp': datetime.utcnow().isoformat(),
       'input_id': source_id,
       'output_ids': target_ids,
       'confidence': confidence_score,
       'method': 'direct_match',
       'parameters': action_params
   })
   ```

3. **Test Data Files** - Create small test datasets that exhibit the behavior you're testing

## Common Pitfalls to Avoid

1. **Modifying Input Lists** - Always work with copies
2. **Assuming 1:1 Mappings** - Always handle M:M
3. **Ignoring Composites** - Check for delimiters
4. **Poor Error Messages** - Be specific about what's wrong
5. **Missing Provenance** - Track everything for debugging

## Next Steps

After developing your action:

1. **Peer Review** - Have someone review the code
2. **Performance Test** - Test with realistic data sizes
3. **Documentation** - Update all relevant docs
4. **Example Strategy** - Create an example using your action
5. **Migration Guide** - If replacing an existing pattern

Remember: Action types are the building blocks of biomapper. Make them robust, well-tested, and easy to understand!