"""Central registry of all API clients and their methods."""

import logging
from typing import Dict, Any, List, Optional, Type
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class MethodSpec:
    """Specification for an API method."""
    
    name: str
    params: List[str]
    optional_params: List[str] = field(default_factory=list)
    returns: str = "Any"
    description: str = ""
    async_method: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "params": self.params,
            "optional_params": self.optional_params,
            "returns": self.returns,
            "description": self.description,
            "async": self.async_method
        }


@dataclass
class ClientSpec:
    """Specification for an API client."""
    
    name: str
    class_name: str
    module_path: str
    methods: Dict[str, MethodSpec]
    description: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "class": self.class_name,
            "module": self.module_path,
            "description": self.description,
            "methods": {
                name: method.to_dict() 
                for name, method in self.methods.items()
            }
        }


class APIClientRegistry:
    """Central registry of all API clients and their methods."""
    
    # Registry of known API clients
    _registry: Dict[str, ClientSpec] = {}
    
    # Pre-defined client specifications
    KNOWN_CLIENTS = {
        'uniprot': ClientSpec(
            name='uniprot',
            class_name='UniProtHistoricalResolverClient',
            module_path='biomapper.mapping.clients.uniprot_historical_resolver_client',
            description='Client for resolving UniProt identifiers including historical IDs',
            methods={
                'map_identifiers': MethodSpec(
                    name='map_identifiers',
                    params=['source_identifiers'],
                    optional_params=['target_ontology_type', 'mapping_params'],
                    returns='Dict[str, Any]',
                    description='Map protein identifiers to UniProt accessions',
                    async_method=True
                ),
                'resolve_batch': MethodSpec(
                    name='resolve_batch',
                    params=['protein_ids'],
                    optional_params=['include_metadata'],
                    returns='Dict[str, Any]',
                    description='Resolve a batch of protein IDs',
                    async_method=True
                ),
                '_fetch_uniprot_search_results': MethodSpec(
                    name='_fetch_uniprot_search_results',
                    params=['query'],
                    returns='Dict[str, Any]',
                    description='Execute search query against UniProt REST API',
                    async_method=True
                )
            }
        ),
        'chembl': ClientSpec(
            name='chembl',
            class_name='ChemblAPIClient',
            module_path='biomapper.mapping.clients.chembl_api_client',
            description='Client for ChEMBL compound database',
            methods={
                'search_compounds': MethodSpec(
                    name='search_compounds',
                    params=['query'],
                    optional_params=['limit', 'filters'],
                    returns='List[Dict[str, Any]]',
                    description='Search for compounds in ChEMBL'
                ),
                'get_compound_by_id': MethodSpec(
                    name='get_compound_by_id',
                    params=['chembl_id'],
                    returns='Dict[str, Any]',
                    description='Get compound details by ChEMBL ID'
                )
            }
        ),
        'pubchem': ClientSpec(
            name='pubchem',
            class_name='PubChemAPIClient',
            module_path='biomapper.mapping.clients.pubchem_api_client',
            description='Client for PubChem compound database',
            methods={
                'get_compound': MethodSpec(
                    name='get_compound',
                    params=['cid'],
                    optional_params=['namespace', 'domain'],
                    returns='Dict[str, Any]',
                    description='Get compound information by CID'
                ),
                'search_by_name': MethodSpec(
                    name='search_by_name',
                    params=['name'],
                    optional_params=['max_results'],
                    returns='List[Dict[str, Any]]',
                    description='Search compounds by name'
                )
            }
        ),
        'hmdb': ClientSpec(
            name='hmdb',
            class_name='HMDBAPIClient',
            module_path='biomapper.mapping.clients.hmdb_api_client',
            description='Client for Human Metabolome Database',
            methods={
                'get_metabolite': MethodSpec(
                    name='get_metabolite',
                    params=['hmdb_id'],
                    returns='Dict[str, Any]',
                    description='Get metabolite information by HMDB ID'
                ),
                'search_metabolites': MethodSpec(
                    name='search_metabolites',
                    params=['query'],
                    optional_params=['search_type', 'limit'],
                    returns='List[Dict[str, Any]]',
                    description='Search metabolites in HMDB'
                )
            }
        )
    }
    
    @classmethod
    def register_client(cls, client_spec: ClientSpec) -> None:
        """Register a new client specification."""
        cls._registry[client_spec.name] = client_spec
        logger.info(f"Registered API client: {client_spec.name}")
    
    @classmethod
    def get_client_spec(cls, client_name: str) -> Optional[ClientSpec]:
        """Get specification for a client."""
        # Check registry first
        if client_name in cls._registry:
            return cls._registry[client_name]
        
        # Check known clients
        if client_name in cls.KNOWN_CLIENTS:
            return cls.KNOWN_CLIENTS[client_name]
        
        return None
    
    @classmethod
    def validate_client(cls, client_name: str, client_instance: Any) -> Dict[str, bool]:
        """
        Validate client has all expected methods.
        
        Args:
            client_name: Name of the client type
            client_instance: Instance of the client
            
        Returns:
            Dict mapping method names to availability
            
        Raises:
            ValueError if client spec not found or validation fails
        """
        spec = cls.get_client_spec(client_name)
        if not spec:
            raise ValueError(
                f"Unknown client type: {client_name}. "
                f"Known clients: {list(cls.KNOWN_CLIENTS.keys()) + list(cls._registry.keys())}"
            )
        
        results = {}
        missing_methods = []
        
        for method_name, method_spec in spec.methods.items():
            if hasattr(client_instance, method_name):
                method = getattr(client_instance, method_name)
                if callable(method):
                    results[method_name] = True
                else:
                    results[method_name] = False
                    missing_methods.append(f"{method_name} (not callable)")
            else:
                results[method_name] = False
                missing_methods.append(method_name)
        
        if missing_methods:
            available = [
                m for m in dir(client_instance)
                if not m.startswith('_') and callable(getattr(client_instance, m, None))
            ]
            
            error_msg = (
                f"Client validation failed for {client_name}:\n"
                f"Missing methods: {missing_methods}\n"
                f"Available methods: {sorted(available)}"
            )
            
            # Check for method name changes
            suggestions = {}
            for missing in missing_methods:
                if isinstance(missing, str) and not missing.endswith("(not callable)"):
                    # Look for similar method names
                    for available_method in available:
                        if missing.lower() in available_method.lower():
                            if missing not in suggestions:
                                suggestions[missing] = []
                            suggestions[missing].append(available_method)
            
            if suggestions:
                error_msg += "\n\nPossible method name changes:"
                for old_name, new_names in suggestions.items():
                    error_msg += f"\n  {old_name} -> {new_names}"
            
            raise ValueError(error_msg)
        
        return results
    
    @classmethod
    def get_method_signature(
        cls, 
        client_name: str, 
        method_name: str
    ) -> Optional[MethodSpec]:
        """
        Get the expected signature for a client method.
        
        Args:
            client_name: Name of the client
            method_name: Name of the method
            
        Returns:
            MethodSpec if found, None otherwise
        """
        spec = cls.get_client_spec(client_name)
        if spec and method_name in spec.methods:
            return spec.methods[method_name]
        return None
    
    @classmethod
    def list_clients(cls) -> List[str]:
        """List all known client types."""
        return list(cls.KNOWN_CLIENTS.keys()) + list(cls._registry.keys())
    
    @classmethod
    def get_client_methods(cls, client_name: str) -> Optional[List[str]]:
        """Get list of methods for a client."""
        spec = cls.get_client_spec(client_name)
        if spec:
            return list(spec.methods.keys())
        return None
    
    @classmethod
    def generate_documentation(cls) -> str:
        """Generate markdown documentation for all registered clients."""
        doc_lines = ["# API Client Methods Reference\n"]
        
        all_clients = {**cls.KNOWN_CLIENTS, **cls._registry}
        
        for client_name, spec in sorted(all_clients.items()):
            doc_lines.append(f"\n## {spec.class_name}")
            doc_lines.append(f"**Location**: `{spec.module_path}`")
            
            if spec.description:
                doc_lines.append(f"\n{spec.description}")
            
            doc_lines.append("\n### Methods:")
            
            for method_name, method_spec in sorted(spec.methods.items()):
                # Method signature
                params_str = ", ".join(method_spec.params)
                if method_spec.optional_params:
                    optional_str = ", ".join(
                        f"{p}=None" for p in method_spec.optional_params
                    )
                    if params_str:
                        params_str += f", {optional_str}"
                    else:
                        params_str = optional_str
                
                async_prefix = "async " if method_spec.async_method else ""
                doc_lines.append(
                    f"\n- `{async_prefix}{method_name}({params_str}) -> {method_spec.returns}`"
                )
                
                if method_spec.description:
                    doc_lines.append(f"  - {method_spec.description}")
                
                # Parameter details
                if method_spec.params:
                    doc_lines.append("  - Required parameters:")
                    for param in method_spec.params:
                        doc_lines.append(f"    - `{param}`")
                
                if method_spec.optional_params:
                    doc_lines.append("  - Optional parameters:")
                    for param in method_spec.optional_params:
                        doc_lines.append(f"    - `{param}`")
        
        return "\n".join(doc_lines)