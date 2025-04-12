#!/usr/bin/env python3
"""
Enhance UniChem property extraction configurations in the metamapper database.

This script:
1. Adds additional property extraction patterns for more UniChem sources
2. Tests the enhanced property extraction patterns
3. Updates the UniChem client SOURCE_IDS mapping

According to UniChem database documentation, there are 25+ source databases available.
We'll focus on high-value metabolite identifiers to expand mapping capabilities.
"""

import sqlite3
import sys
import json
import requests
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("unichem_enhancement")

# Get database path
db_path = Path('data/metamapper.db')
if not db_path.exists():
    logger.error(f"Database file {db_path} not found!")
    sys.exit(1)

logger.info(f"Using database at {db_path}")

# Connect to the database
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row  # Return rows as dictionaries
cursor = conn.cursor()

# UniChem REST API URL
UNICHEM_API_URL = "https://www.ebi.ac.uk/unichem/rest"

# Additional UniChem sources to add (based on UniChem documentation)
# Source database name to UniChem source ID mapping
ADDITIONAL_SOURCES = {
    "lipidmaps": 18,     # LIPID MAPS
    "zinc": 19,          # ZINC database
    "chemspider": 10,    # ChemSpider
    "atlas": 29,         # Atlas Chemical Database
    "gtopdb": 21,        # Guide to Pharmacology
    "emolecules": 38,    # eMolecules
    "cas": 9,            # CAS Registry Numbers
    "bindingdb": 25,     # BindingDB
    "molport": 33,       # MolPort
    "comptox": 46,       # EPA CompTox
    "brenda": 12,        # BRENDA Database
    "metabolights": 39,  # MetaboLights
    "selleck": 37        # Selleck Chemicals
}

# Property configs to add for each source
def create_property_configs(resource_id: int) -> List[Dict[str, Any]]:
    """
    Create property extraction configurations for additional UniChem sources.
    
    Args:
        resource_id: The ID of the UniChem resource in the database
        
    Returns:
        List of property extraction config dictionaries
    """
    configs = []
    
    for source_name, source_id in ADDITIONAL_SOURCES.items():
        # Create property extraction config for this source
        configs.append({
            "resource_id": resource_id,
            "ontology_type": "ID",
            "property_name": f"{source_name}_ids",
            "extraction_method": "json_path",
            "extraction_pattern": f"$.{source_name}_ids",
            "result_type": "list",
            "transform_function": None,
            "priority": 2,  # Medium priority
            "is_active": True,
            "ns_prefix": source_name,
            "ns_uri": f"https://www.ebi.ac.uk/unichem/rest/src_compound_id/{source_id}/",
            "entity_type": "metabolite"
        })
    
    return configs

def get_unichem_source_info() -> List[Dict[str, Any]]:
    """
    Get the current list of sources from UniChem API.
    
    Returns:
        List of source information dictionaries
    """
    try:
        response = requests.get(f"{UNICHEM_API_URL}/sources", timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Failed to fetch UniChem sources: {e}")
        return []

def test_property_extraction(resource_id: int, property_name: str) -> bool:
    """
    Test a property extraction configuration to ensure it works properly.
    
    Args:
        resource_id: The resource ID
        property_name: The property name to test
        
    Returns:
        True if extraction was successful, False otherwise
    """
    from biomapper.mapping.clients.unichem_client import UniChemClient
    
    try:
        # Use ChEMBL ID for caffeine as test compound
        test_compound_id = "CHEMBL113"
        client = UniChemClient()
        
        # Get compound info using the client
        result = client.get_compound_info_by_src_id(test_compound_id, "chembl")
        
        # Check if our property is in the result
        if property_name in result and result[property_name]:
            logger.info(f"Successfully extracted {property_name}: {result[property_name]}")
            return True
        else:
            logger.warning(f"Property {property_name} not found in test extraction")
            return False
            
    except Exception as e:
        logger.error(f"Error testing property extraction for {property_name}: {e}")
        return False

def update_unichem_client_sources():
    """
    Update the UniChem client SOURCE_IDS mapping to include new sources.
    Creates a backup of the original file before making changes.
    """
    unichem_client_path = Path('biomapper/mapping/clients/unichem_client.py')
    
    if not unichem_client_path.exists():
        logger.error(f"UniChem client file not found at {unichem_client_path}")
        return False
    
    # Create backup
    backup_path = unichem_client_path.with_suffix('.py.bak')
    with open(unichem_client_path, 'r') as src:
        with open(backup_path, 'w') as dst:
            dst.write(src.read())
    
    logger.info(f"Created backup of UniChem client at {backup_path}")
    
    # Read the file
    with open(unichem_client_path, 'r') as f:
        content = f.read()
    
    # Find the SOURCE_IDS dictionary
    source_ids_start = content.find("self.SOURCE_IDS = {")
    if source_ids_start == -1:
        logger.error("Could not find SOURCE_IDS dictionary in UniChem client")
        return False
    
    # Find the end of the dictionary
    source_ids_end = content.find("}", source_ids_start)
    if source_ids_end == -1:
        logger.error("Could not find end of SOURCE_IDS dictionary")
        return False
    
    # Extract the current dictionary content
    current_dict = content[source_ids_start:source_ids_end+1]
    
    # Build the new dictionary content
    new_sources_entries = []
    for source_name, source_id in ADDITIONAL_SOURCES.items():
        new_sources_entries.append(f'            "{source_name}": {source_id},')
    
    # Insert new entries before the closing brace
    new_dict = current_dict.replace("}", ",\n" + "\n".join(new_sources_entries) + "\n            }")
    
    # Replace the old dictionary with the new one
    new_content = content.replace(current_dict, new_dict)
    
    # Update the _process_compound_result method to handle new sources
    process_result_start = new_content.find("def _process_compound_result")
    if process_result_start == -1:
        logger.error("Could not find _process_compound_result method")
        return False
    
    # Find the method body
    method_body_start = new_content.find(":", process_result_start)
    if method_body_start == -1:
        logger.error("Could not find _process_compound_result method body")
        return False
    
    # Find the result initialization
    result_init_start = new_content.find("result = self._get_empty_result()", method_body_start)
    if result_init_start == -1:
        logger.error("Could not find result initialization in _process_compound_result method")
        return False
    
    # Find the end of the method body
    next_def = new_content.find("def ", method_body_start + 1)
    if next_def == -1:
        logger.error("Could not find end of _process_compound_result method")
        return False
    
    # Extract the current method body
    current_method_body = new_content[method_body_start+1:next_def]
    
    # Modify the _get_empty_result method to include new sources
    empty_result_start = new_content.find("def _get_empty_result")
    if empty_result_start == -1:
        logger.error("Could not find _get_empty_result method")
        return False
    
    empty_result_body_start = new_content.find(":", empty_result_start)
    if empty_result_body_start == -1:
        logger.error("Could not find _get_empty_result method body")
        return False
    
    empty_result_return_start = new_content.find("return {", empty_result_body_start)
    if empty_result_return_start == -1:
        logger.error("Could not find return statement in _get_empty_result method")
        return False
    
    empty_result_return_end = new_content.find("}", empty_result_return_start)
    if empty_result_return_end == -1:
        logger.error("Could not find end of return statement in _get_empty_result method")
        return False
    
    # Extract the current return statement
    current_empty_result = new_content[empty_result_return_start:empty_result_return_end+1]
    
    # Build the new return statement
    new_empty_result_entries = []
    for source_name in ADDITIONAL_SOURCES.keys():
        new_empty_result_entries.append(f'            "{source_name}_ids": [],')
    
    # Insert new entries before the closing brace
    new_empty_result = current_empty_result.replace("}", ",\n" + "\n".join(new_empty_result_entries) + "\n        }")
    
    # Replace the old return statement with the new one
    new_content = new_content.replace(current_empty_result, new_empty_result)
    
    # Now add handling for new sources in the _process_compound_result method
    source_handling_entries = []
    for source_name, source_id in ADDITIONAL_SOURCES.items():
        source_handling_entries.append(f"""            elif src_id == {source_id}:
                result["{source_name}_ids"].append(compound_id)""")
    
    # Find a good insertion point before the return statement
    insertion_point = current_method_body.rfind("return result")
    if insertion_point == -1:
        logger.error("Could not find return statement in _process_compound_result method")
        return False
    
    # Build the new method body with added source handling
    new_method_body = current_method_body[:insertion_point] + "\n" + "\n".join(source_handling_entries) + "\n        " + current_method_body[insertion_point:]
    
    # Replace the old method body with the new one
    new_content = new_content.replace(current_method_body, new_method_body)
    
    # Write the updated content back to the file
    with open(unichem_client_path, 'w') as f:
        f.write(new_content)
    
    logger.info(f"Updated UniChem client with {len(ADDITIONAL_SOURCES)} new sources")
    return True

try:
    # Get the UniChem resource ID
    cursor.execute("SELECT id FROM resources WHERE name = 'UniChem'")
    result = cursor.fetchone()
    
    if not result:
        logger.error("UniChem resource not found in the database")
        sys.exit(1)
    
    unichem_resource_id = result['id']
    logger.info(f"Found UniChem resource with ID {unichem_resource_id}")
    
    # Check sources from the actual UniChem API
    logger.info("Fetching current UniChem sources from API...")
    unichem_sources = get_unichem_source_info()
    
    if unichem_sources:
        logger.info(f"Found {len(unichem_sources)} sources in UniChem API")
        
        # Validate our source mappings against the API
        for source_name, source_id in list(ADDITIONAL_SOURCES.items()):
            found = False
            for api_source in unichem_sources:
                if api_source.get('src_id') == source_id:
                    logger.info(f"Validated source {source_name} (ID: {source_id}, Name: {api_source.get('name')})")
                    found = True
                    break
            
            if not found:
                logger.warning(f"Source ID {source_id} for {source_name} not found in API - removing")
                del ADDITIONAL_SOURCES[source_name]
    else:
        logger.warning("Could not fetch UniChem sources from API - proceeding with predefined sources")
    
    # Create property extraction configurations for additional sources
    new_configs = create_property_configs(unichem_resource_id)
    logger.info(f"Created {len(new_configs)} new property extraction configurations")
    
    # Check for existing configurations to avoid duplicates
    for config in list(new_configs):
        cursor.execute(
            """
            SELECT id FROM property_extraction_configs 
            WHERE resource_id = ? AND property_name = ?
            """,
            (unichem_resource_id, config['property_name'])
        )
        
        if cursor.fetchone():
            logger.info(f"Configuration for {config['property_name']} already exists - skipping")
            new_configs.remove(config)
    
    # Add new property extraction configurations
    for config in new_configs:
        cursor.execute(
            """
            INSERT INTO property_extraction_configs (
                resource_id, ontology_type, property_name, extraction_method,
                extraction_pattern, result_type, transform_function, priority,
                is_active, ns_prefix, ns_uri, entity_type
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                config['resource_id'],
                config['ontology_type'],
                config['property_name'],
                config['extraction_method'],
                config['extraction_pattern'],
                config['result_type'],
                config['transform_function'],
                config['priority'],
                config['is_active'],
                config['ns_prefix'],
                config['ns_uri'],
                config['entity_type']
            )
        )
        
        logger.info(f"Added property extraction config for {config['property_name']}")
    
    # Update the UniChem client to handle new sources
    if new_configs:
        if update_unichem_client_sources():
            logger.info("Successfully updated UniChem client with new sources")
        else:
            logger.error("Failed to update UniChem client")
    
    # Commit changes
    conn.commit()
    logger.info(f"Successfully added {len(new_configs)} new UniChem property extraction configurations")
    
    # Show all UniChem property extraction configurations
    cursor.execute(
        """
        SELECT property_name, extraction_method, extraction_pattern 
        FROM property_extraction_configs 
        WHERE resource_id = ?
        ORDER BY property_name
        """,
        (unichem_resource_id,)
    )
    
    all_configs = cursor.fetchall()
    
    logger.info(f"\nUniChem now has {len(all_configs)} property extraction configurations:")
    for config in all_configs:
        logger.info(f"  - {config['property_name']} ({config['extraction_method']}): {config['extraction_pattern']}")
    
except Exception as e:
    logger.error(f"Error enhancing UniChem properties: {e}")
    import traceback
    traceback.print_exc()
    conn.rollback()
    sys.exit(1)
    
finally:
    # Close the database connection
    conn.close()

logger.info("\nNext steps:")
logger.info("1. Test the enhanced UniChem property extractions")
logger.info("2. Update mapping paths to utilize new UniChem sources")
logger.info("3. Consider adding custom mapping paths for high-value conversions")
