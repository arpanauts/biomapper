#!/usr/bin/env python3
"""
Test script for v2.2 integrated protein mapping strategy with FULL production datasets.
This script validates all enhancements from parallel work integration.
"""

import asyncio
import json
import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from biomapper_client.client_v2 import BiomapperClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ProductionTestRunner:
    """Runner for production-scale testing of v2.2 strategy."""
    
    def __init__(self):
        self.client = BiomapperClient(base_url="http://localhost:8000")
        self.test_results = {
            "timestamp": datetime.now().isoformat(),
            "strategy": "prot_arv_to_kg2c_uniprot_v2.2_integrated",
            "tests_passed": [],
            "tests_failed": [],
            "statistics": {},
            "performance_metrics": {}
        }
        
    async def run_full_production_test(self) -> bool:
        """Run v2.2 strategy with full production datasets."""
        
        logger.info("=" * 80)
        logger.info("STARTING V2.2 PRODUCTION TEST WITH FULL DATASETS")
        logger.info("=" * 80)
        
        # Define production parameters
        params = {
            "SOURCE_FILE": "/procedure/data/local_data/Arivale_prots/Arivale_prots.txt",
            "TARGET_FILE": "/procedure/data/local_data/MAPPING_ONTOLOGIES/kgc2_nodes_prots.tsv",
            "OUTPUT_DIR": f"/tmp/biomapper/v2.2_production_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "ENABLE_COMPOSITE_PARSING": "true",
            "ENABLE_ONE_TO_MANY_TRACKING": "true",
            "ENABLE_VISUALIZATIONS": "true",
            "ENABLE_HTML_REPORT": "true",
            "ENABLE_GOOGLE_DRIVE_SYNC": "false"  # Disabled for testing
        }
        
        logger.info(f"Output directory: {params['OUTPUT_DIR']}")
        
        try:
            # Start the job
            logger.info("Submitting v2.2 strategy job...")
            start_time = datetime.now()
            
            job_response = await self.client.execute_strategy_async(
                strategy_name="prot_arv_to_kg2c_uniprot_v2.2_integrated",
                parameters=params,
                wait_for_completion=True,
                timeout=600  # 10 minutes timeout
            )
            
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()
            
            if job_response.get("status") == "completed":
                logger.info(f"✅ Strategy completed successfully in {execution_time:.2f} seconds")
                self.test_results["tests_passed"].append("strategy_execution")
                self.test_results["performance_metrics"]["execution_time"] = execution_time
                
                # Validate outputs
                output_dir = Path(params["OUTPUT_DIR"])
                await self.validate_outputs(output_dir, job_response)
                
                return True
            else:
                logger.error(f"❌ Strategy failed: {job_response.get('error', 'Unknown error')}")
                self.test_results["tests_failed"].append("strategy_execution")
                return False
                
        except Exception as e:
            logger.error(f"❌ Exception during execution: {str(e)}")
            self.test_results["tests_failed"].append(f"execution_error: {str(e)}")
            return False
            
    async def validate_outputs(self, output_dir: Path, job_response: Dict[str, Any]):
        """Validate all expected outputs from v2.2 strategy."""
        
        logger.info("\n" + "=" * 80)
        logger.info("VALIDATING OUTPUTS")
        logger.info("=" * 80)
        
        # Expected files from v2.2 strategy
        expected_files = {
            "all_mappings.tsv": "All protein mappings",
            "high_confidence_mappings.tsv": "High confidence mappings only",
            "mapping_report.html": "HTML report",
            "mapping_summary.json": "JSON summary",
            "visualizations/coverage_pie.png": "Coverage pie chart",
            "visualizations/confidence_histogram.png": "Confidence histogram",
            "visualizations/mapping_flow_sankey.html": "Sankey flow diagram",
            "visualizations/one_to_many_distribution.png": "One-to-many distribution",
            "visualizations/statistics_dashboard.png": "Statistics dashboard",
            "visualizations/interactive_scatter.html": "Interactive scatter plot"
        }
        
        # Check each expected file
        for file_path, description in expected_files.items():
            full_path = output_dir / file_path
            if full_path.exists():
                file_size = full_path.stat().st_size
                logger.info(f"✅ {description}: {file_path} ({file_size:,} bytes)")
                self.test_results["tests_passed"].append(f"output_{file_path}")
            else:
                logger.warning(f"⚠️ Missing: {description} - {file_path}")
                self.test_results["tests_failed"].append(f"missing_{file_path}")
                
        # Load and analyze mapping summary
        summary_path = output_dir / "mapping_summary.json"
        if summary_path.exists():
            with open(summary_path) as f:
                summary = json.load(f)
                await self.analyze_mapping_statistics(summary)
                
        # Check HTML report content
        report_path = output_dir / "mapping_report.html"
        if report_path.exists():
            await self.validate_html_report(report_path)
            
    async def analyze_mapping_statistics(self, summary: Dict[str, Any]):
        """Analyze mapping statistics from summary."""
        
        logger.info("\n" + "=" * 80)
        logger.info("MAPPING STATISTICS ANALYSIS")
        logger.info("=" * 80)
        
        stats = summary.get("statistics", {})
        
        # Key metrics to validate
        metrics = {
            "total_input": stats.get("total_input", 0),
            "direct_match": stats.get("direct_match", 0),
            "normalized_match": stats.get("normalized_match", 0),
            "historical_match": stats.get("historical_match", 0),
            "gene_bridge_match": stats.get("gene_bridge_match", 0),
            "ensembl_match": stats.get("ensembl_match", 0),
            "unmapped": stats.get("unmapped", 0),
            "one_to_many_count": stats.get("one_to_many_count", 0),
            "expansion_factor": stats.get("expansion_factor", 1.0)
        }
        
        # Calculate success rates
        total = metrics["total_input"]
        if total > 0:
            direct_rate = (metrics["direct_match"] / total) * 100
            total_matched = sum([
                metrics["direct_match"],
                metrics["normalized_match"],
                metrics["historical_match"],
                metrics["gene_bridge_match"],
                metrics["ensembl_match"]
            ])
            overall_rate = (total_matched / total) * 100
            
            logger.info(f"Total Input Proteins: {total:,}")
            logger.info(f"Direct Match Rate: {direct_rate:.1f}%")
            logger.info(f"Overall Match Rate: {overall_rate:.1f}%")
            logger.info(f"Unmapped: {metrics['unmapped']:,} ({(metrics['unmapped']/total)*100:.1f}%)")
            logger.info(f"One-to-Many Mappings: {metrics['one_to_many_count']:,}")
            logger.info(f"Expansion Factor: {metrics['expansion_factor']:.2f}")
            
            # Validate expected performance
            if 65 <= direct_rate <= 75:
                logger.info("✅ Direct match rate within expected range (65-75%)")
                self.test_results["tests_passed"].append("direct_match_rate")
            else:
                logger.warning(f"⚠️ Direct match rate {direct_rate:.1f}% outside expected range")
                self.test_results["tests_failed"].append("direct_match_rate")
                
            if 85 <= overall_rate <= 90:
                logger.info("✅ Overall match rate within expected range (85-90%)")
                self.test_results["tests_passed"].append("overall_match_rate")
            else:
                logger.warning(f"⚠️ Overall match rate {overall_rate:.1f}% outside expected range")
                self.test_results["tests_failed"].append("overall_match_rate")
                
        # Store statistics
        self.test_results["statistics"] = metrics
        
    async def validate_html_report(self, report_path: Path):
        """Validate HTML report content."""
        
        logger.info("\n" + "=" * 80)
        logger.info("HTML REPORT VALIDATION")
        logger.info("=" * 80)
        
        html_content = report_path.read_text()
        
        # Check for expected sections
        expected_sections = [
            "Executive Summary",
            "Mapping Flow Analysis",
            "Confidence Distribution",
            "One-to-Many Mappings",
            "High Confidence Matches",
            "Unmapped Proteins"
        ]
        
        for section in expected_sections:
            if section in html_content:
                logger.info(f"✅ Report contains: {section}")
                self.test_results["tests_passed"].append(f"report_{section}")
            else:
                logger.warning(f"⚠️ Report missing: {section}")
                self.test_results["tests_failed"].append(f"report_{section}")
                
        # Check for visualization embeds
        if "plotly" in html_content.lower():
            logger.info("✅ Report contains interactive visualizations")
            self.test_results["tests_passed"].append("interactive_viz")
            
        # Check file size (should be substantial)
        file_size = report_path.stat().st_size
        if file_size > 50000:  # > 50KB
            logger.info(f"✅ Report size appropriate: {file_size:,} bytes")
            self.test_results["tests_passed"].append("report_size")
        else:
            logger.warning(f"⚠️ Report seems small: {file_size:,} bytes")
            
    def generate_test_report(self):
        """Generate final test report."""
        
        logger.info("\n" + "=" * 80)
        logger.info("PRODUCTION TEST SUMMARY")
        logger.info("=" * 80)
        
        passed = len(self.test_results["tests_passed"])
        failed = len(self.test_results["tests_failed"])
        total = passed + failed
        
        logger.info(f"Tests Passed: {passed}/{total}")
        logger.info(f"Tests Failed: {failed}/{total}")
        
        if failed == 0:
            logger.info("🎉 ALL TESTS PASSED! V2.2 strategy is production-ready!")
        else:
            logger.warning(f"⚠️ {failed} tests failed. Review required before production use.")
            logger.info("\nFailed tests:")
            for test in self.test_results["tests_failed"]:
                logger.info(f"  - {test}")
                
        # Save test report
        report_path = Path(f"/tmp/biomapper/v2.2_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        report_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(report_path, 'w') as f:
            json.dump(self.test_results, f, indent=2)
            
        logger.info(f"\nTest report saved to: {report_path}")
        
        return failed == 0


async def main():
    """Main entry point."""
    
    runner = ProductionTestRunner()
    
    try:
        # Check API is running
        health = await runner.client.health_check()
        if not health.get("status") == "healthy":
            logger.error("API is not healthy. Please start the API server first.")
            logger.info("Run: cd ../biomapper-api && poetry run uvicorn app.main:app --reload")
            return
            
        # Run production test
        success = await runner.run_full_production_test()
        
        # Generate report
        all_passed = runner.generate_test_report()
        
        if all_passed:
            logger.info("\n✅ V2.2 STRATEGY IS READY FOR PRODUCTION USE")
            logger.info("Next steps:")
            logger.info("1. Review generated reports and visualizations")
            logger.info("2. Test Google Drive sync with credentials")
            logger.info("3. Propagate enhancements to other protein strategies")
        else:
            logger.info("\n⚠️ Some tests failed. Please review and fix issues.")
            
    except Exception as e:
        logger.error(f"Test runner failed: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())