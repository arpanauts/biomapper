#!/usr/bin/env python3
"""
Test the core pipeline directly without broken export steps
"""
import asyncio
import time
import os
from datetime import datetime

os.environ['OUTPUT_DIR'] = '/tmp/biomapper_results'
os.environ['TIMESTAMP'] = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
os.makedirs(os.environ['OUTPUT_DIR'], exist_ok=True)

from biomapper.core.minimal_strategy_service import MinimalStrategyService

async def test_core_pipeline():
    print('🚀 TESTING CORE PIPELINE (WITHOUT EXPORTS)')
    print('=' * 60)
    
    service = MinimalStrategyService('/home/ubuntu/biomapper/configs/strategies')
    
    print('\nExecuting just the core matching steps...')
    start = time.time()
    
    # Create a minimal context to run specific steps
    from biomapper.core.strategy_actions.registry import ACTION_REGISTRY
    
    context = {
        "datasets": {},
        "statistics": {},
        "output_files": []
    }
    
    # Step 1: Load Arivale
    print("\n1. Loading Arivale proteins...")
    load_arivale = ACTION_REGISTRY["LOAD_DATASET_IDENTIFIERS"]()
    result1 = await load_arivale.execute(
        current_identifiers=[],
        current_ontology_type="proteins",
        params={
            "file_path": "/procedure/data/local_data/ARIVALE_SNAPSHOTS/proteomics_metadata.tsv",
            "identifier_column": "uniprot",
            "output_key": "arivale_proteins"
        },
        source_endpoint=None,
        target_endpoint=None,
        context=context
    )
    print(f"   Loaded: {context['statistics'].get('LOAD_DATASET_IDENTIFIERS', {})}")
    
    # Step 2: Load KG2c
    print("\n2. Loading KG2c entities...")
    load_kg2c = ACTION_REGISTRY["LOAD_DATASET_IDENTIFIERS"]()
    result2 = await load_kg2c.execute(
        current_identifiers=[],
        current_ontology_type="proteins",
        params={
            "file_path": "/procedure/data/local_data/MAPPING_ONTOLOGIES/kg2c_ontologies/kg2c_proteins.csv",
            "identifier_column": "id",
            "output_key": "kg2c_entities"
        },
        source_endpoint=None,
        target_endpoint=None,
        context=context
    )
    print(f"   Loaded: {context['statistics'].get('LOAD_DATASET_IDENTIFIERS', {})}")
    
    # Step 3: UniProt Resolution
    print("\n3. Running UniProt resolution (optimized)...")
    resolution = ACTION_REGISTRY["MERGE_WITH_UNIPROT_RESOLUTION"]()
    result3 = await resolution.execute(
        current_identifiers=[],
        current_ontology_type="proteins",
        params={
            "source_dataset_key": "arivale_proteins",
            "target_dataset_key": "kg2c_entities",
            "source_id_column": "uniprot",
            "target_id_column": "id",
            "target_xref_column": "equivalent_identifiers",
            "output_key": "mapping_results",
            "use_api": False  # Disable API for now
        },
        source_endpoint=None,
        target_endpoint=None,
        context=context
    )
    
    elapsed = time.time() - start
    
    print(f"\n✅ CORE PIPELINE COMPLETED in {elapsed:.2f} seconds")
    
    # Print statistics
    print("\n📊 STATISTICS:")
    for action, stats in context.get("statistics", {}).items():
        print(f"\n{action}:")
        if isinstance(stats, dict):
            for key, value in stats.items():
                print(f"  - {key}: {value}")
        else:
            print(f"  {stats}")
    
    # Check if we have mapping results
    if "mapping_results" in context.get("datasets", {}):
        results = context["datasets"]["mapping_results"]
        print(f"\n📈 MAPPING RESULTS:")
        print(f"  - Total rows: {len(results)}")
        if len(results) > 0:
            print(f"  - Sample result: {results[0]}")
    
    print(f"\n💡 With this timing, recommended API timeout: {int(elapsed * 2)} seconds")
    
    return context

asyncio.run(test_core_pipeline())