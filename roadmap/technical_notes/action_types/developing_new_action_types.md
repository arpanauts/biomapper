# Developing New Action Types: A Comprehensive Guide

## Overview

Action types are the building blocks of biomapper's mapping strategies. Each action type represents a specific operation that can be performed on identifiers during the mapping process. This guide provides a systematic approach to developing new action types using the new decorator-based registry system.

## Architecture Overview

### Current Structure
```
biomapper/
├── core/
│   └── strategy_actions/
│       ├── __init__.py                    # Imports actions to trigger registration
│       ├── base.py                        # Defines the BaseStrategyAction abstract class
│       ├── registry.py                    # Defines the @register_action decorator and ACTION_REGISTRY
│       └── ...                            # Individual action implementations
└── services/
    └── mapping_service.py             # Service that uses the MappingExecutor

tests/
└── unit/
    └── core/
        └── strategy_actions/
            ├── test_...                     # Unit tests for each action
```


The `ActionLoader` component, responsible for discovering and loading these actions from the `biomapper.core.strategy_actions/` directory, is part of the core engine and resides in `biomapper.core.engine_components.action_loader`.

### Key Design Principles

1.  **Modular Design**: Each action type is a self-contained module.
2.  **Decorator-Based Registration**: Actions self-register using the `@register_action` decorator, eliminating the need for manual registration in a central file.
3.  **Zero `MappingExecutor` Modification**: Adding a new action **does not** require any changes to `MappingExecutor`.
4.  **Consistent Interface**: All standard actions inherit from `StrategyAction` and use a consistent `ActionContext` for passing data.
5.  **Comprehensive Testing**: Each action has dedicated unit tests.
6.  **Context Awareness**: Actions read from and write to the shared `ActionContext`.

## Step-by-Step Development Process

### Step 1: Plan the Action Type

Before coding, answer these questions:

1.  **What problem does this action solve?**
    - Example: "Handle bidirectional matching with tracking."
2.  **What are the inputs and outputs?**
    - Input: `ActionContext` containing identifiers, ontology types, endpoints, etc.
    - Output: An updated `ActionContext` with results and provenance.
3.  **What parameters will it need from the YAML strategy?**
    ```yaml
    parameters:
      match_mode: "many_to_many"
      track_unmatched: true
    ```
4.  **How does it handle edge cases?** (Empty inputs, composite identifiers, etc.)

### Step 2: Create the Action Module

Create a new file in `/biomapper/core/strategy_actions/`. The class must inherit from `BaseStrategyAction` and be decorated with `@register_action`.

```python
# /biomapper/core/strategy_actions/bidirectional_match.py
"""Bidirectional matching with composite and M2M awareness."""

import logging
from typing import Dict, Any, List

from biomapper.db.models import Endpoint
from .base import BaseStrategyAction
from .registry import register_action

logger = logging.getLogger(__name__)

@register_action("BIDIRECTIONAL_MATCH")
class BidirectionalMatchAction(BaseStrategyAction):
    """
    Perform bidirectional matching between source and target endpoints.
    """
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

        Required `action_params`:
            - `target_ontology`: The ontology type to match against in the target endpoint.
        """
        logger.info(f"Executing BIDIRECTIONAL_MATCH for {len(current_identifiers)} identifiers.")

        # 1. Validate and extract parameters
        target_ontology = action_params.get('target_ontology')
        if not target_ontology:
            raise ValueError("'target_ontology' is a required parameter for BIDIRECTIONAL_MATCH")

        # 2. Perform the action's logic...
        #    (e.g., query databases, call APIs, etc.)
        #    This is a placeholder for the actual matching logic.
        output_identifiers = current_identifiers  # Simulate a 1-to-1 mapping
        provenance = [
            {
                'action': 'BIDIRECTIONAL_MATCH',
                'input_id': in_id,
                'output_id': out_id,
                'comment': 'Placeholder match'
            }
            for in_id, out_id in zip(current_identifiers, output_identifiers)
        ]

        # 3. Return the results dictionary
        return {
            'input_identifiers': current_identifiers,
            'output_identifiers': output_identifiers,
            'output_ontology_type': target_ontology,  # The ontology type of the output
            'provenance': provenance,
            'details': {
                'action': 'BIDIRECTIONAL_MATCH',
                'total_matched': len(output_identifiers)
            }
        }
```

### Step 3: Register the Action via Import

Registration is now a simple, two-part process handled automatically:
1.  The `@register_action` decorator prepares the class for registration.
2.  Importing the class triggers the registration.

To ensure your new action is discovered when the application starts, add an import statement for it in `/biomapper/core/strategy_actions/__init__.py`. This is the **only** other file you need to modify.

```python
# /biomapper/core/strategy_actions/__init__.py

# ... other action imports
from .populate_context import PopulateContextAction
from .resolve_and_match_forward import ResolveAndMatchForwardAction
from .bidirectional_match import BidirectionalMatchAction  # NEW

# The __all__ list is good practice but not strictly required for the registry to work.
__all__ = [
    "PopulateContextAction",
    "ResolveAndMatchForwardAction",
    "BidirectionalMatchAction", # NEW
]
```

**That's it!** You no longer need to modify `MappingExecutor.py`. The old `if/elif` block has been replaced by a dynamic lookup in the `ACTION_REGISTRY`.

### Step 4: Create Comprehensive Tests

This step remains as crucial as ever. Create a corresponding test file in `/tests/unit/core/strategy_actions/`.

```python
# /tests/unit/core/strategy_actions/test_bidirectional_match.py
import pytest
from unittest.mock import Mock, MagicMock
from biomapper.core.strategy_actions.bidirectional_match import BidirectionalMatchAction

@pytest.fixture
def action():
    """Provides an instance of the BidirectionalMatchAction."""
    return BidirectionalMatchAction()

@pytest.mark.asyncio
async def test_simple_matching(action):
    # Arrange
    mock_source_endpoint = MagicMock()
    mock_target_endpoint = MagicMock()
    
    # Act
    result = await action.execute(
        current_identifiers=['P12345'],
        current_ontology_type='uniprot',
        action_params={'target_ontology': 'ensembl'},
        source_endpoint=mock_source_endpoint,
        target_endpoint=mock_target_endpoint,
        context={}
    )

    # Assert
    assert result['details'].get('action') == 'BIDIRECTIONAL_MATCH'
    assert result['output_ontology_type'] == 'ensembl'
    assert len(result['output_identifiers']) == 1
    assert len(result['provenance']) == 1

@pytest.mark.asyncio
async def test_missing_parameter_raises_error(action):
    # Arrange
    mock_source_endpoint = MagicMock()
    mock_target_endpoint = MagicMock()

    # Act & Assert
    with pytest.raises(ValueError, match="'target_ontology' is a required parameter"):
        await action.execute(
            current_identifiers=['P12345'],
            current_ontology_type='uniprot',
            action_params={},  # Missing target_ontology
            source_endpoint=mock_source_endpoint,
            target_endpoint=mock_target_endpoint,
            context={}
        )
```

### Step 5: Documentation

Update all relevant documentation with your new action's details.

1. **Add to `ACTION_TYPES_REFERENCE.md`** (or similar doc):
   ```markdown
   ## BIDIRECTIONAL_MATCH
   
   Performs intelligent bidirectional matching between endpoints.
   
   **Parameters:**
   - `source_ontology` (required): Ontology type in source
   - `target_ontology` (required): Ontology type in target
   - `match_mode`: "many_to_many" or "one_to_one"
   ```

2. **Update strategy examples** in `configs/` to show usage.

### Step 6: Code Review Checklist

Before submitting:

- [ ] Action inherits from `BaseStrategyAction` and uses `@register_action`.
- [ ] Action is imported in `strategy_actions/__init__.py`.
- [ ] All parameters from `action_params` are validated.
- [ ] Error handling is comprehensive.
- [ ] Logging is informative but not excessive.
- [ ] Tests cover happy path and edge cases.
- [ ] Documentation is complete.
- [ ] Code follows project style guidelines.
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
    logger.info("Skipping action due to empty input identifiers.")
    return {
        'input_identifiers': [],
        'output_identifiers': [],
        'output_ontology_type': current_ontology_type, # No change in type
        'provenance': [],
        'details': {'action': 'BIDIRECTIONAL_MATCH', 'status': 'skipped', 'reason': 'empty_input'}
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