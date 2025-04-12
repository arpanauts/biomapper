#!/usr/bin/env python3
"""
Systematically check all resources and their property extraction configurations
against the actual APIs to verify that they work correctly.

This script can be run on a recurring basis to test the integrity of the metamapper database.
"""

import sqlite3
import json
import sys
import time
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import re
import importlib
import traceback
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("resource_verification.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("resource_verification")

# Sample IDs for testing each resource
SAMPLE_IDS = {
    "ChEBI": ["CHEBI:15377", "CHEBI:17303"],  # Glucose, Caffeine
    "PubChem": ["5793", "2519"],  # Caffeine, Glucose
    "KEGG": ["C00031", "C07481"],  # Glucose, Caffeine
    "UniChem": ["chembl:CHEMBL113", "hmdb:HMDB0001847"],  # Caffeine, Glucose
    "RefMet": ["REFMET:1", "REFMET:100"],  # Sample RefMet IDs
    "RaMP-DB": ["hmdb:HMDB0000122", "hmdb:HMDB0001847"],  # Caffeine, Glucose
    "MetabolitesCSV": ["1", "2"],  # Sample IDs from CSV (would need to be adjusted)
    "SPOKE": ["Caffeine", "Glucose"]  # Sample compound names
}

# Test search terms for name-based searches
SAMPLE_SEARCH_TERMS = [
    "glucose", 
    "caffeine", 
    "aspirin", 
    "cholesterol"
]

@dataclass
class ResourceVerification:
    """Class to track verification results for a resource."""
    resource_id: int
    resource_name: str
    client_type: str
    success: bool = False
    client_initialized: bool = False
    search_results: Dict[str, Any] = field(default_factory=dict)
    property_extractions: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    execution_time: float = 0.0

class ResourceVerifier:
    """Class to verify resources and their property extraction configurations."""
    
    def __init__(self, db_path: Path = None):
        """Initialize the resource verifier."""
        self.db_path = db_path or Path('data/metamapper.db')
        if not self.db_path.exists():
            raise FileNotFoundError(f"Database file {self.db_path} not found!")
            
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        
        self.results: Dict[int, ResourceVerification] = {}
        
    def get_all_resources(self) -> List[Dict[str, Any]]:
        """Get all resources from the database."""
        self.cursor.execute(
            """SELECT id, name, description, client_type, config, status 
               FROM resources 
               WHERE status = 'active'
               ORDER BY id"""
        )
        return [dict(row) for row in self.cursor.fetchall()]
    
    def get_property_configs(self, resource_id: int) -> List[Dict[str, Any]]:
        """Get property extraction configurations for a resource."""
        self.cursor.execute(
            """SELECT id, ontology_type, property_name, extraction_method, 
               extraction_pattern, result_type, transform_function, 
               priority, is_active, ns_prefix, ns_uri 
               FROM property_extraction_configs 
               WHERE resource_id = ? AND is_active = 1
               ORDER BY priority DESC""", 
            (resource_id,)
        )
        return [dict(row) for row in self.cursor.fetchall()]
    
    def initialize_client(self, resource: Dict[str, Any]) -> Any:
        """Initialize a client for the resource."""
        try:
            # Parse the configuration
            config_dict = json.loads(resource['config']) if resource['config'] else {}
            logger.info(f"Initializing client for {resource['name']} with config: {config_dict}")
            
            if resource['client_type'] == 'CSVClient':
                # Special handling for CSVClient
                from biomapper.mapping.clients.csv_client import CSVClient, CSVConfig
                # Filter out unknown parameters
                import inspect
                valid_params = set(inspect.signature(CSVConfig).parameters.keys())
                filtered_config = {k: v for k, v in config_dict.items() if k in valid_params}
                logger.info(f"Filtered config for {resource['name']}: {filtered_config}")
                config = CSVConfig(**filtered_config)
                return CSVClient(config)
            
            if resource['client_type'] == 'ArangoDBClient':
                # Special handling for ArangoDBClient
                from biomapper.mapping.clients.arangodb_client import ArangoDBClient, ArangoDBConfig
                import inspect
                valid_params = set(inspect.signature(ArangoDBConfig).parameters.keys())
                filtered_config = {k: v for k, v in config_dict.items() if k in valid_params}
                logger.info(f"Filtered config for {resource['name']}: {filtered_config}")
                config = ArangoDBConfig(**filtered_config)
                return ArangoDBClient(config)
            
            if resource['client_type'] == 'ChEBIClient':
                from biomapper.mapping.clients.chebi_client import ChEBIClient, ChEBIConfig
                import inspect
                valid_params = set(inspect.signature(ChEBIConfig).parameters.keys())
                filtered_config = {k: v for k, v in config_dict.items() if k in valid_params}
                logger.info(f"Filtered config for {resource['name']}: {filtered_config}")
                config = ChEBIConfig(**filtered_config)
                return ChEBIClient(config)
            
            if resource['client_type'] == 'PubChemClient':
                from biomapper.mapping.clients.pubchem_client import PubChemClient, PubChemConfig
                import inspect
                valid_params = set(inspect.signature(PubChemConfig).parameters.keys())
                filtered_config = {k: v for k, v in config_dict.items() if k in valid_params}
                logger.info(f"Filtered config for {resource['name']}: {filtered_config}")
                config = PubChemConfig(**filtered_config)
                return PubChemClient(config)
            
            if resource['client_type'] == 'KEGGClient':
                from biomapper.mapping.clients.kegg_client import KEGGClient, KEGGConfig
                import inspect
                valid_params = set(inspect.signature(KEGGConfig).parameters.keys())
                filtered_config = {k: v for k, v in config_dict.items() if k in valid_params}
                logger.info(f"Filtered config for {resource['name']}: {filtered_config}")
                config = KEGGConfig(**filtered_config)
                return KEGGClient(config)
            
            if resource['client_type'] == 'UniChemClient':
                from biomapper.mapping.clients.unichem_client import UniChemClient, UniChemConfig
                import inspect
                valid_params = set(inspect.signature(UniChemConfig).parameters.keys())
                filtered_config = {k: v for k, v in config_dict.items() if k in valid_params}
                logger.info(f"Filtered config for {resource['name']}: {filtered_config}")
                config = UniChemConfig(**filtered_config)
                return UniChemClient(config)
            
            if resource['client_type'] == 'RefMetClient':
                from biomapper.mapping.clients.refmet_client import RefMetClient, RefMetConfig
                import inspect
                valid_params = set(inspect.signature(RefMetConfig).parameters.keys())
                filtered_config = {k: v for k, v in config_dict.items() if k in valid_params}
                logger.info(f"Filtered config for {resource['name']}: {filtered_config}")
                config = RefMetConfig(**filtered_config)
                return RefMetClient(config)
            
            if resource['client_type'] == 'RaMPClient':
                from biomapper.standardization.ramp_client import RaMPClient, RaMPConfig
                import inspect
                valid_params = set(inspect.signature(RaMPConfig).parameters.keys())
                filtered_config = {k: v for k, v in config_dict.items() if k in valid_params}
                logger.info(f"Filtered config for {resource['name']}: {filtered_config}")
                config = RaMPConfig(**filtered_config)
                return RaMPClient(config)
            
            # Generic approach if none of the specific handlers match
            try:
                module_path = f"biomapper.mapping.clients.{resource['client_type'].lower()}"
                module = importlib.import_module(module_path)
            except ImportError:
                # Try standardization package if mapping.clients fails
                module_path = f"biomapper.standardization.{resource['client_type'].lower()}"
                module = importlib.import_module(module_path)
                
            # Get the client class
            client_class = getattr(module, resource['client_type'])
            
            # Get the config class
            config_class_name = resource['client_type'].replace('Client', 'Config')
            config_class = getattr(module, config_class_name)
            
            # Filter out unknown parameters
            import inspect
            valid_params = set(inspect.signature(config_class).parameters.keys())
            filtered_config = {k: v for k, v in config_dict.items() if k in valid_params}
            logger.info(f"Filtered config for {resource['name']}: {filtered_config}")
            
            # Create config and client instances
            config = config_class(**filtered_config)
            client = client_class(config)
            
            return client
            
        except Exception as e:
            logger.error(f"Error initializing client for {resource['name']}: {str(e)}")
            traceback.print_exc()
            return None
    
    def test_client_search(self, client: Any, resource_name: str) -> Dict[str, Any]:
        """Test a client's search functionality."""
        search_results = {}
        search_terms = SAMPLE_SEARCH_TERMS[:2]  # Limit to 2 terms to avoid rate limiting
        
        for term in search_terms:
            try:
                if resource_name == "ChEBI":
                    results = client.search_by_name(term)
                    search_results[term] = [r.to_dict() if hasattr(r, 'to_dict') else r for r in results] if results else []
                
                elif resource_name == "PubChem":
                    results = client.search_by_name(term)
                    search_results[term] = [r.to_dict() if hasattr(r, 'to_dict') else r for r in results] if results else []
                
                elif resource_name == "KEGG":
                    results = client.search_compound(term)
                    search_results[term] = results if results else []
                
                elif resource_name == "UniChem":
                    # UniChem doesn't have a direct name search - we'd need to search by structure
                    # For now, just record that this test was skipped
                    search_results[term] = {"message": "UniChem doesn't support direct name search"}
                
                elif resource_name == "RefMet":
                    results = client.search_by_name(term)
                    search_results[term] = results if results else []
                
                elif resource_name == "RaMP-DB":
                    # RaMP-DB doesn't have a direct name search in our client
                    # We could use pathway search or pathway by name
                    results = client.get_pathway_by_name(term)
                    search_results[term] = results if results else []
                
                elif resource_name == "MetabolitesCSV":
                    # Implementation would depend on CSV structure
                    search_results[term] = {"message": "CSV search implementation depends on structure"}
                
                elif resource_name == "SPOKE":
                    # SPOKE search would be ArangoDB specific
                    search_results[term] = {"message": "SPOKE search implementation is database-specific"}
                
                time.sleep(1)  # Wait a bit between searches to avoid rate limiting
                
            except Exception as e:
                search_results[term] = {"error": str(e)}
                logger.warning(f"Error searching {resource_name} for '{term}': {str(e)}")
        
        return search_results
    
    def test_client_get_by_id(self, client: Any, resource_name: str) -> Dict[str, Any]:
        """Test a client's get by ID functionality."""
        id_results = {}
        sample_ids = SAMPLE_IDS.get(resource_name, [])
        
        for id_value in sample_ids[:1]:  # Just test the first ID to avoid rate limiting
            try:
                if resource_name == "ChEBI":
                    result = client.get_entity_by_id(id_value.split(':')[-1])
                    if result:
                        if hasattr(result, 'to_dict'):
                            id_results[id_value] = result.to_dict()
                        else:
                            # Convert result to a JSON-serializable dict
                            id_results[id_value] = self._make_serializable(result)
                    else:
                        id_results[id_value] = None
                
                elif resource_name == "PubChem":
                    # PubChem uses get_entity_by_id, not get_compound_by_id
                    result = client.get_entity_by_id(id_value)
                    if result:
                        if hasattr(result, 'to_dict'):
                            id_results[id_value] = result.to_dict()
                        else:
                            # Convert result to a JSON-serializable dict
                            id_results[id_value] = self._make_serializable(result)
                    else:
                        id_results[id_value] = None
                
                elif resource_name == "KEGG":
                    result = client.get_entity_by_id(id_value)
                    if result:
                        if hasattr(result, 'to_dict'):
                            id_results[id_value] = result.to_dict()
                        else:
                            # Convert result to a JSON-serializable dict
                            id_results[id_value] = self._make_serializable(result)
                    else:
                        id_results[id_value] = None
                
                elif resource_name == "UniChem":
                    if ":" in id_value:
                        src_db, comp_id = id_value.split(":") 
                        result = client.get_compound_info_by_src_id(comp_id, src_db)
                        id_results[id_value] = self._make_serializable(result)
                    else:
                        id_results[id_value] = {"error": "ID must be in format src_db:id"}
                
                elif resource_name == "RefMet":
                    if id_value.startswith("REFMET:"):
                        result = client.get_entity_by_id(id_value.split(":")[-1])
                        id_results[id_value] = self._make_serializable(result)
                    else:
                        id_results[id_value] = {"error": "ID must be in format REFMET:id"}
                
                elif resource_name == "RaMP-DB":
                    # RaMP-DB has different functions depending on the type of ID
                    if id_value.startswith("hmdb:"):
                        # Example metabolite lookup
                        result = client.get_metabolite_info(id_value.split(":")[-1])
                        id_results[id_value] = self._make_serializable(result)
                    else:
                        id_results[id_value] = {"error": "ID must be in format hmdb:id"}
                
                elif resource_name == "MetabolitesCSV":
                    # Implementation would depend on CSV structure
                    id_results[id_value] = {"message": "CSV get_by_id implementation depends on structure"}
                
                elif resource_name == "SPOKE":
                    # SPOKE lookup would be ArangoDB specific
                    id_results[id_value] = {"message": "SPOKE get_by_id implementation is database-specific"}
                
                time.sleep(1)  # Wait a bit between retrievals to avoid rate limiting
                
            except Exception as e:
                id_results[id_value] = {"error": str(e)}
                logger.warning(f"Error getting {resource_name} entity by ID '{id_value}': {str(e)}")
        
        return id_results
        
    def _make_serializable(self, obj: Any) -> Any:
        """Convert an object to a JSON-serializable form."""
        if obj is None:
            return None
            
        if isinstance(obj, (str, int, float, bool)):
            return obj
            
        if isinstance(obj, (list, tuple)):
            return [self._make_serializable(item) for item in obj]
            
        if isinstance(obj, dict):
            return {str(k): self._make_serializable(v) for k, v in obj.items()}
            
        if hasattr(obj, 'to_dict') and callable(getattr(obj, 'to_dict')):
            return obj.to_dict()
            
        if hasattr(obj, '__dict__'):
            # For custom dataclasses or objects, extract the __dict__
            return {k: self._make_serializable(v) for k, v in obj.__dict__.items() 
                    if not k.startswith('_')}
        
        # For other objects, convert to string
        return str(obj)
    
    def extract_property(self, data: Any, config: Dict[str, Any]) -> Any:
        """Extract a property from data using the extraction configuration."""
        try:
            if not data:
                return None
                
            extraction_method = config['extraction_method']
            extraction_pattern = config['extraction_pattern']
            
            # Convert data to string for regex extraction
            if extraction_method == 'regex' and not isinstance(data, str):
                if isinstance(data, dict):
                    data = json.dumps(data)
                else:
                    data = str(data)
            
            if extraction_method == 'regex':
                match = re.search(extraction_pattern, data)
                if match:
                    result = match.group(1)
                else:
                    return None
                    
            elif extraction_method == 'json_path':
                import jsonpath_ng.ext as jsonpath
                
                jsonpath_expr = jsonpath.parse(extraction_pattern)
                matches = [match.value for match in jsonpath_expr.find(data)]
                
                if not matches:
                    return None
                
                result = matches[0] if len(matches) == 1 else matches
                
            elif extraction_method == 'xml_xpath_ns':
                # XML extraction is more complex and would need XML parsing libraries
                # For this verification, we'll skip XML extraction
                return {"message": "XML extraction verification not implemented"}
                
            else:
                return {"error": f"Unknown extraction method: {extraction_method}"}
            
            # Apply transform function if specified
            if config['transform_function'] and config['transform_function'] != 'None':
                transform_func = eval(config['transform_function'])
                result = transform_func(result)
            
            return result
            
        except Exception as e:
            logger.warning(f"Error extracting property {config['property_name']}: {str(e)}")
            return {"error": str(e)}
    
    def verify_resource(self, resource: Dict[str, Any]) -> ResourceVerification:
        """Verify a resource and its property extraction configurations."""
        resource_id = resource['id']
        resource_name = resource['name']
        
        start_time = time.time()
        
        result = ResourceVerification(
            resource_id=resource_id,
            resource_name=resource_name,
            client_type=resource['client_type']
        )
        
        logger.info(f"Verifying resource {resource_name} (ID: {resource_id})")
        
        try:
            # Initialize client
            client = self.initialize_client(resource)
            if not client:
                result.errors.append(f"Failed to initialize client for {resource_name}")
                return result
            
            result.client_initialized = True
            
            # Test search functionality
            result.search_results = self.test_client_search(client, resource_name)
            
            # Test get by ID functionality
            id_results = self.test_client_get_by_id(client, resource_name)
            result.search_results.update(id_results)
            
            # Check property extraction configurations
            configs = self.get_property_configs(resource_id)
            
            if not configs:
                result.errors.append(f"No property extraction configurations found for {resource_name}")
            else:
                # For each ID result, try to extract properties
                for id_key, data in id_results.items():
                    if not data or isinstance(data, dict) and "error" in data:
                        continue
                        
                    property_results = {}
                    
                    for config in configs:
                        property_name = config['property_name']
                        extracted_value = self.extract_property(data, config)
                        property_results[property_name] = {
                            "value": extracted_value,
                            "extraction_pattern": config['extraction_pattern'],
                            "extraction_method": config['extraction_method']
                        }
                    
                    result.property_extractions[id_key] = property_results
            
            result.success = True
            
        except Exception as e:
            error_msg = f"Error verifying resource {resource_name}: {str(e)}"
            logger.error(error_msg)
            result.errors.append(error_msg)
            traceback.print_exc()
            
        finally:
            result.execution_time = time.time() - start_time
            return result
    
    def verify_all_resources(self, parallel: bool = False) -> Dict[int, ResourceVerification]:
        """Verify all resources in the database."""
        resources = self.get_all_resources()
        logger.info(f"Found {len(resources)} active resources")
        
        if parallel:
            with ThreadPoolExecutor(max_workers=min(len(resources), 4)) as executor:
                future_to_resource = {executor.submit(self.verify_resource, resource): resource for resource in resources}
                for future in as_completed(future_to_resource):
                    resource = future_to_resource[future]
                    try:
                        result = future.result()
                        self.results[resource['id']] = result
                    except Exception as e:
                        logger.error(f"Error processing resource {resource['name']}: {str(e)}")
        else:
            for resource in resources:
                result = self.verify_resource(resource)
                self.results[resource['id']] = result
        
        return self.results
    
    def print_verification_report(self):
        """Print a report of the verification results."""
        if not self.results:
            print("No verification results available")
            return
            
        print("\n" + "="*80)
        print("Metamapper Resource Verification Report")
        print("="*80)
        
        total_resources = len(self.results)
        successful_resources = sum(1 for r in self.results.values() if r.success)
        
        print(f"\nResources Verified: {successful_resources}/{total_resources} successful")
        
        for resource_id, result in sorted(self.results.items()):
            print("\n" + "-"*80)
            status = "✅ SUCCESS" if result.success else "❌ FAILED"
            print(f"{status} - {result.resource_name} (ID: {result.resource_id}) - {result.client_type}")
            print(f"Execution Time: {result.execution_time:.2f} seconds")
            
            if not result.client_initialized:
                print("  Client Initialization: Failed")
            else:
                print("  Client Initialization: Successful")
            
            print("\n  Search Results:")
            for term, search_result in result.search_results.items():
                if isinstance(search_result, dict) and "error" in search_result:
                    print(f"    {term}: Error - {search_result['error']}")
                elif isinstance(search_result, dict) and "message" in search_result:
                    print(f"    {term}: {search_result['message']}")
                else:
                    status = "Found results" if search_result else "No results"
                    print(f"    {term}: {status}")
            
            if result.property_extractions:
                print("\n  Property Extractions:")
                for id_key, properties in result.property_extractions.items():
                    print(f"    Entity {id_key}:")
                    successful_extractions = 0
                    failed_extractions = 0
                    
                    for prop_name, extraction in properties.items():
                        value = extraction.get("value")
                        if value is None or isinstance(value, dict) and ("error" in value or "message" in value):
                            failed_extractions += 1
                        else:
                            successful_extractions += 1
                    
                    print(f"      {successful_extractions} successful, {failed_extractions} failed extractions")
            
            if result.errors:
                print("\n  Errors:")
                for error in result.errors:
                    print(f"    - {error}")
        
        print("\n" + "="*80)
        print(f"Verification Summary: {successful_resources}/{total_resources} resources verified successfully")
        print("="*80 + "\n")
    
    def save_verification_report(self, output_path: Path = None):
        """Save a detailed verification report to a JSON file."""
        if not self.results:
            logger.warning("No verification results available to save")
            return
            
        output_path = output_path or Path("metamapper_verification_report.json")
        
        # Convert results to serializable dict
        serializable_results = {}
        for resource_id, result in self.results.items():
            # Handle search_results - ensure they're serializable
            search_results = {}
            for key, value in result.search_results.items():
                search_results[key] = self._make_serializable(value)
            
            # Handle property_extractions - ensure they're serializable
            property_extractions = {}
            for id_key, extractions in result.property_extractions.items():
                property_extractions[id_key] = self._make_serializable(extractions)
            
            serializable_results[str(resource_id)] = {
                "resource_id": result.resource_id,
                "resource_name": result.resource_name,
                "client_type": result.client_type,
                "success": result.success,
                "client_initialized": result.client_initialized,
                "execution_time": result.execution_time,
                "errors": result.errors,
                "search_results": search_results,
                "property_extractions": property_extractions
            }
        
        # Add timestamp and summary
        report = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "summary": {
                "total_resources": len(self.results),
                "successful_resources": sum(1 for r in self.results.values() if r.success),
                "client_initialization_rate": sum(1 for r in self.results.values() if r.client_initialized) / len(self.results),
                "average_execution_time": sum(r.execution_time for r in self.results.values()) / len(self.results)
            },
            "results": serializable_results
        }
        
        try:
            with open(output_path, 'w') as f:
                json.dump(report, f, indent=2)
            logger.info(f"Saved verification report to {output_path}")
        except Exception as e:
            logger.error(f"Error saving verification report: {str(e)}")
    
    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Verify resources and property extraction configurations")
    parser.add_argument("--db", type=str, help="Path to the metamapper database file", default="data/metamapper.db")
    parser.add_argument("--parallel", action="store_true", help="Run verification in parallel")
    parser.add_argument("--resource", type=str, help="Verify a specific resource by name")
    parser.add_argument("--output", type=str, help="Output path for the verification report", default="metamapper_verification_report.json")
    args = parser.parse_args()
    
    try:
        verifier = ResourceVerifier(Path(args.db))
        
        if args.resource:
            # Verify a specific resource
            resources = verifier.get_all_resources()
            for resource in resources:
                if resource['name'].lower() == args.resource.lower():
                    result = verifier.verify_resource(resource)
                    verifier.results[resource['id']] = result
                    break
            else:
                logger.error(f"Resource '{args.resource}' not found")
        else:
            # Verify all resources
            verifier.verify_all_resources(args.parallel)
        
        # Print report
        verifier.print_verification_report()
        
        # Save detailed report
        verifier.save_verification_report(Path(args.output))
        
    except Exception as e:
        logger.error(f"Error verifying resources: {str(e)}")
        traceback.print_exc()
    
    finally:
        if 'verifier' in locals():
            verifier.close()
