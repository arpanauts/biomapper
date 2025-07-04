"""
Demonstration of typed strategy actions vs legacy actions.

This script shows how the typed version provides better IDE support,
validation, and type safety compared to the legacy dictionary-based approach.
"""

import asyncio
from unittest.mock import Mock, AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List

from biomapper.core.strategy_actions.execute_mapping_path import ExecuteMappingPathAction
from biomapper.core.strategy_actions.execute_mapping_path_typed import (
    ExecuteMappingPathTypedAction,
    ExecuteMappingPathParams,
    ExecuteMappingPathResult
)
from biomapper.core.models.execution_context import StrategyExecutionContext
from biomapper.db.models import Endpoint, MappingPath


class MockMappingResultBundle:
    """Mock mapping result bundle for demonstration."""
    def __init__(self, results=None):
        self.results = results or {}
    
    def __contains__(self, key):
        return key in self.results
    
    def __getitem__(self, key):
        return self.results[key]


async def demonstrate_legacy_approach():
    """Demonstrate the legacy dictionary-based approach."""
    print("=== Legacy Dictionary-Based Approach ===")
    
    # Setup mocks
    mock_session = Mock(spec=AsyncSession)
    mock_session.execute = AsyncMock()
    
    # Create endpoints
    source_endpoint = Mock(spec=Endpoint)
    target_endpoint = Mock(spec=Endpoint)
    
    # Create mapping path
    mapping_path = Mock(spec=MappingPath)
    mapping_path.name = "uniprot_to_ensembl"
    mapping_path.source_type = "PROTEIN_UNIPROT"
    mapping_path.target_type = "PROTEIN_ENSEMBL"
    mapping_path.steps = [Mock(), Mock()]
    
    # Mock database query result
    mock_result = Mock()
    mock_result.scalar_one_or_none.return_value = mapping_path
    mock_session.execute.return_value = mock_result
    
    # Create mock mapping executor
    mock_mapping_executor = Mock()
    mock_mapping_executor._execute_path = AsyncMock()
    
    # Create mock results
    mock_results = MockMappingResultBundle({
        "P12345": {
            'target_identifiers': ['ENSP001'],
            'confidence_score': 0.95,
            'mapping_source': 'UniProt'
        }
    })
    mock_mapping_executor._execute_path.return_value = mock_results
    
    # Create legacy action
    legacy_action = ExecuteMappingPathAction(mock_session)
    
    # Legacy approach - parameters as dictionaries
    action_params = {
        'path_name': 'uniprot_to_ensembl',
        'batch_size': 100,
        'min_confidence': 0.8
    }
    
    context = {
        'mapping_executor': mock_mapping_executor,
        'cache_settings': {'use_cache': True}
    }
    
    print("Legacy Parameters (dictionary):")
    print(f"  action_params: {action_params}")
    print(f"  context keys: {list(context.keys())}")
    
    # Execute - no type checking, IDE can't help with parameter names
    result = await legacy_action.execute(
        current_identifiers=['P12345'],
        current_ontology_type='PROTEIN_UNIPROT',
        action_params=action_params,
        source_endpoint=source_endpoint,
        target_endpoint=target_endpoint,
        context=context
    )
    
    print("Legacy Result (dictionary):")
    print(f"  Type: {type(result)}")
    print(f"  Keys: {list(result.keys())}")
    print(f"  Output IDs: {result['output_identifiers']}")
    print(f"  Provenance count: {len(result['provenance'])}")
    
    # Common issues with legacy approach:
    print("\nLegacy Approach Issues:")
    print("  - No IDE autocomplete for parameter names")
    print("  - No validation of parameter types or ranges")
    print("  - Runtime errors for typos in parameter names")
    print("  - No type hints for result structure")
    
    # Demonstrate runtime error with typo
    try:
        bad_params = {'path_nam': 'test'}  # Typo in parameter name
        await legacy_action.execute(
            current_identifiers=['P12345'],
            current_ontology_type='PROTEIN_UNIPROT',
            action_params=bad_params,
            source_endpoint=source_endpoint,
            target_endpoint=target_endpoint,
            context=context
        )
    except ValueError as e:
        print(f"  - Runtime error with typo: {e}")


async def demonstrate_typed_approach():
    """Demonstrate the new typed approach."""
    print("\n=== Typed Approach ===")
    
    # Setup mocks (same as legacy)
    mock_session = Mock(spec=AsyncSession)
    mock_session.execute = AsyncMock()
    
    # Create endpoints
    source_endpoint = Mock(spec=Endpoint)
    target_endpoint = Mock(spec=Endpoint)
    
    # Create mapping path
    mapping_path = Mock(spec=MappingPath)
    mapping_path.name = "uniprot_to_ensembl"
    mapping_path.source_type = "PROTEIN_UNIPROT"
    mapping_path.target_type = "PROTEIN_ENSEMBL"
    mapping_path.steps = [Mock(), Mock()]
    
    # Mock database query result
    mock_result = Mock()
    mock_result.scalar_one_or_none.return_value = mapping_path
    mock_session.execute.return_value = mock_result
    
    # Create mock mapping executor
    mock_mapping_executor = Mock()
    mock_mapping_executor._execute_path = AsyncMock()
    
    # Create mock results
    mock_results = MockMappingResultBundle({
        "P12345": {
            'target_identifiers': ['ENSP001'],
            'confidence_score': 0.95,
            'mapping_source': 'UniProt'
        }
    })
    mock_mapping_executor._execute_path.return_value = mock_results
    
    # Create typed action
    typed_action = ExecuteMappingPathTypedAction(mock_session)
    
    # Typed approach - parameters as Pydantic models
    # IDE provides autocomplete and validation
    params = ExecuteMappingPathParams(
        path_name='uniprot_to_ensembl',
        batch_size=100,
        min_confidence=0.8
    )
    
    # Typed context
    context = StrategyExecutionContext(
        initial_identifier="P12345",
        current_identifier="P12345",
        ontology_type="protein"
    )
    context.set_action_data('mapping_executor', mock_mapping_executor)
    
    print("Typed Parameters (Pydantic model):")
    print(f"  params: {params}")
    print(f"  params.path_name: {params.path_name}")
    print(f"  params.batch_size: {params.batch_size}")
    print(f"  params.min_confidence: {params.min_confidence}")
    
    # Execute with full type safety
    result = await typed_action.execute_typed(
        current_identifiers=['P12345'],
        current_ontology_type='PROTEIN_UNIPROT',
        params=params,
        source_endpoint=source_endpoint,
        target_endpoint=target_endpoint,
        context=context
    )
    
    print("Typed Result (Pydantic model):")
    print(f"  Type: {type(result)}")
    print(f"  result.output_identifiers: {result.output_identifiers}")
    print(f"  result.total_input: {result.total_input}")
    print(f"  result.total_mapped: {result.total_mapped}")
    print(f"  result.path_source_type: {result.path_source_type}")
    print(f"  result.path_target_type: {result.path_target_type}")
    
    print("\nTyped Approach Benefits:")
    print("  ✓ IDE autocomplete for all parameter names")
    print("  ✓ Compile-time type checking")
    print("  ✓ Automatic validation of parameter types and ranges")
    print("  ✓ Structured result objects with typed fields")
    print("  ✓ Self-documenting code with clear parameter models")
    
    # Demonstrate validation
    print("\nValidation Examples:")
    
    # Valid parameters
    try:
        valid_params = ExecuteMappingPathParams(
            path_name="test_path",
            batch_size=500,
            min_confidence=0.5
        )
        print(f"  ✓ Valid params: {valid_params}")
    except Exception as e:
        print(f"  ✗ Validation error: {e}")
    
    # Invalid batch size
    try:
        invalid_params = ExecuteMappingPathParams(
            path_name="test_path",
            batch_size=0  # Invalid: must be > 0
        )
        print(f"  ✗ Should not reach here: {invalid_params}")
    except Exception as e:
        print(f"  ✓ Caught validation error: {e}")
    
    # Invalid confidence
    try:
        invalid_params = ExecuteMappingPathParams(
            path_name="test_path",
            min_confidence=1.5  # Invalid: must be <= 1.0
        )
        print(f"  ✗ Should not reach here: {invalid_params}")
    except Exception as e:
        print(f"  ✓ Caught validation error: {e}")


async def demonstrate_backward_compatibility():
    """Demonstrate that typed actions maintain backward compatibility."""
    print("\n=== Backward Compatibility ===")
    
    # Setup mocks
    mock_session = Mock(spec=AsyncSession)
    mock_session.execute = AsyncMock()
    
    # Create endpoints
    source_endpoint = Mock(spec=Endpoint)
    target_endpoint = Mock(spec=Endpoint)
    
    # Create mapping path
    mapping_path = Mock(spec=MappingPath)
    mapping_path.name = "uniprot_to_ensembl"
    mapping_path.source_type = "PROTEIN_UNIPROT"
    mapping_path.target_type = "PROTEIN_ENSEMBL"
    mapping_path.steps = [Mock(), Mock()]
    
    # Mock database query result
    mock_result = Mock()
    mock_result.scalar_one_or_none.return_value = mapping_path
    mock_session.execute.return_value = mock_result
    
    # Create mock mapping executor
    mock_mapping_executor = Mock()
    mock_mapping_executor._execute_path = AsyncMock()
    
    # Create mock results
    mock_results = MockMappingResultBundle({
        "P12345": {
            'target_identifiers': ['ENSP001'],
            'confidence_score': 0.95,
            'mapping_source': 'UniProt'
        }
    })
    mock_mapping_executor._execute_path.return_value = mock_results
    
    # Create typed action
    typed_action = ExecuteMappingPathTypedAction(mock_session)
    
    # Use the typed action with legacy dictionary interface
    action_params = {
        'path_name': 'uniprot_to_ensembl',
        'batch_size': 100,
        'min_confidence': 0.8
    }
    
    context = {
        'mapping_executor': mock_mapping_executor,
        'cache_settings': {'use_cache': True}
    }
    
    print("Using typed action with legacy dictionary interface:")
    
    # Call the legacy execute method
    result = await typed_action.execute(
        current_identifiers=['P12345'],
        current_ontology_type='PROTEIN_UNIPROT',
        action_params=action_params,
        source_endpoint=source_endpoint,
        target_endpoint=target_endpoint,
        context=context
    )
    
    print(f"  ✓ Legacy interface works: {type(result)}")
    print(f"  ✓ Result format maintained: {list(result.keys())}")
    print(f"  ✓ Output IDs: {result['output_identifiers']}")
    
    # Demonstrate parameter validation in legacy mode
    print("\nParameter validation in legacy mode:")
    
    # Valid parameters
    valid_result = await typed_action.execute(
        current_identifiers=['P12345'],
        current_ontology_type='PROTEIN_UNIPROT',
        action_params={'path_name': 'test', 'batch_size': 50},
        source_endpoint=source_endpoint,
        target_endpoint=target_endpoint,
        context=context
    )
    print(f"  ✓ Valid params accepted: {len(valid_result['output_identifiers'])} outputs")
    
    # Invalid parameters - should return error result, not crash
    invalid_result = await typed_action.execute(
        current_identifiers=['P12345'],
        current_ontology_type='PROTEIN_UNIPROT',
        action_params={'path_name': '', 'batch_size': 0},  # Both invalid
        source_endpoint=source_endpoint,
        target_endpoint=target_endpoint,
        context=context
    )
    print(f"  ✓ Invalid params handled gracefully: {invalid_result['details'].get('error', 'No error')}")


async def main():
    """Main demonstration function."""
    print("Biomapper Typed Strategy Actions Demonstration")
    print("=" * 50)
    
    await demonstrate_legacy_approach()
    await demonstrate_typed_approach()
    await demonstrate_backward_compatibility()
    
    print("\n" + "=" * 50)
    print("Summary:")
    print("- Typed actions provide better IDE support and validation")
    print("- Backward compatibility is maintained for existing YAML strategies")
    print("- Parameter validation happens at the Pydantic model level")
    print("- Results are structured and type-safe")
    print("- Migration can be done incrementally, action by action")


if __name__ == "__main__":
    asyncio.run(main())