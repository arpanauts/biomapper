#!/usr/bin/env python3
"""
Simple runner for three-way metabolomics pipeline using direct action execution.

DEPRECATION WARNING:
This script is deprecated and will be removed in v2.0.
Please use the new API client instead:
    biomapper run three_way_metabolomics_simple
    or
    python scripts/pipelines/run_three_way_simple.py
"""

import warnings
warnings.warn(
    "This script is deprecated and will be removed in v2.0. "
    "Use 'biomapper run three_way_metabolomics_simple' or "
    "'python scripts/pipelines/run_three_way_simple.py' instead.",
    DeprecationWarning,
    stacklevel=2
)

import asyncio
import logging
import sys
from pathlib import Path
from typing import Dict, Any
import os
import yaml

# Add biomapper to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import actions directly
from biomapper.core.strategy_actions import (
    LoadDatasetIdentifiersAction,
    NightingaleNmrMatchAction,
    BuildNightingaleReferenceAction,
    BaselineFuzzyMatchAction,
    MetaboliteApiEnrichmentAction,
    SemanticMetaboliteMatchAction,
    CombineMetaboliteMatchesAction,
    CalculateThreeWayOverlapAction,
    GenerateMetabolomicsReportAction
)

# Check for API keys
if "OPENAI_API_KEY" not in os.environ:
    logger.warning("OPENAI_API_KEY not set - semantic matching may fail")


async def run_three_way_pipeline():
    """Execute the complete three-way metabolomics mapping pipeline."""
    
    logger.info("=" * 80)
    logger.info("Starting Three-Way Metabolomics Mapping Pipeline")
    logger.info("=" * 80)
    
    # Initialize context
    context = {
        'custom_action_data': {},
        'results': {}
    }
    
    try:
        # Create output directory
        output_dir = Path("/home/ubuntu/biomapper/data/results/metabolomics_three_way")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # ===== Phase 1: Data Loading =====
        logger.info("\n=== Phase 1: Loading Datasets ===")
        
        # Load Israeli10K
        logger.info("Loading Israeli10K metabolomics data...")
        loader = LoadDatasetIdentifiersAction()
        result = await loader.execute_typed(
            params={
                "file_path": "/procedure/data/local_data/MAPPING_ONTOLOGIES/israeli10k/israeli10k_metabolomics_metadata.csv",
                "identifier_column": "tabular_field_name",
                "additional_columns": ["nightingale_metabolomics_original_name", "field_string", "description_string"],
                "output_key": "israeli10k_data"
            },
            context=context
        )
        if result.success:
            logger.info(f"✓ Loaded {len(context['results'].get('israeli10k_data', []))} Israeli10K metabolites")
        else:
            raise Exception(f"Failed to load Israeli10K: {result.message}")
        
        # Load UKBB
        logger.info("Loading UKBB NMR metabolomics data...")
        result = await loader.execute_typed(
            params={
                "file_path": "/procedure/data/local_data/MAPPING_ONTOLOGIES/ukbb/UKBB_NMR_Meta.tsv",
                "identifier_column": "title",
                "additional_columns": ["field_id", "Group", "Subgroup"],
                "output_key": "ukbb_data"
            },
            context=context
        )
        if result.success:
            logger.info(f"✓ Loaded {len(context['results'].get('ukbb_data', []))} UKBB metabolites")
        else:
            raise Exception(f"Failed to load UKBB: {result.message}")
        
        # Load Arivale
        logger.info("Loading Arivale metabolomics data...")
        result = await loader.execute_typed(
            params={
                "file_path": "/procedure/data/local_data/MAPPING_ONTOLOGIES/arivale/metabolomics_metadata.tsv",
                "identifier_column": "BIOCHEMICAL_NAME",
                "additional_columns": ["HMDB", "KEGG", "PUBCHEM", "CAS", "SUPER_PATHWAY", "SUB_PATHWAY"],
                "output_key": "arivale_data"
            },
            context=context
        )
        if result.success:
            logger.info(f"✓ Loaded {len(context['results'].get('arivale_data', []))} Arivale metabolites")
        else:
            raise Exception(f"Failed to load Arivale: {result.message}")
        
        # ===== Phase 2: Nightingale Platform Harmonization =====
        logger.info("\n=== Phase 2: Nightingale Platform Harmonization ===")
        
        # Match Israeli10K and UKBB
        logger.info("Matching Israeli10K and UKBB using Nightingale NMR commonality...")
        nmr_matcher = NightingaleNmrMatchAction()
        result = await nmr_matcher.execute_typed(
            params={
                "source_dataset_key": "israeli10k_data",
                "target_dataset_key": "ukbb_data",
                "source_nightingale_column": "nightingale_metabolomics_original_name",
                "target_title_column": "title",
                "match_strategy": "fuzzy",
                "confidence_threshold": 0.95,
                "output_key": "nightingale_matches",
                "unmatched_source_key": "israeli10k_unmatched",
                "unmatched_target_key": "ukbb_unmatched"
            },
            context=context
        )
        if result.success:
            matches = len(context['results'].get('nightingale_matches', []))
            logger.info(f"✓ Found {matches} Nightingale platform matches")
        else:
            raise Exception(f"Failed Nightingale matching: {result.message}")
        
        # Build Nightingale reference
        logger.info("Building unified Nightingale reference...")
        ref_builder = BuildNightingaleReferenceAction()
        result = await ref_builder.execute_typed(
            params={
                "israeli10k_data": "israeli10k_data",
                "ukbb_data": "ukbb_data",
                "matched_pairs": "nightingale_matches",
                "output_key": "nightingale_reference",
                "export_csv": True,
                "csv_path": str(output_dir / "nightingale_reference.csv"),
                "include_metadata": True
            },
            context=context
        )
        if result.success:
            ref_count = len(context['results'].get('nightingale_reference', []))
            logger.info(f"✓ Built Nightingale reference with {ref_count} entries")
        else:
            raise Exception(f"Failed to build reference: {result.message}")
        
        # ===== Phase 3: Progressive Arivale Matching =====
        logger.info("\n=== Phase 3: Progressive Arivale Matching ===")
        
        # Tier 1: Direct name matching
        logger.info("Tier 1: Baseline fuzzy matching for Arivale metabolites...")
        fuzzy_matcher = BaselineFuzzyMatchAction()
        result = await fuzzy_matcher.execute_typed(
            params={
                "source_dataset_key": "arivale_data",
                "target_dataset_key": "nightingale_reference",
                "source_column": "BIOCHEMICAL_NAME",
                "target_column": "unified_name",
                "threshold": 0.85,
                "algorithm": "token_set_ratio",
                "output_key": "baseline_matches",
                "unmatched_key": "unmatched.baseline.arivale_data",
                "track_metrics": True,
                "metrics_key": "metrics.baseline"
            },
            context=context
        )
        baseline_matches = len(context['results'].get('baseline_matches', []))
        logger.info(f"✓ Baseline matched {baseline_matches} metabolites")
        
        # Tier 2: API enrichment
        logger.info("Tier 2: Multi-API enrichment for unmatched Arivale metabolites...")
        api_enricher = MetaboliteApiEnrichmentAction()
        result = await api_enricher.execute_typed(
            params={
                "unmatched_dataset_key": "unmatched.baseline.arivale_data",
                "target_dataset_key": "nightingale_reference",
                "api_services": [
                    {
                        "service": "hmdb",
                        "input_column": "HMDB",
                        "output_fields": ["common_name", "synonyms", "iupac_name", "inchikey"],
                        "timeout": 30
                    },
                    {
                        "service": "pubchem",
                        "input_column": "PUBCHEM",
                        "output_fields": ["IUPACName", "synonyms", "InChIKey"],
                        "timeout": 30
                    },
                    {
                        "service": "cts",
                        "input_column": "KEGG",
                        "output_fields": ["chemical_name", "synonyms"],
                        "timeout": 20
                    }
                ],
                "target_column": "unified_name",
                "match_threshold": 0.80,
                "batch_size": 50,
                "output_key": "api_matches",
                "unmatched_key": "unmatched.api.arivale_data",
                "track_metrics": True,
                "metrics_key": "metrics.api"
            },
            context=context
        )
        api_matches = len(context['results'].get('api_matches', []))
        logger.info(f"✓ API enrichment matched {api_matches} additional metabolites")
        
        # Tier 3: Semantic/LLM matching
        if os.environ.get("OPENAI_API_KEY"):
            logger.info("Tier 3: Semantic matching using embeddings and LLM validation...")
            semantic_matcher = SemanticMetaboliteMatchAction()
            result = await semantic_matcher.execute_typed(
                params={
                    "unmatched_dataset": "unmatched.api.arivale_data",
                    "reference_map": "nightingale_reference",
                    "context_fields": {
                        "arivale": ["BIOCHEMICAL_NAME", "SUPER_PATHWAY", "SUB_PATHWAY"],
                        "nightingale": ["unified_name", "description_string", "category"]
                    },
                    "embedding_model": "text-embedding-ada-002",
                    "llm_model": "gpt-4",
                    "confidence_threshold": 0.75,
                    "embedding_similarity_threshold": 0.85,
                    "include_reasoning": True,
                    "max_llm_calls": 100,
                    "batch_size": 10,
                    "output_key": "semantic_matches",
                    "unmatched_key": "final_unmatched"
                },
                context=context
            )
            semantic_matches = len(context['results'].get('semantic_matches', []))
            logger.info(f"✓ Semantic matching found {semantic_matches} additional matches")
        else:
            logger.warning("Skipping semantic matching - OPENAI_API_KEY not set")
            context['results']['semantic_matches'] = []
        
        # ===== Phase 4: Three-Way Integration =====
        logger.info("\n=== Phase 4: Three-Way Integration ===")
        
        # Combine all matches
        logger.info("Combining all matching results with provenance tracking...")
        combiner = CombineMetaboliteMatchesAction()
        result = await combiner.execute_typed(
            params={
                "nightingale_pairs": "nightingale_matches",
                "arivale_mappings": [
                    {
                        "key": "baseline_matches",
                        "tier": "direct",
                        "method": "baseline_fuzzy",
                        "confidence_weight": 1.0
                    },
                    {
                        "key": "api_matches",
                        "tier": "api_enriched",
                        "method": "multi_api",
                        "confidence_weight": 0.9
                    },
                    {
                        "key": "semantic_matches",
                        "tier": "semantic",
                        "method": "llm_validated",
                        "confidence_weight": 0.8
                    }
                ],
                "output_key": "three_way_matches",
                "track_provenance": True,
                "min_confidence": 0.5
            },
            context=context
        )
        total_matches = len(context['results'].get('three_way_matches', []))
        logger.info(f"✓ Combined into {total_matches} three-way matches")
        
        # ===== Phase 5: Analysis & Reporting =====
        logger.info("\n=== Phase 5: Analysis & Reporting ===")
        
        # Calculate overlap statistics
        logger.info("Calculating comprehensive three-way overlap statistics...")
        overlap_calc = CalculateThreeWayOverlapAction()
        result = await overlap_calc.execute_typed(
            params={
                "input_key": "three_way_matches",
                "dataset_names": ["Israeli10K", "UKBB", "Arivale"],
                "confidence_threshold": 0.8,
                "output_dir": str(output_dir / "statistics"),
                "mapping_combo_id": "Israeli10K_UKBB_Arivale_complete",
                "generate_visualizations": ["venn_diagram_3way", "confidence_heatmap", "overlap_progression_chart"],
                "output_key": "three_way_statistics",
                "export_detailed_results": True
            },
            context=context
        )
        if result.success:
            stats = context['results'].get('three_way_statistics', {})
            three_way = stats.get('three_way_overlap', {}).get('count', 0)
            logger.info(f"✓ Found {three_way} metabolites present in all three datasets")
        
        # Generate final report
        logger.info("Generating comprehensive metabolomics mapping report...")
        reporter = GenerateMetabolomicsReportAction()
        result = await reporter.execute_typed(
            params={
                "statistics_key": "three_way_statistics",
                "matches_key": "three_way_matches",
                "nightingale_reference": "nightingale_reference",
                "metrics_keys": ["metrics.baseline", "metrics.api", "metrics.semantic"],
                "output_dir": str(output_dir / "reports"),
                "report_format": "markdown",
                "include_sections": [
                    "executive_summary",
                    "methodology_overview",
                    "dataset_overview",
                    "progressive_matching_results",
                    "three_way_overlap_analysis",
                    "confidence_distribution",
                    "quality_metrics",
                    "recommendations"
                ],
                "export_formats": ["markdown", "html", "json"],
                "include_visualizations": True,
                "max_examples": 10
            },
            context=context
        )
        if result.success:
            logger.info("✓ Generated comprehensive report")
        
        # Final summary
        logger.info("\n" + "=" * 80)
        logger.info("Pipeline completed successfully!")
        logger.info("=" * 80)
        logger.info(f"\nGenerated files in {output_dir}:")
        for file in output_dir.rglob("*"):
            if file.is_file():
                logger.info(f"  - {file.relative_to(output_dir)}")
                
    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        sys.exit(1)


def main():
    """Main entry point."""
    asyncio.run(run_three_way_pipeline())


if __name__ == "__main__":
    main()