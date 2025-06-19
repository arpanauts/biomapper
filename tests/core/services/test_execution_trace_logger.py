"""
Unit tests for ExecutionTraceLogger service.

Tests the logging of execution trace records including MappingSession,
MappingPathExecutionLog, EntityMapping, and ExecutionMetric records to
the cache database.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone
from sqlalchemy.exc import SQLAlchemyError

# Import the service (will need to be created)
from biomapper.core.services.execution_trace_logger import ExecutionTraceLogger

# Import database models
from biomapper.db.cache_models import (
    MappingSession,
    PathExecutionStatus
)

# Import session manager
from biomapper.core.engine_components.session_manager import SessionManager


class TestExecutionTraceLogger:
    """Test suite for ExecutionTraceLogger service."""

    @pytest.fixture
    def mock_session_manager(self):
        """Create a mock SessionManager instance."""
        session_manager = Mock(spec=SessionManager)
        session_manager.get_async_cache_session = Mock()
        return session_manager

    @pytest.fixture
    def mock_async_session(self):
        """Create a mock AsyncSession instance."""
        session = Mock()
        session.add = Mock()
        session.add_all = Mock()
        session.commit = AsyncMock()
        session.refresh = AsyncMock()
        session.get = AsyncMock()
        session.rollback = AsyncMock()
        session.close = AsyncMock()
        return session

    @pytest.fixture
    def execution_trace_logger(self, mock_session_manager):
        """Create ExecutionTraceLogger instance with mocked dependencies."""
        return ExecutionTraceLogger(mock_session_manager)

    @pytest.fixture
    def sample_session_data(self):
        """Sample data for mapping session."""
        return {
            "source_endpoint": "source_api",
            "target_endpoint": "target_api",
            "parameters": {"key": "value"},
            "start_time": datetime.now(timezone.utc)
        }

    @pytest.fixture
    def sample_path_execution_data(self):
        """Sample data for path execution."""
        return {
            "relationship_mapping_path_id": 1,
            "source_entity_id": "entity_123",
            "source_entity_type": "Person",
            "start_time": datetime.now(timezone.utc),
            "end_time": datetime.now(timezone.utc),
            "duration_ms": 150,
            "status": PathExecutionStatus.SUCCESS,
            "log_messages": ["Step 1 complete", "Step 2 complete"]
        }

    @pytest.fixture
    def sample_entity_mappings_data(self):
        """Sample data for entity mappings."""
        return [
            {
                "source_id": "src_1",
                "source_type": "Person",
                "target_id": "tgt_1",
                "target_type": "Individual",
                "confidence": 0.95,
                "mapping_source": "automated",
                "is_derived": False
            },
            {
                "source_id": "src_2",
                "source_type": "Organization",
                "target_id": "tgt_2",
                "target_type": "Company",
                "confidence": 0.87,
                "mapping_source": "automated",
                "is_derived": True,
                "derivation_path": ["step1", "step2"]
            }
        ]

    @pytest.fixture
    def sample_metric_data(self):
        """Sample data for execution metric."""
        return {
            "mapping_session_id": 1,
            "metric_type": "performance",
            "metric_name": "response_time",
            "metric_value": 123.45,
            "timestamp": datetime.now(timezone.utc)
        }

    def test_init(self, mock_session_manager):
        """Test ExecutionTraceLogger initialization."""
        logger = ExecutionTraceLogger(mock_session_manager)
        
        assert logger.session_manager is mock_session_manager
        assert hasattr(logger, 'session_manager')

    @pytest.mark.asyncio
    async def test_log_mapping_session_start(self, execution_trace_logger, mock_session_manager, 
                                           mock_async_session, sample_session_data):
        """Test logging of mapping session start."""
        # Setup
        mock_session_manager.get_async_cache_session.return_value = mock_async_session
        
        with patch('biomapper.core.services.execution_trace_logger.MappingSession') as mock_mapping_session_class:
            mock_mapping_session = Mock()
            mock_mapping_session.id = 123
            mock_mapping_session_class.return_value = mock_mapping_session
            
            # Execute
            result = await execution_trace_logger.log_mapping_session_start(sample_session_data)
            
            # Verify
            mock_session_manager.get_async_cache_session.assert_called_once()
            mock_mapping_session_class.assert_called_once_with(
                source_endpoint=sample_session_data["source_endpoint"],
                target_endpoint=sample_session_data["target_endpoint"],
                parameters=sample_session_data["parameters"],
                start_time=sample_session_data["start_time"]
            )
            mock_async_session.add.assert_called_once_with(mock_mapping_session)
            mock_async_session.commit.assert_called_once()
            mock_async_session.close.assert_called_once()
            assert result == mock_mapping_session

    @pytest.mark.asyncio
    async def test_log_mapping_session_end(self, execution_trace_logger, mock_session_manager, 
                                         mock_async_session):
        """Test logging of mapping session end."""
        # Setup
        session_id = 123
        status = "completed"
        metrics = {"total_mappings": 50, "success_rate": 0.95}
        
        mock_session_manager.get_async_cache_session.return_value = mock_async_session
        mock_mapping_session = Mock()
        mock_async_session.get.return_value = mock_mapping_session
        
        # Execute
        await execution_trace_logger.log_mapping_session_end(session_id, status, metrics)
        
        # Verify
        mock_session_manager.get_async_cache_session.assert_called_once()
        mock_async_session.get.assert_called_once_with(MappingSession, session_id)
        assert mock_mapping_session.status == status
        assert mock_mapping_session.end_time is not None
        mock_async_session.commit.assert_called_once()
        mock_async_session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_log_path_execution(self, execution_trace_logger, mock_session_manager, 
                                    mock_async_session, sample_path_execution_data):
        """Test logging of path execution."""
        # Setup
        mock_session_manager.get_async_cache_session.return_value = mock_async_session
        
        with patch('biomapper.core.services.execution_trace_logger.PathExecutionLog') as mock_path_log_class:
            mock_path_log = Mock()
            mock_path_log.id = 456
            mock_path_log_class.return_value = mock_path_log
            
            # Execute
            result = await execution_trace_logger.log_path_execution(sample_path_execution_data)
            
            # Verify
            mock_session_manager.get_async_cache_session.assert_called_once()
            mock_path_log_class.assert_called_once_with(
                relationship_mapping_path_id=sample_path_execution_data["relationship_mapping_path_id"],
                source_entity_id=sample_path_execution_data["source_entity_id"],
                source_entity_type=sample_path_execution_data["source_entity_type"],
                start_time=sample_path_execution_data["start_time"],
                end_time=sample_path_execution_data["end_time"],
                duration_ms=sample_path_execution_data["duration_ms"],
                status=sample_path_execution_data["status"],
                log_messages=sample_path_execution_data["log_messages"],
                error_message=None
            )
            mock_async_session.add.assert_called_once_with(mock_path_log)
            mock_async_session.commit.assert_called_once()
            mock_async_session.close.assert_called_once()
            assert result == mock_path_log

    @pytest.mark.asyncio
    async def test_log_entity_mappings(self, execution_trace_logger, mock_session_manager, 
                                     mock_async_session, sample_entity_mappings_data):
        """Test logging of entity mappings with provenance."""
        # Setup
        provenance_data = {
            "relationship_mapping_path_id": 1,
            "execution_timestamp": datetime.now(timezone.utc),
            "executor_version": "1.0.0"
        }
        
        mock_session_manager.get_async_cache_session.return_value = mock_async_session
        
        with patch('biomapper.core.services.execution_trace_logger.EntityMapping') as mock_entity_mapping_class, \
             patch('biomapper.core.services.execution_trace_logger.EntityMappingProvenance') as mock_provenance_class:
            
            mock_mappings = [Mock(), Mock()]
            mock_provenance_records = [Mock(), Mock()]
            mock_entity_mapping_class.side_effect = mock_mappings
            mock_provenance_class.side_effect = mock_provenance_records
            
            # Execute
            await execution_trace_logger.log_entity_mappings(sample_entity_mappings_data, provenance_data)
            
            # Verify entity mapping creation
            assert mock_entity_mapping_class.call_count == 2
            mock_entity_mapping_class.assert_any_call(
                source_id="src_1",
                source_type="Person",
                target_id="tgt_1",
                target_type="Individual",
                confidence=0.95,
                mapping_source="automated",
                is_derived=False,
                derivation_path=None
            )
            mock_entity_mapping_class.assert_any_call(
                source_id="src_2",
                source_type="Organization",
                target_id="tgt_2",
                target_type="Company",
                confidence=0.87,
                mapping_source="automated",
                is_derived=True,
                derivation_path=["step1", "step2"]
            )
            
            # Verify provenance creation
            assert mock_provenance_class.call_count == 2
            
            # Verify database operations
            mock_async_session.add_all.assert_called_once()
            mock_async_session.commit.assert_called_once()
            mock_async_session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_log_execution_metric(self, execution_trace_logger, mock_session_manager, 
                                      mock_async_session, sample_metric_data):
        """Test logging of execution metric."""
        # Setup
        mock_session_manager.get_async_cache_session.return_value = mock_async_session
        
        with patch('biomapper.core.services.execution_trace_logger.ExecutionMetric') as mock_metric_class:
            mock_metric = Mock()
            mock_metric.id = 789
            mock_metric_class.return_value = mock_metric
            
            # Execute
            result = await execution_trace_logger.log_execution_metric(sample_metric_data)
            
            # Verify
            mock_session_manager.get_async_cache_session.assert_called_once()
            mock_metric_class.assert_called_once_with(
                mapping_session_id=sample_metric_data["mapping_session_id"],
                metric_type=sample_metric_data["metric_type"],
                metric_name=sample_metric_data["metric_name"],
                metric_value=sample_metric_data["metric_value"],
                string_value=None,
                timestamp=sample_metric_data["timestamp"]
            )
            mock_async_session.add.assert_called_once_with(mock_metric)
            mock_async_session.commit.assert_called_once()
            mock_async_session.close.assert_called_once()
            assert result == mock_metric

    @pytest.mark.asyncio
    async def test_database_session_handling(self, execution_trace_logger, mock_session_manager, 
                                           mock_async_session, sample_session_data):
        """Test proper database session handling."""
        # Setup
        mock_session_manager.get_async_cache_session.return_value = mock_async_session
        
        with patch('biomapper.core.services.execution_trace_logger.MappingSession') as mock_mapping_session_class:
            mock_mapping_session_class.return_value = Mock()
            
            # Execute
            await execution_trace_logger.log_mapping_session_start(sample_session_data)
            
            # Verify session is obtained and closed
            mock_session_manager.get_async_cache_session.assert_called_once()
            mock_async_session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_database_error_handling(self, execution_trace_logger, mock_session_manager, 
                                         mock_async_session, sample_session_data):
        """Test error handling during database operations."""
        # Setup
        mock_session_manager.get_async_cache_session.return_value = mock_async_session
        mock_async_session.commit.side_effect = SQLAlchemyError("Database error")
        
        with patch('biomapper.core.services.execution_trace_logger.MappingSession'):
            # Execute and verify exception handling
            with pytest.raises(Exception):  # Could be SQLAlchemyError or custom CacheTransactionError
                await execution_trace_logger.log_mapping_session_start(sample_session_data)
            
            # Verify rollback and close are called on error
            mock_async_session.rollback.assert_called_once()
            mock_async_session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_malformed_data_handling(self, execution_trace_logger, mock_session_manager, 
                                         mock_async_session):
        """Test handling of malformed input data."""
        # Setup
        malformed_data = {"invalid": "data"}  # Missing required fields
        mock_session_manager.get_async_cache_session.return_value = mock_async_session
        
        # Execute and verify exception handling (should raise KeyError for missing keys)
        with pytest.raises(KeyError):
            await execution_trace_logger.log_mapping_session_start(malformed_data)

    @pytest.mark.asyncio
    async def test_session_cleanup_on_success(self, execution_trace_logger, mock_session_manager, 
                                             mock_async_session, sample_session_data):
        """Test that session is properly cleaned up on successful operations."""
        # Setup
        mock_session_manager.get_async_cache_session.return_value = mock_async_session
        
        with patch('biomapper.core.services.execution_trace_logger.MappingSession') as mock_mapping_session_class:
            mock_mapping_session_class.return_value = Mock()
            
            # Execute
            await execution_trace_logger.log_mapping_session_start(sample_session_data)
            
            # Verify session lifecycle
            mock_session_manager.get_async_cache_session.assert_called_once()
            mock_async_session.add.assert_called_once()
            mock_async_session.commit.assert_called_once()
            mock_async_session.close.assert_called_once()