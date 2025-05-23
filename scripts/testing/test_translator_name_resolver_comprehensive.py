#!/usr/bin/env python
"""
Comprehensive test script for the TranslatorNameResolverClient

This script tests various configurations and options of the TranslatorNameResolverClient
with real API calls to verify its functionality with different entity types
and settings.
"""

import asyncio
import logging
import sys
import time
from typing import List, Dict, Any, Tuple, Optional

from biomapper.mapping.clients.translator_name_resolver_client import TranslatorNameResolverClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Test metabolites with varying complexity
METABOLITES = [
    "glucose",
    "cholesterol",
    "triglycerides",
    "high density lipoprotein",
    "low density lipoprotein",
    "arachidonic acid",
]

# Test proteins with varying complexity
PROTEINS = [
    "insulin",
    "hemoglobin",
    "albumin",
    "cytochrome p450",
    "tumor necrosis factor alpha",
]

# Test genes with varying complexity
GENES = [
    "BRCA1",
    "TP53",
    "EGFR",
    "TNF",
    "IL6",
]

# Test drugs with varying complexity
DRUGS = [
    "aspirin",
    "ibuprofen",
    "acetaminophen",
    "metformin",
    "atorvastatin",
]

async def test_entity_type(
    entity_type: str,
    names: List[str],
    target_db: str,
    biolink_type: str,
    match_threshold: float = 0.5
):
    """
    Test the TranslatorNameResolverClient with a specific entity type.
    
    Args:
        entity_type: Description of the entity type being tested
        names: List of entity names to map
        target_db: Target database for mapping
        biolink_type: Biolink type to use for filtering
        match_threshold: Minimum score threshold for matches
    """
    logger.info(f"Testing {entity_type} mapping with target_db={target_db} and biolink_type={biolink_type}")
    
    # Initialize the client with the specified configuration
    client = TranslatorNameResolverClient(config={
        "target_db": target_db,
        "match_threshold": match_threshold
    })
    
    try:
        # Record start time
        start_time = time.time()
        
        # Map the entity names
        results = await client.map_identifiers(
            names=names,
            target_biolink_type=biolink_type
        )
        
        # Calculate elapsed time
        elapsed_time = time.time() - start_time
        
        # Display the results
        print(f"\n{entity_type} Mapping Results (target_db={target_db}, threshold={match_threshold}):")
        print("=" * 80)
        print(f"Time elapsed: {elapsed_time:.2f} seconds")
        
        for name, (identifiers, confidence) in results.items():
            if identifiers:
                # Limit display to first 5 identifiers for readability
                id_display = identifiers[:5]
                if len(identifiers) > 5:
                    id_display.append(f"... ({len(identifiers) - 5} more)")
                
                print(f"{name:<30} -> {', '.join(id_display)} (confidence: {confidence})")
            else:
                print(f"{name:<30} -> No mapping found")
        
        # Count successful and failed mappings
        successful = sum(1 for ids, _ in results.values() if ids is not None)
        failed = sum(1 for ids, _ in results.values() if ids is None)
        
        print("\nSummary:")
        print(f"Total entities: {len(names)}")
        print(f"Successfully mapped: {successful}")
        print(f"Failed to map: {failed}")
        print(f"Success rate: {successful/len(names)*100:.1f}%")
        
    except Exception as e:
        logger.error(f"Error during {entity_type} testing: {str(e)}")
        raise
    finally:
        # Close the client
        await client.close()

async def test_threshold_sensitivity(names: List[str], target_db: str, biolink_type: str):
    """
    Test the sensitivity of different match thresholds.
    
    Args:
        names: List of entity names to map
        target_db: Target database for mapping
        biolink_type: Biolink type to use for filtering
    """
    print("\nMatch Threshold Sensitivity Analysis:")
    print("=" * 80)
    
    # Test different threshold values
    thresholds = [0.1, 0.5, 0.7, 0.9]
    
    for threshold in thresholds:
        # Initialize the client with the specified threshold
        client = TranslatorNameResolverClient(config={
            "target_db": target_db,
            "match_threshold": threshold
        })
        
        try:
            # Map the entity names
            results = await client.map_identifiers(
                names=names,
                target_biolink_type=biolink_type
            )
            
            # Count matches for each name
            match_counts = {}
            for name, (identifiers, _) in results.items():
                match_counts[name] = len(identifiers) if identifiers else 0
            
            # Calculate success rate
            successful = sum(1 for count in match_counts.values() if count > 0)
            success_rate = successful / len(names) * 100
            
            # Calculate average matches per name
            total_matches = sum(match_counts.values())
            avg_matches = total_matches / len(names)
            
            print(f"Threshold {threshold}:")
            print(f"  Success rate: {success_rate:.1f}%")
            print(f"  Average matches per name: {avg_matches:.1f}")
            print(f"  Total matches: {total_matches}")
            print(f"  Match distribution: {match_counts}")
            print()
            
        except Exception as e:
            logger.error(f"Error during threshold testing ({threshold}): {str(e)}")
        finally:
            # Close the client
            await client.close()

async def main():
    """
    Main entry point for the script.
    """
    # Test metabolite mapping with different databases
    await test_entity_type("Metabolites", METABOLITES, "CHEBI", "biolink:SmallMolecule")
    await test_entity_type("Metabolites", METABOLITES, "PUBCHEM", "biolink:SmallMolecule")
    await test_entity_type("Metabolites", METABOLITES, "HMDB", "biolink:SmallMolecule")
    
    # Test protein mapping
    await test_entity_type("Proteins", PROTEINS, "UNIPROT", "biolink:Protein")
    
    # Test gene mapping
    await test_entity_type("Genes", GENES, "HGNC", "biolink:Gene")
    
    # Test drug mapping
    await test_entity_type("Drugs", DRUGS, "DRUGBANK", "biolink:Drug")
    
    # Test threshold sensitivity with metabolites
    await test_threshold_sensitivity(METABOLITES, "CHEBI", "biolink:SmallMolecule")

if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())