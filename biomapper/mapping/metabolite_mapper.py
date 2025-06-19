"""
Enhanced metabolite name mapper module for Biomapper.

This module implements a comprehensive mapper for metabolite names and identifiers
that integrates with the Resource Metadata System to provide intelligent routing
of mapping operations across various resources.
"""

from typing import Dict, List, Any, Optional

from biomapper.mapping.base_mapper import AbstractEntityMapper


class MetaboliteNameMapper(AbstractEntityMapper):
    """
    Enhanced mapper for metabolite names and identifiers.

    This class provides methods for mapping metabolite names to standard
    identifiers like ChEBI, HMDB, PubChem, and more. It uses the Resource
    Metadata System to intelligently route mapping operations to the most
    appropriate resources.
    """

    def __init__(
        self, db_path: Optional[str] = None, config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the metabolite name mapper.

        Args:
            db_path: Path to metadata database (optional)
            config: Configuration options for resources (optional)
        """
        super().__init__("metabolite", db_path, config)

    async def _setup_entity_resources(self):
        """Setup metabolite-specific resources."""
        # ChEBI adapter
        try:
            chebi_config = self.config.get("chebi_api", {})
            from biomapper.mapping.adapters.chebi_adapter import ChEBIAdapter

            chebi_adapter = ChEBIAdapter(chebi_config, "chebi_api")
            await self.dispatcher.add_resource_adapter("chebi_api", chebi_adapter)
        except Exception as e:
            self.logger.warning(f"Failed to initialize ChEBI adapter: {e}")

        # HMDB adapter
        try:
            hmdb_config = self.config.get("hmdb_api", {})
            from biomapper.mapping.adapters.hmdb_adapter import HMDBAdapter

            hmdb_adapter = HMDBAdapter(hmdb_config, "hmdb_api")
            await self.dispatcher.add_resource_adapter("hmdb_api", hmdb_adapter)
        except Exception as e:
            self.logger.warning(f"Failed to initialize HMDB adapter: {e}")

        # PubChem adapter
        try:
            pubchem_config = self.config.get("pubchem_api", {})
            from biomapper.mapping.adapters.pubchem_adapter import PubChemAdapter

            pubchem_adapter = PubChemAdapter(pubchem_config, "pubchem_api")
            await self.dispatcher.add_resource_adapter("pubchem_api", pubchem_adapter)
        except Exception as e:
            self.logger.warning(f"Failed to initialize PubChem adapter: {e}")

        # RefMet adapter
        try:
            refmet_config = self.config.get("refmet_api", {})
            from biomapper.mapping.adapters.refmet_adapter import RefMetAdapter

            refmet_adapter = RefMetAdapter(refmet_config, "refmet_api")
            await self.dispatcher.add_resource_adapter("refmet_api", refmet_adapter)
        except Exception as e:
            self.logger.warning(f"Failed to initialize RefMet adapter: {e}")

        # UniChem adapter
        try:
            unichem_config = self.config.get("unichem_api", {})
            from biomapper.mapping.adapters.unichem_adapter import UniChemAdapter

            unichem_adapter = UniChemAdapter(unichem_config, "unichem_api")
            await self.dispatcher.add_resource_adapter("unichem_api", unichem_adapter)
        except Exception as e:
            self.logger.warning(f"Failed to initialize UniChem adapter: {e}")

        # LLM adapter if configured
        llm_config = self.config.get("llm_mapper")
        if llm_config:
            try:
                from biomapper.mapping.adapters.llm_adapter import LLMAdapter

                llm_adapter = LLMAdapter(llm_config, "llm_mapper")
                await self.dispatcher.add_resource_adapter("llm_mapper", llm_adapter)
            except Exception as e:
                self.logger.warning(f"Failed to initialize LLM adapter: {e}")

    # Metabolite-specific mapping methods

    async def map_name_to_chebi(
        self,
        name: str,
        confidence_threshold: float = 0.5,
        preferred_resource: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Map a metabolite name to ChEBI identifier.

        Args:
            name: Metabolite name
            confidence_threshold: Minimum confidence score (0-1)
            preferred_resource: Preferred resource to use (optional)

        Returns:
            List of mappings with ChEBI IDs and confidence scores
        """
        return await self.map_entity(
            source_id=name,
            source_type="metabolite_name",
            target_type="chebi",
            confidence_threshold=confidence_threshold,
            preferred_resource=preferred_resource,
        )

    async def map_name_to_hmdb(
        self,
        name: str,
        confidence_threshold: float = 0.5,
        preferred_resource: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Map a metabolite name to HMDB identifier.

        Args:
            name: Metabolite name
            confidence_threshold: Minimum confidence score (0-1)
            preferred_resource: Preferred resource to use (optional)

        Returns:
            List of mappings with HMDB IDs and confidence scores
        """
        return await self.map_entity(
            source_id=name,
            source_type="metabolite_name",
            target_type="hmdb",
            confidence_threshold=confidence_threshold,
            preferred_resource=preferred_resource,
        )

    async def map_name_to_pubchem(
        self,
        name: str,
        confidence_threshold: float = 0.5,
        preferred_resource: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Map a metabolite name to PubChem identifier.

        Args:
            name: Metabolite name
            confidence_threshold: Minimum confidence score (0-1)
            preferred_resource: Preferred resource to use (optional)

        Returns:
            List of mappings with PubChem IDs and confidence scores
        """
        return await self.map_entity(
            source_id=name,
            source_type="metabolite_name",
            target_type="pubchem",
            confidence_threshold=confidence_threshold,
            preferred_resource=preferred_resource,
        )

    async def map_chebi_to_hmdb(
        self,
        chebi_id: str,
        confidence_threshold: float = 0.5,
        preferred_resource: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Map a ChEBI identifier to HMDB identifier.

        Args:
            chebi_id: ChEBI identifier (e.g., "CHEBI:15377")
            confidence_threshold: Minimum confidence score (0-1)
            preferred_resource: Preferred resource to use (optional)

        Returns:
            List of mappings with HMDB IDs and confidence scores
        """
        return await self.map_entity(
            source_id=chebi_id,
            source_type="chebi",
            target_type="hmdb",
            confidence_threshold=confidence_threshold,
            preferred_resource=preferred_resource,
        )

    async def map_hmdb_to_pubchem(
        self,
        hmdb_id: str,
        confidence_threshold: float = 0.5,
        preferred_resource: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Map an HMDB identifier to PubChem identifier.

        Args:
            hmdb_id: HMDB identifier (e.g., "HMDB0000122")
            confidence_threshold: Minimum confidence score (0-1)
            preferred_resource: Preferred resource to use (optional)

        Returns:
            List of mappings with PubChem IDs and confidence scores
        """
        return await self.map_entity(
            source_id=hmdb_id,
            source_type="hmdb",
            target_type="pubchem",
            confidence_threshold=confidence_threshold,
            preferred_resource=preferred_resource,
        )

    async def batch_map_names(
        self,
        names: List[str],
        target_type: str = "chebi",
        confidence_threshold: float = 0.5,
        preferred_resource: Optional[str] = None,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Map multiple metabolite names in batch.

        Args:
            names: List of metabolite names
            target_type: Target identifier type (e.g., "chebi", "hmdb", "pubchem")
            confidence_threshold: Minimum confidence score (0-1)
            preferred_resource: Preferred resource to use (optional)

        Returns:
            Dictionary mapping names to lists of mapping results
        """
        return await self.batch_map_entities(
            source_ids=names,
            source_type="metabolite_name",
            target_type=target_type,
            confidence_threshold=confidence_threshold,
            preferred_resource=preferred_resource,
        )

    async def get_metabolite_metadata(
        self, identifier: str, id_type: str, preferred_resource: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get extended metadata for a metabolite.

        Args:
            identifier: Metabolite identifier
            id_type: Identifier type (e.g., "chebi", "hmdb", "pubchem")
            preferred_resource: Preferred resource to use (optional)

        Returns:
            Dictionary with metabolite metadata
        """
        # Ensure resources are initialized
        await self.initialize_resources()

        # Get metadata from all available resources
        results = []
        resources = self.dispatcher.get_resource_adapters()

        for resource_name, adapter in resources.items():
            if preferred_resource and resource_name != preferred_resource:
                continue

            try:
                metadata = await adapter.get_entity_metadata(identifier, id_type)
                if metadata:
                    metadata["source"] = resource_name
                    results.append(metadata)
            except Exception as e:
                self.logger.warning(f"Error getting metadata from {resource_name}: {e}")

        # Merge metadata from multiple sources
        if not results:
            return {}

        # Start with the most detailed metadata
        results.sort(key=lambda x: len(x), reverse=True)
        merged_metadata = results[0]

        # Add missing fields from other sources
        for result in results[1:]:
            for key, value in result.items():
                if key not in merged_metadata or not merged_metadata[key]:
                    merged_metadata[key] = value

        return merged_metadata

    # Synchronous wrapper methods for backwards compatibility

    def map_name_to_chebi_sync(
        self,
        name: str,
        confidence_threshold: float = 0.5,
        preferred_resource: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Synchronous wrapper for map_name_to_chebi."""
        return self.run_sync(
            self.map_name_to_chebi, name, confidence_threshold, preferred_resource
        )

    def map_name_to_hmdb_sync(
        self,
        name: str,
        confidence_threshold: float = 0.5,
        preferred_resource: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Synchronous wrapper for map_name_to_hmdb."""
        return self.run_sync(
            self.map_name_to_hmdb, name, confidence_threshold, preferred_resource
        )

    def map_name_to_pubchem_sync(
        self,
        name: str,
        confidence_threshold: float = 0.5,
        preferred_resource: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Synchronous wrapper for map_name_to_pubchem."""
        return self.run_sync(
            self.map_name_to_pubchem, name, confidence_threshold, preferred_resource
        )

    def batch_map_names_sync(
        self,
        names: List[str],
        target_type: str = "chebi",
        confidence_threshold: float = 0.5,
        preferred_resource: Optional[str] = None,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Synchronous wrapper for batch_map_names."""
        return self.run_sync(
            self.batch_map_names,
            names,
            target_type,
            confidence_threshold,
            preferred_resource,
        )
