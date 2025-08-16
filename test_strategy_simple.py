#!/usr/bin/env python3
"""Simple test to verify the v3.0 fix"""

import asyncio
import os
os.environ['OUTPUT_DIR'] = '/tmp/biomapper/test_v3_fix'

from biomapper.core.minimal_strategy_service import MinimalStrategyService

async def main():
    service = MinimalStrategyService(strategies_dir="/home/ubuntu/biomapper/configs/strategies")
    
    # Load and execute strategy 
    try:
        result = await service.execute_strategy("prot_arv_to_kg2c_uniprot_v3.0_progressive")
        print(f"Strategy execution result: {result}")
    except Exception as e:
        print(f"Error executing strategy: {e}")
        
        # Check what datasets were created
        if hasattr(service, 'context'):
            datasets = service.context.get('datasets', {})
            print(f"\nDatasets created before failure:")
            for key in datasets:
                print(f"  - {key}")
            
            if 'kg2c_normalized' in datasets:
                print("\n✅ kg2c_normalized was created!")
            else:
                print("\n❌ kg2c_normalized was NOT created")
                
            if 'kg2c_with_uniprot' in datasets:
                import pandas as pd
                df = pd.DataFrame(datasets['kg2c_with_uniprot']) 
                print(f"\nkg2c_with_uniprot columns: {df.columns.tolist()}")

if __name__ == "__main__":
    asyncio.run(main())