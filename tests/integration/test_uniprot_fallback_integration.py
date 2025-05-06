"""
Integration test specifically focusing on the fallback capability for UniProt mapping.

This script tests:
1. Direct mapping initially failing for certain IDs
2. Historical resolution successfully handling those IDs
3. The combined approach using the fallback mechanism correctly

Unlike the previous test, this one simulates actual mapping failures 
for certain IDs to test the fallback mechanism properly.
"""
import os
import sys
import asyncio
import logging
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Tuple
from datetime import datetime

# Add project root to Python path if needed
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from biomapper.mapping.clients.uniprot_historical_resolver_client import UniProtHistoricalResolverClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Output files
OUTPUT_DIR = Path(project_root) / "data"
OUTPUT_FILE = OUTPUT_DIR / "fallback_integration_results.tsv"

class FallbackIntegrationTest:
    """Test the fallback mechanism from direct mapping to historical resolution."""
    
    def __init__(self):
        """Initialize the integration test."""
        self.test_data = self._create_test_data()
        self.historical_resolver = None
        self.results = {}
    
    def _create_test_data(self) -> pd.DataFrame:
        """Create test data including IDs that will require fallback."""
        data = {
            "ID": [f"TEST{i:03d}" for i in range(1, 11)],
            "UniProtID": [
                "P01308",       # Case 1: Primary ID (Insulin)
                "P05067",       # Case 2: Primary ID (APP)
                "Q99895",       # Case 3: Possible secondary ID
                "P0CG05",       # Case 4: Demerged ID (maps to P0DOY2, P0DOY3)
                "A0M8Q4",       # Case 5: Secondary appearing in multiple entries
                "P78358",       # Case 6: Primary ID (test case)
                "P80423",       # Case 7: Secondary that may be demerged
                "P12345",       # Case 8: Primary ID (test case)
                "FAKEID123",    # Case 9: Invalid format
                "NONEXISTENT"   # Case 10: Non-existent ID
            ],
            "Description": [
                "Primary ID (Insulin)",
                "Primary ID (APP)",
                "Possibly secondary ID",
                "Demerged ID (maps to P0DOY2, P0DOY3)",
                "Secondary appearing in multiple entries",
                "Primary ID (test case)",
                "Secondary that may be demerged",
                "Primary ID (test case)",
                "Invalid format",
                "Non-existent ID"
            ],
            # Simulate direct mapping failures for certain IDs
            "DirectMappingFailure": [
                False,   # P01308 - Direct mapping works
                False,   # P05067 - Direct mapping works
                True,    # Q99895 - Direct mapping fails (simulate secondary ID issue)
                True,    # P0CG05 - Direct mapping fails (simulate demerged ID issue)
                True,    # A0M8Q4 - Direct mapping fails (simulate secondary ID issue)
                False,   # P78358 - Direct mapping works
                True,    # P80423 - Direct mapping fails (simulate secondary ID issue)
                False,   # P12345 - Direct mapping works
                True,    # FAKEID123 - Direct mapping fails (invalid ID)
                True     # NONEXISTENT - Direct mapping fails (non-existent ID)
            ]
        }
        
        return pd.DataFrame(data)
    
    async def initialize_components(self):
        """Initialize the components needed for the test."""
        logger.info("Initializing components...")
        self.historical_resolver = UniProtHistoricalResolverClient()
        logger.info("Components initialized successfully")
    
    async def simulate_direct_mapping(self, uniprot_id: str) -> Tuple[Optional[List[str]], bool]:
        """Simulate direct mapping for a UniProt ID.
        
        Args:
            uniprot_id: The UniProt ID to map directly.
            
        Returns:
            Tuple containing:
            - List of mapped IDs or None if mapping failed
            - Boolean indicating if mapping was successful
        """
        # Look up whether this ID is configured to fail direct mapping
        is_failure = self.test_data.loc[
            self.test_data["UniProtID"] == uniprot_id, "DirectMappingFailure"
        ].iloc[0]
        
        if is_failure:
            # Simulate mapping failure
            return None, False
        else:
            # Simulate successful mapping (for simplicity, just return the ID itself)
            return [uniprot_id], True
    
    async def run_test(self):
        """Run the integration test with fallback."""
        # Initialize components
        await self.initialize_components()
        
        # Extract UniProt IDs from test data
        uniprot_ids = list(self.test_data["UniProtID"])
        
        logger.info(f"Running fallback integration test with {len(uniprot_ids)} UniProt IDs")
        
        # Process each ID
        for idx, row in self.test_data.iterrows():
            test_id = row["ID"]
            uniprot_id = row["UniProtID"]
            description = row["Description"]
            
            # Initialize result entry
            result_entry = {
                "TestID": test_id,
                "UniProtID": uniprot_id,
                "Description": description
            }
            
            # Step 1: Try direct mapping
            logger.info(f"Testing direct mapping for {test_id} (UniProt: {uniprot_id})")
            direct_mapped_ids, direct_success = await self.simulate_direct_mapping(uniprot_id)
            
            result_entry["DirectMappedIDs"] = direct_mapped_ids
            result_entry["DirectSuccess"] = direct_success
            
            # Step 2: If direct mapping fails, try historical resolution
            if not direct_success:
                logger.info(f"Direct mapping failed for {test_id}, trying historical resolution")
                
                # Use the historical resolver
                historical_result = await self.historical_resolver.map_identifiers([uniprot_id])
                
                # Process the result
                primary_ids, metadata = historical_result.get(uniprot_id, (None, None))
                historical_success = primary_ids is not None and len(primary_ids) > 0
                
                result_entry["HistoricalIDs"] = primary_ids
                result_entry["HistoricalMetadata"] = metadata
                result_entry["HistoricalSuccess"] = historical_success
                
                # Determine final result
                if historical_success:
                    result_entry["FinalIDs"] = primary_ids
                    result_entry["MappingPath"] = "HistoricalFallback"
                    result_entry["FinalSuccess"] = True
                else:
                    result_entry["FinalIDs"] = None
                    result_entry["MappingPath"] = "Failed"
                    result_entry["FinalSuccess"] = False
            else:
                # Direct mapping succeeded
                result_entry["HistoricalIDs"] = None
                result_entry["HistoricalMetadata"] = None
                result_entry["HistoricalSuccess"] = None
                result_entry["FinalIDs"] = direct_mapped_ids
                result_entry["MappingPath"] = "Direct"
                result_entry["FinalSuccess"] = True
            
            # Store the result
            self.results[test_id] = result_entry
        
        logger.info("Fallback integration test completed")
    
    def save_results(self):
        """Save the test results to a TSV file."""
        # Convert results to DataFrame
        results_df = pd.DataFrame.from_dict(self.results, orient="index")
        
        # Process the DataFrame for better readability
        for col in ["DirectMappedIDs", "HistoricalIDs", "FinalIDs"]:
            if col in results_df.columns:
                results_df[col] = results_df[col].apply(
                    lambda x: ", ".join(x) if isinstance(x, list) else str(x)
                )
        
        # Save to file
        results_df.to_csv(OUTPUT_FILE, sep="\t")
        logger.info(f"Results saved to {OUTPUT_FILE}")
    
    def print_summary(self):
        """Print a summary of the test results."""
        print("\n=== UniProt Mapping Fallback Integration Test Summary ===")
        
        # Count successes and failures
        total_count = len(self.results)
        
        direct_success_count = sum(1 for r in self.results.values() if r.get("DirectSuccess", False))
        direct_failure_count = total_count - direct_success_count
        
        historical_attempted = sum(1 for r in self.results.values() if r.get("HistoricalSuccess") is not None)
        historical_success_count = sum(1 for r in self.results.values() 
                                     if r.get("HistoricalSuccess", False))
        historical_failure_count = historical_attempted - historical_success_count
        
        final_success_count = sum(1 for r in self.results.values() if r.get("FinalSuccess", False))
        final_failure_count = total_count - final_success_count
        
        # Print statistics
        print(f"Total test cases: {total_count}")
        print("\nDirect Mapping Results:")
        print(f"  Success: {direct_success_count}/{total_count} ({direct_success_count/total_count*100:.1f}%)")
        print(f"  Failure: {direct_failure_count}/{total_count} ({direct_failure_count/total_count*100:.1f}%)")
        
        print("\nHistorical Resolution Results (for Direct Mapping failures):")
        print(f"  Attempted: {historical_attempted}/{direct_failure_count} ({historical_attempted/direct_failure_count*100 if direct_failure_count else 0:.1f}%)")
        print(f"  Success: {historical_success_count}/{historical_attempted} ({historical_success_count/historical_attempted*100 if historical_attempted else 0:.1f}%)")
        print(f"  Failure: {historical_failure_count}/{historical_attempted} ({historical_failure_count/historical_attempted*100 if historical_attempted else 0:.1f}%)")
        
        print("\nFinal Results (after fallback):")
        print(f"  Success: {final_success_count}/{total_count} ({final_success_count/total_count*100:.1f}%)")
        print(f"  Failure: {final_failure_count}/{total_count} ({final_failure_count/total_count*100:.1f}%)")
        
        # Calculate fallback effectiveness
        fallback_success_count = sum(1 for r in self.results.values() 
                                    if r.get("MappingPath") == "HistoricalFallback" 
                                    and r.get("FinalSuccess", False))
        
        fallback_effectiveness = (fallback_success_count / direct_failure_count * 100) if direct_failure_count else 0
        improvement_pct = (fallback_success_count / total_count * 100)
        
        print(f"\nFallback Effectiveness: {fallback_success_count}/{direct_failure_count} direct mapping failures successfully handled via historical resolution ({fallback_effectiveness:.1f}%)")
        print(f"Overall Improvement: Historical resolution improved total mapping success by {improvement_pct:.1f}%")
        
        # Print detailed results
        print("\nDetailed Results:")
        print(f"{'ID':<10} {'UniProt':<12} {'Direct':<8} {'Historical':<12} {'Final Path':<16} {'Success':<8}")
        print("-" * 70)
        
        for test_id, result in self.results.items():
            uniprot_id = result.get("UniProtID", "N/A")
            direct = "✓" if result.get("DirectSuccess", False) else "✗"
            
            # Historical resolution may not have been attempted
            if result.get("HistoricalSuccess") is not None:
                historical = "✓" if result.get("HistoricalSuccess", False) else "✗"
            else:
                historical = "N/A"
                
            path = result.get("MappingPath", "Unknown")
            success = "✓" if result.get("FinalSuccess", False) else "✗"
            
            print(f"{test_id:<10} {uniprot_id:<12} {direct:<8} {historical:<12} {path:<16} {success:<8}")
        
        # List successful fallbacks
        if fallback_success_count > 0:
            print("\nIDs successfully mapped via historical resolution fallback:")
            for test_id, result in self.results.items():
                if result.get("MappingPath") == "HistoricalFallback" and result.get("FinalSuccess", False):
                    uniprot_id = result.get("UniProtID", "N/A")
                    metadata = result.get("HistoricalMetadata", "N/A")
                    final_ids = result.get("FinalIDs", [])
                    final_ids_str = ", ".join(final_ids) if isinstance(final_ids, list) else str(final_ids)
                    
                    print(f"  {test_id} (UniProt: {uniprot_id}) -> {final_ids_str} [{metadata}]")

async def run_test():
    """Run the fallback integration test."""
    # Create and run the test
    test = FallbackIntegrationTest()
    await test.run_test()
    
    # Save and summarize results
    test.save_results()
    test.print_summary()

if __name__ == "__main__":
    asyncio.run(run_test())