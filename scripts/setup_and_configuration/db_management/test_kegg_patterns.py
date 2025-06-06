#!/usr/bin/env python3
"""
Test KEGG property extraction patterns against real KEGG API data.
"""

import re
import sys
import time
import logging
import sqlite3
import requests
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Get database path
db_path = Path("data/metamapper.db")
if not db_path.exists():
    logger.error(f"Database file {db_path} not found!")
    sys.exit(1)

logger.info(f"Using database at {db_path}")

# Connect to the database
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row  # Use row factory for named columns
cursor = conn.cursor()

# KEGG API base URL
KEGG_API_URL = "https://rest.kegg.jp"


def get_resource_id(name):
    """Get resource ID by name."""
    cursor.execute("SELECT id FROM resources WHERE name = ?", (name,))
    result = cursor.fetchone()
    if not result:
        logger.error(f"Resource '{name}' not found!")
        return None
    return result["id"]


def get_kegg_property_configs():
    """Get KEGG property extraction configurations."""
    resource_id = get_resource_id("KEGG")
    if not resource_id:
        return []

    cursor.execute(
        """SELECT id, ontology_type, property_name, extraction_method, 
           extraction_pattern, result_type, transform_function, 
           priority, is_active
           FROM property_extraction_configs 
           WHERE resource_id = ?
           ORDER BY property_name""",
        (resource_id,),
    )
    return [dict(row) for row in cursor.fetchall()]


def update_property_config(config_id, method, pattern):
    """Update a property extraction configuration."""
    cursor.execute(
        """UPDATE property_extraction_configs 
           SET extraction_method = ?, extraction_pattern = ?, updated_at = datetime('now')
           WHERE id = ?""",
        (method, pattern, config_id),
    )

    return cursor.rowcount


def get_kegg_compound(compound_id):
    """Get KEGG compound data from the API."""
    try:
        # Respect rate limiting (max 3 requests per second)
        time.sleep(0.34)

        # Make API request
        url = f"{KEGG_API_URL}/get/{compound_id}"
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        return response.text
    except Exception as e:
        logger.error(f"Error retrieving KEGG compound {compound_id}: {str(e)}")
        return None


def extract_property(data, method, pattern):
    """Extract a property using the specified method and pattern."""
    if not data:
        return None

    try:
        if method == "regex":
            match = re.search(pattern, data, re.MULTILINE)
            if match:
                return match.group(1)
            return None

        elif method == "regex_all":
            matches = re.findall(pattern, data, re.MULTILINE)
            if matches:
                return matches
            return None

        else:
            logger.warning(f"Unsupported extraction method: {method}")
            return None
    except Exception as e:
        logger.error(f"Error extracting with pattern {pattern}: {str(e)}")
        return None


def test_patterns(kegg_id="C00031"):  # Default to glucose
    """Test all KEGG patterns against a real KEGG compound."""
    # Get KEGG data
    logger.info(f"Retrieving KEGG compound data for {kegg_id}...")
    kegg_data = get_kegg_compound(kegg_id)

    if not kegg_data:
        logger.error("Failed to retrieve KEGG data!")
        return

    # Get configurations
    configs = get_kegg_property_configs()

    if not configs:
        logger.error("No KEGG property extraction configurations found!")
        return

    logger.info(f"Testing {len(configs)} KEGG property extraction patterns...")

    # Print the raw KEGG data for reference (first 500 chars)
    print("\nKEGG API Raw Data Sample:")
    print("-" * 80)
    print(kegg_data[:500] + "..." if len(kegg_data) > 500 else kegg_data)
    print("-" * 80)

    # Test each pattern
    print(f"\nTesting patterns against KEGG compound {kegg_id}:")
    print(
        f"{'ID':<5} {'Property Name':<20} {'Method':<15} {'Current Pattern':<50} {'Result':<30}"
    )
    print("-" * 120)

    updated_patterns = []

    for config in configs:
        property_name = config["property_name"]
        method = config["extraction_method"]
        pattern = config["extraction_pattern"]

        # Extract using current pattern
        result = extract_property(kegg_data, method, pattern)

        # Display truncated pattern if it's too long
        display_pattern = pattern
        if len(pattern) > 50:
            display_pattern = pattern[:47] + "..."

        # Format result for display
        result_str = str(result)
        if result_str and len(result_str) > 30:
            result_str = result_str[:27] + "..."

        success = "✅" if result else "❌"

        print(
            f"{config['id']:<5} {property_name:<20} {method:<15} "
            f"{display_pattern:<50} {success + ' ' + result_str if result else '❌ No match':<30}"
        )

        # If pattern failed, try to find a better one
        if not result:
            improved_pattern = suggest_improved_pattern(kegg_data, property_name)
            if improved_pattern:
                updated_patterns.append(
                    {
                        "id": config["id"],
                        "property_name": property_name,
                        "old_pattern": pattern,
                        "new_pattern": improved_pattern,
                        "method": "regex" if "_all" not in method else "regex_all",
                    }
                )

    # Ask to update patterns
    if updated_patterns:
        print("\nThe following patterns can be improved:")
        for i, update in enumerate(updated_patterns):
            print(
                f"{i+1}. {update['property_name']}: {update['old_pattern']} -> {update['new_pattern']}"
            )

        choice = (
            input("\nDo you want to update these patterns? (y/n): ").strip().lower()
        )
        if choice == "y":
            for update in updated_patterns:
                rows_updated = update_property_config(
                    update["id"], update["method"], update["new_pattern"]
                )
                if rows_updated:
                    print(f"Updated pattern for {update['property_name']}")

            conn.commit()
            print("Patterns updated successfully!")
        else:
            print("No patterns were updated.")
    else:
        print("\nAll patterns are working correctly!")


def suggest_improved_pattern(data, property_name):
    """Suggest an improved pattern for the given property name based on the data structure."""
    # Common patterns we might find in KEGG data
    if property_name == "compound_name":
        # Look for NAME section
        match = re.search(r"NAME\s+(.*?)(?=\n[A-Z]+:|$)", data, re.DOTALL)
        if match:
            # Take just the first name (before the first semicolon)
            first_name = match.group(1).split(";")[0].strip()
            return r"NAME\s+(.*?)(?=;|\n)"

    elif property_name == "formula":
        match = re.search(r"FORMULA\s+(.*?)(?=\n[A-Z]+:|$)", data, re.DOTALL)
        if match:
            return r"FORMULA\s+(.*?)(?=\n[A-Z]+:|$)"

    elif property_name == "exact_mass":
        match = re.search(r"EXACT_MASS\s+([\d\.]+)", data)
        if match:
            return r"EXACT_MASS\s+([\d\.]+)"

    elif property_name == "mol_weight":
        match = re.search(r"MOL_WEIGHT\s+([\d\.]+)", data)
        if match:
            return r"MOL_WEIGHT\s+([\d\.]+)"

    elif property_name == "kegg_id":
        match = re.search(r"ENTRY\s+(\w+)", data)
        if match:
            return r"ENTRY\s+(\w+)"

    elif property_name == "pubchem_id":
        match = re.search(r"PubChem:\s+(\d+)", data)
        if match:
            return r"PubChem:\s+(\d+)"

    elif property_name == "chebi_id":
        match = re.search(r"ChEBI:\s+(\d+)", data)
        if match:
            return r"ChEBI:\s+(\d+)"

    elif property_name == "hmdb_id":
        match = re.search(r"HMDB:\s+(HMDB\d+)", data)
        if match:
            return r"HMDB:\s+(HMDB\d+)"

    elif property_name == "pathway_ids":
        matches = re.findall(r"(map\d+)", data)
        if matches:
            return r"(map\d+)"

    elif property_name == "smiles":
        match = re.search(r"SMILES:\s+(.+?)(?=\n|$)", data)
        if match:
            return r"SMILES:\s+(.+?)(?=\n|$)"

    elif property_name == "inchi":
        match = re.search(r"InChI=(.+?)(?=\n|$)", data)
        if match:
            return r"InChI=(.+?)(?=\n|$)"

    return None


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Test KEGG property extraction patterns."
    )
    parser.add_argument(
        "--kegg-id", default="C00031", help="KEGG compound ID to test against"
    )
    args = parser.parse_args()

    try:
        test_patterns(args.kegg_id)
    except Exception as e:
        logger.error(f"Error testing KEGG patterns: {str(e)}")
    finally:
        # Close the connection
        conn.close()
