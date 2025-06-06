#!/usr/bin/env python3
"""
Enhanced Resource Verification Script with Entity Type Support

This script extends the verify_resource_extractions.py functionality to be
entity-type aware when testing resources. It ensures appropriate test data
is used for each entity type and provides more detailed reporting by entity type.
"""

import sys
import time
import logging
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
import importlib
from dataclasses import dataclass, field
import sqlite3

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("entity_verification.log"),
        logging.StreamHandler(sys.stdout),
    ],
)

logger = logging.getLogger("entity_verification")

# Sample IDs for testing each entity type and resource
SAMPLE_IDS = {
    # Metabolite resources
    "metabolite": {
        "ChEBI": ["CHEBI:15377", "CHEBI:17303"],  # Glucose, Caffeine
        "PubChem": ["5793", "2519"],  # Caffeine, Glucose
        "KEGG": ["C00031", "C07481"],  # Glucose, Caffeine
        "UniChem": ["chembl:CHEMBL113", "hmdb:HMDB0001847"],  # Caffeine, Glucose
        "RefMet": ["REFMET:1", "REFMET:100"],  # Sample RefMet IDs
        "RaMP-DB": ["hmdb:HMDB0000122", "hmdb:HMDB0001847"],  # Caffeine, Glucose
        "MetabolitesCSV": ["1", "2"],  # Sample IDs from CSV
    },
    # Protein resources (for future use)
    "protein": {
        "UniProt": ["P68871", "P01308"],  # Hemoglobin beta, Insulin
        "PDB": ["4HHB", "3I40"],  # Hemoglobin, Insulin
    },
    # Gene resources (for future use)
    "gene": {
        "NCBI": ["3043", "3630"],  # HBB (hemoglobin beta), INS (insulin)
        "Ensembl": ["ENSG00000244734", "ENSG00000129965"],  # HBB, INS
    },
    # Special handling for multi-entity resources
    "all": {
        "SPOKE": {
            "metabolite": ["Caffeine", "Glucose"],
            "protein": ["Hemoglobin", "Insulin"],
            "gene": ["HBB", "INS"],
            "disease": ["Diabetes", "Anemia"],
        }
    },
}

# Test search terms for name-based searches by entity type
SAMPLE_SEARCH_TERMS = {
    "metabolite": ["glucose", "caffeine", "aspirin", "cholesterol"],
    "protein": ["hemoglobin", "insulin", "albumin", "cytochrome"],
    "gene": ["HBB", "INS", "TP53", "BRCA1"],
    "disease": ["diabetes", "anemia", "alzheimer", "cancer"],
    "pathway": [
        "glycolysis",
        "krebs cycle",
        "electron transport",
        "oxidative phosphorylation",
    ],
    "all": [
        "glucose",
        "hemoglobin",
        "HBB",
        "diabetes",
        "glycolysis",
    ],  # Mixed entities for general search testing
}


def get_test_ids_by_entity_type(resource_name: str, entity_type: str) -> List[str]:
    """
    Get appropriate test IDs for a resource based on its entity type.

    Args:
        resource_name: Name of the resource
        entity_type: Entity type of the resource

    Returns:
        List of sample IDs to test
    """
    if entity_type == "all":
        # For "all" entity type resources like SPOKE, we'll need to determine which IDs to use
        # based on the specific test being performed
        if resource_name in SAMPLE_IDS["all"]:
            # For now, return metabolite IDs as default for "all" resources
            return SAMPLE_IDS["all"][resource_name].get("metabolite", [])
        return []

    # For specific entity types (metabolite, protein, etc.)
    if entity_type in SAMPLE_IDS:
        # If we have specific IDs for this resource
        if resource_name in SAMPLE_IDS[entity_type]:
            return SAMPLE_IDS[entity_type][resource_name]
        # Otherwise return empty list
        return []

    # Default to metabolite IDs if entity type not recognized
    if "metabolite" in SAMPLE_IDS and resource_name in SAMPLE_IDS["metabolite"]:
        return SAMPLE_IDS["metabolite"][resource_name]

    return []


def get_search_terms_by_entity_type(entity_type: str) -> List[str]:
    """
    Get appropriate search terms for a resource based on its entity type.

    Args:
        entity_type: Entity type of the resource

    Returns:
        List of sample search terms to test
    """
    if entity_type in SAMPLE_SEARCH_TERMS:
        return SAMPLE_SEARCH_TERMS[entity_type]

    # Default to metabolite search terms
    return SAMPLE_SEARCH_TERMS.get("metabolite", ["glucose", "caffeine"])


def entity_aware_verification(
    db_path: Path, resource_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Run verification checks with entity type awareness.

    Args:
        db_path: Path to the metamapper database
        resource_name: Optional specific resource to test

    Returns:
        Dictionary containing verification results
    """
    from verify_resource_extractions import ResourceVerifier

    # Create a standard ResourceVerifier
    verifier = ResourceVerifier(db_path)

    try:
        # Get all resources or filter by name
        resources = verifier.get_all_resources()
        if resource_name:
            resources = [
                r for r in resources if r["name"].lower() == resource_name.lower()
            ]
            if not resources:
                logger.error(f"Resource '{resource_name}' not found")
                return {"error": f"Resource '{resource_name}' not found"}

        # Connect to the database directly to get entity_type information
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Add entity_type to resources if not present in ResourceVerifier's result
        for resource in resources:
            if "entity_type" not in resource:
                cursor.execute(
                    "SELECT entity_type FROM resources WHERE id = ?", (resource["id"],)
                )
                result = cursor.fetchone()
                if result and result["entity_type"]:
                    resource["entity_type"] = result["entity_type"]
                else:
                    resource["entity_type"] = "metabolite"  # Default

        # Override sample IDs based on entity type
        for resource in resources:
            entity_type = resource.get("entity_type", "metabolite")
            resource_name = resource["name"]

            # Get appropriate test IDs for this resource's entity type
            test_ids = get_test_ids_by_entity_type(resource_name, entity_type)
            if test_ids:
                logger.info(
                    f"Using entity-specific test IDs for {resource_name} (entity_type: {entity_type})"
                )
                ResourceVerifier.SAMPLE_IDS[resource_name] = test_ids

        # Run verification
        verification_results = {}
        for resource in resources:
            result = verifier.verify_resource(resource)
            verification_results[resource["id"]] = result

        # Print and save entity-aware report
        print_entity_aware_report(verification_results)
        save_entity_aware_report(verification_results)

        # Close the verifier to clean up resources
        verifier.close()

        return {"success": True, "results": verification_results}

    except Exception as e:
        logger.error(f"Error in entity-aware verification: {str(e)}")
        import traceback

        traceback.print_exc()
        return {"error": str(e)}


def print_entity_aware_report(results: Dict[int, Any]) -> None:
    """
    Print a verification report grouped by entity type.

    Args:
        results: Dictionary of verification results keyed by resource ID
    """
    # Group results by entity type
    by_entity_type = {}
    for resource_id, result in results.items():
        entity_type = getattr(result, "entity_type", "metabolite")
        if entity_type not in by_entity_type:
            by_entity_type[entity_type] = []
        by_entity_type[entity_type].append(result)

    print("\nEntity-Aware Verification Report")
    print("================================")

    for entity_type, resources in by_entity_type.items():
        print(f"\n## Entity Type: {entity_type.upper()}")
        print(f"Total Resources: {len(resources)}")
        print(f"Successful: {sum(1 for r in resources if r.success)}/{len(resources)}")

        for resource in resources:
            success_mark = "✓" if resource.success else "✗"
            print(f"\n{success_mark} {resource.resource_name}")

            if not resource.client_initialized:
                print(f"  - ERROR: Client initialization failed")
                if resource.errors:
                    for error in resource.errors:
                        print(f"    {error}")
                continue

            # Show property extraction success rate
            total_props = 0
            successful_props = 0
            for id_results in resource.property_extractions.values():
                for prop_name, extraction in id_results.items():
                    total_props += 1
                    if extraction.get("success", False):
                        successful_props += 1

            if total_props > 0:
                success_rate = (successful_props / total_props) * 100
                print(
                    f"  - Property extraction rate: {success_rate:.1f}% ({successful_props}/{total_props})"
                )
            else:
                print(f"  - No property extractions attempted")

            # Show execution time
            print(f"  - Execution time: {resource.execution_time:.2f}s")


def save_entity_aware_report(
    results: Dict[int, Any], output_path: Optional[Path] = None
) -> None:
    """
    Save a detailed verification report grouped by entity type to a JSON file.

    Args:
        results: Dictionary of verification results keyed by resource ID
        output_path: Optional custom output path for the report
    """
    from verify_resource_extractions import ResourceVerifier

    if not results:
        logger.warning("No verification results available to save")
        return

    output_path = output_path or Path("entity_verification_report.json")

    # Group results by entity type
    by_entity_type = {}
    for resource_id, result in results.items():
        entity_type = getattr(result, "entity_type", "metabolite")
        if entity_type not in by_entity_type:
            by_entity_type[entity_type] = {}

        # Convert to serializable dict using helper from ResourceVerifier
        resource_result = {
            "resource_id": result.resource_id,
            "resource_name": result.resource_name,
            "client_type": result.client_type,
            "success": result.success,
            "client_initialized": result.client_initialized,
            "execution_time": result.execution_time,
            "errors": result.errors,
            "search_results": {},
            "property_extractions": {},
        }

        # Handle serialization manually
        for key, value in result.search_results.items():
            if hasattr(value, "__dict__"):
                resource_result["search_results"][key] = value.__dict__
            else:
                resource_result["search_results"][key] = value

        for id_key, extractions in result.property_extractions.items():
            resource_result["property_extractions"][id_key] = {}
            for prop_name, extraction in extractions.items():
                if hasattr(extraction, "__dict__"):
                    resource_result["property_extractions"][id_key][
                        prop_name
                    ] = extraction.__dict__
                else:
                    resource_result["property_extractions"][id_key][
                        prop_name
                    ] = extraction

        by_entity_type[entity_type][str(resource_id)] = resource_result

    # Create the report
    report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "summary": {
            "total_resources": len(results),
            "successful_resources": sum(1 for r in results.values() if r.success),
            "by_entity_type": {
                entity_type: {
                    "count": len(resources),
                    "success_rate": sum(
                        1 for r_id, r in resources.items() if r["success"]
                    )
                    / len(resources)
                    if resources
                    else 0,
                }
                for entity_type, resources in by_entity_type.items()
            },
        },
        "results_by_entity_type": by_entity_type,
    }

    try:
        with open(output_path, "w") as f:
            json.dump(report, f, indent=2)
        logger.info(f"Saved entity-aware verification report to {output_path}")
    except Exception as e:
        logger.error(f"Error saving entity-aware verification report: {str(e)}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Entity-aware verification of resources"
    )
    parser.add_argument(
        "--db",
        type=str,
        help="Path to the metamapper database file",
        default="data/metamapper.db",
    )
    parser.add_argument(
        "--resource", type=str, help="Verify a specific resource by name"
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output path for the verification report",
        default="entity_verification_report.json",
    )
    args = parser.parse_args()

    try:
        results = entity_aware_verification(Path(args.db), args.resource)

        if "error" in results:
            logger.error(f"Verification error: {results['error']}")
            sys.exit(1)

    except Exception as e:
        logger.error(f"Error in entity-aware verification: {str(e)}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
