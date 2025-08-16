#!/usr/bin/env python3
"""
Simple test with logging to see what's happening
"""
import asyncio
import time
import os
import sys
from datetime import datetime

# Clear and setup output dir
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

# Enable detailed logging for the service
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    stream=sys.stdout
)

async def test_with_progress():
    print('🚀 RUNNING PIPELINE WITH PROGRESS UPDATES')
    print('=' * 60)
    
    service = MinimalStrategyService('/home/ubuntu/biomapper/configs/strategies')
    
    # Hook into the service to add progress logging
    original_execute = service.execute_strategy
    
    async def logged_execute(*args, **kwargs):
        print(f'\n⏳ Starting strategy execution at {datetime.now().strftime("%H:%M:%S")}')
        result = await original_execute(*args, **kwargs)
        print(f'✅ Strategy completed at {datetime.now().strftime("%H:%M:%S")}')
        return result
    
    service.execute_strategy = logged_execute
    
    print('\n📊 Pipeline stages:')
    print('  1. Load Arivale proteins (~1K rows)')
    print('  2. Load KG2c entities (~266K rows)')
    print('  3. Match with optimized algorithm')
    print('  4. Resolve unmapped via UniProt API')
    print('  5. Export results')
    print('  6. Sync to Google Drive')
    print('\n' + '-' * 60)
    
    start = time.time()
    
    # Add periodic progress indicator
    async def progress_indicator():
        elapsed = 0
        while elapsed < 180:  # Max 3 minutes
            await asyncio.sleep(10)
            elapsed = time.time() - start
            print(f'  ⏱️  {elapsed:.0f}s elapsed... still processing...')
            
            # Check if files are being created
            files = os.listdir(os.environ['OUTPUT_DIR'])
            if files:
                print(f'     📁 {len(files)} output files created so far')
    
    # Start progress indicator
    progress_task = asyncio.create_task(progress_indicator())
    
    try:
        # Run the actual strategy
        result = await service.execute_strategy(
            strategy_name='production_complete',
            source_endpoint_name='',
            target_endpoint_name='',
            input_identifiers=[]
        )
        
        elapsed = time.time() - start
        progress_task.cancel()
        
        print(f'\n✅ PIPELINE COMPLETED in {elapsed:.2f} seconds!')
        
        # Check output files
        files = os.listdir(os.environ['OUTPUT_DIR'])
        if files:
            print(f'\n📁 OUTPUT FILES ({len(files)}):')
            total_size = 0
            for f in files:
                size = os.path.getsize(os.path.join(os.environ['OUTPUT_DIR'], f))
                total_size += size
                print(f'  - {f}: {size:,} bytes')
            print(f'\nTotal size: {total_size:,} bytes ({total_size/1024/1024:.1f} MB)')
            
            # Check if Google Drive sync happened
            if 'gdrive_sync_summary.json' in files:
                print('\n✅ Google Drive sync completed!')
        else:
            print('\n⚠️ No output files generated - check for errors above')
            
        # Print any statistics
        if hasattr(result, '__dict__'):
            for key, value in result.__dict__.items():
                if 'statistic' in key.lower():
                    print(f'\n📊 {key}: {value}')
        
    except asyncio.CancelledError:
        pass
    except Exception as e:
        progress_task.cancel()
        elapsed = time.time() - start
        print(f'\n❌ Pipeline failed after {elapsed:.2f} seconds')
        print(f'Error: {e}')
        
        # Still check for partial output
        files = os.listdir(os.environ['OUTPUT_DIR'])
        if files:
            print(f'\n📂 Partial output ({len(files)} files):')
            for f in files:
                print(f'  - {f}')

print('\nStarting pipeline...\n')
asyncio.run(test_with_progress())