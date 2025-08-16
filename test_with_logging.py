#!/usr/bin/env python3
"""
Test pipeline with detailed logging for debugging
"""
import asyncio
import time
import os
import sys
from datetime import datetime
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

os.environ['OUTPUT_DIR'] = '/tmp/biomapper_results'
os.environ['TIMESTAMP'] = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')

# Clear previous results
os.makedirs(os.environ['OUTPUT_DIR'], exist_ok=True)
for f in os.listdir(os.environ['OUTPUT_DIR']):
    try:
        os.remove(os.path.join(os.environ['OUTPUT_DIR'], f))
    except:
        pass

from biomapper.core.minimal_strategy_service import MinimalStrategyService
from biomapper.core.strategy_actions.registry import ACTION_REGISTRY

async def run_with_logging():
    print('🚀 PRODUCTION PIPELINE WITH DETAILED LOGGING')
    print('=' * 60)
    
    # Create custom context with logging
    context = {
        "datasets": {},
        "statistics": {},
        "output_files": [],
        "custom_action_data": {}
    }
    
    print('\n📋 Step 1: Loading Arivale proteins...')
    print('-' * 40)
    
    try:
        load_action = ACTION_REGISTRY["LOAD_DATASET_IDENTIFIERS"]()
        print(f"Action class: {load_action.__class__.__name__}")
        
        # Use the simpler execute_with_context for testing
        from biomapper.core.strategy_execution_context import StrategyExecutionContext
        exec_context = StrategyExecutionContext(
            strategy_name="test",
            source_endpoint_name="",
            target_endpoint_name="",
            input_identifiers=[],
            custom_action_data={}
        )
        
        # Load Arivale
        print("Loading Arivale dataset...")
        result1 = await load_action.execute(
            current_identifiers=[],
            current_ontology_type="proteins",
            params={
                "file_path": "/procedure/data/local_data/ARIVALE_SNAPSHOTS/proteomics_metadata.tsv",
                "identifier_column": "uniprot",
                "output_key": "arivale_proteins"
            },
            source_endpoint=None,
            target_endpoint=None,
            context=exec_context
        )
        print(f"✅ Arivale loaded: {result1}")
        
        # Check what was loaded
        arivale_data = exec_context.get_action_data("datasets", {}).get("arivale_proteins", [])
        print(f"   Rows loaded: {len(arivale_data)}")
        if arivale_data:
            print(f"   Sample row: {arivale_data[0]}")
        
        print('\n📋 Step 2: Loading KG2c entities...')
        print('-' * 40)
        
        # Load KG2c
        print("Loading KG2c dataset...")
        result2 = await load_action.execute(
            current_identifiers=[],
            current_ontology_type="proteins",
            params={
                "file_path": "/procedure/data/local_data/MAPPING_ONTOLOGIES/kg2c_ontologies/kg2c_proteins.csv",
                "identifier_column": "id",
                "output_key": "kg2c_entities"
            },
            source_endpoint=None,
            target_endpoint=None,
            context=exec_context
        )
        print(f"✅ KG2c loaded: {result2}")
        
        kg2c_data = exec_context.get_action_data("datasets", {}).get("kg2c_entities", [])
        print(f"   Rows loaded: {len(kg2c_data)}")
        if kg2c_data:
            print(f"   Sample row: {kg2c_data[0]}")
        
        print('\n📋 Step 3: Running UniProt resolution...')
        print('-' * 40)
        
        # Run resolution
        resolution_action = ACTION_REGISTRY["MERGE_WITH_UNIPROT_RESOLUTION"]()
        print(f"Action class: {resolution_action.__class__.__name__}")
        
        print("Starting resolution (this may take ~1 minute)...")
        start_resolution = time.time()
        
        result3 = await resolution_action.execute(
            current_identifiers=[],
            current_ontology_type="proteins",
            params={
                "source_dataset_key": "arivale_proteins",
                "target_dataset_key": "kg2c_entities",
                "source_id_column": "uniprot",
                "target_id_column": "id",
                "composite_separator": "_",
                "use_api": True,
                "api_batch_size": 100,
                "output_key": "mapping_results"
            },
            source_endpoint=None,
            target_endpoint=None,
            context=exec_context
        )
        
        resolution_time = time.time() - start_resolution
        print(f"✅ Resolution completed in {resolution_time:.2f} seconds")
        
        # Check results
        mapping_data = exec_context.get_action_data("datasets", {}).get("mapping_results", [])
        print(f"   Mappings found: {len(mapping_data)}")
        if mapping_data:
            print(f"   Sample mapping: {mapping_data[0]}")
        
        # Get statistics
        stats = exec_context.get_action_data("statistics", {})
        print(f"\n📊 Statistics:")
        for action_name, action_stats in stats.items():
            print(f"   {action_name}: {action_stats}")
        
        print('\n📋 Step 4: Exporting results...')
        print('-' * 40)
        
        # Try to export
        export_action = ACTION_REGISTRY.get("EXPORT_DATASET")
        if export_action:
            export_instance = export_action()
            print("Exporting mapping results to CSV...")
            
            result4 = await export_instance.execute(
                current_identifiers=[],
                current_ontology_type="proteins",
                params={
                    "input_key": "mapping_results",
                    "output_path": "/tmp/biomapper_results/mapping_results.csv",
                    "format": "csv"
                },
                source_endpoint=None,
                target_endpoint=None,
                context=exec_context
            )
            print(f"Export result: {result4}")
        
        # Check output files
        files = os.listdir('/tmp/biomapper_results')
        if files:
            print(f'\n📁 Output files generated: {len(files)}')
            for f in files:
                size = os.path.getsize(os.path.join('/tmp/biomapper_results', f))
                print(f'   - {f}: {size:,} bytes')
        else:
            print('\n⚠️ No output files generated')
        
        print('\n✅ Pipeline test completed!')
        
    except Exception as e:
        print(f'\n❌ Error: {e}')
        import traceback
        traceback.print_exc()

asyncio.run(run_with_logging())