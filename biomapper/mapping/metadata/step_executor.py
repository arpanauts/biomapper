"""Step executor for mapping operations."""

import json
import logging
from typing import Dict, List, Optional, Any, Union

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from biomapper.db.session import get_async_session
from biomapper.mapping.metadata.interfaces import StepExecutor, ResourceAdapter

logger = logging.getLogger(__name__)

class UniChemAdapter(ResourceAdapter):
    """Adapter for UniChem resource."""
    
    def __init__(self, connection_info: Dict[str, Any]):
        """Initialize the adapter with connection information.
        
        Args:
            connection_info: Dictionary with connection details.
        """
        self.base_url = connection_info.get("base_url", "https://www.ebi.ac.uk/unichem/")
        self.timeout_ms = connection_info.get("timeout_ms", 5000)
        
        # Source and target data source IDs for UniChem
        self.source_datasource_ids = {
            "chebi": "4",
            "chembl": "1",
            "drugbank": "2",
            "hmdb": "3",
            "kegg": "6",
            "pubchem": "22",
            "inchikey": "INCHIKEY",
            "cas": "29",
        }
    
    async def map_id(
        self,
        source_id: str,
        source_type: str,
        target_type: str,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """Map a source ID to target type using UniChem.
        
        Args:
            source_id: The source ID to map.
            source_type: The source ontology type.
            target_type: The target ontology type.
            **kwargs: Additional keyword arguments.
            
        Returns:
            List of mapping results.
        """
        # For demonstration purpose, simulating a limited subset of mappings
        # In a real implementation, this would make an HTTP request to UniChem API
        
        # Special handling for HMDB IDs - remove HMDB prefix if present
        if source_type.lower() == "hmdb" and source_id.startswith("HMDB"):
            source_id = source_id.replace("HMDB", "")
        
        # Sample mappings for testing
        sample_mappings = {
            ("hmdb", "pubchem"): [
                {"id": "5280343", "type": "pubchem", "confidence": 0.9},
            ],
            ("pubchem", "chebi"): [
                {"id": "CHEBI:16027", "type": "chebi", "confidence": 0.9},
            ],
            ("inchikey", "pubchem"): [
                {"id": "5280343", "type": "pubchem", "confidence": 0.9},
            ],
            ("kegg", "pubchem"): [
                {"id": "5280343", "type": "pubchem", "confidence": 0.85},
            ],
        }
        
        key = (source_type.lower(), target_type.lower())
        if key in sample_mappings:
            logger.info(f"UniChem mapping {source_id} from {source_type} to {target_type}")
            return sample_mappings[key]
        
        logger.warning(f"No UniChem mapping found for {source_id} from {source_type} to {target_type}")
        return []
    
    def get_supported_mappings(self) -> List[Dict[str, str]]:
        """Get supported mapping type combinations.
        
        Returns:
            List of dictionaries with source_type and target_type.
        """
        mappings = []
        for source in self.source_datasource_ids.keys():
            for target in self.source_datasource_ids.keys():
                if source != target:
                    mappings.append({
                        "source_type": source,
                        "target_type": target
                    })
        return mappings
    
    def get_resource_info(self) -> Dict[str, Any]:
        """Get information about the UniChem resource.
        
        Returns:
            Dictionary with resource details.
        """
        return {
            "name": "UniChem",
            "description": "Universal Chemical Identifier mapping service",
            "base_url": self.base_url,
            "timeout_ms": self.timeout_ms,
        }


class KEGGAdapter(ResourceAdapter):
    """Adapter for KEGG resource."""
    
    def __init__(self, connection_info: Dict[str, Any]):
        """Initialize the adapter with connection information.
        
        Args:
            connection_info: Dictionary with connection details.
        """
        self.base_url = connection_info.get("base_url", "https://rest.kegg.jp/")
        self.timeout_ms = connection_info.get("timeout_ms", 5000)
    
    async def map_id(
        self,
        source_id: str,
        source_type: str,
        target_type: str,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """Map a source ID to target type using KEGG.
        
        Args:
            source_id: The source ID to map.
            source_type: The source ontology type.
            target_type: The target ontology type.
            **kwargs: Additional keyword arguments.
            
        Returns:
            List of mapping results.
        """
        # For demonstration purpose, simulating a limited subset of mappings
        # In a real implementation, this would make an HTTP request to KEGG API
        
        # Sample mappings for testing
        sample_mappings = {
            ("hmdb", "kegg"): [
                {"id": "C00255", "type": "kegg", "confidence": 0.8},
            ],
            ("kegg", "pubchem"): [
                {"id": "5280343", "type": "pubchem", "confidence": 0.85},
            ],
            ("kegg", "chebi"): [
                {"id": "CHEBI:16027", "type": "chebi", "confidence": 0.8},
            ],
        }
        
        key = (source_type.lower(), target_type.lower())
        if key in sample_mappings:
            logger.info(f"KEGG mapping {source_id} from {source_type} to {target_type}")
            return sample_mappings[key]
        
        logger.warning(f"No KEGG mapping found for {source_id} from {source_type} to {target_type}")
        return []
    
    def get_supported_mappings(self) -> List[Dict[str, str]]:
        """Get supported mapping type combinations.
        
        Returns:
            List of dictionaries with source_type and target_type.
        """
        # Define the ontology types that KEGG can map between
        source_types = ["kegg", "hmdb"]
        target_types = ["kegg", "pubchem", "chebi"]
        
        mappings = []
        for source in source_types:
            for target in target_types:
                if source != target:
                    mappings.append({
                        "source_type": source,
                        "target_type": target
                    })
        return mappings
    
    def get_resource_info(self) -> Dict[str, Any]:
        """Get information about the KEGG resource.
        
        Returns:
            Dictionary with resource details.
        """
        return {
            "name": "KEGG",
            "description": "Kyoto Encyclopedia of Genes and Genomes",
            "base_url": self.base_url,
            "timeout_ms": self.timeout_ms,
        }


class StepExecutorImpl(StepExecutor):
    """Implementation of the StepExecutor interface."""
    
    def __init__(self, resource_adapters: Dict[str, ResourceAdapter]):
        """Initialize the step executor with resource adapters.
        
        Args:
            resource_adapters: Dictionary of resource name to adapter.
        """
        self.resource_adapters = resource_adapters
    
    async def execute_step(
        self,
        source_id: str,
        source_type: str,
        target_type: str,
        step_config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Execute a mapping step.
        
        Args:
            source_id: The source ID to map.
            source_type: The source ontology type.
            target_type: The target ontology type.
            step_config: Step configuration dictionary.
            
        Returns:
            List of mapping results.
        """
        resource_name = step_config.get("resource")
        if not resource_name:
            logger.error("No resource specified in step configuration")
            return []
        
        adapter = self.resource_adapters.get(resource_name.lower())
        if not adapter:
            logger.error(f"Resource adapter for {resource_name} not found")
            return []
        
        try:
            # Apply any transformations specified in step config
            processed_source_id = source_id
            if "transformations" in step_config:
                for transform in step_config["transformations"]:
                    if transform["type"] == "replace" and "from" in transform and "to" in transform:
                        processed_source_id = processed_source_id.replace(transform["from"], transform["to"])
            
            results = await adapter.map_id(
                processed_source_id,
                source_type,
                target_type,
                **step_config.get("options", {})
            )
            
            return results
            
        except Exception as e:
            logger.error(f"Error executing mapping step with {resource_name}: {e}")
            return []


class StepExecutorFactory:
    """Factory for creating step executors."""
    
    @staticmethod
    async def create_step_executor(db_session: Optional[AsyncSession] = None) -> StepExecutor:
        """Create a new step executor with resource adapters.
        
        Args:
            db_session: Optional database session to use for queries.
            
        Returns:
            A StepExecutor instance.
        """
        if db_session is None:
            db_session = await get_async_session()
        
        # Query available mapping resources
        query = """
            SELECT resource_id, name, resource_type, connection_info
            FROM mapping_resources
        """
        result = await db_session.execute(text(query))
        resources = result.fetchall()
        
        resource_adapters = {}
        
        for resource in resources:
            connection_info = {}
            if resource.connection_info:
                try:
                    connection_info = json.loads(resource.connection_info)
                except json.JSONDecodeError:
                    logger.warning(f"Failed to decode connection_info for resource {resource.name}")
            
            adapter = None
            if resource.name.lower() == "unichem":
                adapter = UniChemAdapter(connection_info)
            elif resource.name.lower() == "kegg":
                adapter = KEGGAdapter(connection_info)
            
            if adapter:
                resource_adapters[resource.name.lower()] = adapter
        
        # Create fallback adapters if needed
        if "unichem" not in resource_adapters:
            resource_adapters["unichem"] = UniChemAdapter({})
        
        if "kegg" not in resource_adapters:
            resource_adapters["kegg"] = KEGGAdapter({})
        
        return StepExecutorImpl(resource_adapters)