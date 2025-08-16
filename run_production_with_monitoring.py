#!/usr/bin/env python3
"""
Run production pipeline with extended timeout and progress monitoring
"""
import asyncio
import threading
import time
from datetime import datetime
from biomapper_client.client_v2 import BiomapperClient
import os
import httpx

def monitor_progress(stop_event):
    """Monitor output directory for progress"""
    output_dir = '/tmp/biomapper_results'
    
    print("\n📊 Progress Monitor Started")
    print("-" * 50)
    
    while not stop_event.is_set():
        try:
            # Check for files in output directory
            if os.path.exists(output_dir):
                files = os.listdir(output_dir)
                if files:
                    total_size = sum(os.path.getsize(os.path.join(output_dir, f)) 
                                   for f in files if os.path.isfile(os.path.join(output_dir, f)))
                    
                    print(f"\r⏱️  {datetime.now().strftime('%H:%M:%S')} | "
                          f"📁 Files: {len(files)} | "
                          f"💾 Size: {total_size:,} bytes", end='', flush=True)
                else:
                    print(f"\r⏱️  {datetime.now().strftime('%H:%M:%S')} | "
                          f"⏳ Processing... (no output files yet)", end='', flush=True)
            
            # Also try to check server health
            try:
                response = httpx.get('http://127.0.0.1:8000/api/health', timeout=2)
                if response.status_code == 200:
                    print(" | ✅ Server responding", end='', flush=True)
            except:
                print(" | ⚠️  Server busy", end='', flush=True)
                
        except Exception as e:
            print(f"\r⚠️  Monitor error: {e}", end='', flush=True)
        
        time.sleep(5)  # Check every 5 seconds

async def run_with_extended_timeout():
    """Run the production pipeline with extended timeout"""
    
    # Setup environment
    os.environ['OUTPUT_DIR'] = '/tmp/biomapper_results'
    os.environ['TIMESTAMP'] = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    os.makedirs(os.environ['OUTPUT_DIR'], exist_ok=True)
    
    # Clear any previous results
    for f in os.listdir(os.environ['OUTPUT_DIR']):
        os.remove(os.path.join(os.environ['OUTPUT_DIR'], f))
    
    print("🚀 STARTING PRODUCTION PIPELINE WITH EXTENDED TIMEOUT")
    print("=" * 60)
    print(f"📊 Configuration:")
    print(f"   - Timeout: 30 minutes (1800 seconds)")
    print(f"   - Strategy: simple_production_with_gdrive_demo")
    print(f"   - Source: 1,197 Arivale proteins")
    print(f"   - Target: 266,487 KG2c entities")
    print(f"   - Output: {os.environ['OUTPUT_DIR']}")
    print("=" * 60)
    
    # Start progress monitor in background thread
    stop_monitor = threading.Event()
    monitor_thread = threading.Thread(target=monitor_progress, args=(stop_monitor,))
    monitor_thread.daemon = True
    monitor_thread.start()
    
    # Initialize client with extended timeout
    # Using httpx client with custom timeout
    http_client = httpx.AsyncClient(
        timeout=httpx.Timeout(
            connect=10.0,
            read=1800.0,  # 30 minutes read timeout
            write=30.0,
            pool=10.0
        )
    )
    
    client = BiomapperClient('http://127.0.0.1:8000')
    client._client = http_client  # Override the default client
    
    start_time = time.time()
    
    try:
        print("\n🔄 Executing strategy (this may take up to 30 minutes)...")
        print("   Progress will be shown below:\n")
        
        # Run the strategy with extended timeout
        result = await client._async_run(
            strategy='simple_production_with_gdrive_demo',
            parameters={},
            context={},
            wait=True,
            watch=False  # Don't use SSE watching for now
        )
        
        elapsed = time.time() - start_time
        
        print(f"\n\n✅ PIPELINE COMPLETED in {elapsed/60:.1f} minutes!")
        print("=" * 60)
        print(f"Job ID: {result.job_id}")
        print(f"Status: {result.status}")
        
        if result.statistics:
            print("\n📊 RESULTS:")
            for action, stats in result.statistics.items():
                if isinstance(stats, dict) and stats:
                    print(f"  {action}: {stats}")
        
        if result.output_files:
            print(f"\n📁 OUTPUT FILES: {len(result.output_files)}")
            for f in result.output_files[:5]:
                print(f"  - {f}")
        
        print("\n🎉 SUCCESS! Check Google Drive for uploaded results.")
        
    except asyncio.TimeoutError:
        elapsed = time.time() - start_time
        print(f"\n\n⏱️ TIMEOUT after {elapsed/60:.1f} minutes")
        print("Consider increasing timeout to 60 minutes or implementing chunking.")
        
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"\n\n❌ FAILED after {elapsed/60:.1f} minutes")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Stop the monitor
        stop_monitor.set()
        monitor_thread.join(timeout=1)
        
        # Check what was produced
        if os.path.exists(os.environ['OUTPUT_DIR']):
            files = os.listdir(os.environ['OUTPUT_DIR'])
            if files:
                print(f"\n📂 Partial results saved: {len(files)} files")
                for f in files:
                    size = os.path.getsize(os.path.join(os.environ['OUTPUT_DIR'], f))
                    print(f"  - {f} ({size:,} bytes)")

if __name__ == "__main__":
    asyncio.run(run_with_extended_timeout())