"""Initialization scripts for the resource metadata system."""

import logging
from typing import Dict, List, Optional

from biomapper.cache.manager import CacheManager
from biomapper.db.models_metadata import ResourceType, SupportLevel
from biomapper.metadata.manager import ResourceMetadataManager
from biomapper.spoke.client import SPOKEDBClient, SPOKEConfig
from biomapper.utils.config import Config


logger = logging.getLogger(__name__)


def register_default_resources(
    metadata_manager: Optional[ResourceMetadataManager] = None,
    config: Optional[Config] = None,
) -> Dict[str, str]:
    """Register default resources in the metadata system.
    
    Args:
        metadata_manager: Resource metadata manager
        config: Configuration object
        
    Returns:
        Dict mapping resource names to their types
    """
    if metadata_manager is None:
        metadata_manager = ResourceMetadataManager()
    
    if config is None:
        config = Config()
    
    registered_resources = {}
    
    # Register SQLite cache
    cache_config = config.get("cache", {})
    cache_data_dir = cache_config.get("data_dir")
    cache_db_name = cache_config.get("db_name")
    
    try:
        metadata_manager.register_resource(
            resource_name="sqlite_cache",
            resource_type=ResourceType.CACHE,
            connection_info={
                "data_dir": cache_data_dir,
                "db_name": cache_db_name,
            },
            priority=10,  # Highest priority
            is_active=True,
        )
        registered_resources["sqlite_cache"] = "cache"
        logger.info("Registered SQLite cache resource")
    except Exception as e:
        logger.error(f"Failed to register SQLite cache: {e}")
    
    # Register SPOKE knowledge graph
    spoke_config = config.get("spoke", {})
    spoke_host = spoke_config.get("host", "localhost")
    spoke_port = spoke_config.get("port", 8529)
    spoke_db = spoke_config.get("database", "spoke")
    spoke_username = spoke_config.get("username")
    spoke_password = spoke_config.get("password")
    
    try:
        metadata_manager.register_resource(
            resource_name="spoke_graph",
            resource_type=ResourceType.GRAPH,
            connection_info={
                "host": spoke_host,
                "port": spoke_port,
                "database": spoke_db,
                "username": spoke_username,
                "password": spoke_password,
            },
            priority=5,
            is_active=True,
        )
        registered_resources["spoke_graph"] = "graph"
        logger.info("Registered SPOKE graph resource")
    except Exception as e:
        logger.error(f"Failed to register SPOKE graph: {e}")
    
    # Register external API resources
    api_configs = config.get("api", {})
    
    for api_name, api_config in api_configs.items():
        try:
            metadata_manager.register_resource(
                resource_name=f"{api_name}_api",
                resource_type=ResourceType.API,
                connection_info=api_config,
                priority=1,  # Lowest priority
                is_active=True,
            )
            registered_resources[f"{api_name}_api"] = "api"
            logger.info(f"Registered {api_name} API resource")
        except Exception as e:
            logger.error(f"Failed to register {api_name} API: {e}")
    
    return registered_resources


def register_ontology_coverage(
    metadata_manager: Optional[ResourceMetadataManager] = None,
    ontology_coverage: Optional[Dict[str, List[Dict]]] = None,
) -> None:
    """Register default ontology coverage for resources.
    
    Args:
        metadata_manager: Resource metadata manager
        ontology_coverage: Dictionary of resource name to list of ontology coverages
    """
    if metadata_manager is None:
        metadata_manager = ResourceMetadataManager()
    
    if ontology_coverage is None:
        # Default ontology coverage
        ontology_coverage = {
            "sqlite_cache": [
                {"ontology_type": "chebi", "support_level": SupportLevel.FULL},
                {"ontology_type": "hmdb", "support_level": SupportLevel.FULL},
                {"ontology_type": "pubchem", "support_level": SupportLevel.FULL},
                {"ontology_type": "compound_name", "support_level": SupportLevel.FULL},
                {"ontology_type": "inchi", "support_level": SupportLevel.FULL},
                {"ontology_type": "inchikey", "support_level": SupportLevel.FULL},
                {"ontology_type": "smiles", "support_level": SupportLevel.FULL},
            ],
            "spoke_graph": [
                {"ontology_type": "chebi", "support_level": SupportLevel.PARTIAL},
                {"ontology_type": "hmdb", "support_level": SupportLevel.PARTIAL},
                {"ontology_type": "pubchem", "support_level": SupportLevel.PARTIAL},
                {"ontology_type": "uniprot", "support_level": SupportLevel.FULL},
                {"ontology_type": "ensembl", "support_level": SupportLevel.FULL},
                {"ontology_type": "mondo", "support_level": SupportLevel.FULL},
                {"ontology_type": "gene_symbol", "support_level": SupportLevel.FULL},
            ],
        }
    
    for resource_name, coverages in ontology_coverage.items():
        for coverage in coverages:
            try:
                metadata_manager.register_ontology_coverage(
                    resource_name=resource_name,
                    ontology_type=coverage["ontology_type"],
                    support_level=coverage["support_level"],
                    entity_count=coverage.get("entity_count"),
                )
                logger.info(
                    f"Registered {coverage['ontology_type']} coverage for {resource_name}"
                )
            except Exception as e:
                logger.error(
                    f"Failed to register {coverage['ontology_type']} "
                    f"coverage for {resource_name}: {e}"
                )


def initialize_metadata_system(
    config: Optional[Config] = None,
    force_init: bool = False,
) -> ResourceMetadataManager:
    """Initialize the resource metadata system.
    
    Args:
        config: Configuration object
        force_init: Whether to force initialization even if tables exist
        
    Returns:
        ResourceMetadataManager instance
    """
    if config is None:
        config = Config()
    
    # Initialize metadata manager
    metadata_config = config.get("metadata", {})
    data_dir = metadata_config.get("data_dir")
    db_name = metadata_config.get("db_name")
    
    metadata_manager = ResourceMetadataManager(data_dir=data_dir, db_name=db_name)
    
    # Check if resources already exist
    resources = metadata_manager.list_resources()
    
    if not resources or force_init:
        # Register default resources
        register_default_resources(metadata_manager, config)
        register_ontology_coverage(metadata_manager)
    
    return metadata_manager
