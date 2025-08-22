#!/usr/bin/env python3
"""
Debug script to trace BiomapperClient execution and identify why strategies don't execute.
"""

import os
import sys
import json
import logging
import asyncio
import httpx
from pathlib import Path
from datetime import datetime

# Setup paths
sys.path.insert(0, '/home/ubuntu/biomapper/src')
os.chdir('/home/ubuntu/biomapper')

# Enable comprehensive logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('debug')

print("="*60)
print("BIOMAPPER CLIENT EXECUTION DEBUGGER")
print("="*60)

# Step 1: Check basic environment
print("\n1. ENVIRONMENT CHECK")
print("-"*40)
print(f"Working directory: {os.getcwd()}")
print(f"Python path: {sys.path[0]}")

# Step 2: Check API server health
print("\n2. API SERVER CHECK")
print("-"*40)
try:
    import requests
    response = requests.get('http://localhost:8000/docs', timeout=2)
    print(f"API docs endpoint: {response.status_code}")
    
    # Try health endpoint
    try:
        health = requests.get('http://localhost:8000/health', timeout=2)
        print(f"Health endpoint: {health.status_code}")
        if health.status_code == 200:
            print(f"Health response: {health.json()}")
    except:
        print("No /health endpoint")
    
    # Try API info
    try:
        api_info = requests.get('http://localhost:8000/api/', timeout=2)
        print(f"API root: {api_info.status_code}")
    except:
        pass
        
except Exception as e:
    print(f"❌ API server not responding: {e}")
    sys.exit(1)

# Step 3: Check action registry
print("\n3. ACTION REGISTRY CHECK")
print("-"*40)
try:
    from actions.registry import ACTION_REGISTRY
    print(f"Total registered actions: {len(ACTION_REGISTRY)}")
    metabolite_actions = [k for k in ACTION_REGISTRY.keys() if 'METABOLITE' in k]
    print(f"Metabolite actions: {len(metabolite_actions)}")
    for action in metabolite_actions[:5]:
        print(f"  - {action}")
except Exception as e:
    print(f"❌ Cannot load action registry: {e}")

# Step 4: Check strategy file
print("\n4. STRATEGY FILE CHECK")
print("-"*40)
strategy_path = Path("src/configs/strategies/experimental/met_arv_to_ukbb_progressive_v4.0.yaml")
if strategy_path.exists():
    print(f"✅ Strategy file exists: {strategy_path}")
    print(f"   Size: {strategy_path.stat().st_size} bytes")
else:
    print(f"❌ Strategy file not found: {strategy_path}")

# Step 5: Initialize client with debug
print("\n5. CLIENT INITIALIZATION")
print("-"*40)
try:
    from client.client_v2 import BiomapperClient
    
    # Create client with debug logging
    client = BiomapperClient(base_url="http://localhost:8000")
    print(f"✅ Client created: {client.base_url}")
    
except Exception as e:
    print(f"❌ Cannot create client: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Step 6: Try to list strategies via API
print("\n6. STRATEGY LISTING (API)")
print("-"*40)
async def list_strategies_async():
    """Try to list available strategies."""
    try:
        # Try v2 endpoint
        async with httpx.AsyncClient() as http_client:
            response = await http_client.get("http://localhost:8000/api/strategies/v2/list")
            if response.status_code == 200:
                strategies = response.json()
                print(f"Available strategies (v2): {len(strategies)} found")
                if "met_arv_to_ukbb_progressive_v4.0" in [s.get('name') for s in strategies]:
                    print("✅ Our strategy is in the list!")
                else:
                    print("❌ Our strategy NOT in list")
                    print("First 5 strategies:")
                    for s in strategies[:5]:
                        print(f"  - {s.get('name', 'unknown')}")
            else:
                print(f"v2 endpoint status: {response.status_code}")
    except Exception as e:
        print(f"Cannot list strategies: {e}")
    
    # Try v1 endpoint
    try:
        async with httpx.AsyncClient() as http_client:
            response = await http_client.get("http://localhost:8000/api/strategies")
            if response.status_code == 200:
                print(f"v1 endpoint works: {response.status_code}")
    except:
        pass

asyncio.run(list_strategies_async())

# Step 7: Trace execution with minimal strategy
print("\n7. EXECUTION TRACE")
print("-"*40)

# Create a minimal test strategy
minimal_strategy = {
    "name": "debug_test",
    "steps": [
        {
            "name": "debug_step",
            "action": {
                "type": "CUSTOM_TRANSFORM",
                "params": {
                    "input_key": "dummy",
                    "output_key": "debug_output",
                    "transformations": [
                        {
                            "column": "test",
                            "expression": "print('YAML EXECUTED!'); 'success'"
                        }
                    ]
                }
            }
        }
    ]
}

print("Testing with minimal inline strategy...")

async def trace_execution():
    """Trace the execution path."""
    try:
        # Try to execute the minimal strategy
        print("\nSending execute request...")
        
        # Log the request
        logger.debug(f"Strategy: {json.dumps(minimal_strategy, indent=2)}")
        
        # Use the client's execute_strategy method
        job = await client.execute_strategy(
            strategy=minimal_strategy,
            parameters={},
            context={}
        )
        
        print(f"Job created: {job.id}")
        print(f"Job status: {job.status}")
        
        # Wait for completion
        print("\nWaiting for job completion...")
        await asyncio.sleep(2)
        
        # Check job status
        result = await client.get_job(job.id)
        print(f"Final status: {result.status}")
        
        if result.status == "completed":
            print("✅ Strategy executed successfully!")
            # Try to get results
            try:
                job_result = await client.get_job_result(job.id)
                print(f"Result: {job_result}")
            except:
                pass
        else:
            print(f"❌ Strategy did not complete: {result.status}")
            
    except Exception as e:
        print(f"❌ Execution failed: {e}")
        import traceback
        traceback.print_exc()

# Run the trace
asyncio.run(trace_execution())

# Step 8: Direct API test
print("\n8. DIRECT API TEST")
print("-"*40)

async def direct_api_test():
    """Test API directly without client."""
    try:
        async with httpx.AsyncClient() as http_client:
            # Try v2 execute endpoint
            request_data = {
                "strategy_name": "met_arv_to_ukbb_progressive_v4.0",
                "parameters": {
                    "stages_to_run": [1],
                    "debug_mode": True
                }
            }
            
            print(f"Sending request: {json.dumps(request_data, indent=2)}")
            
            response = await http_client.post(
                "http://localhost:8000/api/strategies/v2/execute",
                json=request_data,
                timeout=10
            )
            
            print(f"Response status: {response.status_code}")
            print(f"Response body: {response.text[:500]}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"Job ID: {data.get('job_id')}")
                
                # Check job status
                if data.get('job_id'):
                    await asyncio.sleep(2)
                    status_response = await http_client.get(
                        f"http://localhost:8000/api/jobs/{data['job_id']}"
                    )
                    if status_response.status_code == 200:
                        status_data = status_response.json()
                        print(f"Job status: {status_data.get('status')}")
                        print(f"Job details: {json.dumps(status_data, indent=2)[:500]}")
                        
    except Exception as e:
        print(f"Direct API test failed: {e}")
        import traceback
        traceback.print_exc()

asyncio.run(direct_api_test())

# Step 9: Check MinimalStrategyService directly
print("\n9. STRATEGY SERVICE CHECK")
print("-"*40)
try:
    from core.minimal_strategy_service import MinimalStrategyService
    
    service = MinimalStrategyService()
    print(f"✅ MinimalStrategyService loaded")
    
    # Try to load our strategy
    strategy_path = "src/configs/strategies/experimental/met_arv_to_ukbb_progressive_v4.0.yaml"
    if Path(strategy_path).exists():
        import yaml
        with open(strategy_path) as f:
            strategy_yaml = yaml.safe_load(f)
        
        print(f"Strategy name: {strategy_yaml.get('name')}")
        print(f"Steps count: {len(strategy_yaml.get('steps', []))}")
        
        # Try to execute directly (sync)
        print("\nTrying direct service execution...")
        try:
            result = service.execute_strategy(
                strategy=strategy_yaml,
                parameters={"stages_to_run": [1], "debug_mode": True}
            )
            print(f"Direct execution result: {result}")
        except Exception as e:
            print(f"Direct execution failed: {e}")
            
except Exception as e:
    print(f"Cannot test MinimalStrategyService: {e}")

print("\n" + "="*60)
print("DEBUGGING COMPLETE")
print("="*60)