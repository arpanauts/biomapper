#!/usr/bin/env python3
"""Test API execution on port 8001."""

from src.client.client_v2 import BiomapperClient

def test_metabolomics():
    """Test metabolomics pipeline with stages parameter."""
    
    # Use port 8001
    client = BiomapperClient(base_url="http://localhost:8001")
    
    print("Testing metabolomics pipeline on port 8001...")
    print("-" * 60)
    
    # Run with just stage 1
    result = client.run(
        "met_arv_to_ukbb_progressive_v4.0",
        parameters={
            "stages_to_run": [1],
            "debug_mode": True,
            "verbose_logging": True,
            "output_dir": "/tmp/biomapper/test_8001"
        }
    )
    
    print(f"\nExecution completed!")
    print(f"Success: {result.success}")
    
    if result.success:
        print("\n✅ SUCCESS! Pipeline executed.")
        
        # Check results
        if result.result_data:
            print(f"\nResult keys: {list(result.result_data.keys())[:10]}")
            
            if "datasets" in result.result_data:
                datasets = result.result_data["datasets"]
                print(f"\nDatasets created: {list(datasets.keys())}")
                
                for key, data in datasets.items():
                    if isinstance(data, list):
                        print(f"  {key}: {len(data)} items")
                    elif isinstance(data, dict):
                        if "_row_count" in data:
                            print(f"  {key}: {data['_row_count']} rows")
                        else:
                            print(f"  {key}: dict with {len(data)} keys")
            
            if "statistics" in result.result_data:
                stats = result.result_data["statistics"]
                if stats:
                    print(f"\nStatistics: {stats}")
            
            if "output_files" in result.result_data:
                files = result.result_data["output_files"]
                if files:
                    print(f"\nOutput files: {list(files.keys())}")
    else:
        print(f"\n❌ FAILED: {result.error}")
        
    return result

if __name__ == "__main__":
    result = test_metabolomics()
    exit(0 if result.success else 1)