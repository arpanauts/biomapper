# Developing New Action Types: A Comprehensive Guide

## Overview

Action types are the building blocks of biomapper's mapping strategies. Each action represents a specific, self-contained operation in a pipeline. This guide provides a systematic approach to developing new action types, reflecting the latest best practices and design patterns.

## Architecture Overview

### Key Design Principles

1.  **Modular Design**: Each action type is a self-contained module.
2.  **Decorator-Based Registration**: Actions self-register using the `@register_action` decorator, eliminating the need for manual registration in a central file.
3.  **Zero `MappingExecutor` Modification**: Adding a new action **does not** require any changes to `MappingExecutor`.
4.  **Consistent Interface**: All actions inherit from `BaseStrategyAction` and implement the `execute` method.
5.  **Comprehensive Testing**: Each action has dedicated unit tests.
6.  **Context-Driven**: Actions are designed to be chained together. They read inputs from and write outputs to a shared context dictionary (`Dict[str, Any]`), allowing for flexible and powerful pipeline construction.

## Step-by-Step Development Process

### Step 1: Plan the Action Type

Before coding, answer these questions:

1.  **What problem does this action solve?**
    - Example: "Convert identifiers using a local, file-based mapping."
2.  **What are the inputs and outputs?**
    - **Inputs**: What keys does it expect to find in the context dictionary? (e.g., a list of identifiers from a previous step).
    - **Outputs**: What keys will it add to the context dictionary? (e.g., a new list of mapped identifiers, statistics, provenance records).
3.  **What parameters will it need from the YAML strategy?**
    - This includes data sources (e.g., file paths), operational flags (e.g., `track_unmatched: true`), and, most importantly, context keys.
    ```yaml
    action:
      type: LOCAL_ID_CONVERTER
      params:
        mapping_file_path: "/path/to/mapping.csv"
        input_context_key: "uniprot_ids"
        output_context_key: "ensembl_ids"
        source_column: "uniprot"
        target_column: "ensembl"
    ```
4.  **How does it handle edge cases?** (Empty inputs, composite identifiers, etc.)

### Step 2: Create the Action Module

Create a new file in `biomapper/core/strategy_actions/`. The class must inherit from `BaseStrategyAction` and be decorated with `@register_action`.

A best-practice implementation includes a comprehensive docstring with a YAML example.

```python
# /biomapper/core/strategy_actions/local_id_converter.py
import logging
from typing import Dict, Any, List

from .base import BaseStrategyAction
from .registry import register_action
# Assume a utility for reading files exists
from ...utils.file_io import read_mapping_file

logger = logging.getLogger(__name__)

@register_action("LOCAL_ID_CONVERTER")
class LocalIdConverterAction(BaseStrategyAction):
    """
    Maps identifiers using a local CSV/TSV file.

    This action reads a local mapping file, and for a given list of source
    identifiers, finds the corresponding target identifiers.

    **YAML Configuration Example:**

    ```yaml
    - name: Map UniProt to Ensembl
      action:
        type: LOCAL_ID_CONVERTER
        params:
          mapping_file_path: "${BIOMAPPER_DATA}/mappings/uniprot_to_ensembl.tsv"
          input_context_key: "uniprot_ids"
          output_context_key: "ensembl_ids_from_local_file"
          source_column: "uniprot_id"
          target_column: "ensembl_id"
    ```
    """
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes the identifier conversion based on parameters stored in the action instance.
        """
        # 1. Validate and extract parameters from self.params
        # The 'params' are injected into the action instance by the strategy executor.
        mapping_file = self.params.get('mapping_file_path')
        input_key = self.params.get('input_context_key')
        output_key = self.params.get('output_context_key')
        source_col = self.params.get('source_column')
        target_col = self.params.get('target_column')

        if not all([mapping_file, input_key, output_key, source_col, target_col]):
            raise ValueError("Missing required parameters for LOCAL_ID_CONVERTER.")

        # 2. Extract input data from the context dictionary
        input_identifiers = context.get(input_key, [])
        if not input_identifiers:
            logger.warning(f"Input key '{input_key}' is empty or not in context. Skipping action.")
            context[output_key] = []
            return context

        # 3. Core logic: read mapping and convert IDs
        # (Assuming a utility function reads the file into a dict)
        mapping_dict = read_mapping_file(mapping_file, source_col, target_col)
        
        output_identifiers = [
            mapping_dict.get(str(identifier))
            for identifier in input_identifiers
            if mapping_dict.get(str(identifier)) is not None
        ]

        # 4. Update context with results
        context[output_key] = output_identifiers
        
        # 5. Add provenance and stats
        provenance_detail = f"Action '{self.__class__.__name__}' mapped {len(input_identifiers)} input IDs to {len(output_identifiers)} output IDs using '{mapping_file}'."
        context.setdefault('provenance', []).append(provenance_detail)
        context.setdefault('stats', {}).update({
            self.__class__.__name__: {
                'inputs': len(input_identifiers),
                'outputs': len(output_identifiers)
            }
        })

        logger.info(f"Successfully mapped {len(output_identifiers)} identifiers.")
        return context
```

### Step 3: Write Comprehensive Unit Tests

Testing is a critical part of action development. Create a corresponding test file in `tests/unit/core/strategy_actions/`.

**Key Testing Principles:**

1.  **Isolate the Action**: Your tests should focus solely on the action's logic. Mock any external dependencies like file reads or database calls.
2.  **Test Parameter Validation**: Ensure your action raises appropriate errors for missing or invalid parameters.
3.  **Cover Edge Cases**: This is crucial for robust bioinformatics pipelines. Your tests should cover:
    *   Empty input lists (`context[input_key] = []`)
    *   Inputs with no matches in the mapping file.
    *   `None` values or empty strings in the input list.
    *   Mappings with special characters or different cases.
    *   Composite identifiers (e.g., `ID1;ID2`).
4.  **Verify the Entire Context**: Don't just check the `output_context_key`. Assert that provenance and statistics are being added to the context correctly.
5.  **Use `pytest` Fixtures**: Use fixtures to create reusable `ActionContext` objects for your tests.

**Example Test Structure:**

```python
# tests/unit/core/strategy_actions/test_local_id_converter.py
import pytest
from unittest.mock import patch
from biomapper.core.strategy_actions.local_id_converter import LocalIdConverterAction

@pytest.fixture
def base_context():
    """Provides a basic action context for tests."""
    return {
        'current_action_params': {
            'mapping_file_path': 'fake/path/map.csv',
            'input_context_key': 'input_ids',
            'output_context_key': 'output_ids',
            'source_column': 'src',
            'target_column': 'tgt'
        },
        'input_ids': ['A', 'B', 'C']
    }

@pytest.mark.asyncio
@patch('biomapper.core.strategy_actions.local_id_converter.read_mapping_file')
async def test_successful_mapping(mock_read_file, base_context):
    # Arrange
    action = LocalIdConverterAction()
    mock_read_file.return_value = {'A': 'X', 'B': 'Y', 'D': 'Z'} # Mock file read

    # Act
    result_context = await action.execute(base_context)

    # Assert
    assert 'output_ids' in result_context
    assert result_context['output_ids'] == ['X', 'Y']
    assert 'stats' in result_context
    assert result_context['stats']['LocalIdConverterAction']['outputs'] == 2
    assert len(result_context['provenance']) == 1

@pytest.mark.asyncio
async def test_empty_input_list(base_context):
    # Arrange
    action = LocalIdConverterAction()
    base_context['input_ids'] = []

    # Act
    result_context = await action.execute(base_context)

    # Assert
    assert result_context['output_ids'] == []
    assert 'stats' not in result_context # No stats updated if no work done
```

### Step 4: Register the Action

To make the action available to the strategy engine, it must be imported in `biomapper/core/strategy_actions/__init__.py`. The act of importing it triggers the `@register_action` decorator.

```python
# /biomapper/core/strategy_actions/__init__.py

# ... other imports
from .local_id_converter import LocalIdConverterAction

__all__ = [
    # ... other actions
    "LocalIdConverterAction",
]
```

## Best Practices

- **Logging**: Use `logger.info()` and `logger.debug()` to provide insight into the action's execution. This is invaluable for debugging complex pipelines.
- **Error Handling**: Validate all incoming parameters from the YAML configuration and raise descriptive `ValueError` exceptions for missing or invalid parameters.
- **Docstrings**: Write a comprehensive docstring for your action class that includes a real-world YAML usage example. This is the primary source of documentation for users of your action.
- **Provenance**: Whenever possible, add detailed provenance records to the context. This allows for full traceability of how identifiers were transformed.
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