# Additional Entity Mapper Implementations

This document details the implementation plans for additional entity mappers built on the `AbstractEntityMapper` base class. These mappers extend the Resource Metadata System to handle different biological entity types.

## ProteinNameMapper

The `ProteinNameMapper` provides mapping functionality for protein names and identifiers across different nomenclature systems.

```python
class ProteinNameMapper(AbstractEntityMapper):
    """Mapper for protein names and identifiers."""
    
    def __init__(self, db_path=None, config=None):
        """Initialize the protein name mapper."""
        super().__init__("protein", db_path, config)
    
    async def _setup_entity_resources(self):
        """Setup protein-specific resources."""
        # UniProt adapter
        try:
            uniprot_config = self.config.get("uniprot_api", {})
            uniprot_adapter = UniProtAdapter(uniprot_config, "uniprot_api")
            await self.dispatcher.add_resource_adapter("uniprot_api", uniprot_adapter)
        except Exception as e:
            self.logger.warning(f"Failed to initialize UniProt adapter: {e}")
            
        # PDB adapter
        try:
            pdb_config = self.config.get("pdb_api", {})
            pdb_adapter = PDBAdapter(pdb_config, "pdb_api")
            await self.dispatcher.add_resource_adapter("pdb_api", pdb_adapter)
        except Exception as e:
            self.logger.warning(f"Failed to initialize PDB adapter: {e}")
            
        # InterPro adapter
        try:
            interpro_config = self.config.get("interpro_api", {})
            interpro_adapter = InterProAdapter(interpro_config, "interpro_api")
            await self.dispatcher.add_resource_adapter("interpro_api", interpro_adapter)
        except Exception as e:
            self.logger.warning(f"Failed to initialize InterPro adapter: {e}")
    
    async def map_name_to_uniprot(self, protein_name, organism="human", confidence_threshold=0.5):
        """
        Map a protein name to UniProt identifier.
        
        Args:
            protein_name: Protein name or gene symbol
            organism: Organism name or taxonomy ID
            confidence_threshold: Minimum confidence score
            
        Returns:
            List of mappings with UniProt IDs and confidence scores
        """
        return await self.map_entity(
            source_id=protein_name,
            source_type="protein_name",
            target_type="uniprot",
            confidence_threshold=confidence_threshold,
            organism=organism
        )
    
    async def map_uniprot_to_pdb(self, uniprot_id, confidence_threshold=0.5):
        """Map a UniProt ID to PDB structure identifiers."""
        return await self.map_entity(
            source_id=uniprot_id,
            source_type="uniprot",
            target_type="pdb",
            confidence_threshold=confidence_threshold
        )
    
    async def map_gene_to_protein(self, gene_symbol, organism="human", confidence_threshold=0.5):
        """Map a gene symbol to protein information."""
        return await self.map_entity(
            source_id=gene_symbol,
            source_type="gene_symbol",
            target_type="uniprot",
            confidence_threshold=confidence_threshold,
            organism=organism
        )
    
    # Synchronous wrappers for backward compatibility
    def map_name_to_uniprot_sync(self, protein_name, organism="human", confidence_threshold=0.5):
        """Synchronous wrapper for map_name_to_uniprot."""
        return self.run_sync(
            self.map_name_to_uniprot, 
            protein_name, 
            organism, 
            confidence_threshold
        )
```

### UniProtAdapter Implementation

The UniProt adapter connects the Resource Metadata System to UniProt's web services:

```python
class UniProtAdapter(BaseResourceAdapter):
    """Adapter for UniProt web services."""
    
    def __init__(self, config=None, name="uniprot_api"):
        """Initialize the UniProt adapter."""
        super().__init__(config or {}, name)
        from biomapper.mapping.clients.uniprot_client import UniProtClient
        self.client = UniProtClient(**config or {})
    
    async def connect(self):
        """Connect to the UniProt API."""
        # Most REST APIs don't require explicit connection
        return True
    
    async def map_entity(self, source_id, source_type, target_type, **kwargs):
        """Map entity using UniProt services."""
        organism = kwargs.get("organism", "human")
        
        if source_type == "protein_name" and target_type == "uniprot":
            # Search by protein name
            results = await self.client.search_protein(source_id, organism)
            return [
                {
                    "target_id": r.get("accession"),
                    "confidence": r.get("score", 0.9) / 100,  # Normalize to 0-1
                    "source": self.name,
                    "metadata": {
                        "entry_name": r.get("entry_name"),
                        "protein_name": r.get("protein_name"),
                        "gene_name": r.get("gene_name"),
                        "organism": r.get("organism")
                    }
                }
                for r in results if r.get("accession")
            ]
        
        elif source_type == "uniprot" and target_type == "pdb":
            # Get PDB structures for UniProt ID
            structures = await self.client.get_structures(source_id)
            return [
                {
                    "target_id": s.get("pdb_id"),
                    "confidence": 1.0,  # Direct mapping
                    "source": self.name,
                    "metadata": {
                        "method": s.get("method"),
                        "resolution": s.get("resolution"),
                        "chains": s.get("chains")
                    }
                }
                for s in structures if s.get("pdb_id")
            ]
        
        elif source_type == "gene_symbol" and target_type == "uniprot":
            # Map gene symbol to UniProt
            results = await self.client.search_gene(source_id, organism)
            return [
                {
                    "target_id": r.get("accession"),
                    "confidence": r.get("score", 0.9) / 100,
                    "source": self.name,
                    "metadata": {
                        "entry_name": r.get("entry_name"),
                        "protein_name": r.get("protein_name"),
                        "gene_name": r.get("gene_name"),
                        "organism": r.get("organism")
                    }
                }
                for r in results if r.get("accession")
            ]
        
        # Unsupported mapping type
        return []
```

## GeneMapper

The `GeneMapper` handles mappings between different gene identifier systems:

```python
class GeneMapper(AbstractEntityMapper):
    """Mapper for gene identifiers."""
    
    def __init__(self, db_path=None, config=None):
        """Initialize the gene mapper."""
        super().__init__("gene", db_path, config)
    
    async def _setup_entity_resources(self):
        """Setup gene-specific resources."""
        # NCBI Gene adapter
        try:
            ncbi_config = self.config.get("ncbi_gene_api", {})
            ncbi_adapter = NCBIGeneAdapter(ncbi_config, "ncbi_gene_api")
            await self.dispatcher.add_resource_adapter("ncbi_gene_api", ncbi_adapter)
        except Exception as e:
            self.logger.warning(f"Failed to initialize NCBI Gene adapter: {e}")
            
        # Ensembl adapter
        try:
            ensembl_config = self.config.get("ensembl_api", {})
            ensembl_adapter = EnsemblAdapter(ensembl_config, "ensembl_api")
            await self.dispatcher.add_resource_adapter("ensembl_api", ensembl_adapter)
        except Exception as e:
            self.logger.warning(f"Failed to initialize Ensembl adapter: {e}")
    
    async def map_symbol_to_entrez(self, gene_symbol, organism="human", confidence_threshold=0.5):
        """Map a gene symbol to Entrez Gene ID."""
        return await self.map_entity(
            source_id=gene_symbol,
            source_type="gene_symbol",
            target_type="entrez",
            confidence_threshold=confidence_threshold,
            organism=organism
        )
    
    async def map_entrez_to_ensembl(self, entrez_id, confidence_threshold=0.5):
        """Map an Entrez Gene ID to Ensembl ID."""
        return await self.map_entity(
            source_id=entrez_id,
            source_type="entrez",
            target_type="ensembl",
            confidence_threshold=confidence_threshold
        )
    
    async def map_symbol_to_hgnc(self, gene_symbol, confidence_threshold=0.5):
        """Map a gene symbol to HGNC ID."""
        return await self.map_entity(
            source_id=gene_symbol,
            source_type="gene_symbol",
            target_type="hgnc",
            confidence_threshold=confidence_threshold
        )
    
    async def batch_map_symbols(self, gene_symbols, target_type="entrez", organism="human", confidence_threshold=0.5):
        """Map multiple gene symbols in batch."""
        return await self.batch_map_entities(
            source_ids=gene_symbols,
            source_type="gene_symbol",
            target_type=target_type,
            confidence_threshold=confidence_threshold,
            organism=organism
        )
```

## DiseaseMapper

The `DiseaseMapper` handles mappings between different disease ontologies:

```python
class DiseaseMapper(AbstractEntityMapper):
    """Mapper for disease identifiers."""
    
    def __init__(self, db_path=None, config=None):
        """Initialize the disease mapper."""
        super().__init__("disease", db_path, config)
    
    async def _setup_entity_resources(self):
        """Setup disease-specific resources."""
        # MONDO adapter
        try:
            mondo_config = self.config.get("mondo_api", {})
            mondo_adapter = MONDOAdapter(mondo_config, "mondo_api")
            await self.dispatcher.add_resource_adapter("mondo_api", mondo_adapter)
        except Exception as e:
            self.logger.warning(f"Failed to initialize MONDO adapter: {e}")
            
        # DisGeNet adapter
        try:
            disgenet_config = self.config.get("disgenet_api", {})
            disgenet_adapter = DisGeNetAdapter(disgenet_config, "disgenet_api")
            await self.dispatcher.add_resource_adapter("disgenet_api", disgenet_adapter)
        except Exception as e:
            self.logger.warning(f"Failed to initialize DisGeNet adapter: {e}")
            
        # OMIM adapter
        try:
            omim_config = self.config.get("omim_api", {})
            omim_adapter = OMIMAdapter(omim_config, "omim_api")
            await self.dispatcher.add_resource_adapter("omim_api", omim_adapter)
        except Exception as e:
            self.logger.warning(f"Failed to initialize OMIM adapter: {e}")
    
    async def map_name_to_mondo(self, disease_name, confidence_threshold=0.5):
        """Map a disease name to MONDO ID."""
        return await self.map_entity(
            source_id=disease_name,
            source_type="disease_name",
            target_type="mondo",
            confidence_threshold=confidence_threshold
        )
    
    async def map_mondo_to_doid(self, mondo_id, confidence_threshold=0.5):
        """Map a MONDO ID to Disease Ontology ID."""
        return await self.map_entity(
            source_id=mondo_id,
            source_type="mondo",
            target_type="doid",
            confidence_threshold=confidence_threshold
        )
    
    async def map_name_to_mesh(self, disease_name, confidence_threshold=0.5):
        """Map a disease name to MeSH ID."""
        return await self.map_entity(
            source_id=disease_name,
            source_type="disease_name",
            target_type="mesh",
            confidence_threshold=confidence_threshold
        )
    
    async def get_disease_genes(self, disease_id, source_type="mondo", confidence_threshold=0.5):
        """Get genes associated with a disease."""
        return await self.map_entity(
            source_id=disease_id,
            source_type=source_type,
            target_type="gene_symbol",
            confidence_threshold=confidence_threshold
        )
```

## PathwayMapper

The `PathwayMapper` handles mappings for biological pathways:

```python
class PathwayMapper(AbstractEntityMapper):
    """Mapper for pathway identifiers."""
    
    def __init__(self, db_path=None, config=None):
        """Initialize the pathway mapper."""
        super().__init__("pathway", db_path, config)
    
    async def _setup_entity_resources(self):
        """Setup pathway-specific resources."""
        # Reactome adapter
        try:
            reactome_config = self.config.get("reactome_api", {})
            reactome_adapter = ReactomeAdapter(reactome_config, "reactome_api")
            await self.dispatcher.add_resource_adapter("reactome_api", reactome_adapter)
        except Exception as e:
            self.logger.warning(f"Failed to initialize Reactome adapter: {e}")
            
        # KEGG adapter
        try:
            kegg_config = self.config.get("kegg_api", {})
            kegg_adapter = KEGGAdapter(kegg_config, "kegg_api")
            await self.dispatcher.add_resource_adapter("kegg_api", kegg_adapter)
        except Exception as e:
            self.logger.warning(f"Failed to initialize KEGG adapter: {e}")
            
        # WikiPathways adapter
        try:
            wiki_config = self.config.get("wikipathways_api", {})
            wiki_adapter = WikiPathwaysAdapter(wiki_config, "wikipathways_api")
            await self.dispatcher.add_resource_adapter("wikipathways_api", wiki_adapter)
        except Exception as e:
            self.logger.warning(f"Failed to initialize WikiPathways adapter: {e}")
    
    async def map_name_to_reactome(self, pathway_name, organism="human", confidence_threshold=0.5):
        """Map a pathway name to Reactome ID."""
        return await self.map_entity(
            source_id=pathway_name,
            source_type="pathway_name",
            target_type="reactome",
            confidence_threshold=confidence_threshold,
            organism=organism
        )
    
    async def map_name_to_kegg(self, pathway_name, organism="human", confidence_threshold=0.5):
        """Map a pathway name to KEGG pathway ID."""
        return await self.map_entity(
            source_id=pathway_name,
            source_type="pathway_name",
            target_type="kegg",
            confidence_threshold=confidence_threshold,
            organism=organism
        )
    
    async def get_pathway_genes(self, pathway_id, source_type="reactome", confidence_threshold=0.5):
        """Get genes associated with a pathway."""
        return await self.map_entity(
            source_id=pathway_id,
            source_type=source_type,
            target_type="gene_symbol",
            confidence_threshold=confidence_threshold
        )
    
    async def get_pathway_metabolites(self, pathway_id, source_type="reactome", confidence_threshold=0.5):
        """Get metabolites associated with a pathway."""
        return await self.map_entity(
            source_id=pathway_id,
            source_type=source_type,
            target_type="chebi",
            confidence_threshold=confidence_threshold
        )
```

## Unified EntityMapper

The `EntityMapper` provides a central entry point for accessing all entity-specific mappers:

```python
class EntityMapper:
    """
    Unified mapper for all biological entity types.
    
    This class provides a single interface for mapping operations
    across different biological entity types.
    """
    
    def __init__(self, db_path=None, config=None):
        """
        Initialize the unified entity mapper.
        
        Args:
            db_path: Path to metadata database (optional)
            config: Configuration options for resources (optional)
        """
        self.config = config or {}
        self.db_path = db_path
        
        # Initialize entity-specific mappers
        self.metabolite_mapper = MetaboliteNameMapper(db_path, config)
        self.protein_mapper = ProteinNameMapper(db_path, config)
        self.gene_mapper = GeneMapper(db_path, config)
        self.disease_mapper = DiseaseMapper(db_path, config)
        self.pathway_mapper = PathwayMapper(db_path, config)
        
        # Create dispatcher for direct access
        self.metadata_manager = ResourceMetadataManager(db_path)
        self.dispatcher = MappingDispatcher(self.metadata_manager)
    
    async def map_entity(self, source_id, source_type, target_type, **kwargs):
        """
        Map any biological entity.
        
        This method routes the mapping operation to the appropriate
        specialized mapper based on the source and target types.
        
        Args:
            source_id: Source identifier
            source_type: Source ontology type
            target_type: Target ontology type
            **kwargs: Additional mapping parameters
            
        Returns:
            List of mapping results
        """
        # Route to the appropriate specialized mapper
        if source_type.startswith("metabolite") or source_type in ["chebi", "hmdb", "pubchem"] or \
           target_type in ["chebi", "hmdb", "pubchem"]:
            return await self.metabolite_mapper.map_entity(
                source_id, source_type, target_type, **kwargs
            )
            
        elif source_type.startswith("protein") or source_type in ["uniprot", "pdb"] or \
             target_type in ["uniprot", "pdb"]:
            return await self.protein_mapper.map_entity(
                source_id, source_type, target_type, **kwargs
            )
            
        elif source_type.startswith("gene") or source_type in ["entrez", "ensembl", "hgnc"] or \
             target_type in ["entrez", "ensembl", "hgnc"]:
            return await self.gene_mapper.map_entity(
                source_id, source_type, target_type, **kwargs
            )
            
        elif source_type.startswith("disease") or source_type in ["mondo", "doid", "mesh", "omim"] or \
             target_type in ["mondo", "doid", "mesh", "omim"]:
            return await self.disease_mapper.map_entity(
                source_id, source_type, target_type, **kwargs
            )
            
        elif source_type.startswith("pathway") or source_type in ["reactome", "kegg", "wikipathways"] or \
             target_type in ["reactome", "kegg", "wikipathways"]:
            return await self.pathway_mapper.map_entity(
                source_id, source_type, target_type, **kwargs
            )
            
        # Default to direct mapping
        await self.metadata_manager.connect()
        return await self.dispatcher.map_entity(
            source_id, source_type, target_type, **kwargs
        )
    
    # Synchronous wrapper for ease of use
    def map(self, source_id, source_type, target_type, **kwargs):
        """Synchronous wrapper for map_entity."""
        import asyncio
        return asyncio.run(self.map_entity(source_id, source_type, target_type, **kwargs))
```

## Integration with SPOKE and Hybrid Architecture

These mappers integrate with the existing hybrid architecture that combines SPOKE Knowledge Graph, Extension Graph, and SQL-based Mapping Cache:

1. **SPOKE Integration**: Each mapper automatically uses SPOKE when available through the `SpokeResourceAdapter`
2. **SQL Cache**: All mapping results are cached in the SQLite database for faster future access
3. **Extension Graph**: The resource adapters can connect to the Extension Graph for additional mappings
4. **Resource Prioritization**: The metadata system automatically prioritizes resources based on performance

The Resource Metadata System creates a unified layer that coordinates access to all these components, ensuring that:

1. The fastest resource is tried first
2. Unavailable resources don't block operations
3. New mappings are automatically added to the cache
4. Performance is continuously monitored and optimized

## Implementation Strategy

For an efficient implementation of these mappers:

1. Start with the `AbstractEntityMapper` base class
2. Implement the `CacheResourceAdapter` and `SpokeResourceAdapter`
3. Develop the `MetaboliteNameMapper` as the first concrete mapper
4. Gradually add other mappers in order of priority
5. Create adapters for external APIs as needed
6. Implement the unified `EntityMapper` last

This approach allows for incremental development and testing, with each component building on the previous ones.
