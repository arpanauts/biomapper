# Developing New Action Types: A Comprehensive Guide

## Overview

Action types are the building blocks of biomapper's mapping strategies. Each action represents a specific, self-contained operation in a pipeline. This guide provides a systematic approach to developing new action types based on the actual implementation in the codebase.

## Architecture Overview

### Key Design Principles

1. **Modular Design**: Each action type is a self-contained module
2. **Decorator-Based Registration**: Actions self-register using the `@register_action` decorator
3. **Consistent Interface**: All actions implement a standard `execute` method
4. **Context-Driven**: Actions communicate via a shared context dictionary
5. **Database Integration**: Actions can access database sessions for complex operations

## Step-by-Step Development Process

### Step 1: Plan the Action Type

Before coding, answer these questions:

1. **What problem does this action solve?**
   - Example: "Load all identifiers from a configured endpoint"
   
2. **What are the inputs and outputs?**
   - **Standard Inputs**: 
     - `current_identifiers`: List of identifiers from previous step
     - `current_ontology_type`: Current ontology type of identifiers
     - `action_params`: Parameters from YAML configuration
     - `source_endpoint`: Source endpoint object
     - `target_endpoint`: Target endpoint object
     - `context`: Shared context dictionary
   - **Outputs**: Must return a dictionary with:
     - `input_identifiers`: Original input list
     - `output_identifiers`: Processed identifier list
     - `output_ontology_type`: Ontology type after processing
     - `provenance`: List of tracking records
     - `details`: Action-specific metadata

3. **What parameters will it need from the YAML strategy?**
   ```yaml
   action:
     type: YOUR_ACTION_TYPE
     params:
       input_context_key: "source_ids"      # Read from context
       output_context_key: "processed_ids"  # Write to context
       other_param: "value"
   ```

### Step 2: Create the Action Module

Create a new file in `biomapper/core/strategy_actions/`:

```python
"""
YourAction: Brief description of what this action does.

This action performs [detailed description of the operation].
"""

import logging
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession

from biomapper.core.strategy_actions.base import BaseStrategyAction
from biomapper.core.strategy_actions.registry import register_action
from biomapper.db.models import Endpoint

logger = logging.getLogger(__name__)


@register_action("YOUR_ACTION_TYPE")
class YourAction(BaseStrategyAction):
    """
    Action that [does something specific].
    
    This action:
    - Point 1 about what it does
    - Point 2 about what it does
    - Point 3 about what it does
    
    Required parameters:
    - param1: Description
    - param2: Description
    
    Optional parameters:
    - param3: Description (default: value)
    """
    
    def __init__(self, session: AsyncSession):
        """
        Initialize the action with a database session.
        
        Args:
            session: AsyncSession for database operations
        """
        self.session = session
        self.logger = logging.getLogger(__name__)
    
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
        Execute the action.
        
        Args:
            current_identifiers: List of identifiers to process
            current_ontology_type: Current ontology type
            action_params: Parameters from YAML configuration
            source_endpoint: Source endpoint object
            target_endpoint: Target endpoint object
            context: Shared execution context
            
        Returns:
            Dictionary containing:
            - input_identifiers: Original input
            - output_identifiers: Processed output
            - output_ontology_type: Output ontology type
            - provenance: Tracking information
            - details: Additional metadata
            
        Raises:
            ValueError: If required parameters are missing
        """
        # 1. Validate required parameters
        param1 = action_params.get('param1')
        if not param1:
            raise ValueError("param1 is required for YOUR_ACTION_TYPE")
        
        # 2. Handle context-based input if specified
        input_key = action_params.get('input_context_key')
        if input_key:
            # Override current_identifiers with context data
            current_identifiers = context.get(input_key, [])
        
        # 3. Early exit for empty input
        if not current_identifiers:
            self.logger.info("No identifiers to process, returning empty result")
            return {
                'input_identifiers': [],
                'output_identifiers': [],
                'output_ontology_type': current_ontology_type,
                'provenance': [],
                'details': {
                    'action': 'YOUR_ACTION_TYPE',
                    'status': 'skipped',
                    'reason': 'empty_input'
                }
            }
        
        # 4. Core processing logic
        output_identifiers = []
        provenance_records = []
        
        try:
            # Your processing logic here
            for identifier in current_identifiers:
                # Process each identifier
                processed = self._process_identifier(identifier, param1)
                if processed:
                    output_identifiers.append(processed)
                    provenance_records.append({
                        'action': 'YOUR_ACTION_TYPE',
                        'source_id': identifier,
                        'target_id': processed,
                        'confidence': 1.0,
                        'method': 'your_method'
                    })
            
            # 5. Update context if output key specified
            output_key = action_params.get('output_context_key')
            if output_key:
                context[output_key] = output_identifiers
                self.logger.info(f"Stored {len(output_identifiers)} identifiers in context['{output_key}']")
            
            # 6. Prepare result
            return {
                'input_identifiers': current_identifiers,
                'output_identifiers': output_identifiers,
                'output_ontology_type': action_params.get('output_ontology_type', current_ontology_type),
                'provenance': provenance_records,
                'details': {
                    'action': 'YOUR_ACTION_TYPE',
                    'parameters': action_params,
                    'input_count': len(current_identifiers),
                    'output_count': len(output_identifiers),
                    'success_rate': len(output_identifiers) / len(current_identifiers) if current_identifiers else 0
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error in YOUR_ACTION_TYPE: {str(e)}")
            raise
    
    def _process_identifier(self, identifier: str, param1: str) -> str:
        """Helper method for processing individual identifiers."""
        # Implementation here
        return identifier  # Placeholder
```

### Step 3: Common Implementation Patterns

#### Loading Data from Endpoints

```python
from biomapper.mapping.adapters.csv_adapter import CSVAdapter

# In execute method:
endpoint_name = action_params.get('endpoint_name')
if endpoint_name == 'SOURCE':
    endpoint = source_endpoint
elif endpoint_name == 'TARGET':
    endpoint = target_endpoint
else:
    # Query endpoint by name from database
    pass

# Load data using adapter
adapter = CSVAdapter(endpoint=endpoint)
df = await adapter.load_data(columns_to_load=['column_name'])
```

#### Handling Composite Identifiers

```python
# Split composite IDs (e.g., "ID1;ID2;ID3")
delimiter = action_params.get('delimiter', ';')
expanded_ids = []
for identifier in current_identifiers:
    if delimiter in identifier:
        expanded_ids.extend(identifier.split(delimiter))
    else:
        expanded_ids.append(identifier)
```

#### Database Queries

```python
from sqlalchemy import select
from biomapper.db.models import SomeModel

# Query using the session
stmt = select(SomeModel).where(SomeModel.field == value)
result = await self.session.execute(stmt)
records = result.scalars().all()
```

### Step 4: Write Comprehensive Unit Tests

Create test file in `tests/unit/core/strategy_actions/`:

```python
import pytest
from unittest.mock import Mock, AsyncMock
from biomapper.core.strategy_actions.your_action import YourAction

@pytest.fixture
def mock_session():
    """Mock database session."""
    session = AsyncMock()
    return session

@pytest.fixture
def mock_endpoints():
    """Mock source and target endpoints."""
    source = Mock()
    source.name = "SOURCE_ENDPOINT"
    target = Mock()
    target.name = "TARGET_ENDPOINT"
    return source, target

@pytest.mark.asyncio
async def test_successful_execution(mock_session, mock_endpoints):
    """Test successful action execution."""
    # Arrange
    action = YourAction(mock_session)
    source_endpoint, target_endpoint = mock_endpoints
    
    current_identifiers = ['ID1', 'ID2', 'ID3']
    action_params = {
        'param1': 'value1',
        'output_context_key': 'results'
    }
    context = {}
    
    # Act
    result = await action.execute(
        current_identifiers=current_identifiers,
        current_ontology_type='ORIGINAL_TYPE',
        action_params=action_params,
        source_endpoint=source_endpoint,
        target_endpoint=target_endpoint,
        context=context
    )
    
    # Assert
    assert result['input_identifiers'] == current_identifiers
    assert len(result['output_identifiers']) > 0
    assert result['output_ontology_type'] == 'ORIGINAL_TYPE'
    assert len(result['provenance']) > 0
    assert result['details']['action'] == 'YOUR_ACTION_TYPE'
    assert 'results' in context
    assert context['results'] == result['output_identifiers']

@pytest.mark.asyncio
async def test_empty_input_handling(mock_session, mock_endpoints):
    """Test handling of empty input."""
    # Arrange
    action = YourAction(mock_session)
    source_endpoint, target_endpoint = mock_endpoints
    
    # Act
    result = await action.execute(
        current_identifiers=[],
        current_ontology_type='TYPE',
        action_params={'param1': 'value'},
        source_endpoint=source_endpoint,
        target_endpoint=target_endpoint,
        context={}
    )
    
    # Assert
    assert result['output_identifiers'] == []
    assert result['details']['status'] == 'skipped'
    assert result['details']['reason'] == 'empty_input'

@pytest.mark.asyncio
async def test_missing_required_parameter(mock_session, mock_endpoints):
    """Test validation of required parameters."""
    # Arrange
    action = YourAction(mock_session)
    source_endpoint, target_endpoint = mock_endpoints
    
    # Act & Assert
    with pytest.raises(ValueError, match="param1 is required"):
        await action.execute(
            current_identifiers=['ID1'],
            current_ontology_type='TYPE',
            action_params={},  # Missing param1
            source_endpoint=source_endpoint,
            target_endpoint=target_endpoint,
            context={}
        )

@pytest.mark.asyncio
async def test_context_input_override(mock_session, mock_endpoints):
    """Test reading input from context."""
    # Arrange
    action = YourAction(mock_session)
    source_endpoint, target_endpoint = mock_endpoints
    
    context = {
        'other_ids': ['CTX1', 'CTX2']
    }
    
    action_params = {
        'param1': 'value',
        'input_context_key': 'other_ids'
    }
    
    # Act
    result = await action.execute(
        current_identifiers=['IGNORED'],  # Should be overridden
        current_ontology_type='TYPE',
        action_params=action_params,
        source_endpoint=source_endpoint,
        target_endpoint=target_endpoint,
        context=context
    )
    
    # Assert
    assert result['input_identifiers'] == ['CTX1', 'CTX2']
```

### Step 5: Register the Action

The action self-registers via the decorator, but you may need to ensure it's imported:

```python
# In biomapper/core/strategy_actions/__init__.py (if needed for discovery)
from .your_action import YourAction

__all__ = [
    # ... existing actions
    "YourAction",
]
```

## Best Practices

### Logging
```python
self.logger.debug(f"Processing {len(identifiers)} identifiers")
self.logger.info(f"Successfully processed {len(output)} identifiers")
self.logger.warning(f"No matches found for {unmatched_count} identifiers")
self.logger.error(f"Failed to process: {error_message}")
```

### Error Handling
```python
# Validate parameters early
if not action_params.get('required_param'):
    raise ValueError("required_param is required for ACTION_TYPE")

# Provide context in errors
try:
    result = process_data(data)
except Exception as e:
    raise ValueError(f"Failed to process data: {str(e)}") from e
```

### Provenance Tracking
```python
provenance_records.append({
    'action': 'YOUR_ACTION_TYPE',
    'source_id': source_id,
    'target_id': target_id,
    'confidence': confidence_score,
    'method': 'direct_match',
    'source_ontology': current_ontology_type,
    'target_ontology': output_ontology_type,
    'timestamp': datetime.utcnow().isoformat()
})
```

## Common Pitfalls to Avoid

1. **Incorrect Return Structure** - Always return all required fields
2. **Ignoring Context Flow** - Remember to read from and write to context
3. **Missing Parameter Validation** - Validate early and fail with clear messages
4. **Not Handling Empty Input** - Always check for empty lists
5. **Forgetting Provenance** - Track all transformations for debugging

## Performance Considerations

1. **Batch Processing** - Process identifiers in batches for large datasets
2. **Async Operations** - Use async/await for I/O operations
3. **Memory Management** - Stream large files instead of loading entirely
4. **Caching** - Use context to cache expensive operations

## Debugging Tips

1. **Use Detailed Logging** - Log at each major step
2. **Include Context in Errors** - Show what data caused the failure
3. **Test with Small Datasets** - Start with minimal test cases
4. **Check Context Flow** - Log what's read from and written to context

## Next Steps

After developing your action:

1. **Integration Test** - Test the action in a real strategy
2. **Documentation** - Update action reference documentation
3. **Example Strategy** - Create a sample YAML showing usage
4. **Performance Test** - Verify it handles production data sizes
5. **Code Review** - Have peers review the implementation

Remember: Actions are the workhorses of biomapper. Make them robust, well-tested, and easy to understand!