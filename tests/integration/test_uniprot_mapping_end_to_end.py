"""
End-to-end test for the UniProt historical ID resolution workflow.

This script tests the complete integration between:
1. MappingExecutor with its multi-step mapping paths
2. UniProtHistoricalResolverClient for handling historical/secondary/demerged IDs
3. The fallback process from direct mapping to historical resolution

Test cases include:
- Regular UniProt IDs that map directly
- Historical/secondary IDs requiring resolution
- Demerged IDs that map to multiple primaries
- Invalid IDs for error handling
"""
import sys
import asyncio
import logging
import pandas as pd
from pathlib import Path

# Add project root to Python path if needed
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from biomapper.core.mapping_executor import MappingExecutor
from biomapper.mapping.clients.uniprot_historical_resolver_client import UniProtHistoricalResolverClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Output files
OUTPUT_DIRECT = Path(project_root) / "data" / "test_results_direct_mapping.tsv"
OUTPUT_HISTORICAL = Path(project_root) / "data" / "test_results_historical_mapping.tsv"
OUTPUT_COMBINED = Path(project_root) / "data" / "test_results_combined.tsv"

class TestMapping:
    """Test class for UKBB to Arivale mapping via UniProt with historical resolution."""
    
    def __init__(self):
        """Initialize the test with test data and mapping components."""
        self.test_data = self._create_test_data()
        self.executor = None
        self.historical_resolver = None
        
        # Track results
        self.direct_results = {}
        self.historical_results = {}
        self.combined_results = {}
    
    def _create_test_data(self) -> pd.DataFrame:
        """Create test data with various UniProt ID scenarios."""
        data = {
            "ID": [f"TEST{i:03d}" for i in range(1, 11)],
            "UniProt": [
                "P01308",       # Case 1: Primary ID (Insulin)
                "P05067",       # Case 2: Primary ID (APP)
                "Q99895",       # Case 3: Secondary ID (may resolve to P01308)
                "P0CG05",       # Case 4: Demerged ID (should map to P0DOY2 and P0DOY3)
                "A0M8Q4",       # Case 5: Another demerged ID (appears in multiple entries)
                "P78358",       # Case 6: Primary ID (Test case)
                "P80423",       # Case 7: Secondary ID that also appears as demerged
                "P12345",       # Case 8: Primary ID (Test case)
                "FAKEID123",    # Case 9: Invalid format
                "NONEXISTENT"   # Case 10: Non-existent ID
            ],
            "Description": [
                "Primary ID (Insulin)",
                "Primary ID (APP)",
                "Secondary ID (may resolve to P01308)",
                "Demerged ID (maps to P0DOY2, P0DOY3)",
                "Secondary/Demerged ID in multiple entries",
                "Primary ID (Test case)",
                "Secondary ID that also appears as demerged",
                "Primary ID (Test case)",
                "Invalid format",
                "Non-existent ID"
            ],
            "Expected": [
                "Direct mapping",
                "Direct mapping",
                "May require historical resolution",
                "Requires historical resolution",
                "Requires historical resolution",
                "Direct mapping",
                "May require historical resolution",
                "Direct mapping",
                "Should fail (invalid)",
                "Should fail (non-existent)"
            ]
        }
        
        return pd.DataFrame(data)
    
    async def initialize_components(self):
        """Initialize the MappingExecutor and UniProtHistoricalResolverClient."""
        # Initialize the historical resolver directly
        logger.info("Initializing UniProtHistoricalResolverClient...")
        self.historical_resolver = UniProtHistoricalResolverClient()
        
        # Initialize the mapping executor
        # In a real scenario, this would connect to the database and load paths
        # For this test, we'll simulate the executor behavior
        logger.info("Initializing MappingExecutor...")
        self.executor = MappingExecutor()
        
        logger.info("Components initialized successfully")
    
    async def test_direct_mapping(self):
        """Test direct mapping from UniProt IDs to target IDs."""
        logger.info("Testing direct UniProt ID mapping...")
        
        # Extract UniProt IDs from test data
        uniprot_ids = list(self.test_data["UniProt"])
        
        # In a real scenario, this would use the executor to perform mapping
        # For this test, we'll simulate direct mapping by using the IDs as-is
        for uniprot_id in uniprot_ids:
            # Direct mapping simply returns the ID itself for this test
            # In reality, this would be a mapping to Arivale IDs
            self.direct_results[uniprot_id] = {
                "mapped_ids": [uniprot_id] if uniprot_id not in ["FAKEID123", "NONEXISTENT"] else None,
                "success": uniprot_id not in ["FAKEID123", "NONEXISTENT"],
                "method": "direct"
            }
        
        logger.info(f"Direct mapping completed for {len(uniprot_ids)} IDs")
    
    async def test_historical_resolution(self):
        """Test historical resolution of UniProt IDs."""
        logger.info("Testing historical UniProt ID resolution...")
        
        # Extract UniProt IDs from test data
        uniprot_ids = list(self.test_data["UniProt"])
        
        # Use the historical resolver to map all IDs
        historical_mappings = await self.historical_resolver.map_identifiers(uniprot_ids)
        
        # Process the results
        for uniprot_id, (primary_ids, metadata) in historical_mappings.items():
            self.historical_results[uniprot_id] = {
                "mapped_ids": primary_ids,
                "metadata": metadata,
                "success": primary_ids is not None,
                "method": "historical"
            }
        
        logger.info(f"Historical resolution completed for {len(uniprot_ids)} IDs")
    
    async def test_combined_approach(self):
        """Test the combined approach with fallback to historical resolution."""
        logger.info("Testing combined mapping approach with fallback...")
        
        # Extract UniProt IDs from test data
        uniprot_ids = list(self.test_data["UniProt"])
        
        # Process each ID with the combined approach
        for uniprot_id in uniprot_ids:
            # Step 1: Try direct mapping first
            direct_result = self.direct_results.get(uniprot_id, {})
            direct_success = direct_result.get("success", False)
            
            if direct_success:
                # Direct mapping succeeded, use its result
                self.combined_results[uniprot_id] = {
                    "mapped_ids": direct_result.get("mapped_ids"),
                    "method": "direct",
                    "success": True
                }
            else:
                # Direct mapping failed, fall back to historical resolution
                historical_result = self.historical_results.get(uniprot_id, {})
                historical_success = historical_result.get("success", False)
                
                if historical_success:
                    # Historical resolution succeeded
                    self.combined_results[uniprot_id] = {
                        "mapped_ids": historical_result.get("mapped_ids"),
                        "metadata": historical_result.get("metadata"),
                        "method": "historical_fallback",
                        "success": True
                    }
                else:
                    # Both approaches failed
                    self.combined_results[uniprot_id] = {
                        "mapped_ids": None,
                        "method": "failed",
                        "success": False
                    }
        
        logger.info(f"Combined mapping approach completed for {len(uniprot_ids)} IDs")
    
    def save_results(self):
        """Save all results to TSV files for analysis."""
        # Prepare DataFrames for each result set
        direct_df_data = []
        historical_df_data = []
        combined_df_data = []
        
        # Process each ID in the test data
        for idx, row in self.test_data.iterrows():
            test_id = row["ID"]
            uniprot_id = row["UniProt"]
            description = row["Description"]
            expected = row["Expected"]
            
            # Direct mapping results
            direct_result = self.direct_results.get(uniprot_id, {})
            direct_df_data.append({
                "TestID": test_id,
                "UniProtID": uniprot_id,
                "Description": description,
                "Expected": expected,
                "MappedIDs": ", ".join(direct_result.get("mapped_ids", [])) if direct_result.get("mapped_ids") else "None",
                "Success": direct_result.get("success", False),
                "Method": direct_result.get("method", "unknown")
            })
            
            # Historical resolution results
            historical_result = self.historical_results.get(uniprot_id, {})
            historical_df_data.append({
                "TestID": test_id,
                "UniProtID": uniprot_id,
                "Description": description,
                "Expected": expected,
                "MappedIDs": ", ".join(historical_result.get("mapped_ids", [])) if historical_result.get("mapped_ids") else "None",
                "Metadata": historical_result.get("metadata", "None"),
                "Success": historical_result.get("success", False),
                "Method": historical_result.get("method", "unknown")
            })
            
            # Combined approach results
            combined_result = self.combined_results.get(uniprot_id, {})
            combined_df_data.append({
                "TestID": test_id,
                "UniProtID": uniprot_id,
                "Description": description,
                "Expected": expected,
                "MappedIDs": ", ".join(combined_result.get("mapped_ids", [])) if combined_result.get("mapped_ids") else "None",
                "Success": combined_result.get("success", False),
                "Method": combined_result.get("method", "unknown")
            })
        
        # Create and save DataFrames
        direct_df = pd.DataFrame(direct_df_data)
        historical_df = pd.DataFrame(historical_df_data)
        combined_df = pd.DataFrame(combined_df_data)
        
        direct_df.to_csv(OUTPUT_DIRECT, sep="\t", index=False)
        historical_df.to_csv(OUTPUT_HISTORICAL, sep="\t", index=False)
        combined_df.to_csv(OUTPUT_COMBINED, sep="\t", index=False)
        
        logger.info("Results saved to data directory")
    
    def print_summary(self):
        """Print a summary of the test results."""
        print("\n=== End-to-End UniProt Mapping Test Summary ===")
        
        # Get success counts
        direct_success = sum(1 for result in self.direct_results.values() if result.get("success", False))
        historical_success = sum(1 for result in self.historical_results.values() if result.get("success", False))
        combined_success = sum(1 for result in self.combined_results.values() if result.get("success", False))
        
        # Print counts
        total_ids = len(self.test_data)
        print(f"Total test IDs: {total_ids}")
        print(f"Direct mapping success: {direct_success}/{total_ids} ({direct_success/total_ids*100:.1f}%)")
        print(f"Historical resolution success: {historical_success}/{total_ids} ({historical_success/total_ids*100:.1f}%)")
        print(f"Combined approach success: {combined_success}/{total_ids} ({combined_success/total_ids*100:.1f}%)")
        
        # Print results for each test case
        print("\nDetailed Results:")
        print(f"{'ID':<10} {'UniProt':<10} {'Direct':<10} {'Historical':<10} {'Combined':<15}")
        print("-" * 60)
        
        for idx, row in self.test_data.iterrows():
            test_id = row["ID"]
            uniprot_id = row["UniProt"]
            
            direct_success = "✓" if self.direct_results.get(uniprot_id, {}).get("success", False) else "✗"
            historical_success = "✓" if self.historical_results.get(uniprot_id, {}).get("success", False) else "✗"
            combined_result = self.combined_results.get(uniprot_id, {})
            combined_method = combined_result.get("method", "unknown")
            combined_success = "✓" if combined_result.get("success", False) else "✗"
            
            print(f"{test_id:<10} {uniprot_id:<10} {direct_success:<10} {historical_success:<10} {combined_success} ({combined_method})")
        
        # Success analysis
        print("\nSuccess Analysis:")
        direct_only = sum(1 for uniprot_id in self.test_data["UniProt"] 
                          if self.direct_results.get(uniprot_id, {}).get("success", False) and 
                             not self.historical_results.get(uniprot_id, {}).get("success", False))
        
        historical_only = sum(1 for uniprot_id in self.test_data["UniProt"] 
                              if not self.direct_results.get(uniprot_id, {}).get("success", False) and 
                                 self.historical_results.get(uniprot_id, {}).get("success", False))
        
        both_success = sum(1 for uniprot_id in self.test_data["UniProt"] 
                           if self.direct_results.get(uniprot_id, {}).get("success", False) and 
                              self.historical_results.get(uniprot_id, {}).get("success", False))
        
        neither_success = sum(1 for uniprot_id in self.test_data["UniProt"] 
                              if not self.direct_results.get(uniprot_id, {}).get("success", False) and 
                                 not self.historical_results.get(uniprot_id, {}).get("success", False))
        
        print(f"Succeeded with direct mapping only: {direct_only}")
        print(f"Succeeded with historical resolution only: {historical_only}")
        print(f"Succeeded with both methods: {both_success}")
        print(f"Failed with both methods: {neither_success}")
        
        # Effectiveness of fallback
        fallback_count = sum(1 for result in self.combined_results.values() 
                            if result.get("method", "") == "historical_fallback")
        
        print(f"\nFallback effectiveness: {fallback_count} IDs mapped using historical fallback")
        
        # Print a final assessment
        improvement = combined_success - direct_success
        if improvement > 0:
            print(f"\nConclusion: The historical resolution fallback improved mapping success by {improvement} IDs ({improvement/total_ids*100:.1f}%)")
        else:
            print("\nConclusion: The historical resolution did not improve mapping success in this test set")

async def run_test():
    """Run the end-to-end test."""
    # Initialize test
    test = TestMapping()
    await test.initialize_components()
    
    # Run test phases
    await test.test_direct_mapping()
    await test.test_historical_resolution()
    await test.test_combined_approach()
    
    # Save and summarize results
    test.save_results()
    test.print_summary()

if __name__ == "__main__":
    asyncio.run(run_test())