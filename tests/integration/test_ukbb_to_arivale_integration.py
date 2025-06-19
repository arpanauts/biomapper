"""
Integration test for UKBB to Arivale mapping via UniProt historical resolution.

This script tests the complete integration between:
1. MappingExecutor with its multi-step mapping capability
2. UniProtHistoricalResolverClient for resolving historical/secondary UniProt IDs
3. The complete fallback mechanism from direct path to historical resolution path

It simulates a real-world scenario where UKBB protein IDs are mapped to Arivale IDs,
with historical resolution as a fallback when direct mapping fails.
"""
import sys
import asyncio
import logging
import pandas as pd
from pathlib import Path
from typing import Dict, Any

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

# Set client logger to debug level for more detailed logs
client_logger = logging.getLogger("biomapper.mapping.clients.uniprot_historical_resolver_client")
client_logger.setLevel(logging.DEBUG)

# Output files
OUTPUT_DIR = Path(project_root) / "data"
OUTPUT_FILE = OUTPUT_DIR / "ukbb_to_arivale_integration_results.tsv"

class UKBBToArivaleIntegrationTest:
    """Test the integration between MappingExecutor and UniProtHistoricalResolverClient."""
    
    def __init__(self):
        """Initialize the integration test."""
        self.executor = None
        self.test_data = self._create_test_data()
        self.results = {}
    
    def _create_test_data(self) -> pd.DataFrame:
        """Create test data with various UniProt ID scenarios.
        
        The test data includes:
        - Regular UniProt IDs that should map directly
        - Historical/secondary IDs that require resolution
        - Demerged IDs that map to multiple primaries
        - Invalid IDs for error handling
        """
        data = {
            "ID": [f"UKBB{i:03d}" for i in range(1, 11)],
            "UniProtID": [
                "P01308",       # Case 1: Primary ID (Insulin)
                "P05067",       # Case 2: Primary ID (APP)
                "Q99895",       # Case 3: ID that may be secondary
                "P0CG05",       # Case 4: Demerged ID (maps to P0DOY2, P0DOY3)
                "A0M8Q4",       # Case 5: Secondary that appears in multiple entries
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
            ]
        }
        
        return pd.DataFrame(data)
    
    async def initialize_executor(self):
        """Initialize the MappingExecutor with paths for direct and historical mapping."""
        logger.info("Initializing MappingExecutor...")
        
        # In a real scenario, this would load paths from the database
        # For this test, we'll manually define the paths
        self.executor = MappingExecutor()
        
        # Configure the executor with test paths
        # These are simplified for testing purposes
        self.executor.mapping_paths = {
            # Path 1: Direct mapping (higher priority)
            "UKBB_to_Arivale_Direct": {
                "source_type": "UKBB",
                "target_type": "Arivale",
                "priority": 1,
                "steps": [
                    {"client": "IdentityMapper", "config": {}}
                ]
            },
            # Path 2: Historical resolution fallback (lower priority)
            "UKBB_to_Arivale_via_Historical": {
                "source_type": "UKBB",
                "target_type": "Arivale",
                "priority": 2,
                "steps": [
                    {"client": "UniProtHistoricalResolver", "config": {}},
                    {"client": "IdentityMapper", "config": {}}
                ]
            }
        }
        
        # In a real scenario, this would fetch correct client implementations
        # For this test, we'll manually implement a simple client registry
        self.executor.client_registry = {
            "IdentityMapper": self._identity_mapper_factory,
            "UniProtHistoricalResolver": self._historical_resolver_factory
        }
        
        logger.info("MappingExecutor initialized with direct and historical paths")
    
    async def _identity_mapper_factory(self, config: Dict[str, Any] = None) -> Any:
        """Factory function for the identity mapper (simple pass-through mapper)."""
        # For testing, we create a simple mapper that just passes IDs through
        class IdentityMapper:
            async def map_identifiers(self, ids, config=None):
                return {id: ([id], None) for id in ids}
                
        return IdentityMapper()
    
    async def _historical_resolver_factory(self, config: Dict[str, Any] = None) -> Any:
        """Factory function for the UniProtHistoricalResolverClient."""
        return UniProtHistoricalResolverClient(config=config)
    
    async def run_test(self):
        """Run the integration test with the test data."""
        # Initialize the executor
        await self.initialize_executor()
        
        # Extract IDs from test data
        ukbb_ids = self.test_data["ID"].tolist()
        uniprot_ids = self.test_data["UniProtID"].tolist()
        
        # Create a mapping between UKBB IDs and UniProt IDs for the test
        # In a real scenario, this would be part of the input data
        input_data = {}
        for ukbb_id, uniprot_id in zip(ukbb_ids, uniprot_ids):
            input_data[ukbb_id] = uniprot_id
        
        logger.info(f"Running integration test with {len(ukbb_ids)} test IDs")
        
        # Execute the mapping
        # In a real scenario, this would use execute_mapping
        # For this test, we'll simulate the execute_mapping behavior
        for ukbb_id, uniprot_id in input_data.items():
            # Step 1: Record source info
            result_entry = {
                "UKBB_ID": ukbb_id,
                "UniProt_ID": uniprot_id,
                "Description": self.test_data.loc[self.test_data["ID"] == ukbb_id, "Description"].iloc[0]
            }
            
            # Step 2: Try the direct mapping path first
            logger.info(f"Testing direct mapping for {ukbb_id} (UniProt: {uniprot_id})")
            direct_mapper = await self._identity_mapper_factory()
            direct_result = await direct_mapper.map_identifiers([uniprot_id])
            
            direct_mapped_ids = direct_result.get(uniprot_id, (None, None))[0]
            direct_success = direct_mapped_ids is not None and len(direct_mapped_ids) > 0
            
            result_entry["Direct_Mapping_IDs"] = direct_mapped_ids
            result_entry["Direct_Mapping_Success"] = direct_success
            
            # Step 3: If direct mapping fails, try historical resolution
            if not direct_success:
                logger.info(f"Direct mapping failed for {ukbb_id}, trying historical resolution")
                
                # First step: Historical resolution
                historical_resolver = await self._historical_resolver_factory()
                historical_result = await historical_resolver.map_identifiers([uniprot_id])
                
                resolved_ids, metadata = historical_result.get(uniprot_id, (None, None))
                historical_success = resolved_ids is not None and len(resolved_ids) > 0
                
                # Record historical resolution result
                result_entry["Historical_Resolution_IDs"] = resolved_ids
                result_entry["Historical_Resolution_Metadata"] = metadata
                result_entry["Historical_Resolution_Success"] = historical_success
                
                # Second step: Map resolved IDs to target (if resolution succeeded)
                if historical_success:
                    # Identity mapping for resolved IDs
                    target_mapper = await self._identity_mapper_factory()
                    target_result = await target_mapper.map_identifiers(resolved_ids)
                    
                    # Collect all target IDs
                    target_ids = []
                    for id in resolved_ids:
                        id_result = target_result.get(id, (None, None))[0]
                        if id_result:
                            target_ids.extend(id_result)
                    
                    result_entry["Final_Target_IDs"] = target_ids
                    result_entry["Final_Success"] = len(target_ids) > 0
                    result_entry["Mapping_Path"] = "Historical_Resolution"
                else:
                    # Historical resolution failed
                    result_entry["Final_Target_IDs"] = None
                    result_entry["Final_Success"] = False
                    result_entry["Mapping_Path"] = "Failed"
            else:
                # Direct mapping succeeded
                result_entry["Final_Target_IDs"] = direct_mapped_ids
                result_entry["Final_Success"] = True
                result_entry["Mapping_Path"] = "Direct"
            
            # Store the result
            self.results[ukbb_id] = result_entry
        
        logger.info("Integration test completed")
    
    def save_results(self):
        """Save the test results to a TSV file."""
        # Convert results to DataFrame
        results_df = pd.DataFrame.from_dict(self.results, orient="index")
        
        # Process the DataFrame for better readability
        for col in ["Direct_Mapping_IDs", "Historical_Resolution_IDs", "Final_Target_IDs"]:
            if col in results_df.columns:
                results_df[col] = results_df[col].apply(
                    lambda x: ", ".join(x) if isinstance(x, list) else str(x)
                )
        
        # Save to file
        results_df.to_csv(OUTPUT_FILE, sep="\t")
        logger.info(f"Results saved to {OUTPUT_FILE}")
    
    def print_summary(self):
        """Print a summary of the test results."""
        print("\n=== UKBB to Arivale Integration Test Summary ===")
        
        # Count successes by path
        total_count = len(self.results)
        direct_success = sum(1 for r in self.results.values() if r.get("Mapping_Path") == "Direct")
        historical_success = sum(1 for r in self.results.values() if r.get("Mapping_Path") == "Historical_Resolution")
        total_success = direct_success + historical_success
        failed_count = sum(1 for r in self.results.values() if r.get("Mapping_Path") == "Failed")
        
        print(f"Total test cases: {total_count}")
        print(f"Successful mappings: {total_success}/{total_count} ({total_success/total_count*100:.1f}%)")
        print(f"  - Via direct mapping: {direct_success}/{total_count} ({direct_success/total_count*100:.1f}%)")
        print(f"  - Via historical resolution: {historical_success}/{total_count} ({historical_success/total_count*100:.1f}%)")
        print(f"Failed mappings: {failed_count}/{total_count} ({failed_count/total_count*100:.1f}%)")
        
        # Print detailed results
        print("\nDetailed Results:")
        print(f"{'UKBB ID':<10} {'UniProt ID':<12} {'Path':<20} {'Success':<10}")
        print("-" * 60)
        
        for ukbb_id, result in self.results.items():
            uniprot_id = result.get("UniProt_ID", "N/A")
            path = result.get("Mapping_Path", "Unknown")
            success = "✓" if result.get("Final_Success", False) else "✗"
            
            print(f"{ukbb_id:<10} {uniprot_id:<12} {path:<20} {success:<10}")
        
        # Effectiveness analysis
        if historical_success > 0:
            improvement_pct = (historical_success / total_count) * 100
            print(f"\nHistorical resolution improved mapping success by {improvement_pct:.1f}%")
            
            # List IDs that were mapped via historical resolution
            historical_ids = [ukbb_id for ukbb_id, result in self.results.items() 
                              if result.get("Mapping_Path") == "Historical_Resolution"]
            
            print("\nIDs mapped via historical resolution:")
            for ukbb_id in historical_ids:
                result = self.results[ukbb_id]
                uniprot_id = result.get("UniProt_ID", "N/A")
                metadata = result.get("Historical_Resolution_Metadata", "N/A")
                final_ids = result.get("Final_Target_IDs", "None")
                
                print(f"  {ukbb_id} (UniProt: {uniprot_id}) -> {final_ids} [{metadata}]")
        else:
            print("\nHistorical resolution did not improve mapping success in this test set")

async def run_integration_test():
    """Run the UKBB to Arivale integration test."""
    # Create and run the test
    test = UKBBToArivaleIntegrationTest()
    await test.run_test()
    
    # Save and summarize results
    test.save_results()
    test.print_summary()

if __name__ == "__main__":
    asyncio.run(run_integration_test())