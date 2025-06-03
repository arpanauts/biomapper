"""Script to populate the metamapper.db configuration database from YAML configuration files."""

import argparse
import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
import yaml

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import inspect

import biomapper.db.models
from biomapper.config import settings
from biomapper.db.models import (
    Ontology, MappingResource, MappingPath, MappingPathStep,
    OntologyPreference, EndpointRelationship, PropertyExtractionConfig,
    EndpointPropertyConfig, OntologyCoverage, Property, Endpoint,
    MappingSessionLog, RelationshipMappingPath, Base
)
from biomapper.db.session import get_db_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ConfigurationValidator:
    """Validates YAML configuration files before database population."""
    
    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
    
    def validate(self, config_data: Dict[str, Any], config_filename: str) -> bool:
        """Validate the entire configuration data."""
        self.errors = []
        self.warnings = []
        self.config_filename = config_filename

        # Basic structure validation
        required_top_level_keys = ['entity_type', 'version', 'ontologies', 'databases'] # 'mapping_paths' is optional
        for key in required_top_level_keys:
            if key not in config_data:
                self.errors.append(f"Missing required top-level key: '{key}'")
        
        if self.errors: # Stop if basic structure is wrong
            return False

        ontologies_data = config_data.get('ontologies', {})
        databases_data = config_data.get('databases', {})
        mapping_paths_data = config_data.get('mapping_paths', [])
        additional_resources_data = config_data.get('additional_resources', []) # Get additional_resources

        self._validate_ontologies(ontologies_data)
        self._validate_databases(databases_data, ontologies_data)
        # Pass additional_resources_data to _validate_mapping_paths
        self._validate_mapping_paths(mapping_paths_data, ontologies_data, databases_data, additional_resources_data)
        self._validate_additional_resources(additional_resources_data, ontologies_data)

        return len(self.errors) == 0
    
    def _validate_ontologies(self, ontologies: Dict[str, Any]):
        """Validate ontologies section."""
        # ontologies is guaranteed to be a dict by the caller config_data.get('ontologies', {})
        if not ontologies: # Handles case where 'ontologies' key is missing or its value is not a dict (caller passes {})
            self.errors.append("Ontologies section is empty or not a valid dictionary structure.")
            return
            
        primary_count = 0
        found_valid_ontology_entry = False
        for ont_name, ont_data in ontologies.items():
            if not isinstance(ont_data, dict):
                self.errors.append(
                    f"Ontology entry '{ont_name}' is not a dictionary (type: {type(ont_data).__name__}). Value: {str(ont_data)[:100]}"
                )
                continue # Skip this malformed entry for further checks
            
            found_valid_ontology_entry = True # At least one entry was a dict
            if ont_data.get('is_primary', False):
                primary_count += 1
        
        if not found_valid_ontology_entry and ontologies: 
             # Errors for malformed entries already logged.
             pass

        if found_valid_ontology_entry: # Only check primary count if there were valid entries to assess
            if primary_count == 0:
                self.errors.append("No primary identifier defined among valid ontologies.")
            elif primary_count > 1:
                self.errors.append("Multiple primary identifiers defined among valid ontologies.")
    
    def _validate_databases(self, databases: Dict[str, Any], ontologies: Dict[str, Any]):
        """Validate databases section."""
        # databases is guaranteed to be a dict by the caller config_data.get('databases', {})
        if not databases: # Handles case where 'databases' key is missing or its value is not a dict (caller passes {})
            self.warnings.append("Databases section is empty or not a valid dictionary structure.")
            return
            
        for db_name, db_config_value in databases.items():
            if not isinstance(db_config_value, dict):
                self.errors.append(
                    f"Database configuration for '{db_name}' is not a dictionary (type: {type(db_config_value).__name__}). Value: {str(db_config_value)[:100]}"
                )
                continue # Skip this malformed database entry for further validation

            db_config = db_config_value # Now we know db_config is a dict
            
            # Check endpoint configuration
            endpoint_config = db_config.get('endpoint', {})
            if not isinstance(endpoint_config, dict):
                self.errors.append(f"Database '{db_name}' has an 'endpoint' section that is not a dictionary (type: {type(endpoint_config).__name__}). Value: {str(endpoint_config)[:100]}")
            else:
                connection_details = endpoint_config.get('connection_details')
                if connection_details is None:
                    self.errors.append(f"Database '{db_name}', endpoint '{endpoint_config.get('name', 'N/A')}' is missing 'connection_details'.")
                elif not isinstance(connection_details, dict):
                    self.errors.append(f"Database '{db_name}', endpoint '{endpoint_config.get('name', 'N/A')}', has 'connection_details' that is not a dictionary (type: {type(connection_details).__name__}). Value: {str(connection_details)[:100]}")
                else:
                    # Validate file paths if present
                    if 'file_path' in connection_details or 'path' in connection_details:
                        file_path = connection_details.get('file_path') or connection_details.get('path')
                        resolved_path = self._resolve_path(file_path)
                        if resolved_path and not Path(resolved_path).exists():
                            self.warnings.append(f"File not found for database '{db_name}', endpoint '{endpoint_config.get('name', 'N/A')}': {resolved_path}")

            # Validate properties section
            properties_config = db_config.get('properties', {})
            if not isinstance(properties_config, dict):
                self.errors.append(f"Database '{db_name}' has a 'properties' section that is not a dictionary (type: {type(properties_config).__name__}). Value: {str(properties_config)[:100]}")
            else:
                primary_ontology_type = properties_config.get('primary')
                if primary_ontology_type and primary_ontology_type not in ontologies:
                    self.errors.append(f"Database '{db_name}', properties.primary, references undefined ontology '{primary_ontology_type}'.")
                
                mappings_data = properties_config.get('mappings', {})
                if not isinstance(mappings_data, dict):
                    self.errors.append(f"Database '{db_name}', properties section, has 'mappings' that is not a dictionary (type: {type(mappings_data).__name__}). Value: {str(mappings_data)[:100]}")
                else:
                    for mapping_name, mapping_details in mappings_data.items():
                        if not isinstance(mapping_details, dict):
                            self.errors.append(f"Database '{db_name}', properties.mappings entry '{mapping_name}' is not a dictionary (type: {type(mapping_details).__name__}). Value: {str(mapping_details)[:100]}")
                            continue
                        
                        ont_type = mapping_details.get('ontology_type')
                        if ont_type and ont_type not in ontologies:
                            self.errors.append(
                                f"Database '{db_name}', properties.mappings.{mapping_name}, references undefined ontology '{ont_type}'"
                            )
            
            # Validate mapping clients
            for client_entry in db_config.get('mapping_clients', []): 
                if not isinstance(client_entry, dict):
                    self.warnings.append(f"Item in mapping_clients for database '{db_name}' is not a dictionary: {client_entry}")
                    continue

                client_name = client_entry.get('name')
                if not client_name:
                    self.warnings.append(f"Client entry in database '{db_name}' is missing a 'name' key: {client_entry}")
                    # If name is crucial for further validation steps for this client, might 'continue' here.
                    # For now, we'll proceed, but error messages might be less specific if name is missing.

                input_onto = client_entry.get('input_ontology_type')
                output_onto = client_entry.get('output_ontology_type')
                
                actual_client_name_for_msg = client_name if client_name else "Unnamed client"

                if input_onto and input_onto not in ontologies:
                    self.errors.append(
                        f"Client '{actual_client_name_for_msg}' in database '{db_name}' uses undefined input ontology '{input_onto}'"
                    )
                if output_onto and output_onto not in ontologies:
                    self.errors.append(
                        f"Client '{actual_client_name_for_msg}' in database '{db_name}' uses undefined output ontology '{output_onto}'"
                    )
                
                # Validate client-specific config
                self._validate_client_config(client_name, client_entry.get('config', {}))
    
    def _validate_mapping_paths(self, paths: List[Dict[str, Any]], ontologies: Dict[str, Any], 
                           databases: Dict[str, Any], additional_resources: List[Dict[str, Any]]):
        """Validate mapping paths."""
        # Collect all client names from all databases
        all_clients = set()
        for db_name, db_config_content in databases.items(): # Iterate over each database's config
            if not isinstance(db_config_content, dict):
                # This case should ideally be caught by _validate_databases, but good to be defensive.
                self.warnings.append(f"Configuration for database '{db_name}' is not a dictionary in _validate_mapping_paths. Skipping its clients.")
                continue

            mapping_clients_list = db_config_content.get('mapping_clients', []) # Default to empty list
            
            if not isinstance(mapping_clients_list, list):
                # This case should also be caught by _validate_databases if a client config is malformed at the top level.
                self.warnings.append(f"Database '{db_name}' has a 'mapping_clients' section that is not a list (type: {type(mapping_clients_list).__name__}) in _validate_mapping_paths. Skipping its clients.")
                continue

            for client_entry in mapping_clients_list:
                if isinstance(client_entry, dict):
                    client_name = client_entry.get('name')
                    if client_name:
                        all_clients.add(client_name)
                else:
                    # Log a warning if a client entry itself is not a dictionary, as _validate_databases should have caught this.
                    self.warnings.append(f"Encountered a non-dictionary client entry in 'mapping_clients' for database '{db_name}' within _validate_mapping_paths: {str(client_entry)[:100]}")
        
        # Add clients from additional_resources
        if not isinstance(additional_resources, list):
            self.warnings.append(f"'additional_resources' section is not a list (type: {type(additional_resources).__name__}). Skipping these resources for path validation.")
        else:
            for res_entry in additional_resources:
                if isinstance(res_entry, dict):
                    res_name = res_entry.get('name')
                    if res_name:
                        all_clients.add(res_name)
                else:
                    self.warnings.append(f"Encountered a non-dictionary entry in 'additional_resources' within _validate_mapping_paths: {str(res_entry)[:100]}")

        for path in paths:
            # Check source and target types
            for field in ['source_type', 'target_type']:
                ont_type = path.get(field)
                if ont_type and ont_type not in ontologies:
                    self.errors.append(
                        f"Mapping path '{path.get('name')}' references "
                        f"undefined ontology '{ont_type}' in '{field}'"
                    )
            
            # Check steps reference valid resources
            for i, step in enumerate(path.get('steps', [])):
                resource = step.get('resource')
                if resource not in all_clients:
                    self.errors.append(
                        f"Step {i+1} in path '{path.get('name')}' references "
                        f"undefined resource '{resource}'"
                    )
    
    def _validate_additional_resources(self, additional_resources: List[Dict[str, Any]], ontologies: Dict[str, Any]):
        """Validate additional_resources section."""
        if not isinstance(additional_resources, list):
            self.warnings.append(f"Configuration section 'additional_resources' is not a list. Found type: {type(additional_resources).__name__}. Skipping validation of these resources.")
            return

        for i, resource_entry in enumerate(additional_resources):
            if not isinstance(resource_entry, dict):
                self.errors.append(f"Item at index {i} in 'additional_resources' is not a dictionary (type: {type(resource_entry).__name__}). Value: {str(resource_entry)[:100]}")
                continue
            
            client_name = resource_entry.get('name')
            if not client_name:
                self.errors.append(f"Item at index {i} in 'additional_resources' is missing a 'name'.")
                continue 

            if not resource_entry.get('client_class_path'):
                self.errors.append(f"Additional resource '{client_name}' (index {i}) is missing 'client_class_path'.")

            for ont_key in ['input_ontology_type', 'output_ontology_type']:
                ont_type = resource_entry.get(ont_key)
                if ont_type and ont_type not in ontologies:
                    self.errors.append(
                        f"Additional resource '{client_name}' (index {i}) uses undefined ontology '{ont_type}' for '{ont_key}'."
                    )
            
            # Validate client config (similar to _validate_client_config)
            self._validate_client_config(f"additional_resource '{client_name}' (index {i})", resource_entry.get('config', {}))
    
    def _validate_client_config(self, client_name: str, config: Any): # Changed type hint for flexibility
        """Validate client-specific configuration."""
        if not isinstance(config, dict):
            self.warnings.append(
                f"Client '{client_name}' has a 'config' section that is not a dictionary (type: {type(config).__name__}). Skipping config validation for this client."
            )
            return
        # For file-based clients, check required fields
        if any(key in config for key in ['file_path', 'path']):
            if 'key_column' not in config:
                self.errors.append(f"Client '{client_name}' missing 'key_column' in config")
            if 'value_column' not in config:
                self.errors.append(f"Client '{client_name}' missing 'value_column' in config")
            
            # Check file existence
            file_path = config.get('file_path') or config.get('path')
            if file_path:
                resolved_path = self._resolve_path(file_path)
                if resolved_path and not Path(resolved_path).exists():
                    self.warnings.append(f"File not found for client '{client_name}': {resolved_path}")
    
    def _resolve_path(self, path: str) -> Optional[str]:
        """Resolve environment variables in paths."""
        if not path:
            return None
        # Replace ${DATA_DIR} with actual path
        return path.replace('${DATA_DIR}', str(settings.data_dir))
    
    def get_report(self) -> str:
        """Get validation report."""
        report = []
        if self.errors:
            report.append("ERRORS:")
            report.extend(f"  - {err}" for err in self.errors)
        if self.warnings:
            report.append("WARNINGS:")
            report.extend(f"  - {warn}" for warn in self.warnings)
        return "\n".join(report) if report else "Validation passed"


async def delete_existing_db():
    """Deletes the existing database file if it exists."""
    db_url = settings.metamapper_db_url
    if not db_url.startswith("sqlite"):
        logger.warning(f"Database URL {db_url} is not SQLite. Skipping deletion.")
        return

    path_part = db_url.split("///", 1)[-1]
    if not path_part or path_part == db_url:
        logger.error(f"Could not extract file path from SQLite URL: {db_url}")
        return

    db_file_path = Path(path_part)
    if db_file_path.exists():
        logger.warning(f"Existing database found at {db_file_path}. Deleting...")
        try:
            db_file_path.unlink()
            logger.info("Existing database deleted successfully.")
        except OSError as e:
            logger.error(f"Error deleting database file {db_file_path}: {e}")
            raise
    else:
        logger.info(f"No existing database found at {db_file_path}. Proceeding.")


def resolve_environment_variables(data: Any) -> Any:
    """Recursively resolve environment variables in configuration data."""
    if isinstance(data, str):
        # Replace ${DATA_DIR} with actual path
        return data.replace('${DATA_DIR}', str(settings.data_dir))
    elif isinstance(data, dict):
        return {k: resolve_environment_variables(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [resolve_environment_variables(item) for item in data]
    return data


async def populate_ontologies(session: AsyncSession, ontologies_data: Dict[str, Any], 
                            entity_name: str) -> Dict[str, Ontology]:
    """Populate ontologies from configuration."""
    logger.info(f"Populating ontologies for {entity_name}...")
    ontology_objects = {}
    
    for ont_name, ont_config in ontologies_data.items():
        ontology = Ontology(
            name=ont_name,
            description=ont_config.get('description', ''),
            identifier_prefix=ont_config.get('prefix'),
            namespace_uri=ont_config.get('uri'),
            version=ont_config.get('version', '1.0')
        )
        session.add(ontology)
        ontology_objects[ont_name] = ontology
    
    await session.flush()
    
    # Create properties for each ontology
    for ont_name, ont_config in ontologies_data.items():
        ontology = ontology_objects[ont_name]
        property_obj = Property(
            name=ont_name,
            description=ont_config.get('description', ''),
            ontology_id=ontology.id,
            is_primary=ont_config.get('is_primary', False),
            data_type='string'
        )
        session.add(property_obj)
    
    await session.flush()
    return ontology_objects


async def populate_endpoints_and_properties(session: AsyncSession, databases_data: Dict[str, Any],
                                          entity_name: str, ontology_objects: Dict[str, Ontology]) -> Dict[str, Any]:
    """Populate endpoints and their property configurations."""
    logger.info(f"Populating endpoints and properties for {entity_name}...")
    
    endpoints = {}
    resources = {}
    prop_configs = []
    
    for db_name, db_config in databases_data.items():
        endpoint_config = db_config.get('endpoint', {})
        
        # Create endpoint
        endpoint = Endpoint(
            name=endpoint_config.get('name', db_name),
            description=endpoint_config.get('description', ''),
            type=endpoint_config.get('type'),
            connection_details=json.dumps(resolve_environment_variables(
                endpoint_config.get('connection_details', {})
            )),
            primary_property_name=endpoint_config.get('primary_property')
        )
        session.add(endpoint)
        endpoints[db_name] = endpoint
    
    await session.flush()
    
    # Create property extraction configs and endpoint property configs
    for db_name, db_config in databases_data.items():
        endpoint = endpoints[db_name] # Endpoint object, already has ID
        
        properties_section = db_config.get('properties', {})
        if not isinstance(properties_section, dict):
            logger.warning(f"Properties section for database '{db_name}' is not a dictionary. Skipping property configs for this database.")
            continue

        primary_ontology_for_db = properties_section.get('primary')
        mappings_dict = properties_section.get('mappings', {})

        if not isinstance(mappings_dict, dict):
            logger.warning(f"Mappings section for database '{db_name}' is not a dictionary. Skipping property configs for this database.")
            continue

        for mapping_key_name, mapping_details in mappings_dict.items():
            if not isinstance(mapping_details, dict):
                logger.warning(f"Details for mapping '{mapping_key_name}' in database '{db_name}' is not a dictionary. Skipping this mapping.")
                continue

            ontology_type_for_mapping = mapping_details.get('ontology_type')
            if not ontology_type_for_mapping:
                logger.warning(f"Mapping '{mapping_key_name}' in database '{db_name}' is missing 'ontology_type'. Skipping this mapping.")
                continue

            # Determine extraction pattern and method
            extraction_method = mapping_details.get('extraction_method', 'column')
            extraction_config_payload = {}
            if extraction_method == 'column':
                column_name = mapping_details.get('column')
                if column_name:
                    extraction_config_payload = {'column': column_name}
                else:
                    logger.warning(f"Mapping '{mapping_key_name}' in database '{db_name}' uses 'column' extraction method but is missing 'column' field. Skipping property extraction config.")
                    continue # Cannot create PEC without column for column method
            else:
                extraction_config_payload = mapping_details.get('extraction_config', {})
            
            # Create property extraction config
            extraction = PropertyExtractionConfig(
                resource_id=None, # This extraction is for an endpoint property, not a generic mapping resource
                ontology_type=ontology_type_for_mapping,
                property_name=mapping_key_name, # The key from the 'mappings' dictionary
                extraction_method=extraction_method,
                extraction_pattern=json.dumps(extraction_config_payload),
                result_type=mapping_details.get('result_type', 'string')
            )
            session.add(extraction)
            try:
                await session.flush() # Flush to get extraction.id
            except Exception as e:
                logger.error(f"Error flushing PropertyExtractionConfig for '{mapping_key_name}' in database '{db_name}': {e}. Skipping this property.")
                await session.rollback() # Rollback the failed flush
                continue
            
            # Create endpoint property config
            epc = EndpointPropertyConfig(
                endpoint_id=endpoint.id,
                property_name=mapping_key_name, # The key from the 'mappings' dictionary
                ontology_type=ontology_type_for_mapping,
                is_primary_identifier=(ontology_type_for_mapping == primary_ontology_for_db),
                property_extraction_config_id=extraction.id
            )
            session.add(epc)
    
    await session.flush()
    return {'endpoints': endpoints, 'resources': resources}


async def populate_mapping_resources(session: AsyncSession, databases_data: Dict[str, Any],
                                   additional_resources_data: List[Dict[str, Any]], 
                                   entity_name: str) -> Dict[str, MappingResource]:
    """Populate mapping resources from configuration."""
    logger.info(f"Populating mapping resources for {entity_name}...")
    resources = {}
    
    for db_name, db_config in databases_data.items():
        for client_entry in db_config.get('mapping_clients', []):
            if not isinstance(client_entry, dict):
                logger.warning(
                    f"Skipping non-dictionary item in mapping_clients for {db_name}: {client_entry}"
                )
                continue
            client_name = client_entry.get('name')
            if not client_name:
                logger.warning(
                    f"Skipping client entry in mapping_clients for {db_name} without 'name' key: {client_entry}"
                )
                continue
            
            client_config = client_entry
            
            resource = MappingResource(
                name=client_name,
                description=client_config.get('description', ''),
                resource_type=client_config.get('type', 'client'),
                client_class_path=client_config.get('class'),
                input_ontology_term=client_config.get('input_ontology_type'),
                output_ontology_term=client_config.get('output_ontology_type'),
                config_template=json.dumps(resolve_environment_variables(
                    client_config.get('config', {})
                ))
            )
            session.add(resource)
            resources[client_name] = resource

    # Process additional_resources
    if additional_resources_data:
        for res_entry in additional_resources_data:
            if not isinstance(res_entry, dict):
                logger.warning(
                    f"Skipping non-dictionary item in additional_resources: {res_entry}"
                )
                continue
            res_name = res_entry.get('name')
            if not res_name:
                logger.warning(
                    f"Skipping entry in additional_resources without 'name' key: {res_entry}"
                )
                continue

            # Ensure client_class_path is present, as it's key for a resource
            client_class_path = res_entry.get('client_class_path')
            if not client_class_path:
                logger.warning(f"Skipping additional resource '{res_name}' due to missing 'client_class_path'.")
                continue

            resource = MappingResource(
                name=res_name,
                description=res_entry.get('description', ''),
                resource_type=res_entry.get('type', 'client'), # Default to 'client'
                client_class_path=client_class_path,
                input_ontology_term=res_entry.get('input_ontology_type'),
                output_ontology_term=res_entry.get('output_ontology_type'),
                config_template=json.dumps(resolve_environment_variables(
                    res_entry.get('config', {})
                ))
            )
            session.add(resource)
            resources[res_name] = resource
    
    # Flush to get IDs for all resources
    await session.flush()
    
    # Now add ontology coverage with valid resource IDs
    for db_name, db_config in databases_data.items():
        for client_entry in db_config.get('mapping_clients', []):
            if not isinstance(client_entry, dict):
                # Already logged in the first loop, but good to be safe
                continue 
            client_name = client_entry.get('name')
            if not client_name or client_name not in resources:
                # Client might have been skipped or name missing
                logger.warning(f"Skipping ontology coverage for client '{client_name}' in {db_name} as it was not properly registered or name is missing.")
                continue

            resource = resources[client_name]
            input_ontology_type = client_entry.get('input_ontology_type')
            output_ontology_type = client_entry.get('output_ontology_type')

            if input_ontology_type and output_ontology_type:
                coverage = OntologyCoverage(
                    resource_id=resource.id,
                    source_type=input_ontology_type,
                    target_type=output_ontology_type,
                    support_level=client_entry.get('support_level', 'client_lookup')
                )
                session.add(coverage)

    # Add ontology coverage for additional_resources
    if additional_resources_data:
        for res_entry in additional_resources_data:
            if not isinstance(res_entry, dict):
                continue
            res_name = res_entry.get('name')
            # Check if resource was successfully registered (e.g. had client_class_path)
            if not res_name or res_name not in resources:
                logger.warning(f"Skipping ontology coverage for additional resource '{res_name}' as it was not properly registered or name is missing.")
                continue

            resource = resources[res_name]
            input_ontology_type = res_entry.get('input_ontology_type')
            output_ontology_type = res_entry.get('output_ontology_type')

            if input_ontology_type and output_ontology_type:
                coverage = OntologyCoverage(
                    resource_id=resource.id,
                    source_type=input_ontology_type,
                    target_type=output_ontology_type,
                    support_level=res_entry.get('support_level', 'client_lookup')
                )
                session.add(coverage)
    
    await session.flush()
    return resources


async def populate_mapping_paths(session: AsyncSession, paths_data: List[Dict[str, Any]],
                               entity_name: str, resources: Dict[str, MappingResource]):
    """Populate mapping paths from configuration."""
    logger.info(f"Populating mapping paths for {entity_name}...")
    
    for path_config in paths_data:
        path = MappingPath(
            name=path_config['name'],
            source_type=path_config['source_type'],
            target_type=path_config['target_type'],
            priority=path_config.get('priority', 10),
            description=path_config.get('description', ''),
            is_active=True
        )
        session.add(path)
        await session.flush()
        
        # Add steps
        for i, step_config in enumerate(path_config.get('steps', [])):
            resource_name = step_config['resource']
            if resource_name not in resources:
                logger.warning(f"Resource '{resource_name}' not found for path '{path.name}'")
                continue
                
            step = MappingPathStep(
                mapping_path_id=path.id,
                mapping_resource_id=resources[resource_name].id,
                step_order=i + 1,
                description=step_config.get('description', ''),
                config_override=step_config.get('config_override')
            )
            session.add(step)
    
    await session.flush()


async def populate_entity_type(session: AsyncSession, entity_name: str, config_data: Dict[str, Any]):
    """Populate all data for a single entity type from its configuration."""
    logger.info(f"Processing entity type: {entity_name}")
    
    # Populate ontologies
    ontology_objects = await populate_ontologies(
        session, config_data.get('ontologies', {}), entity_name
    )
    
    # Populate endpoints and properties
    db_objects = await populate_endpoints_and_properties(
        session, config_data.get('databases', {}), entity_name, ontology_objects
    )
    
    # Populate mapping resources
    resources = await populate_mapping_resources(
        session, 
        config_data.get('databases', {}), 
        config_data.get('additional_resources', []), 
        entity_name
    )
    
    # Populate mapping paths
    if 'mapping_paths' in config_data:
        await populate_mapping_paths(
            session, config_data['mapping_paths'], entity_name, resources
        )


async def populate_from_configs(session: AsyncSession):
    """Main function to populate database from YAML configuration files."""
    # Get project root from config file's parent parent directory
    project_root = Path(settings.data_dir).parent
    configs_dir = project_root / 'configs'
    
    if not configs_dir.exists():
        logger.warning(f"Configs directory not found at {configs_dir}")
        return
    
    # Find all YAML configuration files
    yaml_files = list(configs_dir.glob('*_config.yaml'))
    
    if not yaml_files:
        logger.warning(f"No configuration files found in {configs_dir}")
        return
    
    validator = ConfigurationValidator()
    any_errors_during_processing = False
    
    for yaml_file in sorted(yaml_files):
        logger.info(f"Processing configuration file: {yaml_file}")
        
        try:
            with open(yaml_file, 'r') as f:
                config_data = yaml.safe_load(f)

            if not isinstance(config_data, dict):
                logger.error(
                    f"Loaded content from {yaml_file} is not a dictionary (type: {type(config_data).__name__}). "
                    f"File might be malformed or empty. Skipping this file."
                )
                any_errors_during_processing = True
                continue
            
            # Validate configuration
            if not validator.validate(config_data, str(yaml_file)):
                logger.error(f"Validation failed for {yaml_file}:")
                logger.error(validator.get_report())
                continue
            
            # Show warnings if any
            if validator.warnings:
                logger.warning(f"Warnings for {yaml_file}:")
                for warning in validator.warnings:
                    logger.warning(f"  - {warning}")
            
            # Get entity name from config or filename
            entity_name = config_data.get('entity_type', yaml_file.stem.replace('_config', ''))
            
            # Populate this entity type
            await populate_entity_type(session, entity_name, config_data)
            
        except Exception as e:
            logger.error(f"Error processing {yaml_file}: {e}")
            logger.exception(f"Full traceback for error in {yaml_file}:")
            any_errors_during_processing = True
            continue
    
    if any_errors_during_processing:
        logger.error("Database population incomplete due to errors in one or more configuration files.")
        # Depending on desired behavior, one might choose to rollback here if any error occurred.
        # For now, we proceed to commit any data that was successfully processed from valid files.

    try:
        await session.commit()
        if not any_errors_during_processing:
            logger.info("Successfully populated database from configuration files.")
        else:
            logger.info("Partially populated database. Check logs for errors in specific configuration files.")
    except Exception as e:
        await session.rollback()
        logger.error(f"Error committing to database: {e}")
        raise


async def main(drop_all=False):
    """Main function to set up DB and populate data."""
    db_url = settings.metamapper_db_url
    logger.info(f"Target database URL: {db_url}")

    # Delete existing DB if requested
    if drop_all:
        await delete_existing_db()

    # Force re-instantiation of the default DatabaseManager
    logger.info("Initializing DatabaseManager...")
    manager = get_db_manager(db_url=db_url, echo=True)
    logger.info(f"Using DatabaseManager instance: {id(manager)} with URL: {manager.db_url}")

    # Initialize DB schema
    logger.info("Initializing database schema...")
    await manager.init_db_async(drop_all=True)
    logger.info("Database schema initialization completed.")

    # Get async session and populate from configs
    logger.info("Populating database from YAML configurations...")
    async with await manager.create_async_session() as session:
        logger.info(f"Successfully obtained async session: {id(session)}")
        await populate_from_configs(session)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Populate metamapper database from YAML configuration files"
    )
    parser.add_argument(
        "--drop-all", 
        action="store_true", 
        help="Drop existing database before creating new one"
    )
    args = parser.parse_args()
    
    asyncio.run(main(drop_all=args.drop_all))