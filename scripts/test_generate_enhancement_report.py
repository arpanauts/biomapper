#!/usr/bin/env python3
"""Test script to generate an example enhancement report."""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from biomapper.core.strategy_actions.generate_enhancement_report import (
    GenerateEnhancementReport,
    GenerateEnhancementReportParams
)


async def main():
    """Generate an example enhancement report with realistic data."""
    
    # Realistic metrics data from a three-stage enhancement
    context = {
        "metrics.baseline": {
            "stage": "baseline",
            "total_unmatched_input": 3500,
            "total_matched": 1575,
            "match_rate": 0.45,
            "avg_confidence": 0.87,
            "execution_time": 18.3,
            "match_distribution": {
                "exact": 1225,
                "fuzzy": 350
            }
        },
        "metrics.api": {
            "stage": "api_enhanced",
            "total_unmatched_input": 1925,
            "total_matched": 577,
            "match_rate": 0.30,
            "cumulative_match_rate": 0.615,
            "api_calls_made": 962,
            "cache_hits": 415,
            "execution_time": 48.7,
            "enrichment_sources": {
                "pubchem": 301,
                "chebi": 178,
                "hmdb": 98
            }
        },
        "metrics.vector": {
            "stage": "vector_enhanced", 
            "total_unmatched_input": 1348,
            "total_matched": 337,
            "match_rate": 0.25,
            "cumulative_match_rate": 0.711,
            "vectors_searched": 1348,
            "avg_similarity_score": 0.805,
            "execution_time": 25.8,
            "similarity_distribution": {
                "very_high": 63,
                "high": 125,
                "medium": 105,
                "low": 44
            }
        }
    }
    
    # Configure report parameters
    output_path = Path(__file__).parent.parent / "data" / "results" / "example_enhancement_report.md"
    
    params = GenerateEnhancementReportParams(
        metrics_keys=["metrics.baseline", "metrics.api", "metrics.vector"],
        stage_names=["Baseline Fuzzy Matching", "CTS API Enhancement", "Vector Similarity Search"],
        output_path=str(output_path),
        include_visualizations=True,
        include_detailed_stats=True
    )
    
    # Create action and generate report
    action = GenerateEnhancementReport()
    
    print(f"Generating enhancement report...")
    result = await action.execute_typed(
        current_identifiers=[],
        current_ontology_type="metabolite",
        params=params,
        source_endpoint=None,
        target_endpoint=None,
        context=context
    )
    
    print(f"✅ Report generated successfully!")
    print(f"📄 Output: {result.details['report_path']}")
    print(f"📊 Metrics aggregated: {result.details['metrics_found']}")
    print(f"\nReport Summary:")
    print(f"- Initial match rate: 45.0%")
    print(f"- Final match rate: 71.1%") 
    print(f"- Overall improvement: 58% relative improvement")
    print(f"- Total metabolites: 3,500")
    print(f"- Total matched: 2,489")
    print(f"\nView the report at: {output_path}")


if __name__ == "__main__":
    asyncio.run(main())