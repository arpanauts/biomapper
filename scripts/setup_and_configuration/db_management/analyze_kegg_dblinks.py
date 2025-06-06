#!/usr/bin/env python3
"""
Analyze the DBLINKS section of KEGG compound entries.
"""

import re
import sys
import time
import logging
import requests
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# KEGG API base URL
KEGG_API_URL = "https://rest.kegg.jp"


def get_kegg_compound(compound_id):
    """Get KEGG compound data from the API."""
    try:
        # Respect rate limiting (max 3 requests per second)
        time.sleep(0.34)

        # Make API request
        url = f"{KEGG_API_URL}/get/{compound_id}"
        logger.info(f"Requesting URL: {url}")
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        return response.text
    except Exception as e:
        logger.error(f"Error retrieving KEGG compound {compound_id}: {str(e)}")
        return None


def extract_dblinks_section(data):
    """Extract the DBLINKS section from KEGG data."""
    if not data:
        return None

    # Look for the DBLINKS section
    match = re.search(r"DBLINKS\s+(.*?)(?=\n[A-Z]+:|$)", data, re.DOTALL)
    if match:
        return match.group(1)

    return None


def analyze_compound_structure(data):
    """Analyze the structure section (including FORMULA, EXACT_MASS, etc.)."""
    sections = {}

    # Extract different sections of interest
    for section in ["FORMULA", "EXACT_MASS", "MOL_WEIGHT", "STRUCTURE"]:
        match = re.search(f"{section}\\s+(.*?)(?=\\n[A-Z]+:|$)", data, re.DOTALL)
        if match:
            sections[section] = match.group(1).strip()

    return sections


def analyze_compound(kegg_id):
    """Analyze a KEGG compound."""
    # Get KEGG data
    logger.info(f"Retrieving KEGG compound data for {kegg_id}...")
    kegg_data = get_kegg_compound(kegg_id)

    if not kegg_data:
        logger.error("Failed to retrieve KEGG data!")
        return

    # Extract and analyze DBLINKS section
    dblinks = extract_dblinks_section(kegg_data)

    print("\nKEGG API Raw Data:")
    print("-" * 80)
    print(kegg_data)
    print("-" * 80)

    print("\nDBLINKS Section:")
    print("-" * 80)
    if dblinks:
        print(dblinks)
    else:
        print("No DBLINKS section found!")
    print("-" * 80)

    # Analyze structure information
    structure_info = analyze_compound_structure(kegg_data)

    print("\nStructure Information:")
    print("-" * 80)
    for section, content in structure_info.items():
        print(f"{section}: {content}")
    print("-" * 80)

    # Check for specific identifiers
    print("\nIdentifier Checks:")
    print("-" * 80)
    if kegg_data:
        # Check for HMDB ID
        hmdb_match = re.search(r"HMDB:\s+(HMDB\d+)", kegg_data)
        print(f"HMDB ID: {hmdb_match.group(1) if hmdb_match else 'Not found'}")

        # Check for InChI
        inchi_match = re.search(r"InChI=([^\n]+)", kegg_data)
        print(f"InChI: {inchi_match.group(0) if inchi_match else 'Not found'}")

        # Check for SMILES
        smiles_match = re.search(r"SMILES:\s+([^\n]+)", kegg_data)
        print(f"SMILES: {smiles_match.group(1) if smiles_match else 'Not found'}")

        # Check for ChEBI
        chebi_match = re.search(r"ChEBI:\s+(\d+)", kegg_data)
        print(f"ChEBI ID: {chebi_match.group(1) if chebi_match else 'Not found'}")

        # Check for PubChem
        pubchem_match = re.search(r"PubChem:\s+(\d+)", kegg_data)
        print(f"PubChem ID: {pubchem_match.group(1) if pubchem_match else 'Not found'}")
    print("-" * 80)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Analyze KEGG compound structure and DBLINKS."
    )
    parser.add_argument(
        "--kegg-id", default="C00031", help="KEGG compound ID to analyze"
    )
    args = parser.parse_args()

    analyze_compound(args.kegg_id)
