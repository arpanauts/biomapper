"""Comprehensive tests for the Resource Manager service."""

import pytest
import asyncio
import sys
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from contextlib import asynccontextmanager
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.services.resource_manager import (
    ResourceManager,
    ResourceConfig,
    ResourceType,
    ResourceStatus,
    ManagedResource,
)


class DockerException(Exception):
    """Mock Docker exception."""

    pass


class NotFound(DockerException):
    """Mock Docker NotFound exception."""

    pass


@pytest.fixture
def mock_docker_client():
    """Create a mock Docker client."""
    with patch("app.services.resource_manager.docker") as mock_docker:
        client = MagicMock()
        mock_docker.from_env.return_value = client

        # Set up exception classes
        mock_docker.errors.DockerException = DockerException
        mock_docker.errors.NotFound = NotFound

        # Also patch the NotFound import in resource_manager
        with patch("app.services.resource_manager.NotFound", NotFound):
            yield client


@pytest.fixture
def resource_config():
    """Create test resource configuration."""
    return {
        "qdrant": ResourceConfig(
            name="qdrant",
            type=ResourceType.QDRANT,
            required=True,
            auto_start=True,
            health_check_interval=30,
            config={"host": "localhost", "port": 6333, "container_name": "test-qdrant"},
        ),
        "cts_api": ResourceConfig(
            name="cts_api",
            type=ResourceType.EXTERNAL_API,
            required=False,
            auto_start=False,
            health_check_interval=60,
            config={
                "base_url": "https://cts.fiehnlab.ucdavis.edu",
                "health_endpoint": "https://cts.fiehnlab.ucdavis.edu/rest/status",
            },
        ),
        "redis": ResourceConfig(
            name="redis",
            type=ResourceType.DOCKER_CONTAINER,
            required=False,
            auto_start=True,
            health_check_interval=30,
            config={
                "container_name": "test-redis",
                "image": "redis:alpine",
                "port": 6379,
            },
        ),
    }


@pytest.fixture
async def resource_manager(resource_config):
    """Create a ResourceManager instance."""
    manager = ResourceManager(resource_config)
    # Don't actually initialize to avoid real connections
    manager._initialized = True
    return manager


class TestResourceManager:
    """Test suite for ResourceManager."""

    @pytest.mark.asyncio
    async def test_initialization(self, resource_config, mock_docker_client):
        """Test ResourceManager initialization."""
        with patch("app.services.resource_manager.DOCKER_AVAILABLE", True):
            manager = ResourceManager(resource_config)

            # Mock the methods called during initialization
            manager.register_resource = AsyncMock()
            manager.start_monitoring = AsyncMock()
            manager.ensure_required_resources = AsyncMock(return_value={})

            await manager.initialize()

            assert manager._initialized
            assert manager.docker_client is not None
            assert manager.register_resource.call_count == len(resource_config)
            manager.start_monitoring.assert_called_once()
            manager.ensure_required_resources.assert_called_once()

    @pytest.mark.asyncio
    async def test_register_resource(self, resource_manager, resource_config):
        """Test resource registration."""
        config = resource_config["qdrant"]
        await resource_manager.register_resource("qdrant", config)

        assert "qdrant" in resource_manager.resources
        resource = resource_manager.resources["qdrant"]
        assert resource.name == "qdrant"
        assert resource.type == ResourceType.QDRANT
        assert resource.status == ResourceStatus.UNKNOWN

    @pytest.mark.asyncio
    async def test_check_qdrant_healthy(self, resource_manager):
        """Test Qdrant health check when healthy."""
        with patch("app.services.resource_manager.QDRANT_AVAILABLE", True):
            with patch("app.services.resource_manager.QdrantClient") as MockClient:
                mock_instance = Mock()
                MockClient.return_value = mock_instance
                mock_collections = Mock()
                mock_collections.collections = []
                mock_instance.get_collections.return_value = mock_collections

                config = resource_manager.config["qdrant"]
                status = await resource_manager._check_qdrant(config)

                assert status == ResourceStatus.HEALTHY
                MockClient.assert_called_with(host="localhost", port=6333, timeout=5)

    @pytest.mark.asyncio
    async def test_check_qdrant_unavailable(self, resource_manager):
        """Test Qdrant health check when unavailable."""
        with patch("app.services.resource_manager.QDRANT_AVAILABLE", True):
            with patch("app.services.resource_manager.QdrantClient") as MockClient:
                MockClient.side_effect = Exception("Connection failed")

                config = resource_manager.config["qdrant"]
                status = await resource_manager._check_qdrant(config)

                assert status == ResourceStatus.UNAVAILABLE

    @pytest.mark.asyncio
    async def test_check_external_api_healthy(self, resource_manager):
        """Test external API health check when healthy."""
        config = resource_manager.config["cts_api"]

        # Create async context manager for response
        @asynccontextmanager
        async def mock_session_get(*args, **kwargs):
            mock_response = Mock()
            mock_response.status = 200
            yield mock_response

        # Create async context manager for session
        @asynccontextmanager
        async def mock_session():
            session = Mock()
            session.get = mock_session_get
            yield session

        with patch("app.services.resource_manager.aiohttp.ClientSession", mock_session):
            status = await resource_manager._check_external_api(config)
            assert status == ResourceStatus.HEALTHY

    @pytest.mark.asyncio
    async def test_check_external_api_degraded(self, resource_manager):
        """Test external API health check when degraded."""
        config = resource_manager.config["cts_api"]

        # Create async context manager for response
        @asynccontextmanager
        async def mock_session_get(*args, **kwargs):
            mock_response = Mock()
            mock_response.status = 503
            yield mock_response

        # Create async context manager for session
        @asynccontextmanager
        async def mock_session():
            session = Mock()
            session.get = mock_session_get
            yield session

        with patch("app.services.resource_manager.aiohttp.ClientSession", mock_session):
            status = await resource_manager._check_external_api(config)
            assert status == ResourceStatus.DEGRADED

    @pytest.mark.asyncio
    async def test_check_external_api_timeout(self, resource_manager):
        """Test external API health check with timeout."""
        config = resource_manager.config["cts_api"]

        # Create async context manager for session that raises timeout
        @asynccontextmanager
        async def mock_session():
            session = Mock()
            session.get.side_effect = asyncio.TimeoutError()
            yield session

        with patch("app.services.resource_manager.aiohttp.ClientSession", mock_session):
            status = await resource_manager._check_external_api(config)
            assert status == ResourceStatus.DEGRADED

    @pytest.mark.asyncio
    async def test_check_docker_container_running(
        self, resource_manager, mock_docker_client
    ):
        """Test Docker container check when running."""
        resource_manager.docker_client = mock_docker_client
        config = resource_manager.config["redis"]

        mock_container = Mock()
        mock_container.status = "running"
        mock_container.attrs = {"State": {}}
        mock_docker_client.containers.get.return_value = mock_container

        status = await resource_manager._check_docker_container(config)
        assert status == ResourceStatus.HEALTHY

    @pytest.mark.asyncio
    async def test_check_docker_container_not_found(
        self, resource_manager, mock_docker_client
    ):
        """Test Docker container check when not found."""
        resource_manager.docker_client = mock_docker_client
        config = resource_manager.config["redis"]

        # Use the proper Docker NotFound exception (defined in the module)
        mock_docker_client.containers.get.side_effect = NotFound("Container not found")

        status = await resource_manager._check_docker_container(config)
        assert status == ResourceStatus.UNAVAILABLE

    @pytest.mark.asyncio
    async def test_start_qdrant_existing_container(
        self, resource_manager, mock_docker_client
    ):
        """Test starting Qdrant with existing container."""
        resource_manager.docker_client = mock_docker_client
        config = resource_manager.config["qdrant"]

        mock_container = Mock()
        mock_container.status = "exited"
        mock_docker_client.containers.get.return_value = mock_container

        # Mock health check
        resource_manager._check_qdrant = AsyncMock(return_value=ResourceStatus.HEALTHY)
        resource_manager._initialize_qdrant_collections = AsyncMock()

        success = await resource_manager.start_qdrant(config)

        assert success
        mock_container.start.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_qdrant_create_container(
        self, resource_manager, mock_docker_client
    ):
        """Test starting Qdrant by creating new container."""
        resource_manager.docker_client = mock_docker_client
        config = resource_manager.config["qdrant"]

        # Simulate container not found - use proper Docker NotFound exception (defined in the module)
        mock_docker_client.containers.get.side_effect = NotFound("Container not found")

        # Mock container creation
        mock_container = Mock()
        mock_docker_client.containers.run.return_value = mock_container

        # Mock health check
        resource_manager._check_qdrant = AsyncMock(return_value=ResourceStatus.HEALTHY)
        resource_manager._initialize_qdrant_collections = AsyncMock()

        success = await resource_manager.start_qdrant(config)

        assert success
        mock_docker_client.containers.run.assert_called_once()

    @pytest.mark.asyncio
    async def test_ensure_required_resources_all_healthy(self, resource_manager):
        """Test ensuring required resources when all are healthy."""
        # Set up resources
        for name in resource_manager.config:
            resource_manager.resources[name] = ManagedResource(
                name=name,
                type=resource_manager.config[name].type,
                status=ResourceStatus.HEALTHY,
                last_check=datetime.now(),
            )

        # Mock check_resource
        resource_manager.check_resource = AsyncMock(return_value=ResourceStatus.HEALTHY)

        results = await resource_manager.ensure_required_resources()

        # Only "qdrant" is marked as required in our config
        assert results == {"qdrant": True}

    @pytest.mark.asyncio
    async def test_ensure_required_resources_with_auto_start(self, resource_manager):
        """Test ensuring required resources with auto-start."""
        # Set qdrant as unavailable
        resource_manager.resources["qdrant"] = ManagedResource(
            name="qdrant",
            type=ResourceType.QDRANT,
            status=ResourceStatus.UNAVAILABLE,
            last_check=datetime.now(),
        )

        # Mock methods
        resource_manager.check_resource = AsyncMock(
            return_value=ResourceStatus.UNAVAILABLE
        )
        resource_manager.start_resource = AsyncMock(return_value=True)

        results = await resource_manager.ensure_required_resources()

        assert results == {"qdrant": True}
        resource_manager.start_resource.assert_called_once_with("qdrant")

    @pytest.mark.asyncio
    async def test_get_resource_requirements(self, resource_manager):
        """Test determining resource requirements from strategy."""
        strategy = {
            "steps": [
                {"action": {"type": "VECTOR_ENHANCED_MATCH"}},
                {"action": {"type": "CTS_ENRICHED_MATCH"}},
                {"action": {"type": "SOME_OTHER_ACTION"}},
            ]
        }

        requirements = await resource_manager.get_resource_requirements(strategy)

        assert "qdrant" in requirements
        assert "cts_api" in requirements
        assert "postgres" in requirements  # Always required

    @pytest.mark.asyncio
    async def test_monitor_resource_recovery(self, resource_manager):
        """Test resource monitoring with automatic recovery."""
        config = resource_manager.config["qdrant"]
        config.health_check_interval = 0.1  # Speed up for testing
        config.max_retries = 2

        # Set up resource
        resource_manager.resources["qdrant"] = ManagedResource(
            name="qdrant",
            type=ResourceType.QDRANT,
            status=ResourceStatus.HEALTHY,
            last_check=datetime.now(),
        )

        # Mock health checks - fail then succeed
        check_results = [ResourceStatus.UNAVAILABLE, ResourceStatus.HEALTHY]
        resource_manager.check_resource = AsyncMock(side_effect=check_results)
        resource_manager.start_resource = AsyncMock(return_value=True)

        # Start monitoring task
        task = asyncio.create_task(resource_manager._monitor_resource("qdrant", config))

        # Let it run for a bit
        await asyncio.sleep(0.3)

        # Cancel the task
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        # Verify recovery was attempted
        resource_manager.start_resource.assert_called_with("qdrant")

    @pytest.mark.asyncio
    async def test_cleanup(self, resource_manager):
        """Test cleanup of monitoring tasks."""
        # Create some mock tasks
        task1 = asyncio.create_task(asyncio.sleep(10))
        task2 = asyncio.create_task(asyncio.sleep(10))

        resource_manager.health_check_tasks = {"task1": task1, "task2": task2}

        await resource_manager.cleanup()

        assert len(resource_manager.health_check_tasks) == 0
        assert task1.cancelled()
        assert task2.cancelled()


class TestResourceAwareExecution:
    """Test resource-aware execution features."""

    @pytest.mark.asyncio
    async def test_pre_execution_checks_all_ready(self):
        """Test pre-execution checks when all resources are ready."""
        from app.services.resource_aware_engine import ResourceAwareExecutionEngine

        mock_db = AsyncMock()
        mock_registry = {}
        mock_manager = AsyncMock()

        engine = ResourceAwareExecutionEngine(mock_db, mock_registry, mock_manager)

        # Mock resource requirements
        mock_manager.get_resource_requirements = AsyncMock(
            return_value=["qdrant", "postgres"]
        )

        # Mock resource status
        mock_resources = {
            "qdrant": ManagedResource(
                name="qdrant",
                type=ResourceType.QDRANT,
                status=ResourceStatus.HEALTHY,
                last_check=datetime.now(),
            ),
            "postgres": ManagedResource(
                name="postgres",
                type=ResourceType.DATABASE,
                status=ResourceStatus.HEALTHY,
                last_check=datetime.now(),
            ),
        }
        mock_manager.get_resource_status = AsyncMock(return_value=mock_resources)
        mock_manager.config = {}

        strategy = {"steps": []}
        result = await engine.pre_execution_checks(strategy)

        assert result["ready"] is True
        assert result["required_resources"] == ["qdrant", "postgres"]
        assert len(result["missing_resources"]) == 0

    @pytest.mark.asyncio
    async def test_pre_execution_checks_missing_resources(self):
        """Test pre-execution checks with missing resources."""
        from app.services.resource_aware_engine import ResourceAwareExecutionEngine

        mock_db = AsyncMock()
        mock_registry = {}
        mock_manager = AsyncMock()

        engine = ResourceAwareExecutionEngine(mock_db, mock_registry, mock_manager)

        # Mock resource requirements
        mock_manager.get_resource_requirements = AsyncMock(
            return_value=["qdrant", "postgres"]
        )

        # Mock resource status - qdrant unavailable
        mock_resources = {
            "qdrant": ManagedResource(
                name="qdrant",
                type=ResourceType.QDRANT,
                status=ResourceStatus.UNAVAILABLE,
                last_check=datetime.now(),
            ),
            "postgres": ManagedResource(
                name="postgres",
                type=ResourceType.DATABASE,
                status=ResourceStatus.HEALTHY,
                last_check=datetime.now(),
            ),
        }
        mock_manager.get_resource_status = AsyncMock(return_value=mock_resources)
        mock_manager.config = {}

        strategy = {"steps": []}
        result = await engine.pre_execution_checks(strategy)

        assert result["ready"] is False
        assert "qdrant" in result["missing_resources"]
        assert result["resource_status"]["qdrant"] == "unavailable"
