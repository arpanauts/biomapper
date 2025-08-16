#!/usr/bin/env python3
"""
Simple test of v2.2 strategy using direct API calls.
"""

import json
import time
import requests
from pathlib import Path


def test_v2_2_strategy():
    """Test v2.2 strategy with sample data."""
    
    # API base URL
    base_url = "http://localhost:8000"
    
    # Create sample test files
    sample_dir = Path("/tmp/biomapper_v2.2_test")
    sample_dir.mkdir(parents=True, exist_ok=True)
    
    # Small sample of Arivale proteins
    arivale_sample = sample_dir / "arivale_sample.txt"
    arivale_sample.write_text("""uniprot_id\tname\txrefs
P12345\tProtein 1\tENSG001
Q67890,Q11111\tProtein 2\tENSG002;ENSG003
A12345\tProtein 3\t
B67890\tProtein 4\tENSG004
P00533\tEGFR\tENSG00000146648
""")
    
    # Small sample of KG2C entities  
    kg2c_sample = sample_dir / "kg2c_sample.tsv"
    kg2c_sample.write_text("""id\tname\tcategory
P12345\tProtein 1\tprotein
Q67890\tProtein 2 variant\tprotein
P00533\tEpidermal growth factor receptor\tprotein
ENSG00000146648\tEGFR gene\tgene
UniProtKB:P00533\tEGFR UniProt\tprotein
""")
    
    print(f"Created sample files in {sample_dir}")
    
    # Prepare request - parameters must match the YAML parameter names exactly
    request_body = {
        "strategy": "prot_arv_to_kg2c_uniprot_v2.2_integrated",
        "parameters": {
            # These override the defaults in the YAML
            "source_file": str(arivale_sample),
            "target_file": str(kg2c_sample),
            "output_dir": str(sample_dir / "output"),
            "min_confidence": 0.6,
            "high_confidence_threshold": 0.8,
            "enable_composite_parsing": False,  # Disable for quick test
            "enable_one_to_many_tracking": False,
            "enable_visualizations": False,
            "enable_html_report": False,
            "enable_google_drive_sync": False,
            "arivale_id_column": "uniprot_id",
            "kg2c_id_column": "id",
            "kg2c_name_column": "name",
            "kg2c_category_column": "category"
        },
        "options": {
            "checkpoint_enabled": False,
            "timeout_seconds": 60
        }
    }
    
    print("\nSubmitting v2.2 strategy to API...")
    
    # Submit job
    response = requests.post(
        f"{base_url}/api/strategies/v2/execute",
        json=request_body
    )
    
    if response.status_code != 200:
        print(f"❌ Failed to submit job: {response.status_code}")
        print(response.text)
        return False
        
    job_data = response.json()
    job_id = job_data.get("job_id")
    print(f"✅ Job submitted: {job_id}")
    
    # Poll for completion
    print("\nWaiting for job completion...")
    max_attempts = 30
    for i in range(max_attempts):
        time.sleep(2)
        
        # Check status
        status_response = requests.get(
            f"{base_url}/api/strategies/v2/jobs/{job_id}/status"
        )
        
        if status_response.status_code == 200:
            status_data = status_response.json()
            status = status_data.get("status")
            print(f"  Status: {status}")
            
            if status == "completed":
                print("\n✅ Job completed successfully!")
                
                # Get results
                results_response = requests.get(
                    f"{base_url}/api/strategies/v2/jobs/{job_id}/results"
                )
                
                if results_response.status_code == 200:
                    results = results_response.json()
                    
                    # Check outputs
                    output_dir = Path(sample_dir / "output")
                    if output_dir.exists():
                        files = list(output_dir.glob("*"))
                        print(f"\nGenerated {len(files)} output files:")
                        for f in files[:5]:
                            print(f"  - {f.name} ({f.stat().st_size} bytes)")
                            
                    # Show statistics if available
                    if "statistics" in results:
                        print("\nStatistics:")
                        stats = results["statistics"]
                        if isinstance(stats, dict):
                            for key, value in list(stats.items())[:5]:
                                print(f"  {key}: {value}")
                                
                return True
                
            elif status in ["failed", "error"]:
                print(f"\n❌ Job failed: {status}")
                print(f"Error: {status_data.get('error', 'Unknown error')}")
                
                # Try to get more details
                results_response = requests.get(
                    f"{base_url}/api/strategies/v2/jobs/{job_id}/results"
                )
                if results_response.status_code == 200:
                    results = results_response.json()
                    if "error" in results:
                        print(f"Detailed error: {results['error']}")
                    if "traceback" in results:
                        print(f"Traceback: {results['traceback'][:500]}")
                        
                return False
                
    print("\n⚠️ Job timed out")
    return False


if __name__ == "__main__":
    success = test_v2_2_strategy()
    
    if success:
        print("\n✅ V2.2 strategy test passed!")
        print("Ready for full production test.")
    else:
        print("\n❌ V2.2 strategy test failed.")
        print("Check the logs and fix issues before production test.")