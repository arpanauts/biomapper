#!/usr/bin/env python3
"""
Stage 4: Integrate Ontological Enrichment into Kraken Mapping Structure

This script integrates the comprehensive ontological enrichment results (85.6% coverage)
into the existing Kraken mapping structure, replacing the basic mapping results (48% coverage)
while maintaining compatibility with the BiOMapper coverage calculation system.

Input:  - Ontological enrichment results: arivale_metabolites_final_with_rag_20250924_091325.tsv
        - Current Kraken results: arivale_metabolites_production_standardized.tsv
        - Original Arivale metabolites: metabolomics_metadata.tsv

Output: - Enhanced production standardized file with 85%+ coverage
        - Updated mapping statistics and metadata
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import json
import re
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
ENRICHMENT_RESULTS = "/home/ubuntu/biomapper/data/harmonization/metabolites/arivale_metabolites_ontological_enrichment_to_convert_to_biomapper/results/arivale_metabolites_final_with_rag_20250924_091325.tsv"
CURRENT_KRAKEN_FILE = "results/arivale_metabolites_production_standardized.tsv"
ORIGINAL_ARIVALE_FILE = "/home/ubuntu/biomapper/data/harmonization/metabolites/arivale_metabolites_ontological_enrichment_to_convert_to_biomapper/data/arivale_metabolites_filtered.tsv"
OUTPUT_FILE = "results/arivale_metabolites_production_standardized_enhanced.tsv"
STATISTICS_FILE = "results/integration_statistics.json"

def load_enrichment_results():
    """Load the comprehensive ontological enrichment results."""
    logger.info("Loading ontological enrichment results...")

    enriched_df = pd.read_csv(ENRICHMENT_RESULTS, sep='\t')
    logger.info(f"  - Loaded {len(enriched_df)} enriched metabolites")

    # Analyze enrichment status distribution
    status_counts = enriched_df['enrichment_status'].value_counts()
    logger.info("  - Enrichment status breakdown:")
    for status, count in status_counts.items():
        percentage = (count / len(enriched_df)) * 100
        logger.info(f"    • {status}: {count} ({percentage:.1f}%)")

    return enriched_df

def load_current_kraken_results():
    """Load existing Kraken mapping results for comparison."""
    logger.info("Loading current Kraken mapping results...")

    current_file = Path(CURRENT_KRAKEN_FILE)
    if current_file.exists():
        current_df = pd.read_csv(current_file, sep='\t')
        logger.info(f"  - Loaded {len(current_df)} current Kraken mappings")

        # Analyze current mapping success
        if 'mapped' in current_df.columns:
            mapped_count = current_df['mapped'].sum()
            percentage = (mapped_count / len(current_df)) * 100
            logger.info(f"  - Current mapping success: {mapped_count}/{len(current_df)} ({percentage:.1f}%)")

        return current_df
    else:
        logger.warning(f"  - Current Kraken file not found: {current_file}")
        return pd.DataFrame()

def load_original_arivale_data():
    """Load original Arivale metabolite data for complete coverage."""
    logger.info("Loading original Arivale metabolite data...")

    original_df = pd.read_csv(ORIGINAL_ARIVALE_FILE, sep='\t')
    logger.info(f"  - Loaded {len(original_df)} original Arivale metabolites")

    return original_df

def normalize_hmdb_id(hmdb_id):
    """Normalize HMDB ID to Kraken node format."""
    if pd.isna(hmdb_id) or hmdb_id == '':
        return None

    # Handle different HMDB formats
    hmdb_str = str(hmdb_id).strip()

    # Extract HMDB ID pattern (e.g., HMDB01301 or HMDB0001301)
    hmdb_match = re.search(r'HMDB(\d+)', hmdb_str, re.IGNORECASE)
    if hmdb_match:
        hmdb_number = hmdb_match.group(1)
        # Ensure 7-digit format (pad with zeros if needed)
        padded_number = hmdb_number.zfill(7)
        return f"HMDB:HMDB{padded_number}"

    return None

def calculate_mapping_confidence(row):
    """Calculate mapping confidence based on enrichment method and source."""

    # Check enrichment status
    enrichment_status = row.get('enrichment_status', '')

    if enrichment_status == 'hmdb_mapped':
        # Original HMDB mapping - highest confidence
        if 'original' in str(row.get('hmdb_source', '')):
            return 1.0
        else:
            return 0.95

    elif enrichment_status == 'rag_mapped':
        # Use RAG confidence if available
        rag_confidence = row.get('rag_confidence', 0.0)
        try:
            if pd.notna(rag_confidence) and rag_confidence != '':
                confidence_val = float(rag_confidence)
                if confidence_val > 0:
                    return confidence_val
        except (ValueError, TypeError):
            pass
        return 0.75  # Default for RAG mappings without confidence

    elif enrichment_status in ['partially_enriched']:
        return 0.65  # Moderate confidence for partial enrichment

    else:
        # unenriched, rag_no_match
        return 0.0

def transform_enrichment_to_kraken_format(enriched_df):
    """Transform enrichment results to Kraken-compatible format."""
    logger.info("Transforming enrichment results to Kraken format...")

    # Start with enriched dataframe
    kraken_df = enriched_df.copy()

    # Transform HMDB IDs to Kraken node format
    kraken_df['kraken_node_id'] = kraken_df['final_hmdb_id'].apply(normalize_hmdb_id)

    # Set kraken_name based on BIOCHEMICAL_NAME
    kraken_df['kraken_name'] = kraken_df['BIOCHEMICAL_NAME']

    # Set kraken_category
    kraken_df['kraken_category'] = 'biolink:MolecularEntity'

    # Calculate mapping confidence
    kraken_df['mapping_confidence'] = kraken_df.apply(calculate_mapping_confidence, axis=1)

    # Set mapped boolean flag
    kraken_df['mapped'] = (kraken_df['kraken_node_id'].notna() &
                          (kraken_df['mapping_confidence'] > 0.0))

    # Add processing information
    kraken_df['processing_timestamp'] = datetime.now().isoformat()
    kraken_df['processing_notes'] = kraken_df.apply(
        lambda row: f"Enriched via {row.get('enrichment_status', 'unknown')} | " +
                   f"Methods: {row.get('enrichment_methods', 'none')}", axis=1
    )

    # Select standard Kraken columns
    kraken_columns = [
        'CHEMICAL_ID', 'BIOCHEMICAL_NAME', 'SUB_PATHWAY', 'SUPER_PATHWAY',
        'kraken_node_id', 'kraken_name', 'kraken_category', 'mapping_confidence',
        'mapped', 'processing_timestamp', 'processing_notes'
    ]

    # Add missing columns if they don't exist
    for col in kraken_columns:
        if col not in kraken_df.columns:
            if col in ['CHEMICAL_ID', 'BIOCHEMICAL_NAME', 'SUB_PATHWAY', 'SUPER_PATHWAY']:
                logger.warning(f"Missing required column: {col}")
                kraken_df[col] = ''
            else:
                kraken_df[col] = None

    # Filter to standard columns
    kraken_df = kraken_df[kraken_columns]

    return kraken_df

def create_complete_outer_merge(kraken_transformed_df, original_arivale_df):
    """Create complete left outer merge ensuring all original metabolites are preserved."""
    logger.info("Creating complete outer merge with all original metabolites...")

    # Start with original Arivale data to ensure complete coverage
    complete_df = original_arivale_df.copy()

    # Standardize column names
    if 'COMP_ID' in complete_df.columns and 'CHEMICAL_ID' not in complete_df.columns:
        complete_df['CHEMICAL_ID'] = complete_df['COMP_ID']

    # Merge with enriched Kraken data
    complete_df = complete_df.merge(
        kraken_transformed_df,
        on=['CHEMICAL_ID', 'BIOCHEMICAL_NAME', 'SUB_PATHWAY', 'SUPER_PATHWAY'],
        how='left',
        suffixes=('', '_enriched')
    )

    # Fill missing mapping information for unprocessed metabolites
    complete_df['kraken_node_id'] = complete_df['kraken_node_id'].fillna('')
    complete_df['kraken_name'] = complete_df['kraken_name'].fillna(complete_df['BIOCHEMICAL_NAME'])
    complete_df['kraken_category'] = complete_df['kraken_category'].fillna('biolink:MolecularEntity')
    complete_df['mapping_confidence'] = complete_df['mapping_confidence'].fillna(0.0)
    complete_df['mapped'] = complete_df['mapped'].fillna(False)
    complete_df['processing_timestamp'] = complete_df['processing_timestamp'].fillna(datetime.now().isoformat())
    complete_df['processing_notes'] = complete_df['processing_notes'].fillna('Not processed in ontological enrichment')

    logger.info(f"  - Complete dataset: {len(complete_df)} metabolites")

    return complete_df

def generate_integration_statistics(original_df, current_kraken_df, enhanced_df):
    """Generate comprehensive statistics about the integration results."""
    logger.info("Generating integration statistics...")

    # Calculate coverage improvements
    original_count = len(original_df)

    current_mapped = len(current_kraken_df[current_kraken_df['mapped'] == True]) if len(current_kraken_df) > 0 else 0
    current_coverage = (current_mapped / original_count * 100) if original_count > 0 else 0

    enhanced_mapped = len(enhanced_df[enhanced_df['mapped'] == True])
    enhanced_coverage = (enhanced_mapped / original_count * 100) if original_count > 0 else 0

    # Confidence distribution
    confidence_dist = enhanced_df['mapping_confidence'].value_counts().sort_index().to_dict()

    # Processing method distribution
    if 'processing_notes' in enhanced_df.columns:
        method_counts = enhanced_df['processing_notes'].str.extract(r'Enriched via (\w+)')[0].value_counts()
        method_distribution = method_counts.to_dict()
    else:
        method_distribution = {}

    statistics = {
        'integration_timestamp': datetime.now().isoformat(),
        'data_sources': {
            'enrichment_results': ENRICHMENT_RESULTS,
            'current_kraken_results': CURRENT_KRAKEN_FILE,
            'original_arivale_data': ORIGINAL_ARIVALE_FILE
        },
        'coverage_analysis': {
            'total_metabolites': original_count,
            'previous_mapped': current_mapped,
            'previous_coverage_percent': round(current_coverage, 2),
            'enhanced_mapped': enhanced_mapped,
            'enhanced_coverage_percent': round(enhanced_coverage, 2),
            'improvement': {
                'additional_mapped': enhanced_mapped - current_mapped,
                'coverage_increase_percent': round(enhanced_coverage - current_coverage, 2)
            }
        },
        'confidence_distribution': {str(k): int(v) for k, v in confidence_dist.items()},
        'enrichment_method_distribution': {str(k): int(v) for k, v in method_distribution.items()},
        'quality_metrics': {
            'high_confidence_mappings': len(enhanced_df[enhanced_df['mapping_confidence'] >= 0.8]),
            'medium_confidence_mappings': len(enhanced_df[(enhanced_df['mapping_confidence'] >= 0.5) &
                                                         (enhanced_df['mapping_confidence'] < 0.8)]),
            'low_confidence_mappings': len(enhanced_df[(enhanced_df['mapping_confidence'] > 0.0) &
                                                      (enhanced_df['mapping_confidence'] < 0.5)]),
            'unmapped': len(enhanced_df[enhanced_df['mapping_confidence'] == 0.0])
        }
    }

    return statistics

def main():
    """Execute Stage 4: Ontological Enrichment Integration."""
    logger.info("="*60)
    logger.info("STAGE 4: ONTOLOGICAL ENRICHMENT INTEGRATION")
    logger.info("="*60)

    try:
        # Step 1: Load all data sources
        logger.info("\nStep 1: Loading data sources...")
        enriched_df = load_enrichment_results()
        current_kraken_df = load_current_kraken_results()
        original_df = load_original_arivale_data()

        # Step 2: Transform enrichment results to Kraken format
        logger.info("\nStep 2: Transforming to Kraken format...")
        kraken_format_df = transform_enrichment_to_kraken_format(enriched_df)

        mapped_count = kraken_format_df['mapped'].sum()
        total_count = len(kraken_format_df)
        logger.info(f"  - Transformed results: {mapped_count}/{total_count} mapped ({mapped_count/total_count*100:.1f}%)")

        # Step 3: Create complete outer merge
        logger.info("\nStep 3: Creating complete dataset...")
        enhanced_df = create_complete_outer_merge(kraken_format_df, original_df)

        # Step 4: Generate statistics
        logger.info("\nStep 4: Generating statistics...")
        statistics = generate_integration_statistics(original_df, current_kraken_df, enhanced_df)

        # Step 5: Save enhanced results
        logger.info("\nStep 5: Saving enhanced results...")

        # Create results directory if it doesn't exist
        results_dir = Path("results")
        results_dir.mkdir(exist_ok=True)

        # Save enhanced metabolite mappings
        enhanced_df.to_csv(OUTPUT_FILE, sep='\t', index=False)
        logger.info(f"  - Enhanced mappings saved: {OUTPUT_FILE}")

        # Save statistics
        with open(STATISTICS_FILE, 'w') as f:
            json.dump(statistics, f, indent=2)
        logger.info(f"  - Statistics saved: {STATISTICS_FILE}")

        # Display summary
        logger.info("\n" + "="*60)
        logger.info("INTEGRATION SUMMARY")
        logger.info("="*60)
        logger.info(f"Total metabolites: {statistics['coverage_analysis']['total_metabolites']}")
        logger.info(f"Previous coverage: {statistics['coverage_analysis']['previous_coverage_percent']}%")
        logger.info(f"Enhanced coverage: {statistics['coverage_analysis']['enhanced_coverage_percent']}%")
        logger.info(f"Coverage improvement: +{statistics['coverage_analysis']['improvement']['coverage_increase_percent']}%")
        logger.info(f"Additional mappings: +{statistics['coverage_analysis']['improvement']['additional_mapped']}")

        logger.info("\nQuality distribution:")
        logger.info(f"  - High confidence (≥0.8): {statistics['quality_metrics']['high_confidence_mappings']}")
        logger.info(f"  - Medium confidence (0.5-0.8): {statistics['quality_metrics']['medium_confidence_mappings']}")
        logger.info(f"  - Low confidence (0.0-0.5): {statistics['quality_metrics']['low_confidence_mappings']}")
        logger.info(f"  - Unmapped: {statistics['quality_metrics']['unmapped']}")

        logger.info("\n" + "="*60)
        logger.info("STAGE 4 COMPLETED SUCCESSFULLY")
        logger.info("Enhanced production file ready for BiOMapper coverage calculation")
        logger.info("="*60)

        return True

    except Exception as e:
        logger.error(f"Error in Stage 4 integration: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)