"""Unit tests for ExecuteMappingPathAction."""

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

from biomapper.core.strategy_actions.execute_mapping_path import ExecuteMappingPathAction
from biomapper.db.models import Endpoint, MappingPath


class MockMappingResult:
    """Mock mapping result for testing."""
    def __init__(self, source_identifier, mapped_value, confidence=1.0, mapping_source=None):
        self.source_identifier = source_identifier
        self.mapped_value = mapped_value
        self.confidence = confidence
        self.mapping_source = mapping_source


class MockMappingResultBundle:
    """Mock mapping result bundle for testing."""
    def __init__(self, results=None):
        self.results = results or {}


class TestExecuteMappingPathAction:
    """Test suite for ExecuteMappingPathAction."""
    
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
        return mapping_path
    
    @pytest.fixture
    def mock_mapping_executor(self):
        """Create a mock mapping executor."""
        executor = Mock()
        executor._execute_path = AsyncMock()
        return executor
    
    @pytest.fixture
    def mock_mapping_result_bundle(self):
        """Create a mock mapping result bundle."""
        # Create individual mapping results
        result1 = MockMappingResult("P12345", "ENSP001", 0.95, "UniProt")
        result2 = MockMappingResult("Q67890", "ENSP002", 0.90, "UniProt")
        result3 = MockMappingResult("R11111", None, 0.0, None)  # Unmapped
        
        bundle = MockMappingResultBundle({
            "P12345": result1,
            "Q67890": result2,
            "R11111": result3
        })
        
        return bundle
    
    @pytest.mark.asyncio
    async def test_successful_execution(self, mock_session, mock_endpoints, mock_mapping_path, 
                                      mock_mapping_executor, mock_mapping_result_bundle):
        """Test successful execution with valid mapping path."""
        source_endpoint, target_endpoint = mock_endpoints
        
        # Setup mock session to return mapping path
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_mapping_path
        mock_session.execute.return_value = mock_result
        
        # Setup mock executor to return result bundle
        mock_mapping_executor._execute_path.return_value = mock_mapping_result_bundle
        
        action = ExecuteMappingPathAction(mock_session)
        
        context = {
            'mapping_executor': mock_mapping_executor,
            'cache_settings': {'use_cache': True, 'max_cache_age_days': 7},
            'min_confidence': 0.8
        }
        
        result = await action.execute(
            current_identifiers=['P12345', 'Q67890', 'R11111'],
            current_ontology_type='PROTEIN_UNIPROT',
            action_params={'path_name': 'uniprot_to_ensembl'},
            source_endpoint=source_endpoint,
            target_endpoint=target_endpoint,
            context=context
        )
        
        # Verify results
        assert result['input_identifiers'] == ['P12345', 'Q67890', 'R11111']
        assert result['output_identifiers'] == ['ENSP001', 'ENSP002']  # R11111 unmapped
        assert result['output_ontology_type'] == 'PROTEIN_ENSEMBL'
        assert len(result['provenance']) == 2  # Only mapped results
        
        # Check provenance
        prov1 = result['provenance'][0]
        assert prov1['source_id'] == 'P12345'
        assert prov1['target_id'] == 'ENSP001'
        assert prov1['confidence'] == 0.95
        assert prov1['method'] == 'mapping_path'
        assert prov1['path_name'] == 'uniprot_to_ensembl'
        
        # Check details
        details = result['details']
        assert details['action'] == 'EXECUTE_MAPPING_PATH'
        assert details['path_name'] == 'uniprot_to_ensembl'
        assert details['total_input'] == 3
        assert details['total_mapped'] == 2
        assert details['total_unmapped'] == 1
        
        # Verify executor was called correctly
        mock_mapping_executor._execute_path.assert_called_once_with(
            path_id=1,
            identifiers=['P12345', 'Q67890', 'R11111'],
            is_reverse=False,
            use_cache=True,
            max_cache_age_days=7,
            min_confidence=0.8
        )
    
    @pytest.mark.asyncio
    async def test_nonexistent_mapping_path(self, mock_session, mock_endpoints):
        """Test handling of non-existent mapping path."""
        source_endpoint, target_endpoint = mock_endpoints
        
        # Setup mock session to return None
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result
        
        action = ExecuteMappingPathAction(mock_session)
        
        with pytest.raises(ValueError, match="Mapping path 'invalid_path' not found"):
            await action.execute(
                current_identifiers=['P12345'],
                current_ontology_type='PROTEIN_UNIPROT',
                action_params={'path_name': 'invalid_path'},
                source_endpoint=source_endpoint,
                target_endpoint=target_endpoint,
                context={'mapping_executor': Mock()}
            )
    
    @pytest.mark.asyncio
    async def test_missing_path_name(self, mock_session, mock_endpoints):
        """Test validation when path_name is missing."""
        source_endpoint, target_endpoint = mock_endpoints
        
        action = ExecuteMappingPathAction(mock_session)
        
        with pytest.raises(ValueError, match="path_name is required"):
            await action.execute(
                current_identifiers=['P12345'],
                current_ontology_type='PROTEIN_UNIPROT',
                action_params={},
                source_endpoint=source_endpoint,
                target_endpoint=target_endpoint,
                context={}
            )
    
    @pytest.mark.asyncio
    async def test_missing_mapping_executor(self, mock_session, mock_endpoints, mock_mapping_path):
        """Test handling when mapping executor is not provided in context."""
        source_endpoint, target_endpoint = mock_endpoints
        
        # Setup mock session to return mapping path
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_mapping_path
        mock_session.execute.return_value = mock_result
        
        action = ExecuteMappingPathAction(mock_session)
        
        with pytest.raises(ValueError, match="MappingExecutor not provided in context"):
            await action.execute(
                current_identifiers=['P12345'],
                current_ontology_type='PROTEIN_UNIPROT',
                action_params={'path_name': 'uniprot_to_ensembl'},
                source_endpoint=source_endpoint,
                target_endpoint=target_endpoint,
                context={}  # Missing mapping_executor
            )
    
    @pytest.mark.asyncio
    async def test_executor_error_propagation(self, mock_session, mock_endpoints, mock_mapping_path, 
                                            mock_mapping_executor):
        """Test correct propagation of errors from _execute_path."""
        source_endpoint, target_endpoint = mock_endpoints
        
        # Setup mock session to return mapping path
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_mapping_path
        mock_session.execute.return_value = mock_result
        
        # Make executor raise an exception
        mock_mapping_executor._execute_path.side_effect = RuntimeError("Database connection failed")
        
        action = ExecuteMappingPathAction(mock_session)
        
        with pytest.raises(RuntimeError, match="Database connection failed"):
            await action.execute(
                current_identifiers=['P12345'],
                current_ontology_type='PROTEIN_UNIPROT',
                action_params={'path_name': 'uniprot_to_ensembl'},
                source_endpoint=source_endpoint,
                target_endpoint=target_endpoint,
                context={'mapping_executor': mock_mapping_executor}
            )
    
    @pytest.mark.asyncio
    async def test_default_cache_settings(self, mock_session, mock_endpoints, mock_mapping_path, 
                                        mock_mapping_executor, mock_mapping_result_bundle):
        """Test default cache settings when not provided in context."""
        source_endpoint, target_endpoint = mock_endpoints
        
        # Setup mock session to return mapping path
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_mapping_path
        mock_session.execute.return_value = mock_result
        
        # Setup mock executor to return result bundle
        mock_mapping_executor._execute_path.return_value = mock_mapping_result_bundle
        
        action = ExecuteMappingPathAction(mock_session)
        
        # Context without cache_settings
        context = {'mapping_executor': mock_mapping_executor}
        
        result = await action.execute(
            current_identifiers=['P12345'],
            current_ontology_type='PROTEIN_UNIPROT',
            action_params={'path_name': 'uniprot_to_ensembl'},
            source_endpoint=source_endpoint,
            target_endpoint=target_endpoint,
            context=context
        )
        
        # Verify executor was called with default cache settings
        mock_mapping_executor._execute_path.assert_called_once_with(
            path_id=1,
            identifiers=['P12345'],
            is_reverse=False,
            use_cache=True,  # Default
            max_cache_age_days=None,  # Not specified
            min_confidence=0.0  # Default
        )
    
    @pytest.mark.asyncio
    async def test_all_unmapped_identifiers(self, mock_session, mock_endpoints, mock_mapping_path, 
                                           mock_mapping_executor):
        """Test behavior when all identifiers are unmapped."""
        source_endpoint, target_endpoint = mock_endpoints
        
        # Setup mock session to return mapping path
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_mapping_path
        mock_session.execute.return_value = mock_result
        
        # Create result bundle with all unmapped
        result1 = MockMappingResult("P12345", None, 0.0, None)
        result2 = MockMappingResult("Q67890", None, 0.0, None)
        
        bundle = MockMappingResultBundle({
            "P12345": result1,
            "Q67890": result2
        })
        
        mock_mapping_executor._execute_path.return_value = bundle
        
        action = ExecuteMappingPathAction(mock_session)
        
        result = await action.execute(
            current_identifiers=['P12345', 'Q67890'],
            current_ontology_type='PROTEIN_UNIPROT',
            action_params={'path_name': 'uniprot_to_ensembl'},
            source_endpoint=source_endpoint,
            target_endpoint=target_endpoint,
            context={'mapping_executor': mock_mapping_executor}
        )
        
        assert result['output_identifiers'] == []
        assert result['provenance'] == []
        assert result['details']['total_mapped'] == 0
        assert result['details']['total_unmapped'] == 2
    
    @pytest.mark.asyncio
    async def test_empty_input_identifiers(self, mock_session, mock_endpoints, mock_mapping_path, 
                                          mock_mapping_executor):
        """Test behavior with empty list of input identifiers."""
        source_endpoint, target_endpoint = mock_endpoints
        
        # Setup mock session to return mapping path
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_mapping_path
        mock_session.execute.return_value = mock_result
        
        # Create empty result bundle
        bundle = MockMappingResultBundle({})
        
        mock_mapping_executor._execute_path.return_value = bundle
        
        action = ExecuteMappingPathAction(mock_session)
        
        result = await action.execute(
            current_identifiers=[],
            current_ontology_type='PROTEIN_UNIPROT',
            action_params={'path_name': 'uniprot_to_ensembl'},
            source_endpoint=source_endpoint,
            target_endpoint=target_endpoint,
            context={'mapping_executor': mock_mapping_executor}
        )
        
        assert result['input_identifiers'] == []
        assert result['output_identifiers'] == []
        assert result['provenance'] == []
        assert result['details']['total_input'] == 0
        assert result['details']['total_mapped'] == 0