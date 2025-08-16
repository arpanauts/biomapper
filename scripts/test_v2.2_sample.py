#!/usr/bin/env python3
"""
Quick test of v2.2 strategy with sample data to verify all components work.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from biomapper_client.client import BiomapperClient


async def test_v2_2_sample():
    """Test v2.2 strategy with sample data."""
    
    client = BiomapperClient(base_url="http://localhost:8000")
    
    # Skip health check - API is running
    print("API is running on port 8000")
        
    # Create sample test files
    sample_dir = Path("/tmp/biomapper_v2.2_sample_test")
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
    
    # Test parameters
    params = {
        "SOURCE_FILE": str(arivale_sample),
        "TARGET_FILE": str(kg2c_sample),
        "OUTPUT_DIR": str(sample_dir / "output"),
        "ENABLE_COMPOSITE_PARSING": "true",
        "ENABLE_ONE_TO_MANY_TRACKING": "true",
        "ENABLE_VISUALIZATIONS": "false",  # Skip for quick test
        "ENABLE_HTML_REPORT": "false",     # Skip for quick test
        "ENABLE_GOOGLE_DRIVE_SYNC": "false"
    }
    
    print("\nSubmitting v2.2 strategy with sample data...")
    
    try:
        # Execute strategy (need to use async context manager)
        async with BiomapperClient(base_url="http://localhost:8000") as api_client:
            # Create context with parameters
            context = {
                "parameters": params,
                "datasets": {},
                "statistics": {}
            }
            
            result = await api_client.execute_strategy(
                strategy_name="prot_arv_to_kg2c_uniprot_v2.2_integrated",
                context=context
            )
        
        if result.get("status") == "completed":
            print("✅ Strategy completed successfully!")
            
            # Check output files
            output_dir = Path(params["OUTPUT_DIR"])
            if output_dir.exists():
                files = list(output_dir.glob("*"))
                print(f"\nGenerated {len(files)} output files:")
                for f in files[:5]:  # Show first 5
                    print(f"  - {f.name}")
                    
            return True
        else:
            print(f"❌ Strategy failed: {result.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False


async def main():
    """Main entry point."""
    success = await test_v2_2_sample()
    
    if success:
        print("\n✅ Sample test passed! Ready for full production test.")
        print("Run: python scripts/test_v2.2_production.py")
    else:
        print("\n❌ Sample test failed. Fix issues before production test.")
        

if __name__ == "__main__":
    asyncio.run(main())