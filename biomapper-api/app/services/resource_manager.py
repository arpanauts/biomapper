"""Resource Management Service for External Dependencies."""
import asyncio
import logging
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field

try:
    import docker
    from docker.errors import DockerException, NotFound
    DOCKER_AVAILABLE = True
except ImportError:
    DOCKER_AVAILABLE = False
    # Define dummy exception class if docker is not available
    class NotFound(Exception):
        pass

try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, VectorParams
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False

import aiohttp

logger = logging.getLogger(__name__)


class ResourceType(str, Enum):
    """Types of manageable resources."""
    DOCKER_CONTAINER = "docker_container"
    QDRANT = "qdrant"
    EXTERNAL_API = "external_api"
    DATABASE = "database"
    FILE_SYSTEM = "file_system"
    COMPUTE = "compute"


class ResourceStatus(str, Enum):
    """Resource health status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    STARTING = "starting"
    STOPPING = "stopping"
    UNKNOWN = "unknown"


class ResourceConfig(BaseModel):
    """Configuration for a managed resource."""
    name: str
    type: ResourceType
    required: bool = False
    auto_start: bool = False
    health_check_interval: int = 30
    max_retries: int = 3
    config: Dict[str, Any] = Field(default_factory=dict)


class ManagedResource(BaseModel):
    """A resource managed by the system."""
    name: str
    type: ResourceType
    status: ResourceStatus
    last_check: datetime
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ResourceUnavailableError(Exception):
    """Raised when a required resource is unavailable."""
    pass


class ResourceManager:
    """
    Manages all external resources required by biomapper.
    
    Responsibilities:
    - Start/stop resources
    - Health monitoring
    - Automatic recovery
    - Dependency management
    - Resource allocation
    """
    
    def __init__(self, config: Dict[str, ResourceConfig]):
        """Initialize resource manager."""
        self.resources: Dict[str, ManagedResource] = {}
        self.config = config
        self.docker_client = None
        self.health_check_tasks: Dict[str, asyncio.Task] = {}
        self._initialized = False
        
    async def initialize(self):
        """Initialize resource manager and start monitoring."""
        if self._initialized:
            return
            
        # Initialize Docker client
        if DOCKER_AVAILABLE:
            try:
                self.docker_client = docker.from_env()
                logger.info("Docker client initialized successfully")
            except DockerException as e:
                logger.warning(f"Docker not available: {e}")
        else:
            logger.warning("Docker library not installed - container management disabled")
        
        # Register all configured resources
        for name, config in self.config.items():
            await self.register_resource(name, config)
        
        # Start health monitoring
        await self.start_monitoring()
        
        # Auto-start required resources
        await self.ensure_required_resources()
        
        self._initialized = True
        logger.info(f"Resource manager initialized with {len(self.resources)} resources")
    
    async def register_resource(self, name: str, config: ResourceConfig):
        """Register a new managed resource."""
        resource = ManagedResource(
            name=name,
            type=config.type,
            status=ResourceStatus.UNKNOWN,
            last_check=datetime.now()
        )
        self.resources[name] = resource
        logger.debug(f"Registered resource: {name} (type: {config.type})")
    
    async def start_monitoring(self):
        """Start health monitoring for all resources."""
        for name, config in self.config.items():
            if config.health_check_interval > 0:
                task = asyncio.create_task(
                    self._monitor_resource(name, config)
                )
                self.health_check_tasks[name] = task
                logger.debug(f"Started monitoring for resource: {name}")
    
    async def ensure_required_resources(self) -> Dict[str, bool]:
        """
        Ensure all required resources are available.
        Returns status of each resource.
        """
        results = {}
        
        for name, config in self.config.items():
            if not config.required:
                continue
                
            status = await self.check_resource(name)
            
            if status != ResourceStatus.HEALTHY:
                if config.auto_start:
                    logger.info(f"Auto-starting required resource: {name}")
                    success = await self.start_resource(name)
                    results[name] = success
                else:
                    results[name] = False
                    logger.error(f"Required resource {name} is not available and auto-start is disabled")
            else:
                results[name] = True
                logger.debug(f"Required resource {name} is healthy")
        
        return results
    
    async def check_resource(self, name: str) -> ResourceStatus:
        """Check the health of a specific resource."""
        if name not in self.resources:
            raise ValueError(f"Unknown resource: {name}")
        
        config = self.config[name]
        
        try:
            if config.type == ResourceType.QDRANT:
                status = await self._check_qdrant(config)
            elif config.type == ResourceType.EXTERNAL_API:
                status = await self._check_external_api(config)
            elif config.type == ResourceType.DOCKER_CONTAINER:
                status = await self._check_docker_container(config)
            elif config.type == ResourceType.DATABASE:
                status = await self._check_database(config)
            else:
                status = ResourceStatus.UNKNOWN
            
            # Update resource status
            resource = self.resources[name]
            resource.status = status
            resource.last_check = datetime.now()
            resource.error_message = None
            
            return status
            
        except Exception as e:
            resource = self.resources[name]
            resource.status = ResourceStatus.UNAVAILABLE
            resource.last_check = datetime.now()
            resource.error_message = str(e)
            logger.error(f"Error checking resource {name}: {e}")
            return ResourceStatus.UNAVAILABLE
    
    # === Qdrant Management ===
    
    async def _check_qdrant(self, config: ResourceConfig) -> ResourceStatus:
        """Check Qdrant health."""
        if not QDRANT_AVAILABLE:
            logger.warning("Qdrant client library not installed")
            return ResourceStatus.UNKNOWN
            
        try:
            client = QdrantClient(
                host=config.config.get("host", "localhost"),
                port=config.config.get("port", 6333),
                timeout=5
            )
            # Try to get collections info
            collections = client.get_collections()
            logger.debug(f"Qdrant healthy - {len(collections.collections)} collections found")
            return ResourceStatus.HEALTHY
        except Exception as e:
            logger.debug(f"Qdrant health check failed: {e}")
            return ResourceStatus.UNAVAILABLE
    
    async def start_qdrant(self, config: ResourceConfig) -> bool:
        """Start Qdrant instance."""
        if not self.docker_client:
            logger.error("Docker not available - cannot start Qdrant")
            return False
        
        try:
            container_name = config.config.get("container_name", "biomapper-qdrant")
            
            try:
                container = self.docker_client.containers.get(container_name)
                if container.status != "running":
                    container.start()
                    logger.info(f"Started existing Qdrant container: {container_name}")
                else:
                    logger.info(f"Qdrant container already running: {container_name}")
                return True
            except NotFound:
                # Create new container
                logger.info(f"Creating new Qdrant container: {container_name}")
                container = self.docker_client.containers.run(
                    "qdrant/qdrant",
                    name=container_name,
                    ports={'6333/tcp': config.config.get("port", 6333)},
                    environment={
                        'QDRANT__SERVICE__HTTP_PORT': '6333',
                        'QDRANT__SERVICE__GRPC_PORT': '6334'
                    },
                    volumes={
                        'biomapper_qdrant_storage': {'bind': '/qdrant/storage', 'mode': 'rw'}
                    },
                    detach=True,
                    remove=False
                )
                logger.info(f"Created new Qdrant container: {container_name}")
                
                # Wait for healthy status
                for i in range(30):
                    await asyncio.sleep(1)
                    if await self._check_qdrant(config) == ResourceStatus.HEALTHY:
                        logger.info(f"Qdrant container is healthy after {i+1} seconds")
                        
                        # Initialize collections if needed
                        await self._initialize_qdrant_collections(config)
                        return True
                
                logger.error("Qdrant container failed to become healthy within 30 seconds")
                return False
                
        except Exception as e:
            logger.error(f"Failed to start Qdrant: {e}")
            return False
    
    async def _initialize_qdrant_collections(self, config: ResourceConfig):
        """Initialize Qdrant collections if they don't exist."""
        if not QDRANT_AVAILABLE:
            return
            
        try:
            client = QdrantClient(
                host=config.config.get("host", "localhost"),
                port=config.config.get("port", 6333)
            )
            
            collections_to_create = config.config.get("collections", [])
            existing_collections = {c.name for c in client.get_collections().collections}
            
            for collection_name in collections_to_create:
                if collection_name not in existing_collections:
                    # Create collection with default settings
                    client.create_collection(
                        collection_name=collection_name,
                        vectors_config=VectorParams(
                            size=384,  # Default for all-MiniLM-L6-v2
                            distance=Distance.COSINE
                        )
                    )
                    logger.info(f"Created Qdrant collection: {collection_name}")
                    
        except Exception as e:
            logger.error(f"Error initializing Qdrant collections: {e}")
    
    # === External API Management ===
    
    async def _check_external_api(self, config: ResourceConfig) -> ResourceStatus:
        """Check external API health."""
        url = config.config.get("health_endpoint")
        if not url:
            url = config.config.get("base_url")
        
        if not url:
            logger.warning(f"No URL configured for external API resource")
            return ResourceStatus.UNKNOWN
        
        try:
            timeout = config.config.get("timeout", 5)
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    timeout=aiohttp.ClientTimeout(total=timeout)
                ) as response:
                    if response.status == 200:
                        return ResourceStatus.HEALTHY
                    elif 500 <= response.status < 600:
                        return ResourceStatus.DEGRADED
                    else:
                        return ResourceStatus.UNAVAILABLE
        except asyncio.TimeoutError:
            logger.debug(f"API timeout for {url}")
            return ResourceStatus.DEGRADED
        except Exception as e:
            logger.debug(f"API check failed for {url}: {e}")
            return ResourceStatus.UNAVAILABLE
    
    # === Docker Container Management ===
    
    async def _check_docker_container(self, config: ResourceConfig) -> ResourceStatus:
        """Check Docker container health."""
        if not self.docker_client:
            return ResourceStatus.UNKNOWN
        
        try:
            container = self.docker_client.containers.get(
                config.config.get("container_name")
            )
            
            if container.status == "running":
                # Check container health if configured
                if container.attrs.get("State", {}).get("Health"):
                    health = container.attrs["State"]["Health"]["Status"]
                    if health == "healthy":
                        return ResourceStatus.HEALTHY
                    elif health == "unhealthy":
                        return ResourceStatus.DEGRADED
                return ResourceStatus.HEALTHY
            elif container.status == "restarting":
                return ResourceStatus.STARTING
            else:
                return ResourceStatus.UNAVAILABLE
                
        except NotFound:
            return ResourceStatus.UNAVAILABLE
        except Exception as e:
            logger.error(f"Docker check failed: {e}")
            return ResourceStatus.UNKNOWN
    
    async def start_docker_container(self, config: ResourceConfig) -> bool:
        """Start a Docker container."""
        if not self.docker_client:
            logger.error("Docker not available")
            return False
        
        try:
            container_name = config.config.get("container_name")
            
            try:
                container = self.docker_client.containers.get(container_name)
                if container.status != "running":
                    container.start()
                    logger.info(f"Started container: {container_name}")
                return True
            except NotFound:
                # Create new container
                image = config.config.get("image")
                port = config.config.get("port")
                
                if not image:
                    logger.error(f"No image specified for container {container_name}")
                    return False
                
                ports = {f'{port}/tcp': port} if port else None
                
                container = self.docker_client.containers.run(
                    image,
                    name=container_name,
                    ports=ports,
                    detach=True,
                    remove=False
                )
                logger.info(f"Created new container: {container_name}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to start container: {e}")
            return False
    
    # === Database Management ===
    
    async def _check_database(self, config: ResourceConfig) -> ResourceStatus:
        """Check database health."""
        # For now, we'll assume database is managed externally
        # This could be extended to check actual database connectivity
        return ResourceStatus.HEALTHY
    
    # === Resource Lifecycle ===
    
    async def start_resource(self, name: str) -> bool:
        """Start a resource."""
        if name not in self.resources:
            raise ValueError(f"Unknown resource: {name}")
        
        config = self.config[name]
        resource = self.resources[name]
        
        resource.status = ResourceStatus.STARTING
        
        try:
            if config.type == ResourceType.QDRANT:
                success = await self.start_qdrant(config)
            elif config.type == ResourceType.DOCKER_CONTAINER:
                success = await self.start_docker_container(config)
            else:
                logger.warning(f"Cannot auto-start resource type: {config.type}")
                success = False
            
            if success:
                # Verify the resource is actually healthy
                await asyncio.sleep(2)
                status = await self.check_resource(name)
                resource.status = status
            else:
                resource.status = ResourceStatus.UNAVAILABLE
                
            return success
            
        except Exception as e:
            resource.status = ResourceStatus.UNAVAILABLE
            resource.error_message = str(e)
            logger.error(f"Failed to start resource {name}: {e}")
            return False
    
    async def stop_resource(self, name: str) -> bool:
        """Stop a resource."""
        if name not in self.resources:
            raise ValueError(f"Unknown resource: {name}")
        
        config = self.config[name]
        resource = self.resources[name]
        
        resource.status = ResourceStatus.STOPPING
        
        try:
            if config.type == ResourceType.DOCKER_CONTAINER or config.type == ResourceType.QDRANT:
                container_name = config.config.get("container_name")
                if self.docker_client and container_name:
                    try:
                        container = self.docker_client.containers.get(container_name)
                        container.stop()
                        logger.info(f"Stopped container: {container_name}")
                        resource.status = ResourceStatus.UNAVAILABLE
                        return True
                    except NotFound:
                        logger.warning(f"Container not found: {container_name}")
                        resource.status = ResourceStatus.UNAVAILABLE
                        return True
            
            logger.warning(f"Cannot stop resource type: {config.type}")
            return False
            
        except Exception as e:
            logger.error(f"Failed to stop resource {name}: {e}")
            return False
    
    # === Monitoring ===
    
    async def _monitor_resource(self, name: str, config: ResourceConfig):
        """Monitor a resource health in background."""
        retry_count = 0
        
        while True:
            try:
                await asyncio.sleep(config.health_check_interval)
                
                status = await self.check_resource(name)
                resource = self.resources[name]
                
                # Handle status changes
                if status != resource.status:
                    old_status = resource.status
                    resource.status = status
                    resource.last_check = datetime.now()
                    
                    logger.info(f"Resource {name} status changed: {old_status} -> {status}")
                    
                    # Trigger recovery if needed
                    if status == ResourceStatus.UNAVAILABLE and config.auto_start:
                        retry_count += 1
                        if retry_count <= config.max_retries:
                            logger.warning(f"Resource {name} unavailable, attempting restart (retry {retry_count}/{config.max_retries})")
                            success = await self.start_resource(name)
                            if success:
                                retry_count = 0
                        else:
                            logger.error(f"Resource {name} failed after {config.max_retries} retries")
                    elif status == ResourceStatus.HEALTHY:
                        retry_count = 0
                    
            except asyncio.CancelledError:
                logger.info(f"Monitoring cancelled for resource: {name}")
                break
            except Exception as e:
                logger.error(f"Error monitoring resource {name}: {e}")
    
    async def get_resource_status(self) -> Dict[str, ManagedResource]:
        """Get current status of all resources."""
        return self.resources.copy()
    
    async def get_resource_requirements(self, strategy: Dict[str, Any]) -> List[str]:
        """
        Determine which resources are required for a strategy.
        """
        required = set()
        
        # Parse strategy to determine requirements
        for step in strategy.get("steps", []):
            action = step.get("action", {})
            action_type = action.get("type")
            
            # Check for vector-based actions that need Qdrant
            if action_type in ["VECTOR_ENHANCED_MATCH", "SEMANTIC_METABOLITE_MATCH"]:
                required.add("qdrant")
            
            # Check for CTS API actions
            if action_type in ["CTS_ENRICHED_MATCH", "METABOLITE_API_ENRICHMENT"]:
                required.add("cts_api")
            
            # Check for HMDB actions
            if "HMDB" in action_type:
                required.add("hmdb_api")
        
        # Always require database
        required.add("postgres")
        
        return list(required)
    
    async def cleanup(self):
        """Clean up resources and cancel monitoring tasks."""
        logger.info("Cleaning up resource manager")
        
        # Cancel all monitoring tasks
        for name, task in self.health_check_tasks.items():
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        self.health_check_tasks.clear()
        logger.info("Resource manager cleanup complete")