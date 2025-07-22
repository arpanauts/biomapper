#!/usr/bin/env python
"""
Meta script to execute all 9 protein mapping pipelines in parallel.

This script orchestrates the complete cross-mapping analysis by running:
1. UKBB_HPA, UKBB_QIN, HPA_QIN
2. Arivale_SPOKE, Arivale_KG2C, Arivale_UKBB  
3. UKBB_KG2C, UKBB_SPOKE, HPA_SPOKE

Features:
- Sequential execution (API-friendly)
- Progress tracking and logging
- Error handling and reporting
- Summary statistics aggregation
- Results consolidation

Results are saved to results/ directory with standardized structure.
"""
import asyncio
import logging
import sys
import time
from pathlib import Path
from typing import Dict, List, Tuple
import subprocess
import json

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Define all 9 mapping configurations
MAPPINGS = [
    ("UKBB_HPA", "run_ukbb_hpa_mapping.py"),
    ("UKBB_QIN", "run_ukbb_qin_mapping.py"),
    ("HPA_QIN", "run_hpa_qin_mapping.py"),
    ("Arivale_SPOKE", "run_arivale_spoke_mapping.py"),
    ("Arivale_KG2C", "run_arivale_kg2c_mapping.py"),
    ("Arivale_UKBB", "run_arivale_ukbb_mapping.py"),
    ("UKBB_KG2C", "run_ukbb_kg2c_mapping.py"),
    ("UKBB_SPOKE", "run_ukbb_spoke_mapping.py"),
    ("HPA_SPOKE", "run_hpa_spoke_mapping.py"),
]

async def run_mapping_script(mapping_id: str, script_name: str) -> Tuple[str, bool, str]:
    """
    Run a single mapping script asynchronously.
    
    Returns:
        Tuple of (mapping_id, success, output/error)
    """
    script_path = project_root / "scripts" / "main_pipelines" / script_name
    
    if not script_path.exists():
        return mapping_id, False, f"Script not found: {script_path}"
    
    logger.info(f"🚀 Starting {mapping_id} mapping...")
    
    try:
        # Run the script
        process = await asyncio.create_subprocess_exec(
            sys.executable, str(script_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(project_root)
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode == 0:
            logger.info(f"✅ {mapping_id} completed successfully!")
            return mapping_id, True, stdout.decode('utf-8')
        else:
            logger.error(f"❌ {mapping_id} failed with return code {process.returncode}")
            return mapping_id, False, stderr.decode('utf-8')
            
    except Exception as e:
        logger.error(f"❌ {mapping_id} failed with exception: {e}")
        return mapping_id, False, str(e)

async def collect_results_summary() -> Dict:
    """
    Collect and aggregate statistics from all mapping results.
    
    Returns:
        Dictionary with consolidated statistics
    """
    results_dir = project_root / "results"
    summary = {
        "total_mappings": len(MAPPINGS),
        "successful_mappings": 0,
        "failed_mappings": 0,
        "mapping_details": {},
        "cross_mapping_matrix": {}
    }
    
    # Check each mapping's results
    for mapping_id, _ in MAPPINGS:
        mapping_dir = results_dir / mapping_id
        stats_file = mapping_dir / "overlap_statistics.csv"
        
        if stats_file.exists():
            try:
                import pandas as pd
                df = pd.read_csv(stats_file)
                if not df.empty:
                    stats = df.iloc[0].to_dict()
                    summary["mapping_details"][mapping_id] = stats
                    summary["successful_mappings"] += 1
                else:
                    summary["failed_mappings"] += 1
            except Exception as e:
                logger.warning(f"Could not read statistics for {mapping_id}: {e}")
                summary["failed_mappings"] += 1
        else:
            summary["failed_mappings"] += 1
    
    return summary

async def main():
    """
    Execute all 9 protein mapping pipelines and generate summary report.
    """
    start_time = time.time()
    
    logger.info("🔬 Starting comprehensive protein mapping analysis...")
    logger.info(f"📊 Executing {len(MAPPINGS)} mapping combinations:")
    
    for mapping_id, script_name in MAPPINGS:
        logger.info(f"  • {mapping_id}")
    
    # Create results directory
    results_dir = project_root / "results"
    results_dir.mkdir(exist_ok=True)
    
    # Execute all mappings sequentially to avoid overwhelming UniProt API
    logger.info("\n🚀 Launching sequential execution (API-friendly)...")
    
    results = []
    for i, (mapping_id, script_name) in enumerate(MAPPINGS, 1):
        logger.info(f"📊 Progress: {i}/{len(MAPPINGS)} - Processing {mapping_id}")
        result = await run_mapping_script(mapping_id, script_name)
        results.append(result)
        
        # Brief pause between mappings to be respectful to UniProt API
        if i < len(MAPPINGS):
            logger.info("⏱️  Pausing 30 seconds between mappings...")
            await asyncio.sleep(30)
    
    # Process results
    successful = []
    failed = []
    
    for result in results:
        if isinstance(result, Exception):
            failed.append(("Unknown", str(result)))
        else:
            mapping_id, success, output = result
            if success:
                successful.append((mapping_id, output))
            else:
                failed.append((mapping_id, output))
    
    # Generate summary
    end_time = time.time()
    duration = end_time - start_time
    
    logger.info(f"\n📈 EXECUTION COMPLETE")
    logger.info(f"⏱️  Total time: {duration:.1f} seconds")
    logger.info(f"✅ Successful mappings: {len(successful)}/{len(MAPPINGS)}")
    logger.info(f"❌ Failed mappings: {len(failed)}")
    
    if successful:
        logger.info("\n🎉 Successful mappings:")
        for mapping_id, _ in successful:
            logger.info(f"  ✅ {mapping_id}")
    
    if failed:
        logger.info("\n💥 Failed mappings:")
        for mapping_id, error in failed:
            logger.info(f"  ❌ {mapping_id}: {error[:100]}...")
    
    # Collect and save comprehensive summary
    try:
        summary = await collect_results_summary()
        summary_file = results_dir / "cross_mapping_summary.json"
        
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2, default=str)
        
        logger.info(f"\n📊 Summary saved to: {summary_file}")
        logger.info(f"📁 All results available in: {results_dir}")
        
        # Print key statistics
        if summary["mapping_details"]:
            logger.info("\n📈 Key Statistics:")
            total_matches = sum(
                details.get("matched_rows", 0) 
                for details in summary["mapping_details"].values()
            )
            avg_jaccard = sum(
                details.get("jaccard_index", 0) 
                for details in summary["mapping_details"].values()
            ) / len(summary["mapping_details"])
            
            logger.info(f"  🎯 Total matches across all mappings: {total_matches:,}")
            logger.info(f"  📊 Average Jaccard Index: {avg_jaccard:.3f}")
        
    except Exception as e:
        logger.error(f"Failed to generate summary: {e}")
    
    # Return appropriate exit code
    if failed:
        logger.error(f"\n❌ {len(failed)} mappings failed. Check logs for details.")
        return 1
    else:
        logger.info("\n🎉 All mappings completed successfully!")
        return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)