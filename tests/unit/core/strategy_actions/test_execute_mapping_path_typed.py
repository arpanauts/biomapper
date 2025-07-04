"""Unit tests for ExecuteMappingPathTypedAction."""

import pytest
from unittest.mock import Mock, AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import ValidationError

from biomapper.core.strategy_actions.execute_mapping_path_typed import (
    ExecuteMappingPathTypedAction,
    ExecuteMappingPathParams,
    ExecuteMappingPathResult,
    MappingProvenanceRecord
)
from biomapper.core.models.execution_context import StrategyExecutionContext
from biomapper.db.models import Endpoint, MappingPath


class MockMappingResultBundle:
    """Mock mapping result bundle for testing."""
    def __init__(self, results=None):
        self.results = results or {}
    
    def __contains__(self, key):
        return key in self.results
    
    def __getitem__(self, key):
        return self.results[key]
    
    def get(self, key, default=None):
        return self.results.get(key, default)


class TestExecuteMappingPathTypedAction:
    """Test suite for ExecuteMappingPathTypedAction."""
    
    @pytest.fixture
    def mock_session(self):
        """Create a mock database session."""
        session = Mock(spec=AsyncSession)
        session.execute = AsyncMock()
        return session
    
    @pytest.fixture
    def mock_endpoints(self):
        """Create mock source and target endpoints."""
        source_endpoint = Mock(spec=Endpoint)
        source_endpoint.id = 1
        source_endpoint.name = "source_endpoint"
        
        target_endpoint = Mock(spec=Endpoint)
        target_endpoint.id = 2
        target_endpoint.name = "target_endpoint"
        
        return source_endpoint, target_endpoint
    
    @pytest.fixture
    def mock_mapping_path(self):
        """Create a mock mapping path."""
        mapping_path = Mock(spec=MappingPath)
        mapping_path.id = 1
        mapping_path.name = "uniprot_to_ensembl"
        mapping_path.source_type = "PROTEIN_UNIPROT"
        mapping_path.target_type = "PROTEIN_ENSEMBL"
        mapping_path.steps = [Mock(), Mock()]  # Mock steps
        return mapping_path
    
    @pytest.fixture
    def mock_mapping_executor(self):
        """Create a mock mapping executor."""
        executor = Mock()
        executor._execute_path = AsyncMock()
        return executor
    
    @pytest.fixture
    def sample_context(self, mock_mapping_executor):
        """Create a sample execution context."""
        context = StrategyExecutionContext(
            initial_identifier="P12345",
            current_identifier="P12345",
            ontology_type="protein"
        )
        context.set_action_data('mapping_executor', mock_mapping_executor)
        return context
    
    @pytest.fixture
    def mock_mapping_result_bundle(self):
        """Create a mock mapping result bundle."""
        result1 = {
            'target_identifiers': ['ENSP001'],
            'confidence_score': 0.95,
            'mapping_source': 'UniProt'
        }
        result2 = {
            'target_identifiers': ['ENSP002', 'ENSP003'],  # Multiple targets
            'confidence_score': 0.90,
            'mapping_source': 'UniProt'
        }
        result3 = {
            'target_identifiers': [],
            'confidence_score': 0.0,
            'mapping_source': None
        }
        
        bundle = MockMappingResultBundle({
            "P12345": result1,
            "Q67890": result2,
            "R11111": result3
        })
        
        return bundle
    
    def test_params_model_validation(self):
        """Test ExecuteMappingPathParams validation."""
        # Valid parameters
        params = ExecuteMappingPathParams(
            path_name="uniprot_to_ensembl",
            batch_size=100,
            min_confidence=0.5
        )
        assert params.path_name == "uniprot_to_ensembl"
        assert params.batch_size == 100
        assert params.min_confidence == 0.5
        
        # Test defaults
        params_default = ExecuteMappingPathParams(path_name="test_path")
        assert params_default.batch_size == 250
        assert params_default.min_confidence == 0.0
        
        # Test validation errors
        with pytest.raises(ValidationError, match="path_name"):
            ExecuteMappingPathParams(path_name="")
        
        with pytest.raises(ValidationError, match="path_name"):
            ExecuteMappingPathParams(path_name="   ")
        
        with pytest.raises(ValidationError, match="batch_size"):
            ExecuteMappingPathParams(path_name="test", batch_size=0)
        
        with pytest.raises(ValidationError, match="batch_size"):
            ExecuteMappingPathParams(path_name="test", batch_size=1001)
        
        with pytest.raises(ValidationError, match="min_confidence"):
            ExecuteMappingPathParams(path_name="test", min_confidence=-0.1)
        
        with pytest.raises(ValidationError, match="min_confidence"):
            ExecuteMappingPathParams(path_name="test", min_confidence=1.1)
    
    def test_result_model_creation(self):
        """Test ExecuteMappingPathResult creation."""
        result = ExecuteMappingPathResult(
            input_identifiers=["P12345", "Q67890"],
            output_identifiers=["ENSP001", "ENSP002"],
            output_ontology_type="PROTEIN_ENSEMBL",
            path_source_type="PROTEIN_UNIPROT",
            path_target_type="PROTEIN_ENSEMBL",
            total_input=2,
            total_mapped=2,
            total_unmapped=0,
            provenance=[{
                "source_id": "P12345",
                "target_id": "ENSP001",
                "confidence": 0.95
            }],
            details={"action": "EXECUTE_MAPPING_PATH_TYPED"}
        )
        
        assert result.input_identifiers == ["P12345", "Q67890"]
        assert result.output_identifiers == ["ENSP001", "ENSP002"]
        assert result.total_input == 2
        assert result.total_mapped == 2
        assert result.total_unmapped == 0
        assert len(result.provenance) == 1
    
    def test_mapping_provenance_record(self):
        """Test MappingProvenanceRecord validation."""
        record = MappingProvenanceRecord(
            source_id="P12345",
            source_ontology="PROTEIN_UNIPROT",
            target_id="ENSP001",
            target_ontology="PROTEIN_ENSEMBL",
            path_name="uniprot_to_ensembl",
            confidence=0.95,
            mapping_source="UniProt"
        )
        
        assert record.source_id == "P12345"
        assert record.confidence == 0.95
        assert record.method == "mapping_path"
        
        # Test confidence validation
        with pytest.raises(ValidationError, match="confidence"):
            MappingProvenanceRecord(
                source_id="P12345",
                source_ontology="PROTEIN_UNIPROT",
                target_id="ENSP001",
                target_ontology="PROTEIN_ENSEMBL",
                path_name="test",
                confidence=1.5  # Invalid confidence
            )
    
    @pytest.mark.asyncio
    async def test_typed_execution_success(self, mock_session, mock_endpoints, mock_mapping_path, 
                                         sample_context, mock_mapping_result_bundle):
        """Test successful typed execution."""
        source_endpoint, target_endpoint = mock_endpoints
        
        # Setup mock session to return mapping path
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_mapping_path
        mock_session.execute.return_value = mock_result
        
        # Setup mock executor to return result bundle
        mock_executor = sample_context.get_action_data('mapping_executor')
        mock_executor._execute_path.return_value = mock_mapping_result_bundle
        
        action = ExecuteMappingPathTypedAction(mock_session)
        
        # Create typed parameters
        params = ExecuteMappingPathParams(
            path_name="uniprot_to_ensembl",
            batch_size=100,
            min_confidence=0.8
        )
        
        result = await action.execute_typed(
            current_identifiers=['P12345', 'Q67890', 'R11111'],
            current_ontology_type='PROTEIN_UNIPROT',
            params=params,
            source_endpoint=source_endpoint,
            target_endpoint=target_endpoint,
            context=sample_context
        )
        
        # Verify result type and structure
        assert isinstance(result, ExecuteMappingPathResult)
        assert result.input_identifiers == ['P12345', 'Q67890', 'R11111']
        assert result.output_identifiers == ['ENSP001', 'ENSP002', 'ENSP003']
        assert result.output_ontology_type == 'PROTEIN_ENSEMBL'
        assert result.path_source_type == 'PROTEIN_UNIPROT'
        assert result.path_target_type == 'PROTEIN_ENSEMBL'
        assert result.total_input == 3
        assert result.total_mapped == 2  # P12345 and Q67890 mapped, R11111 unmapped
        assert result.total_unmapped == 1
        assert len(result.provenance) == 3  # ENSP001, ENSP002, ENSP003
        
        # Check provenance records
        assert result.provenance[0]['source_id'] == 'P12345'
        assert result.provenance[0]['target_id'] == 'ENSP001'
        assert result.provenance[0]['confidence'] == 0.95
        
        assert result.provenance[1]['source_id'] == 'Q67890'
        assert result.provenance[1]['target_id'] == 'ENSP002'
        assert result.provenance[1]['confidence'] == 0.90
        
        # Check details
        assert result.details['action'] == 'EXECUTE_MAPPING_PATH_TYPED'
        assert result.details['path_name'] == 'uniprot_to_ensembl'
        assert result.details['batch_size'] == 100
        assert result.details['min_confidence'] == 0.8
        assert result.details['path_steps'] == 2
        
        # Verify executor was called correctly
        mock_executor._execute_path.assert_called_once_with(
            session=mock_session,
            path=mock_mapping_path,
            input_identifiers=['P12345', 'Q67890', 'R11111'],
            source_ontology='PROTEIN_UNIPROT',
            target_ontology='PROTEIN_ENSEMBL',
            batch_size=100,
            filter_confidence=0.8
        )
        
        # Verify context was updated
        step_results = sample_context.step_results
        assert len(step_results) == 1
        step_result = list(step_results.values())[0]
        assert step_result.success
        assert step_result.data['path_name'] == 'uniprot_to_ensembl'
    
    @pytest.mark.asyncio
    async def test_legacy_compatibility(self, mock_session, mock_endpoints, mock_mapping_path, 
                                      mock_mapping_executor, mock_mapping_result_bundle):
        """Test backward compatibility with legacy execute() method."""
        source_endpoint, target_endpoint = mock_endpoints
        
        # Setup mock session to return mapping path
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_mapping_path
        mock_session.execute.return_value = mock_result
        
        # Setup mock executor to return result bundle
        mock_mapping_executor._execute_path.return_value = mock_mapping_result_bundle
        
        action = ExecuteMappingPathTypedAction(mock_session)
        
        # Use legacy dictionary-based call
        context = {
            'mapping_executor': mock_mapping_executor,
            'min_confidence': 0.8,
            'batch_size': 100
        }
        
        result = await action.execute(
            current_identifiers=['P12345', 'Q67890'],
            current_ontology_type='PROTEIN_UNIPROT',
            action_params={
                'path_name': 'uniprot_to_ensembl',
                'batch_size': 150,  # This should override context
                'min_confidence': 0.9
            },
            source_endpoint=source_endpoint,
            target_endpoint=target_endpoint,
            context=context
        )
        
        # Verify legacy format is maintained
        assert isinstance(result, dict)
        assert 'input_identifiers' in result
        assert 'output_identifiers' in result
        assert 'output_ontology_type' in result
        assert 'provenance' in result
        assert 'details' in result
        
        assert result['input_identifiers'] == ['P12345', 'Q67890']
        assert result['output_identifiers'] == ['ENSP001', 'ENSP002', 'ENSP003']
        assert result['output_ontology_type'] == 'PROTEIN_ENSEMBL'
        
        # Verify executor was called with parameters from action_params
        mock_mapping_executor._execute_path.assert_called_once_with(
            session=mock_session,
            path=mock_mapping_path,
            input_identifiers=['P12345', 'Q67890'],
            source_ontology='PROTEIN_UNIPROT',
            target_ontology='PROTEIN_ENSEMBL',
            batch_size=150,  # From action_params
            filter_confidence=0.9  # From action_params
        )
    
    @pytest.mark.asyncio
    async def test_parameter_validation_error_handling(self, mock_session, mock_endpoints):
        """Test handling of parameter validation errors in legacy mode."""
        source_endpoint, target_endpoint = mock_endpoints
        
        action = ExecuteMappingPathTypedAction(mock_session)
        
        # Test invalid parameters
        result = await action.execute(
            current_identifiers=['P12345'],
            current_ontology_type='PROTEIN_UNIPROT',
            action_params={
                'path_name': '',  # Invalid empty path name
                'batch_size': 0   # Invalid batch size
            },
            source_endpoint=source_endpoint,
            target_endpoint=target_endpoint,
            context={'mapping_executor': Mock()}
        )
        
        # Should return error in standard format
        assert result['input_identifiers'] == ['P12345']
        assert result['output_identifiers'] == []
        assert result['output_ontology_type'] == 'PROTEIN_UNIPROT'
        assert result['provenance'] == []
        assert 'error' in result['details']
        assert 'validation_errors' in result['details']
        assert 'Invalid parameters' in result['details']['error']
    
    @pytest.mark.asyncio
    async def test_execution_error_handling(self, mock_session, mock_endpoints, mock_mapping_path, 
                                          sample_context):
        """Test handling of execution errors."""
        source_endpoint, target_endpoint = mock_endpoints
        
        # Setup mock session to return mapping path
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_mapping_path
        mock_session.execute.return_value = mock_result
        
        # Make executor raise an exception
        mock_executor = sample_context.get_action_data('mapping_executor')
        mock_executor._execute_path.side_effect = RuntimeError("Database connection failed")
        
        action = ExecuteMappingPathTypedAction(mock_session)
        
        # Should propagate the exception in typed mode
        params = ExecuteMappingPathParams(path_name="uniprot_to_ensembl")
        
        with pytest.raises(RuntimeError, match="Database connection failed"):
            await action.execute_typed(
                current_identifiers=['P12345'],
                current_ontology_type='PROTEIN_UNIPROT',
                params=params,
                source_endpoint=source_endpoint,
                target_endpoint=target_endpoint,
                context=sample_context
            )
        
        # Verify failure was recorded in context
        step_results = sample_context.step_results
        assert len(step_results) == 1
        step_result = list(step_results.values())[0]
        assert not step_result.success
        assert "Database connection failed" in step_result.data['error']
    
    @pytest.mark.asyncio
    async def test_legacy_error_handling(self, mock_session, mock_endpoints, mock_mapping_path,
                                       mock_mapping_executor):
        """Test error handling in legacy mode."""
        source_endpoint, target_endpoint = mock_endpoints
        
        # Setup mock session to return mapping path
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_mapping_path
        mock_session.execute.return_value = mock_result
        
        # Make executor raise an exception
        mock_mapping_executor._execute_path.side_effect = RuntimeError("Database connection failed")
        
        action = ExecuteMappingPathTypedAction(mock_session)
        
        # Should return error in standard format in legacy mode
        result = await action.execute(
            current_identifiers=['P12345'],
            current_ontology_type='PROTEIN_UNIPROT',
            action_params={'path_name': 'uniprot_to_ensembl'},
            source_endpoint=source_endpoint,
            target_endpoint=target_endpoint,
            context={'mapping_executor': mock_mapping_executor}
        )
        
        assert result['input_identifiers'] == ['P12345']
        assert result['output_identifiers'] == []
        assert result['output_ontology_type'] == 'PROTEIN_UNIPROT'
        assert result['provenance'] == []
        assert 'error' in result['details']
        assert 'error_type' in result['details']
        assert result['details']['error'] == "Database connection failed"
        assert result['details']['error_type'] == "RuntimeError"
    
    @pytest.mark.asyncio
    async def test_missing_mapping_path_typed(self, mock_session, mock_endpoints, sample_context):
        """Test typed execution with non-existent mapping path."""
        source_endpoint, target_endpoint = mock_endpoints
        
        # Setup mock session to return None
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result
        
        action = ExecuteMappingPathTypedAction(mock_session)
        
        params = ExecuteMappingPathParams(path_name="invalid_path")
        
        with pytest.raises(ValueError, match="Mapping path 'invalid_path' not found"):
            await action.execute_typed(
                current_identifiers=['P12345'],
                current_ontology_type='PROTEIN_UNIPROT',
                params=params,
                source_endpoint=source_endpoint,
                target_endpoint=target_endpoint,
                context=sample_context
            )
    
    @pytest.mark.asyncio
    async def test_missing_mapping_executor_typed(self, mock_session, mock_endpoints, mock_mapping_path):
        """Test typed execution with missing mapping executor."""
        source_endpoint, target_endpoint = mock_endpoints
        
        # Setup mock session to return mapping path
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_mapping_path
        mock_session.execute.return_value = mock_result
        
        # Create context without mapping executor
        context = StrategyExecutionContext(
            initial_identifier="P12345",
            current_identifier="P12345",
            ontology_type="protein"
        )
        
        action = ExecuteMappingPathTypedAction(mock_session)
        
        params = ExecuteMappingPathParams(path_name="uniprot_to_ensembl")
        
        with pytest.raises(ValueError, match="MappingExecutor not provided in context"):
            await action.execute_typed(
                current_identifiers=['P12345'],
                current_ontology_type='PROTEIN_UNIPROT',
                params=params,
                source_endpoint=source_endpoint,
                target_endpoint=target_endpoint,
                context=context
            )
    
    @pytest.mark.asyncio
    async def test_backward_compatibility_with_mapped_value(self, mock_session, mock_endpoints, 
                                                          mock_mapping_path, sample_context):
        """Test backward compatibility with old 'mapped_value' format."""
        source_endpoint, target_endpoint = mock_endpoints
        
        # Setup mock session to return mapping path
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_mapping_path
        mock_session.execute.return_value = mock_result
        
        # Create result bundle with old format
        result_old_format = {
            'mapped_value': 'ENSP001',
            'confidence_score': 0.95,
            'mapping_source': 'UniProt'
        }
        
        bundle = MockMappingResultBundle({
            "P12345": result_old_format
        })
        
        mock_executor = sample_context.get_action_data('mapping_executor')
        mock_executor._execute_path.return_value = bundle
        
        action = ExecuteMappingPathTypedAction(mock_session)
        
        params = ExecuteMappingPathParams(path_name="uniprot_to_ensembl")
        
        result = await action.execute_typed(
            current_identifiers=['P12345'],
            current_ontology_type='PROTEIN_UNIPROT',
            params=params,
            source_endpoint=source_endpoint,
            target_endpoint=target_endpoint,
            context=sample_context
        )
        
        # Should work with old format
        assert result.output_identifiers == ['ENSP001']
        assert len(result.provenance) == 1
        assert result.provenance[0]['target_id'] == 'ENSP001'
        assert result.provenance[0]['confidence'] == 0.95
    
    def test_model_registration(self):
        """Test that the action's model methods return correct types."""
        action = ExecuteMappingPathTypedAction(Mock())
        
        assert action.get_params_model() == ExecuteMappingPathParams
        assert action.get_result_model() == ExecuteMappingPathResult
        
        # Test that we can instantiate the models
        params = action.get_params_model()(path_name="test")
        assert isinstance(params, ExecuteMappingPathParams)
        
        result = action.get_result_model()(
            input_identifiers=[],
            output_identifiers=[],
            output_ontology_type="test",
            path_source_type="test",
            path_target_type="test",
            total_input=0,
            total_mapped=0,
            total_unmapped=0
        )
        assert isinstance(result, ExecuteMappingPathResult)