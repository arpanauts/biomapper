#!/usr/bin/env python3
"""
Integration Script: Merge Harmonization COMPLETE Files with Kraken Mapping Results

This script merges existing harmonization COMPLETE.tsv files (which contain all original
entities plus LLM reasoning for unmapped entities) with kraken mapping results to create
enhanced COMPLETE files in the kraken directories.

The approach:
1. Load harmonization COMPLETE.tsv as base (preserves all entities + LLM reasoning)
2. Load kraken mapping results
3. Left outer merge to add kraken mapping columns where available
4. Save enhanced COMPLETE file to kraken results directory
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import json
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def merge_complete_with_kraken(harmonization_complete_path, kraken_results_path,
                              output_path, join_columns, kraken_columns=None):
    """
    Merge harmonization COMPLETE file with kraken mapping results.

    Args:
        harmonization_complete_path: Path to harmonization COMPLETE.tsv file
        kraken_results_path: Path to kraken mapping results file
        output_path: Path for enhanced COMPLETE output
        join_columns: Dict with 'harmonization' and 'kraken' keys for join columns
        kraken_columns: List of kraken columns to preserve (default: common kraken cols)
    """
    logger.info(f"Merging {Path(harmonization_complete_path).name} with {Path(kraken_results_path).name}")

    if kraken_columns is None:
        kraken_columns = ['kraken_node_id', 'kraken_name', 'kraken_category',
                         'mapping_confidence', 'mapping_type', 'semantic_category']

    # Load harmonization COMPLETE file (base with all entities + LLM reasoning)
    logger.info(f"Loading harmonization COMPLETE file: {harmonization_complete_path}")
    harmonization_df = pd.read_csv(harmonization_complete_path, sep='\t')
    logger.info(f"  - Loaded {len(harmonization_df)} entities from harmonization")

    # Load kraken mapping results
    logger.info(f"Loading kraken results: {kraken_results_path}")
    if not Path(kraken_results_path).exists():
        logger.warning(f"  - Kraken file not found: {kraken_results_path}")
        return harmonization_df

    kraken_df = pd.read_csv(kraken_results_path, sep='\t')
    logger.info(f"  - Loaded {len(kraken_df)} kraken mappings")

    # Filter kraken columns to only include what we want to add
    available_kraken_cols = [col for col in kraken_columns if col in kraken_df.columns]
    join_cols_to_add = [join_columns['kraken']] + available_kraken_cols
    kraken_subset = kraken_df[join_cols_to_add].copy()

    logger.info(f"  - Adding kraken columns: {available_kraken_cols}")

    # Left outer merge (harmonization as base to preserve all entities)
    merged_df = harmonization_df.merge(
        kraken_subset,
        left_on=join_columns['harmonization'],
        right_on=join_columns['kraken'],
        how='left',
        suffixes=('', '_kraken')
    )

    # Count successful integrations
    kraken_mapped = merged_df['kraken_node_id'].notna().sum() if 'kraken_node_id' in merged_df.columns else 0
    harmonization_unmapped = (harmonization_df.get('loinc_code', harmonization_df.get('mondo_id', pd.Series())) == 'NO_MATCH').sum()

    logger.info(f"  - Total entities preserved: {len(merged_df)}")
    logger.info(f"  - Kraken mappings integrated: {kraken_mapped}")
    logger.info(f"  - Harmonization unmapped preserved: {harmonization_unmapped}")

    # Add metadata
    merged_df['integration_timestamp'] = datetime.now().isoformat()
    merged_df['integration_source'] = f"harmonization+kraken"

    # Save enhanced COMPLETE file
    output_dir = Path(output_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)

    merged_df.to_csv(output_path, sep='\t', index=False)
    logger.info(f"  - Enhanced COMPLETE file saved: {output_path}")

    return merged_df

def integrate_arivale_proteins():
    """Integrate Arivale proteins COMPLETE file with kraken results."""
    logger.info("\n=== INTEGRATING ARIVALE PROTEINS ===")

    harmonization_path = "/home/ubuntu/biomapper/data/harmonization/proteins/arivale_proteins_progressive_to_convert_to_biomapper/results/arivale_proteins_progressive_mapping_COMPLETE.tsv"
    kraken_path = "/home/ubuntu/biomapper/data/kraken_mapping/proteins/arivale_to_kraken_to_convert_to_biomapper/results/arivale_kraken_mappings.tsv"
    output_path = "/home/ubuntu/biomapper/data/kraken_mapping/proteins/arivale_to_kraken_to_convert_to_biomapper/results/arivale_proteins_COMPLETE.tsv"

    join_columns = {
        'harmonization': 'name',  # protein name
        'kraken': 'arivale_uniprot'  # need to check actual column name
    }

    # First check the actual column names
    harmonization_df = pd.read_csv(harmonization_path, sep='\t', nrows=1)
    kraken_df = pd.read_csv(kraken_path, sep='\t', nrows=1)

    logger.info(f"Harmonization columns: {list(harmonization_df.columns)[:10]}")
    logger.info(f"Kraken columns: {list(kraken_df.columns)[:10]}")

    # Adjust join columns based on actual schema
    if 'uniprot' in harmonization_df.columns and 'arivale_uniprot' in kraken_df.columns:
        join_columns = {'harmonization': 'uniprot', 'kraken': 'arivale_uniprot'}
    elif 'name' in harmonization_df.columns and 'arivale_name' in kraken_df.columns:
        join_columns = {'harmonization': 'name', 'kraken': 'arivale_name'}

    logger.info(f"Using join columns: {join_columns}")

    return merge_complete_with_kraken(harmonization_path, kraken_path, output_path, join_columns)

def integrate_questionnaires():
    """Integrate questionnaires COMPLETE files with kraken results."""
    logger.info("\n=== INTEGRATING QUESTIONNAIRES ===")

    integrations = [
        {
            'name': 'Arivale LOINC Questionnaires',
            'harmonization': '/home/ubuntu/biomapper/data/harmonization/questionnaires/results/arivale_questionnaires_weighted_loinc_COMPLETE.tsv',
            'kraken': '/home/ubuntu/biomapper/data/kraken_mapping/questionnaires/arivale_to_kraken_to_convert_to_biomapper/results/arivale_to_kraken_mappings.tsv',
            'output': '/home/ubuntu/biomapper/data/kraken_mapping/questionnaires/arivale_to_kraken_to_convert_to_biomapper/results/arivale_questionnaires_COMPLETE.tsv',
            'join_cols': {'harmonization': 'field_name', 'kraken': 'arivale_field'}
        },
        {
            'name': 'Arivale MONDO Questionnaires',
            'harmonization': '/home/ubuntu/biomapper/data/harmonization/mondo/results/arivale_questionnaires_mondo_COMPLETE.tsv',
            'kraken': '/home/ubuntu/biomapper/data/kraken_mapping/questionnaires/arivale_mondo_questionnaires_to_convert_to_biomapper/results/arivale_questionnaires_mondo.tsv',
            'output': '/home/ubuntu/biomapper/data/kraken_mapping/questionnaires/arivale_mondo_questionnaires_to_convert_to_biomapper/results/arivale_mondo_questionnaires_COMPLETE.tsv',
            'join_cols': {'harmonization': 'field_name', 'kraken': 'field_name'}
        },
        {
            'name': 'UKBB LOINC Questionnaires',
            'harmonization': '/home/ubuntu/biomapper/data/harmonization/questionnaires/results/ukbb_questionnaires_weighted_loinc_COMPLETE.tsv',
            'kraken': '/home/ubuntu/biomapper/data/kraken_mapping/questionnaires/ukbb_to_kraken_to_convert_to_biomapper/results/ukbb_questionnaires_to_kraken_v1.0.0.tsv',
            'output': '/home/ubuntu/biomapper/data/kraken_mapping/questionnaires/ukbb_to_kraken_to_convert_to_biomapper/results/ukbb_questionnaires_COMPLETE.tsv',
            'join_cols': {'harmonization': 'field_name', 'kraken': 'ukbb_field_name'}
        },
        {
            'name': 'Israeli10K LOINC Questionnaires',
            'harmonization': '/home/ubuntu/biomapper/data/harmonization/questionnaires/results/israeli10k_questionnaires_weighted_loinc_COMPLETE.tsv',
            'kraken': '/home/ubuntu/biomapper/data/kraken_mapping/questionnaires/israeli10k_to_kraken_to_convert_to_biomapper/results/israeli10k_kraken_mappings.tsv',
            'output': '/home/ubuntu/biomapper/data/kraken_mapping/questionnaires/israeli10k_to_kraken_to_convert_to_biomapper/results/israeli10k_questionnaires_COMPLETE.tsv',
            'join_cols': {'harmonization': 'field_name', 'kraken': 'field_name'}
        }
    ]

    results = []
    for integration in integrations:
        logger.info(f"\nProcessing {integration['name']}")
        try:
            result = merge_complete_with_kraken(
                integration['harmonization'],
                integration['kraken'],
                integration['output'],
                integration['join_cols']
            )
            results.append(result)
        except Exception as e:
            logger.error(f"Failed to integrate {integration['name']}: {e}")
            continue

    return results

def integrate_chemistry():
    """Integrate chemistry COMPLETE files with kraken results."""
    logger.info("\n=== INTEGRATING CHEMISTRY ===")

    integrations = [
        {
            'name': 'UKBB Chemistry',
            'harmonization': '/home/ubuntu/biomapper/data/harmonization/chemistry/results/ukbb_chemistry_weighted_loinc_COMPLETE.tsv',
            'kraken': '/home/ubuntu/biomapper/data/kraken_mapping/chemistry/ukbb_standard_to_kraken_to_convert_to_biomapper/results/ukbb_kraken_mappings_updated.tsv',
            'output': '/home/ubuntu/biomapper/data/kraken_mapping/chemistry/ukbb_standard_to_kraken_to_convert_to_biomapper/results/ukbb_chemistry_COMPLETE.tsv',
            'join_cols': {'harmonization': 'field_name', 'kraken': 'ukbb_field_name'}
        }
    ]

    results = []
    for integration in integrations:
        logger.info(f"\nProcessing {integration['name']}")
        try:
            result = merge_complete_with_kraken(
                integration['harmonization'],
                integration['kraken'],
                integration['output'],
                integration['join_cols']
            )
            results.append(result)
        except Exception as e:
            logger.error(f"Failed to integrate {integration['name']}: {e}")
            continue

    return results

def main():
    """Execute all integrations."""
    logger.info("="*60)
    logger.info("HARMONIZATION + KRAKEN INTEGRATION")
    logger.info("="*60)

    try:
        # Integration 1: Arivale Proteins
        proteins_result = integrate_arivale_proteins()

        # Integration 2: Questionnaires
        questionnaires_results = integrate_questionnaires()

        # Integration 3: Chemistry
        chemistry_results = integrate_chemistry()

        logger.info("\n" + "="*60)
        logger.info("INTEGRATION SUMMARY")
        logger.info("="*60)
        logger.info("✅ Arivale proteins integrated")
        logger.info(f"✅ {len(questionnaires_results)} questionnaire files integrated")
        logger.info(f"✅ {len(chemistry_results)} chemistry files integrated")
        logger.info("\nEnhanced COMPLETE.tsv files created in kraken mapping directories")
        logger.info("="*60)

        return True

    except Exception as e:
        logger.error(f"Integration failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)