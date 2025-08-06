"""Resource configuration for biomapper API."""
import os
from typing import Dict
from ..services.resource_manager import ResourceConfig, ResourceType

# Get configuration from environment variables
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
POSTGRES_URL = os.getenv("DATABASE_URL", "postgresql://localhost/biomapper")
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

RESOURCE_CONFIGURATION: Dict[str, ResourceConfig] = {
    "qdrant": ResourceConfig(
        name="qdrant",
        type=ResourceType.QDRANT,
        required=False,  # Not all strategies need it
        auto_start=True,
        health_check_interval=30,
        config={
            "host": QDRANT_HOST,
            "port": QDRANT_PORT,
            "container_name": "biomapper-qdrant",
            "collections": ["metabolites", "proteins", "genes", "hmdb_metabolites"]
        }
    ),
    
    "cts_api": ResourceConfig(
        name="cts_api",
        type=ResourceType.EXTERNAL_API,
        required=False,
        auto_start=False,  # Can't start external API
        health_check_interval=60,
        config={
            "base_url": "https://cts.fiehnlab.ucdavis.edu",
            "health_endpoint": "https://cts.fiehnlab.ucdavis.edu/rest/status",
            "timeout": 30
        }
    ),
    
    "hmdb_api": ResourceConfig(
        name="hmdb_api",
        type=ResourceType.EXTERNAL_API,
        required=False,
        auto_start=False,
        health_check_interval=60,
        config={
            "base_url": "https://www.hmdb.ca",
            "health_endpoint": "https://www.hmdb.ca",
            "timeout": 30
        }
    ),
    
    "pubchem_api": ResourceConfig(
        name="pubchem_api",
        type=ResourceType.EXTERNAL_API,
        required=False,
        auto_start=False,
        health_check_interval=120,
        config={
            "base_url": "https://pubchem.ncbi.nlm.nih.gov",
            "health_endpoint": "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/1/property/MolecularFormula/JSON",
            "timeout": 10
        }
    ),
    
    "chemspider_api": ResourceConfig(
        name="chemspider_api",
        type=ResourceType.EXTERNAL_API,
        required=False,
        auto_start=False,
        health_check_interval=120,
        config={
            "base_url": "https://www.chemspider.com",
            "health_endpoint": "https://www.chemspider.com",
            "timeout": 10
        }
    ),
    
    "postgres": ResourceConfig(
        name="postgres",
        type=ResourceType.DATABASE,
        required=True,
        auto_start=False,  # Database should be managed externally
        health_check_interval=30,
        config={
            "connection_string": POSTGRES_URL,
            "pool_size": 10
        }
    ),
    
    "redis": ResourceConfig(
        name="redis",
        type=ResourceType.DOCKER_CONTAINER,
        required=False,
        auto_start=True,
        health_check_interval=30,
        config={
            "container_name": "biomapper-redis",
            "image": "redis:alpine",
            "host": REDIS_HOST,
            "port": REDIS_PORT
        }
    )
}