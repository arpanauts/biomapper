"""
Tests for TypedStrategyAction base class.
"""

import pytest
from typing import List, Dict, Any
from unittest.mock import AsyncMock, MagicMock
from pydantic import BaseModel

from biomapper.core.strategy_actions.typed_base import TypedStrategyAction, StandardActionResult
from biomapper.core.models.execution_context import StrategyExecutionContext
from biomapper.db.models import Endpoint


class TestActionParams(BaseModel):
    """Test parameters model."""
    batch_size: int = 100
    include_obsolete: bool = False
    custom_param: str = "default"


class TestActionResult(StandardActionResult):
    """Test result model extending standard result."""
    processed_count: int = 0
    custom_field: str = "test"


class TestTypedAction(TypedStrategyAction[TestActionParams, TestActionResult]):
    """Test implementation of TypedStrategyAction."""
    
    def __init__(self, session=None):
        """Initialize test action."""
        super().__init__()
        self.session = session
        self.execute_typed_called = False
    
    def get_params_model(self):
        """Return params model."""
        return TestActionParams
    
    def get_result_model(self):
        """Return result model."""
        return TestActionResult
    
    async def execute_typed(
        self,
        current_identifiers: List[str],
        current_ontology_type: str,
        params: TestActionParams,
        source_endpoint: Endpoint,
        target_endpoint: Endpoint,
        context: StrategyExecutionContext
    ) -> TestActionResult:
        """Execute typed implementation."""
        self.execute_typed_called = True
        
        # Verify we got typed parameters
        assert isinstance(params, TestActionParams)
        assert isinstance(context, StrategyExecutionContext)
        
        # Store test data in context
        context.set_action_data('test_batch_size', params.batch_size)
        
        # Return typed result
        return TestActionResult(
            input_identifiers=current_identifiers,
            output_identifiers=[f"processed_{id}" for id in current_identifiers],
            output_ontology_type=current_ontology_type,
            provenance=[
                {"action": "test", "identifier": id}
                for id in current_identifiers
            ],
            details={"batch_size": params.batch_size},
            processed_count=len(current_identifiers),
            custom_field=params.custom_param
        )


class TestTypedStrategyAction:
    """Test cases for TypedStrategyAction base class."""
    
    @pytest.fixture
    def mock_endpoints(self):
        """Create mock endpoint objects."""
        source = MagicMock(spec=Endpoint)
        source.name = "SOURCE"
        
        target = MagicMock(spec=Endpoint)
        target.name = "TARGET"
        
        return source, target
    
    @pytest.fixture
    def action(self):
        """Create test action instance."""
        return TestTypedAction(session=AsyncMock())
    
    async def test_backward_compatible_execute(self, action, mock_endpoints):
        """Test that the backward-compatible execute method works."""
        source, target = mock_endpoints
        context = {}
        
        result = await action.execute(
            current_identifiers=["ID1", "ID2", "ID3"],
            current_ontology_type="PROTEIN_ONTOLOGY",
            action_params={
                "batch_size": 50,
                "include_obsolete": True,
                "custom_param": "test_value"
            },
            source_endpoint=source,
            target_endpoint=target,
            context=context
        )
        
        # Verify execute_typed was called
        assert action.execute_typed_called
        
        # Verify standard result format
        assert result['input_identifiers'] == ["ID1", "ID2", "ID3"]
        assert result['output_identifiers'] == ["processed_ID1", "processed_ID2", "processed_ID3"]
        assert result['output_ontology_type'] == "PROTEIN_ONTOLOGY"
        assert len(result['provenance']) == 3
        assert result['details']['batch_size'] == 50
        
        # Verify context was updated
        assert context['test_batch_size'] == 50
    
    async def test_parameter_validation_error(self, action, mock_endpoints):
        """Test that parameter validation errors are handled gracefully."""
        source, target = mock_endpoints
        
        result = await action.execute(
            current_identifiers=["ID1"],
            current_ontology_type="PROTEIN_ONTOLOGY",
            action_params={
                "batch_size": "not_a_number",  # Invalid type
                "include_obsolete": "yes"  # Invalid type
            },
            source_endpoint=source,
            target_endpoint=target,
            context={}
        )
        
        # Should return error result
        assert result['input_identifiers'] == ["ID1"]
        assert result['output_identifiers'] == []
        assert 'error' in result['details']
        assert 'validation_errors' in result['details']
    
    async def test_execution_error_handling(self, action, mock_endpoints):
        """Test that execution errors are handled gracefully."""
        source, target = mock_endpoints
        
        # Override execute_typed to raise an error
        async def failing_execute(*args, **kwargs):
            raise ValueError("Test error")
        
        action.execute_typed = failing_execute
        
        result = await action.execute(
            current_identifiers=["ID1"],
            current_ontology_type="PROTEIN_ONTOLOGY",
            action_params={"batch_size": 100},
            source_endpoint=source,
            target_endpoint=target,
            context={}
        )
        
        # Should return error result
        assert result['input_identifiers'] == ["ID1"]
        assert result['output_identifiers'] == []
        assert result['details']['error'] == "Test error"
        assert result['details']['error_type'] == "ValueError"
    
    async def test_context_conversion(self, action, mock_endpoints):
        """Test that context is properly converted between dict and typed."""
        source, target = mock_endpoints
        
        # Test with existing context data
        context = {
            'initial_identifier': 'INIT_ID',
            'current_identifier': 'CURR_ID',
            'custom_key': 'custom_value',
            'step_results': {},
            'provenance': []
        }
        
        result = await action.execute(
            current_identifiers=["ID1"],
            current_ontology_type="GENE_ONTOLOGY",  # Should map to "gene"
            action_params={"batch_size": 25},
            source_endpoint=source,
            target_endpoint=target,
            context=context
        )
        
        # Verify context preservation
        assert context['initial_identifier'] == 'INIT_ID'
        assert context['current_identifier'] == 'CURR_ID'
        assert context['test_batch_size'] == 25  # Added by action
        
    async def test_ontology_type_mapping(self, action, mock_endpoints):
        """Test that ontology types are correctly mapped."""
        source, target = mock_endpoints
        
        test_cases = [
            ("GENE_ONTOLOGY", "gene"),
            ("PROTEIN_UNIPROTKB_AC_ONTOLOGY", "protein"),
            ("METABOLITE_CHEBI_ONTOLOGY", "metabolite"),
            ("PATHWAY_REACTOME", "pathway"),
            ("DISEASE_MONDO", "disease"),
            ("UNKNOWN_TYPE", "protein")  # Default
        ]
        
        for input_type, _ in test_cases:
            result = await action.execute(
                current_identifiers=["ID1"],
                current_ontology_type=input_type,
                action_params={},
                source_endpoint=source,
                target_endpoint=target,
                context={}
            )
            
            # Should complete without error
            assert result['output_ontology_type'] == input_type
    
    async def test_result_conversion_with_extra_fields(self, action, mock_endpoints):
        """Test that extra fields in typed result are preserved in details."""
        source, target = mock_endpoints
        
        result = await action.execute(
            current_identifiers=["ID1", "ID2"],
            current_ontology_type="PROTEIN_ONTOLOGY",
            action_params={"custom_param": "special_value"},
            source_endpoint=source,
            target_endpoint=target,
            context={}
        )
        
        # Standard fields should be at top level
        assert 'input_identifiers' in result
        assert 'output_identifiers' in result
        assert 'provenance' in result
        
        # Custom fields should be in details
        assert result['details']['processed_count'] == 2
        assert result['details']['custom_field'] == "special_value"