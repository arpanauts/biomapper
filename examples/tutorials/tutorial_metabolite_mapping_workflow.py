#!/usr/bin/env python3
"""
Complete Biomapper Tutorial: Compound Mapping and Analysis Workflow

This tutorial demonstrates how to use Biomapper to:
1. Map compound names to standardized identifiers using API lookups and RAG
2. Integrate with SPOKE knowledge graph for pathway analysis
3. Use LLM-powered analysis for deeper insights
4. Process and validate results with confidence scoring

Example Usage:
    python tutorial_complete_mapping_workflow.py --input compounds.txt --output results/

For more examples and documentation, visit:
https://biomapper.readthedocs.io/
"""

import argparse
import asyncio
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

import pandas as pd

from biomapper import (
    MetaboliteNameMapper,
    MultiProviderMapper,
    ChromaCompoundStore,
    PromptManager,
    DSPyOptimizer,
)
from biomapper.mapping.result_processor import ResultProcessor
from biomapper.spoke import SPOKEClient, MetaboliteSPOKEMapper
from biomapper.llm import MetaboliteLLMAnalyzer
from biomapper.monitoring import MetricsTracker

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def load_compounds(input_path: Path) -> List[str]:
    """
    Load compound names from a file.

    The file should contain one compound name per line.
    Lines starting with # are treated as comments.
    Empty lines are ignored.

    Args:
        input_path: Path to input file

    Returns:
        List of compound names

    Raises:
        FileNotFoundError: If input file doesn't exist
    """
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    compounds = []
    with open(input_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                compounds.append(line)

    logger.info(f"Loaded {len(compounds)} compounds from {input_path}")
    return compounds


async def process_compounds(
    compound_list: List[str],
    output_dir: Path,
    enable_optimization: bool = False,
    confidence_threshold: float = 0.8,
    enable_spoke: bool = True,
    enable_llm_analysis: bool = True,
) -> Dict[str, Any]:
    """
    Process compounds through the complete mapping and analysis pipeline.

    This function demonstrates the full Biomapper workflow:
    1. Initial API lookup using MetaboliteNameMapper
    2. RAG-based mapping for unmatched compounds
    3. SPOKE integration for pathway analysis
    4. LLM-powered analysis of results
    5. Result processing with confidence scoring

    Args:
        compound_list: List of compound names to process
        output_dir: Directory to save results
        enable_optimization: Whether to enable DSPy optimization
        confidence_threshold: Threshold for high-confidence matches
        enable_spoke: Whether to enable SPOKE integration
        enable_llm_analysis: Whether to enable LLM analysis

    Returns:
        Dictionary containing:
            - results: DataFrame with mapping results
            - statistics: Mapping statistics
            - spoke_analysis: SPOKE pathway analysis (if enabled)
            - llm_insights: LLM-generated insights (if enabled)

    Example:
        >>> compounds = ["glucose", "vitamin D3", "unknown compound"]
        >>> results = await process_compounds(compounds, Path("output"))
        >>> print(results["statistics"])
        {
            'total_compounds': 3,
            'matched_api': 2,
            'needs_review': 1,
            'unmatched': 0,
            'spoke_mapped': 2
        }
    """
    logger.info(f"Processing {len(compound_list)} compounds...")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Initialize components
    name_mapper = MetaboliteNameMapper()
    rag_mapper = MultiProviderMapper(
        compound_store=ChromaCompoundStore(),
        prompt_manager=PromptManager(),
        optimizer=DSPyOptimizer() if enable_optimization else None,
    )
    result_processor = ResultProcessor()
    metrics = MetricsTracker()

    # Optional components
    spoke_mapper = MetaboliteSPOKEMapper() if enable_spoke else None
    llm_analyzer = MetaboliteLLMAnalyzer() if enable_llm_analysis else None

    # Step 1: Initial API mapping
    api_results = await name_mapper.map_compounds(compound_list)
    metrics.track_mapping("api", api_results)

    # Step 2: RAG mapping for unmatched compounds
    unmatched = [c for c in compound_list if c not in api_results.matched]
    if unmatched:
        logger.info(f"Using RAG for {len(unmatched)} unmatched compounds...")
        rag_results = await rag_mapper.map_compounds(unmatched)
        metrics.track_mapping("rag", rag_results)
    else:
        rag_results = None

    # Step 3: Process and combine results
    combined_results = result_processor.process_results(
        api_results=api_results,
        rag_results=rag_results,
        confidence_threshold=confidence_threshold,
    )

    # Step 4: SPOKE integration (if enabled)
    spoke_analysis = None
    if enable_spoke and spoke_mapper:
        logger.info("Performing SPOKE pathway analysis...")
        spoke_entities = await spoke_mapper.map_to_spoke(combined_results.mapped)
        spoke_analysis = await spoke_mapper.analyze_pathways(spoke_entities)
        metrics.track_spoke_analysis(spoke_analysis)

    # Step 5: LLM analysis (if enabled)
    llm_insights = None
    if enable_llm_analysis and llm_analyzer:
        logger.info("Performing LLM analysis of results...")
        llm_insights = await llm_analyzer.analyze_results(
            mapping_results=combined_results,
            spoke_results=spoke_analysis,
        )
        metrics.track_llm_analysis(llm_insights)

    # Save results
    results_df = combined_results.to_dataframe()
    results_df.to_csv(output_dir / "mapping_results.csv", index=False)

    if spoke_analysis:
        pd.DataFrame(spoke_analysis).to_csv(
            output_dir / "spoke_analysis.csv", index=False
        )

    if llm_insights:
        with open(output_dir / "llm_insights.json", "w") as f:
            json.dump(llm_insights, f, indent=2)

    # Generate summary statistics
    statistics = {
        "total_compounds": len(compound_list),
        "matched_api": len(api_results.matched),
        "matched_rag": len(rag_results.matched) if rag_results else 0,
        "needs_review": len(combined_results.needs_review),
        "unmatched": len(combined_results.unmatched),
        "spoke_mapped": len(spoke_analysis) if spoke_analysis else 0,
    }

    metrics.save_metrics(output_dir / "metrics.json")

    return {
        "results": results_df,
        "statistics": statistics,
        "spoke_analysis": spoke_analysis,
        "llm_insights": llm_insights,
    }


async def main():
    """Run example workflow with command line arguments."""
    parser = argparse.ArgumentParser(description="Biomapper Complete Workflow Tutorial")
    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="Input file with compound names (one per line)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results"),
        help="Output directory for results",
    )
    parser.add_argument(
        "--optimize", action="store_true", help="Enable DSPy optimization for RAG"
    )
    parser.add_argument(
        "--confidence",
        type=float,
        default=0.8,
        help="Confidence threshold for matches (0.0-1.0)",
    )
    parser.add_argument(
        "--disable-spoke", action="store_true", help="Disable SPOKE integration"
    )
    parser.add_argument(
        "--disable-llm", action="store_true", help="Disable LLM analysis"
    )

    args = parser.parse_args()

    compounds = load_compounds(args.input)
    results = await process_compounds(
        compounds,
        args.output,
        enable_optimization=args.optimize,
        confidence_threshold=args.confidence,
        enable_spoke=not args.disable_spoke,
        enable_llm_analysis=not args.disable_llm,
    )

    logger.info("\nProcessing complete! Summary:")
    for key, value in results["statistics"].items():
        logger.info(f"  {key}: {value}")

    logger.info(f"\nResults saved to: {args.output}/")


if __name__ == "__main__":
    asyncio.run(main())
