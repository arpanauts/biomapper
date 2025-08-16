#!/usr/bin/env python3
"""
Test the complete pipeline WITHOUT API calls first
"""
import asyncio
import time
import os
from datetime import datetime
import yaml

os.environ['OUTPUT_DIR'] = '/tmp/biomapper_results'
os.environ['TIMESTAMP'] = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
os.makedirs(os.environ['OUTPUT_DIR'], exist_ok=True)

# Clear previous results
for f in os.listdir(os.environ['OUTPUT_DIR']):
    try:
        os.remove(os.path.join(os.environ['OUTPUT_DIR'], f))
    except:
        pass

from biomapper.core.minimal_strategy_service import MinimalStrategyService

async def test_without_api():
    print('🚀 TESTING PIPELINE WITHOUT API CALLS')
    print('=' * 60)
    print('This tests the optimized matching without UniProt API resolution')
    print('=' * 60)
    
    # Create a modified strategy that disables API
    strategy_yaml = """
name: test_no_api
description: Test pipeline without API calls
parameters:
  arivale_file: "/procedure/data/local_data/ARIVALE_SNAPSHOTS/proteomics_metadata.tsv"
  kg2c_file: "/procedure/data/local_data/MAPPING_ONTOLOGIES/kg2c_ontologies/kg2c_proteins.csv"
  output_dir: "/tmp/biomapper_results"

steps:
  - name: load_arivale
    action:
      type: LOAD_DATASET_IDENTIFIERS
      params:
        file_path: "${parameters.arivale_file}"
        identifier_column: "uniprot"
        output_key: "arivale_proteins"
        
  - name: load_kg2c
    action:
      type: LOAD_DATASET_IDENTIFIERS
      params:
        file_path: "${parameters.kg2c_file}"
        identifier_column: "id"
        output_key: "kg2c_entities"
        
  - name: uniprot_resolution
    action:
      type: MERGE_WITH_UNIPROT_RESOLUTION
      params:
        source_dataset_key: "arivale_proteins"
        target_dataset_key: "kg2c_entities"
        source_id_column: "uniprot"
        target_id_column: "id"
        composite_separator: "_"
        use_api: false  # DISABLED
        output_key: "mapping_results"
"""
    
    # Write temporary strategy
    with open('/tmp/test_no_api.yaml', 'w') as f:
        f.write(strategy_yaml)
    
    # Load it into the service
    service = MinimalStrategyService('/home/ubuntu/biomapper/configs/strategies')
    service.strategies['test_no_api'] = yaml.safe_load(strategy_yaml)
    
    print('\nStarting execution...')
    start = time.time()
    
    try:
        result = await service.execute_strategy(
            strategy_name='test_no_api',
            source_endpoint_name='',
            target_endpoint_name='',
            input_identifiers=[]
        )
        
        elapsed = time.time() - start
        print(f'\n✅ COMPLETED in {elapsed:.2f} seconds ({elapsed/60:.1f} minutes)')
        
        # Print statistics
        if hasattr(result, 'statistics') and result.statistics:
            print('\n📊 STATISTICS:')
            for action, stats in result.statistics.items():
                if isinstance(stats, dict):
                    print(f'\n{action}:')
                    for key, value in stats.items():
                        print(f'  - {key}: {value}')
        
        print(f'\n💡 Performance: ~{len(result.statistics.get("LOAD_DATASET_IDENTIFIERS", {}).get("arivale_proteins", {}).get("identifiers_loaded", 0)) * 266487 / elapsed / 1000000:.1f}M comparisons/second')
        
        return result
        
    except Exception as e:
        elapsed = time.time() - start
        print(f'\n❌ Failed after {elapsed:.2f} seconds')
        print(f'Error: {e}')
        import traceback
        traceback.print_exc()

asyncio.run(test_without_api())