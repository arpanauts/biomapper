#!/usr/bin/env python3
"""Test Stage 1 coverage with simple strategy."""

from src.client.client_v2 import BiomapperClient

def main():
    client = BiomapperClient(base_url="http://localhost:8001")
    
    print("="*60)
    print("STAGE 1 REAL COVERAGE TEST")
    print("="*60)
    
    result = client.run("test_stage1_only")
    
    if result.success:
        print("✅ Stage 1 executed successfully!")
        
        if result.result_data and "datasets" in result.result_data:
            datasets = result.result_data["datasets"]
            
            # Get counts
            arivale_count = len(datasets.get("arivale_data", [])) 
            ref_count = len(datasets.get("reference_data", []))
            matched_count = len(datasets.get("stage_1_matched", []))
            
            print(f"\nArivale metabolites: {arivale_count}")
            print(f"UKBB reference: {ref_count}")
            print(f"Matched: {matched_count}")
            
            if ref_count > 0:
                coverage = (matched_count / ref_count) * 100
                print(f"\n📊 ACTUAL STAGE 1 COVERAGE: {coverage:.1f}%")
                print(f"\nClaimed: 57.9%")
                print(f"Actual:  {coverage:.1f}%")
                
                if coverage < 20:
                    print("\n⚠️ ACTUAL COVERAGE IS ~3X LOWER THAN CLAIMED!")
    else:
        print(f"❌ Failed: {result.error}")

if __name__ == "__main__":
    main()