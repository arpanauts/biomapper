#!/usr/bin/env python3
"""
Test script for executing 8 metabolite strategies using BiomapperClient.
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Add biomapper_client to path
sys.path.insert(0, "/home/ubuntu/biomapper")

from biomapper_client import BiomapperClient


def ensure_output_dir(base_dir: str, strategy_name: str) -> str:
    """Create output directory for strategy results."""
    output_dir = Path(base_dir) / strategy_name
    output_dir.mkdir(parents=True, exist_ok=True)
    return str(output_dir)


def test_metabolite_strategies():
    """Execute and test all 8 metabolite strategies."""

    # Initialize client
    client = BiomapperClient(base_url="http://localhost:8001")

    # Base directories
    test_data_dir = "/tmp/metabolite_test_data"
    results_dir = "/tmp/metabolite_test_results"

    # Ensure results directory exists
    Path(results_dir).mkdir(parents=True, exist_ok=True)

    # Define strategies to test with their data files
    strategies = [
        {
            "name": "met_arv_to_kg2c_multi_v1_base",
            "data_file": f"{test_data_dir}/arivale_metabolites.tsv",
            "params": {
                "arivale_file": f"{test_data_dir}/arivale_metabolites.tsv",
                "output_dir": ensure_output_dir(
                    results_dir, "met_arv_to_kg2c_multi_v1_base"
                ),
            },
        },
        {
            "name": "met_arv_to_spoke_multi_v1_base",
            "data_file": f"{test_data_dir}/arivale_metabolites.tsv",
            "params": {
                "arivale_file": f"{test_data_dir}/arivale_metabolites.tsv",
                "output_dir": ensure_output_dir(
                    results_dir, "met_arv_to_spoke_multi_v1_base"
                ),
            },
        },
        {
            "name": "met_isr_lipid_to_kg2c_hmdb_v1_base",
            "data_file": f"{test_data_dir}/israeli_lipids.tsv",
            "params": {
                "israeli_file": f"{test_data_dir}/israeli_lipids.tsv",
                "output_dir": ensure_output_dir(
                    results_dir, "met_isr_lipid_to_kg2c_hmdb_v1_base"
                ),
            },
        },
        {
            "name": "met_isr_lipid_to_spoke_inchikey_v1_base",
            "data_file": f"{test_data_dir}/israeli_lipids.tsv",
            "params": {
                "israeli_file": f"{test_data_dir}/israeli_lipids.tsv",
                "output_dir": ensure_output_dir(
                    results_dir, "met_isr_lipid_to_spoke_inchikey_v1_base"
                ),
            },
        },
        {
            "name": "met_isr_metab_to_kg2c_hmdb_v1_base",
            "data_file": f"{test_data_dir}/israeli_metabolites.tsv",
            "params": {
                "israeli_file": f"{test_data_dir}/israeli_metabolites.tsv",
                "output_dir": ensure_output_dir(
                    results_dir, "met_isr_metab_to_kg2c_hmdb_v1_base"
                ),
            },
        },
        {
            "name": "met_isr_metab_to_spoke_inchikey_v1_base",
            "data_file": f"{test_data_dir}/israeli_metabolites.tsv",
            "params": {
                "israeli_file": f"{test_data_dir}/israeli_metabolites.tsv",
                "output_dir": ensure_output_dir(
                    results_dir, "met_isr_metab_to_spoke_inchikey_v1_base"
                ),
            },
        },
        {
            "name": "met_multi_semantic_enrichment_v1_advanced",
            "data_file": "multiple",
            "params": {
                "arivale_file": f"{test_data_dir}/arivale_metabolites.tsv",
                "israeli_lipid_file": f"{test_data_dir}/israeli_lipids.tsv",
                "israeli_metabolite_file": f"{test_data_dir}/israeli_metabolites.tsv",
                "output_dir": ensure_output_dir(
                    results_dir, "met_multi_semantic_enrichment_v1_advanced"
                ),
                "enable_semantic_matching": True,
                "confidence_threshold": 0.7,
            },
        },
        {
            "name": "met_multi_to_unified_semantic_v1_enhanced",
            "data_file": "multiple",
            "params": {
                "arivale_file": f"{test_data_dir}/arivale_metabolites.tsv",
                "israeli_file": f"{test_data_dir}/israeli_metabolites.tsv",
                "output_dir": ensure_output_dir(
                    results_dir, "met_multi_to_unified_semantic_v1_enhanced"
                ),
                "enable_semantic_matching": True,
                "enable_fuzzy_matching": True,
                "min_confidence": 0.6,
            },
        },
    ]

    # Track results
    results = []
    successful = []
    failed = []

    print(f"\n{'='*80}")
    print(f"Testing {len(strategies)} Metabolite Strategies")
    print(f"Start Time: {datetime.now().isoformat()}")
    print(f"{'='*80}\n")

    for i, strategy in enumerate(strategies, 1):
        print(f"\n[{i}/{len(strategies)}] Testing: {strategy['name']}")
        print(f"  Data file: {strategy['data_file']}")
        print(f"  Output dir: {strategy['params']['output_dir']}")

        try:
            # Check if data file exists (skip for multi-file strategies)
            if strategy["data_file"] != "multiple":
                if not Path(strategy["data_file"]).exists():
                    print(f"  ⚠️  WARNING: Data file not found: {strategy['data_file']}")

            # Execute strategy
            print("  Executing strategy...")
            result = client.execute_strategy(
                strategy_name=strategy["name"], params=strategy["params"]
            )

            # Check result
            if result.get("status") == "completed":
                print("  ✅ SUCCESS: Strategy completed")
                successful.append(strategy["name"])

                # Save result summary
                summary_file = (
                    Path(strategy["params"]["output_dir"]) / "execution_summary.json"
                )
                with open(summary_file, "w") as f:
                    json.dump(
                        {
                            "strategy": strategy["name"],
                            "status": "success",
                            "timestamp": datetime.now().isoformat(),
                            "result": result,
                        },
                        f,
                        indent=2,
                    )

            else:
                print("  ❌ FAILED: Strategy execution failed")
                print(f"     Status: {result.get('status', 'unknown')}")
                if "error" in result:
                    print(f"     Error: {result['error']}")
                failed.append((strategy["name"], result.get("error", "Unknown error")))

            results.append(
                {
                    "strategy": strategy["name"],
                    "status": result.get("status"),
                    "error": result.get("error") if "error" in result else None,
                }
            )

        except Exception as e:
            print(f"  ❌ EXCEPTION: {str(e)}")
            failed.append((strategy["name"], str(e)))
            results.append(
                {"strategy": strategy["name"], "status": "exception", "error": str(e)}
            )

    # Print summary
    print(f"\n{'='*80}")
    print("EXECUTION SUMMARY")
    print(f"{'='*80}")
    print(f"Total strategies tested: {len(strategies)}")
    print(f"Successful: {len(successful)}")
    print(f"Failed: {len(failed)}")
    print(f"End Time: {datetime.now().isoformat()}")

    if successful:
        print(f"\n✅ SUCCESSFUL STRATEGIES ({len(successful)}):")
        for name in successful:
            print(f"  - {name}")

    if failed:
        print(f"\n❌ FAILED STRATEGIES ({len(failed)}):")
        for name, error in failed:
            print(f"  - {name}")
            print(f"    Error: {error[:200]}...")  # Truncate long errors

    # Save full results
    summary_file = Path(results_dir) / "test_execution_summary.json"
    with open(summary_file, "w") as f:
        json.dump(
            {
                "test_run": datetime.now().isoformat(),
                "total_strategies": len(strategies),
                "successful": successful,
                "failed": [{"name": name, "error": error} for name, error in failed],
                "detailed_results": results,
            },
            f,
            indent=2,
        )

    print(f"\n📄 Full results saved to: {summary_file}")

    return len(successful), len(failed)


if __name__ == "__main__":
    success_count, fail_count = test_metabolite_strategies()

    # Exit with appropriate code
    if fail_count == 0:
        print("\n🎉 All strategies executed successfully!")
        sys.exit(0)
    else:
        print(f"\n⚠️  {fail_count} strategies failed. Check the logs for details.")
        sys.exit(1)
