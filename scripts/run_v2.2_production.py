#!/usr/bin/env python3
"""
Run v2.2 strategy with production datasets using the hard-coded paths in YAML.
"""

import json
import time
import requests
from pathlib import Path
from datetime import datetime


def run_production_test():
    """Run v2.2 strategy with production data."""
    
    print("=" * 80)
    print("RUNNING V2.2 STRATEGY WITH PRODUCTION DATA")
    print("=" * 80)
    
    # The strategy YAML has the production file paths hard-coded:
    # - source_file: /procedure/data/local_data/ARIVALE_SNAPSHOTS/proteomics_metadata.tsv
    # - target_file: /procedure/data/local_data/MAPPING_ONTOLOGIES/kg2c_ontologies/kg2c_proteins.csv
    # - output_dir: /tmp/biomapper/protein_mapping_v2.2
    
    # Check if input files exist
    source_file = Path("/procedure/data/local_data/ARIVALE_SNAPSHOTS/proteomics_metadata.tsv")
    target_file = Path("/procedure/data/local_data/MAPPING_ONTOLOGIES/kg2c_ontologies/kg2c_proteins.csv")
    
    if not source_file.exists():
        print(f"❌ Source file not found: {source_file}")
        return False
        
    if not target_file.exists():
        print(f"❌ Target file not found: {target_file}")
        return False
        
    # Count lines in files
    with open(source_file) as f:
        source_lines = sum(1 for _ in f) - 1  # Subtract header
    with open(target_file) as f:
        target_lines = sum(1 for _ in f) - 1  # Subtract header
        
    print(f"✅ Source file: {source_lines:,} Arivale proteins")
    print(f"✅ Target file: {target_lines:,} KG2C entities")
    
    # API endpoint
    base_url = "http://localhost:8000"
    
    # Submit job - no parameters needed since they're hard-coded in YAML
    request_body = {
        "strategy": "prot_arv_to_kg2c_uniprot_v2.2_integrated",
        "parameters": {},  # Empty - use YAML defaults
        "options": {
            "checkpoint_enabled": False,
            "timeout_seconds": 600  # 10 minutes for production data
        }
    }
    
    print(f"\nSubmitting v2.2 strategy job...")
    start_time = time.time()
    
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
    print("\nMonitoring job progress...")
    max_attempts = 300  # 10 minutes with 2-second intervals
    last_status = None
    
    for i in range(max_attempts):
        time.sleep(2)
        
        # Check status
        status_response = requests.get(
            f"{base_url}/api/strategies/v2/jobs/{job_id}/status"
        )
        
        if status_response.status_code == 200:
            status_data = status_response.json()
            status = status_data.get("status")
            
            if status != last_status:
                elapsed = int(time.time() - start_time)
                print(f"  [{elapsed}s] Status: {status}")
                last_status = status
            
            if status == "completed":
                total_time = time.time() - start_time
                print(f"\n✅ Job completed successfully in {total_time:.1f} seconds!")
                
                # Get results
                results_response = requests.get(
                    f"{base_url}/api/strategies/v2/jobs/{job_id}/results"
                )
                
                if results_response.status_code == 200:
                    results = results_response.json()
                    
                    # Check output files
                    output_dir = Path("/tmp/biomapper/protein_mapping_v2.2")
                    if output_dir.exists():
                        print(f"\n📁 Output directory: {output_dir}")
                        
                        # List key output files
                        key_files = [
                            "all_mappings.tsv",
                            "high_confidence_mappings.tsv",
                            "mapping_summary.json",
                            "mapping_report.html",
                            "mapping_report.pdf"
                        ]
                        
                        print("\n📄 Output Files:")
                        for filename in key_files:
                            filepath = output_dir / filename
                            if filepath.exists():
                                size = filepath.stat().st_size
                                print(f"  ✅ {filename}: {size:,} bytes")
                            else:
                                print(f"  ⚠️ {filename}: Not found")
                                
                        # Check visualization directory
                        viz_dir = output_dir / "visualizations"
                        if viz_dir.exists():
                            viz_files = list(viz_dir.glob("*"))
                            print(f"\n📊 Visualizations: {len(viz_files)} files generated")
                            for vf in viz_files[:5]:
                                print(f"  - {vf.name}")
                                
                    # Show summary statistics
                    summary_file = output_dir / "mapping_summary.json"
                    if summary_file.exists():
                        with open(summary_file) as f:
                            summary = json.load(f)
                            
                        print("\n📈 Mapping Statistics:")
                        if "statistics" in summary:
                            stats = summary["statistics"]
                            if "total_input" in stats:
                                total = stats["total_input"]
                                direct = stats.get("direct_match", 0)
                                unmapped = stats.get("unmapped", 0)
                                
                                print(f"  Total Input: {total:,}")
                                print(f"  Direct Matches: {direct:,} ({(direct/total)*100:.1f}%)")
                                print(f"  Unmapped: {unmapped:,} ({(unmapped/total)*100:.1f}%)")
                                
                                if "one_to_many_count" in stats:
                                    print(f"  One-to-Many: {stats['one_to_many_count']:,}")
                                if "expansion_factor" in stats:
                                    print(f"  Expansion Factor: {stats['expansion_factor']:.2f}")
                                    
                return True
                
            elif status in ["failed", "error"]:
                print(f"\n❌ Job failed: {status}")
                print(f"Error: {status_data.get('error', 'Unknown error')}")
                
                # Get detailed error
                results_response = requests.get(
                    f"{base_url}/api/strategies/v2/jobs/{job_id}/results"
                )
                if results_response.status_code == 200:
                    results = results_response.json()
                    if "error" in results:
                        print(f"Details: {results['error']}")
                        
                return False
                
    print("\n⚠️ Job timed out after 10 minutes")
    return False


if __name__ == "__main__":
    success = run_production_test()
    
    if success:
        print("\n" + "=" * 80)
        print("🎉 V2.2 PRODUCTION TEST COMPLETED SUCCESSFULLY!")
        print("=" * 80)
        print("\nNext steps:")
        print("1. Review the generated reports and visualizations")
        print("2. Validate the mapping statistics")
        print("3. Test Google Drive sync if needed")
        print("4. Propagate enhancements to other strategies")
    else:
        print("\n" + "=" * 80)
        print("❌ V2.2 PRODUCTION TEST FAILED")
        print("=" * 80)
        print("\nCheck the logs and fix any issues before proceeding.")