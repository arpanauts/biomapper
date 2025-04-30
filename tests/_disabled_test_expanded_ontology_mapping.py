#!/usr/bin/env python3
"""
Test script for expanded ontology coverage in Biomapper.

This script tests the newly implemented PubChem and KEGG clients and their
mapping paths to demonstrate the expanded ontology coverage beyond ChEBI.
"""

import asyncio
import logging
import sys
from pathlib import Path
import argparse

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from biomapper.mapping.metadata.engine import MetamappingEngine
from biomapper.mapping.clients.pubchem_client import PubChemClient
from biomapper.mapping.clients.kegg_client import KEGGClient
from biomapper.mapping.clients.chebi_client import ChEBIClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def print_entity_details(entity, prefix=""):
    """Print details of an entity in a readable format."""
    if entity is None:
        print(f"{prefix}No entity found.")
        return

    print(f"{prefix}Entity details:")

    # Common properties
    for prop in ["name", "formula", "smiles", "inchi", "inchikey"]:
        if hasattr(entity, prop):
            value = getattr(entity, prop)
            if value:
                print(f"{prefix}  {prop.capitalize()}: {value}")

    # PubChem specific
    if hasattr(entity, "pubchem_cid"):
        print(f"{prefix}  PubChem CID: {entity.pubchem_cid}")

    # ChEBI specific
    if hasattr(entity, "chebi_id"):
        print(f"{prefix}  ChEBI ID: {entity.chebi_id}")

    # KEGG specific
    if hasattr(entity, "kegg_id"):
        print(f"{prefix}  KEGG ID: {entity.kegg_id}")

    # Cross-references
    if hasattr(entity, "xrefs") and entity.xrefs:
        print(f"{prefix}  Cross-references:")
        for db, id_value in entity.xrefs.items():
            print(f"{prefix}    {db.upper()}: {id_value}")

    # Other databases in KEGG
    if hasattr(entity, "other_dbs") and entity.other_dbs:
        print(f"{prefix}  Cross-references:")
        for db, id_value in entity.other_dbs.items():
            print(f"{prefix}    {db.upper()}: {id_value}")


async def test_direct_client_searches(compound_name):
    """Test direct client searches using PubChem, KEGG, and ChEBI clients."""
    print("\n" + "=" * 80)
    print(f"DIRECT CLIENT SEARCHES FOR: {compound_name}")
    print("=" * 80)

    # PubChem search
    print("\nSearching PubChem...")
    try:
        pubchem_client = PubChemClient()
        pubchem_results = pubchem_client.search_by_name(compound_name, max_results=1)
        if pubchem_results:
            print_entity_details(pubchem_results[0])
        else:
            print(f"No PubChem results found for '{compound_name}'")
    except Exception as e:
        print(f"PubChem search error: {e}")

    # KEGG search
    print("\nSearching KEGG...")
    try:
        kegg_client = KEGGClient()
        kegg_results = kegg_client.search_by_name(compound_name, max_results=1)
        if kegg_results:
            print_entity_details(kegg_results[0])
        else:
            print(f"No KEGG results found for '{compound_name}'")
    except Exception as e:
        print(f"KEGG search error: {e}")

    # ChEBI search for comparison
    print("\nSearching ChEBI...")
    try:
        chebi_client = ChEBIClient()
        chebi_results = chebi_client.search_by_name(compound_name, max_results=1)
        if chebi_results:
            print_entity_details(chebi_results[0])
        else:
            print(f"No ChEBI results found for '{compound_name}'")
    except Exception as e:
        print(f"ChEBI search error: {e}")


async def test_metamapping_engine(compound_name):
    """Test the MetamappingEngine with the expanded ontology coverage."""
    print("\n" + "=" * 80)
    print(f"METAMAPPING ENGINE TESTS FOR: {compound_name}")
    print("=" * 80)

    # Initialize the metamapping engine
    engine = MetamappingEngine()
    await engine.connect()

    try:
        # Test NAME → PUBCHEM
        print("\nMapping NAME → PUBCHEM:")
        results, metadata = await engine.search_by_name(
            compound_name, "PUBCHEM", limit=1
        )
        if results:
            print(f"Found PubChem ID: {results[0]}")
            print(f"Confidence: {metadata.get('confidence', 'N/A')}")
            print(f"Execution time: {metadata.get('execution_time_ms', 'N/A')} ms")

            # Now lookup entity details
            print("\nGetting PubChem entity details:")
            entity_result, _ = await engine.lookup_entity(
                results[0], "PUBCHEM", "PUBCHEM"
            )
            print_entity_details(entity_result)
        else:
            print(f"No PubChem mapping found for '{compound_name}'")
            print(f"Error: {metadata.get('error_message', 'N/A')}")

        # Test NAME → KEGG
        print("\nMapping NAME → KEGG:")
        results, metadata = await engine.search_by_name(compound_name, "KEGG", limit=1)
        if results:
            print(f"Found KEGG ID: {results[0]}")
            print(f"Confidence: {metadata.get('confidence', 'N/A')}")
            print(f"Execution time: {metadata.get('execution_time_ms', 'N/A')} ms")

            # Now lookup entity details
            print("\nGetting KEGG entity details:")
            entity_result, _ = await engine.lookup_entity(results[0], "KEGG", "KEGG")
            print_entity_details(entity_result)
        else:
            print(f"No KEGG mapping found for '{compound_name}'")
            print(f"Error: {metadata.get('error_message', 'N/A')}")

        # Test NAME → PUBCHEM → INCHI (multi-step)
        print("\nMulti-step mapping NAME → PUBCHEM → INCHI:")
        results, metadata = await engine.lookup_entity(compound_name, "NAME", "INCHI")
        if results:
            print(f"Found InChI: {results}")
            print(f"Confidence: {metadata.get('confidence', 'N/A')}")
            print(f"Execution time: {metadata.get('execution_time_ms', 'N/A')} ms")
        else:
            print(f"No InChI mapping found for '{compound_name}'")
            print(f"Error: {metadata.get('error_message', 'N/A')}")

        # Test NAME → PUBCHEM → CHEBI (multi-step)
        print("\nMulti-step mapping NAME → PUBCHEM → CHEBI:")
        results, metadata = await engine.lookup_entity(compound_name, "NAME", "CHEBI")
        if results:
            print(f"Found ChEBI ID: {results}")
            print(f"Confidence: {metadata.get('confidence', 'N/A')}")
            print(f"Execution time: {metadata.get('execution_time_ms', 'N/A')} ms")

            # Now lookup ChEBI entity details
            if isinstance(results, str) and results.startswith("CHEBI:"):
                print("\nGetting ChEBI entity details:")
                entity_result, _ = await engine.lookup_entity(results, "CHEBI", "CHEBI")
                print_entity_details(entity_result)
        else:
            print(f"No ChEBI mapping found for '{compound_name}'")
            print(f"Error: {metadata.get('error_message', 'N/A')}")

    finally:
        # Close the connection
        await engine.close()


async def main():
    """Main function to run the tests."""
    parser = argparse.ArgumentParser(
        description="Test expanded ontology coverage in Biomapper"
    )
    parser.add_argument(
        "--compound", default="glucose", help="Compound name to search for"
    )
    parser.add_argument("--setup", action="store_true", help="Run setup scripts first")
    args = parser.parse_args()

    if args.setup:
        print("Running setup scripts for PubChem and KEGG paths...")
        sys.path.append(str(Path(__file__).parent.parent))
        from scripts.setup_pubchem_paths import setup_pubchem_paths
        from scripts.setup_kegg_paths import setup_kegg_paths

        await setup_pubchem_paths()
        await setup_kegg_paths()

    await test_direct_client_searches(args.compound)
    await test_metamapping_engine(args.compound)


if __name__ == "__main__":
    asyncio.run(main())
