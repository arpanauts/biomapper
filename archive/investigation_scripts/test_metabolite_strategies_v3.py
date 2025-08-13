#!/usr/bin/env python3
"""
Test script for executing 8 metabolite strategies using v2 API with async job handling.
"""

import sys
import json
import time
import requests
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional


def ensure_output_dir(base_dir: str, strategy_name: str) -> str:
    """Create output directory for strategy results."""
    output_dir = Path(base_dir) / strategy_name
    output_dir.mkdir(parents=True, exist_ok=True)
    return str(output_dir)


def start_strategy_execution(strategy_name: str, params: Dict) -> Optional[str]:
    """Start a strategy execution and return the job ID."""
    url = "http://localhost:8002/api/strategies/v2/execute"
    payload = {
        "strategy": strategy_name,
        "parameters": params,  # Changed from 'params' to 'parameters'
    }

    try:
        response = requests.post(url, json=payload, timeout=30)
        if response.status_code == 200:
            data = response.json()
            return data.get("job_id")
        else:
            print(
                f"     Failed to start: HTTP {response.status_code}: {response.text[:200]}"
            )
            return None
    except Exception as e:
        print(f"     Exception starting job: {str(e)}")
        return None


def wait_for_job_completion(job_id: str, timeout: int = 300) -> Dict:
    """Wait for a job to complete and return its final status."""
    url = f"http://localhost:8002/api/strategies/v2/jobs/{job_id}/status"
    start_time = time.time()

    while time.time() - start_time < timeout:
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                status = data.get("status", "unknown")

                if status in ["completed", "failed"]:
                    return data

                # Still running, wait a bit
                time.sleep(2)
            else:
                return {
                    "status": "failed",
                    "error": f"Failed to get job status: HTTP {response.status_code}",
                }
        except Exception as e:
            return {
                "status": "failed",
                "error": f"Exception checking job status: {str(e)}",
            }

    return {
        "status": "timeout",
        "error": f"Job did not complete within {timeout} seconds",
    }


def test_metabolite_strategies():
    """Execute and test all 8 metabolite strategies."""

    # Base directories
    test_data_dir = "/tmp/metabolite_test_data"
    results_dir = "/tmp/metabolite_test_results"

    # Ensure results directory exists
    Path(results_dir).mkdir(parents=True, exist_ok=True)

    # Define strategies to test with their data files
    # Using the actual strategy names from the YAML files
    strategies = [
        {
            "name": "Arivale Metabolomics to KG2c via Multi-Bridge",
            "file": "met_arv_to_kg2c_multi_v1_base",
            "data_file": f"{test_data_dir}/arivale_metabolites.tsv",
            "params": {
                "arivale_file": f"{test_data_dir}/arivale_metabolites.tsv",
                "output_dir": ensure_output_dir(
                    results_dir, "met_arv_to_kg2c_multi_v1_base"
                ),
            },
        },
        {
            "name": "Arivale Metabolomics to SPOKE via Multi-Bridge",
            "file": "met_arv_to_spoke_multi_v1_base",
            "data_file": f"{test_data_dir}/arivale_metabolites.tsv",
            "params": {
                "arivale_file": f"{test_data_dir}/arivale_metabolites.tsv",
                "output_dir": ensure_output_dir(
                    results_dir, "met_arv_to_spoke_multi_v1_base"
                ),
            },
        },
        {
            "name": "Israeli10k Lipidomics to KG2c via HMDB",
            "file": "met_isr_lipid_to_kg2c_hmdb_v1_base",
            "data_file": f"{test_data_dir}/israeli_lipids.tsv",
            "params": {
                "israeli_file": f"{test_data_dir}/israeli_lipids.tsv",
                "output_dir": ensure_output_dir(
                    results_dir, "met_isr_lipid_to_kg2c_hmdb_v1_base"
                ),
            },
        },
        {
            "name": "Israeli10k Lipidomics to SPOKE via InChIKey",
            "file": "met_isr_lipid_to_spoke_inchikey_v1_base",
            "data_file": f"{test_data_dir}/israeli_lipids.tsv",
            "params": {
                "israeli_file": f"{test_data_dir}/israeli_lipids.tsv",
                "output_dir": ensure_output_dir(
                    results_dir, "met_isr_lipid_to_spoke_inchikey_v1_base"
                ),
            },
        },
        {
            "name": "Israeli10k Metabolomics to KG2c via HMDB",
            "file": "met_isr_metab_to_kg2c_hmdb_v1_base",
            "data_file": f"{test_data_dir}/israeli_metabolites.tsv",
            "params": {
                "israeli_file": f"{test_data_dir}/israeli_metabolites.tsv",
                "output_dir": ensure_output_dir(
                    results_dir, "met_isr_metab_to_kg2c_hmdb_v1_base"
                ),
            },
        },
        {
            "name": "Israeli10k Metabolomics to SPOKE via InChIKey",
            "file": "met_isr_metab_to_spoke_inchikey_v1_base",
            "data_file": f"{test_data_dir}/israeli_metabolites.tsv",
            "params": {
                "israeli_file": f"{test_data_dir}/israeli_metabolites.tsv",
                "output_dir": ensure_output_dir(
                    results_dir, "met_isr_metab_to_spoke_inchikey_v1_base"
                ),
            },
        },
        {
            "name": "Semantic Metabolite Enrichment Pipeline",
            "file": "met_multi_semantic_enrichment_v1_advanced",
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
            "name": "Multi-Source Metabolite Unified Analysis",
            "file": "met_multi_to_unified_semantic_v1_enhanced",
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
    print("API Endpoint: http://localhost:8002/api/strategies/v2/execute")
    print(f"{'='*80}\n")

    # Start all jobs
    jobs = []
    for i, strategy in enumerate(strategies, 1):
        print(f"\n[{i}/{len(strategies)}] Starting: {strategy['name']}")
        print(f"  Data file: {strategy['data_file']}")
        print(f"  Output dir: {strategy['params']['output_dir']}")

        # Check if data file exists (skip for multi-file strategies)
        if strategy["data_file"] != "multiple":
            if not Path(strategy["data_file"]).exists():
                print(f"  ⚠️  WARNING: Data file not found: {strategy['data_file']}")

        # Start strategy execution
        print("  Starting job...")
        job_id = start_strategy_execution(strategy["name"], strategy["params"])

        if job_id:
            print(f"  Job started with ID: {job_id}")
            jobs.append(
                {
                    "job_id": job_id,
                    "strategy": strategy["name"],
                    "params": strategy["params"],
                    "start_time": datetime.now(),
                }
            )
        else:
            print("  ❌ Failed to start job")
            failed.append((strategy["name"], "Failed to start job"))

    # Wait for all jobs to complete
    print(f"\n{'='*40}")
    print(f"Waiting for {len(jobs)} jobs to complete...")
    print(f"{'='*40}\n")

    for job in jobs:
        print(f"Checking job {job['job_id']} for strategy {job['strategy']}...")
        result = wait_for_job_completion(job["job_id"], timeout=300)

        status = result.get("status")
        if status == "completed":
            print("  ✅ SUCCESS: Strategy completed")
            successful.append(job["strategy"])

            # Save result summary
            summary_file = Path(job["params"]["output_dir"]) / "execution_summary.json"
            with open(summary_file, "w") as f:
                json.dump(
                    {
                        "strategy": job["strategy"],
                        "status": "success",
                        "job_id": job["job_id"],
                        "timestamp": datetime.now().isoformat(),
                        "result": result,
                    },
                    f,
                    indent=2,
                )

        else:
            error_msg = result.get("error", "Unknown error")
            print(f"  ❌ FAILED: {status}")
            print(f"     Error: {error_msg[:200]}...")
            failed.append((job["strategy"], error_msg))

        results.append(
            {
                "strategy": job["strategy"],
                "job_id": job["job_id"],
                "status": status,
                "error": result.get("error") if "error" in result else None,
                "result": result,
            }
        )

    # Print summary
    print(f"\n{'='*80}")
    print("EXECUTION SUMMARY")
    print(f"{'='*80}")
    print(f"Total strategies tested: {len(strategies)}")
    print(f"Jobs started: {len(jobs)}")
    print(f"Successful: {len(successful)}")
    print(f"Failed: {len(failed) + (len(strategies) - len(jobs))}")
    print(f"End Time: {datetime.now().isoformat()}")

    if successful:
        print(f"\n✅ SUCCESSFUL STRATEGIES ({len(successful)}):")
        for name in successful:
            print(f"  - {name}")

    if failed:
        print(f"\n❌ FAILED STRATEGIES ({len(failed)}):")
        for name, error in failed:
            print(f"  - {name}")
            if len(error) > 200:
                print(f"    Error: {error[:200]}...")
            else:
                print(f"    Error: {error}")

    # Save full results
    summary_file = Path(results_dir) / "test_execution_summary.json"
    with open(summary_file, "w") as f:
        json.dump(
            {
                "test_run": datetime.now().isoformat(),
                "total_strategies": len(strategies),
                "jobs_started": len(jobs),
                "successful": successful,
                "failed": [{"name": name, "error": error} for name, error in failed],
                "detailed_results": results,
            },
            f,
            indent=2,
        )

    print(f"\n📄 Full results saved to: {summary_file}")

    # Also save a detailed log of any failures
    if failed:
        failure_log = Path(results_dir) / "failure_details.txt"
        with open(failure_log, "w") as f:
            f.write(f"Test Run: {datetime.now().isoformat()}\n")
            f.write(f"Failed Strategies: {len(failed)}\n\n")
            for name, error in failed:
                f.write(f"Strategy: {name}\n")
                f.write(f"Error: {error}\n")
                f.write("-" * 80 + "\n\n")
        print(f"📄 Failure details saved to: {failure_log}")

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
