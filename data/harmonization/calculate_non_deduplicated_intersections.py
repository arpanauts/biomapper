#!/usr/bin/env python3
"""
Non-Deduplicated Venn Intersection Calculator
Counts all source rows/measurements, not just unique canonical IDs.
"""

import pandas as pd
import numpy as np
import json
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Set, Tuple, Optional
from datetime import datetime
import sys

# Add parent directory to path to import from calculate_coverage_data
sys.path.append('/home/ubuntu/biomapper/data')

@dataclass
class EntityMeasurement:
    """Single measurement/row from source file"""
    cohort: str
    entity_id: str
    row_index: int
    metadata: dict

@dataclass
class EntityOverlap:
    """Enriched measurement with overlap info"""
    measurement: EntityMeasurement
    exists_in_arivale: bool
    exists_in_ukbb: bool
    exists_in_hpp: bool
    venn_region: str


class SourceMeasurementExtractor:
    """Extract all source rows as measurements (non-deduplicated)."""

    def __init__(self, base_dir="/home/ubuntu/biomapper/data"):
        self.base_dir = Path(base_dir)

        # Import source file paths from calculate_coverage_data.py
        # These are the ORIGINAL source files with all rows
        self.source_files = {
            # Proteins - source TSV files with all protein measurements
            ('proteins', 'Arivale'): 'kraken_mapping/proteins/arivale_to_kraken_to_convert_to_biomapper/data/arivale_proteins_normalized.tsv',
            ('proteins', 'UKBB'): 'kraken_mapping/proteins/ukbb_to_kraken_to_convert_to_biomapper/data/ukbb_proteins_cleaned.tsv',
            ('proteins', 'HPP'): 'harmonization/proteins/enhanced_cross_cohort_proteins_harmonization/results/enhanced_cross_cohort_proteins_latest.tsv',

            # Metabolites - use comprehensive enhanced files
            ('metabolites', 'Arivale'): 'kraken_mapping/metabolites/arivale_comprehensive_enhanced/arivale_metabolites_comprehensive_enhanced_20250925_212751.tsv',
            ('metabolites', 'UKBB'): 'harmonization/metabolites/corrected_cross_cohort_metabolites_harmonization/results/corrected_cross_cohort_metabolites_latest.tsv',
            ('metabolites', 'HPP'): 'harmonization/metabolites/corrected_cross_cohort_metabolites_harmonization/results/corrected_cross_cohort_metabolites_latest.tsv',

            # Chemistry - use enhanced cross-cohort file
            ('chemistry', 'Arivale'): 'harmonization/chemistry/cross_cohort_chemistry_to_convert_to_biomapper/results/enhanced_cross_cohort_chemistry_latest.tsv',
            ('chemistry', 'UKBB'): 'harmonization/chemistry/cross_cohort_chemistry_to_convert_to_biomapper/results/enhanced_cross_cohort_chemistry_latest.tsv',
            ('chemistry', 'HPP'): 'harmonization/chemistry/cross_cohort_chemistry_to_convert_to_biomapper/results/enhanced_cross_cohort_chemistry_latest.tsv',

            # Demographics - use harmonized file
            ('demographics', 'Arivale'): 'harmonization/demographics/cross_cohort_demographics_to_convert_to_biomapper/results/harmonized_demographics.tsv',
            ('demographics', 'UKBB'): 'harmonization/demographics/cross_cohort_demographics_to_convert_to_biomapper/results/harmonized_demographics.tsv',
            ('demographics', 'HPP'): 'harmonization/demographics/cross_cohort_demographics_to_convert_to_biomapper/results/harmonized_demographics.tsv',

            # Questionnaires → LOINC - NEW v1.0 files for Arivale
            ('questionnaires_loinc', 'Arivale'): 'harmonization/analysis_results/arivale_questionnaires_loinc_v1.0.tsv',
            ('questionnaires_loinc', 'UKBB'): 'harmonization/questionnaires/hierarchical_loinc_questionnaire_entities_latest.json',
            ('questionnaires_loinc', 'HPP'): 'harmonization/questionnaires/hierarchical_loinc_questionnaire_entities_latest.json',

            # Questionnaires → MONDO - NEW v1.0 files for Arivale
            ('questionnaires_mondo', 'Arivale'): 'harmonization/analysis_results/arivale_questionnaires_mondo_v1.0.tsv',
            ('questionnaires_mondo', 'UKBB'): 'harmonization/mondo/hierarchical_mondo_questionnaire_entities_latest.json',
            ('questionnaires_mondo', 'HPP'): 'harmonization/mondo/hierarchical_mondo_questionnaire_entities_latest.json',
        }

    def get_id_column(self, entity_type: str, cohort: str) -> str:
        """Get the appropriate ID column for each entity type and cohort."""

        if entity_type == 'proteins':
            if cohort == 'Arivale':
                return 'uniprot_normalized'
            elif cohort == 'UKBB':
                return 'ukbb_uniprot'
            else:  # HPP
                return 'canonical_uniprot_id'

        elif entity_type == 'metabolites':
            if cohort == 'Arivale':
                return 'metabolite'
            else:
                return 'metabolite_id'

        elif entity_type in ['chemistry', 'demographics']:
            return 'loinc_code'

        elif entity_type == 'questionnaires_loinc':
            return 'loinc_code'

        elif entity_type == 'questionnaires_mondo':
            return 'mondo_id'

        else:
            raise ValueError(f"Unknown entity type: {entity_type}")

    def extract_measurements(self, entity_type: str, cohort: str) -> List[EntityMeasurement]:
        """Extract all rows as measurements for a given entity type and cohort."""

        print(f"  Extracting {cohort} {entity_type} measurements...")

        file_path = self.source_files.get((entity_type, cohort))
        if not file_path:
            print(f"    WARNING: No source file for {entity_type} {cohort}")
            return []

        full_path = self.base_dir / file_path

        if not full_path.exists():
            print(f"    WARNING: File not found: {full_path}")
            return []

        measurements = []

        try:
            # Handle JSON files for UKBB/HPP questionnaires
            if file_path.endswith('.json'):
                with open(full_path, 'r') as f:
                    data = json.load(f)

                # Extract entities for this cohort from hierarchical JSON
                cohort_key = 'israeli10k' if cohort == 'HPP' else cohort.lower()

                for canonical_id, entity_data in data.items():
                    cohorts = entity_data.get('cohort_contexts', {})
                    if cohorts.get(cohort_key):
                        measurements.append(EntityMeasurement(
                            cohort=cohort,
                            entity_id=canonical_id,
                            row_index=len(measurements),
                            metadata={'source': 'hierarchical_json'}
                        ))

            else:
                # Load TSV/CSV file
                df = pd.read_csv(full_path, sep='\t')

                # Special handling for different entity types
                if entity_type == 'proteins' and cohort == 'HPP':
                    # Filter to only HPP proteins
                    df = df[df['israeli10k_present'] == True]

                elif entity_type == 'metabolites' and cohort in ['UKBB', 'HPP']:
                    # Filter to cohort-specific metabolites
                    col_name = 'israeli10k_present' if cohort == 'HPP' else 'ukbb_present'
                    df = df[df[col_name] == True]

                elif entity_type in ['chemistry', 'demographics']:
                    # Filter by cohort presence
                    if 'arivale_present' in df.columns:
                        col_name = 'israeli10k_present' if cohort == 'HPP' else f"{cohort.lower()}_present"
                        df = df[df[col_name] == True]
                    elif 'cohorts' in df.columns:
                        # Parse cohorts column
                        cohort_filter = 'israeli' if cohort == 'HPP' else cohort.lower()
                        df = df[df['cohorts'].str.contains(cohort_filter, case=False, na=False)]

                elif entity_type == 'questionnaires_loinc' and cohort == 'Arivale':
                    # Only count successfully mapped questionnaires
                    df = df[df['loinc_code'] != 'NO_MATCH']

                elif entity_type == 'questionnaires_mondo' and cohort == 'Arivale':
                    # Only count successfully mapped questionnaires
                    df = df[df['mondo_id'] != 'NO_MATCH']

                # Get ID column
                id_col = self.get_id_column(entity_type, cohort)

                # Extract measurements from dataframe
                for idx, row in df.iterrows():
                    if id_col in row and pd.notna(row[id_col]) and row[id_col] != '':
                        measurements.append(EntityMeasurement(
                            cohort=cohort,
                            entity_id=str(row[id_col]),
                            row_index=idx,
                            metadata=row.to_dict() if len(row) < 50 else {'row_num': idx}
                        ))

        except Exception as e:
            print(f"    ERROR processing {full_path}: {e}")

        print(f"    Extracted {len(measurements)} measurements")

        # For proteins, show duplication info
        if entity_type == 'proteins' and measurements:
            unique_ids = len(set(m.entity_id for m in measurements))
            duplication_factor = len(measurements) / unique_ids if unique_ids > 0 else 1.0
            print(f"    ({unique_ids} unique IDs, duplication factor: {duplication_factor:.2f}x)")

        return measurements


class OverlapEnricher:
    """Enrich measurements with overlap information."""

    def enrich_measurements(self,
                           arivale_measurements: List[EntityMeasurement],
                           ukbb_measurements: List[EntityMeasurement],
                           hpp_measurements: List[EntityMeasurement]) -> List[EntityOverlap]:
        """Determine which Venn region each measurement belongs to."""

        # Build ID existence sets for fast lookup
        arivale_ids = {m.entity_id for m in arivale_measurements}
        ukbb_ids = {m.entity_id for m in ukbb_measurements}
        hpp_ids = {m.entity_id for m in hpp_measurements}

        print(f"  ID sets: Arivale={len(arivale_ids)}, UKBB={len(ukbb_ids)}, HPP={len(hpp_ids)}")

        enriched = []

        # Process all measurements
        all_measurements = arivale_measurements + ukbb_measurements + hpp_measurements

        for measurement in all_measurements:
            entity_id = measurement.entity_id

            # Determine overlaps
            exists_in_arivale = entity_id in arivale_ids
            exists_in_ukbb = entity_id in ukbb_ids
            exists_in_hpp = entity_id in hpp_ids

            # Determine Venn region based on source cohort and overlaps
            venn_region = self.determine_region(
                measurement.cohort,
                exists_in_arivale,
                exists_in_ukbb,
                exists_in_hpp
            )

            enriched.append(EntityOverlap(
                measurement=measurement,
                exists_in_arivale=exists_in_arivale,
                exists_in_ukbb=exists_in_ukbb,
                exists_in_hpp=exists_in_hpp,
                venn_region=venn_region
            ))

        return enriched

    def determine_region(self, source_cohort: str, in_a: bool, in_u: bool, in_h: bool) -> str:
        """Determine which of 7 Venn regions this measurement belongs to."""

        # The measurement must be from its source cohort
        if source_cohort == 'Arivale':
            if in_u and in_h:
                return 'all_three'
            elif in_u:
                return 'arivale_ukbb_only'
            elif in_h:
                return 'arivale_hpp_only'
            else:
                return 'arivale_only'

        elif source_cohort == 'UKBB':
            if in_a and in_h:
                return 'all_three'
            elif in_a:
                return 'arivale_ukbb_only'
            elif in_h:
                return 'ukbb_hpp_only'
            else:
                return 'ukbb_only'

        else:  # HPP
            if in_a and in_u:
                return 'all_three'
            elif in_a:
                return 'arivale_hpp_only'
            elif in_u:
                return 'ukbb_hpp_only'
            else:
                return 'hpp_only'


class VennAggregator:
    """Aggregate enriched measurements into Venn counts."""

    def aggregate_to_venn(self, enriched_overlaps: List[EntityOverlap]) -> Dict:
        """Count measurements in each Venn region."""

        # Initialize counters
        regions = {
            'arivale_only': 0,
            'ukbb_only': 0,
            'hpp_only': 0,
            'arivale_ukbb_only': 0,
            'arivale_hpp_only': 0,
            'ukbb_hpp_only': 0,
            'all_three': 0
        }

        # Count by region
        for overlap in enriched_overlaps:
            regions[overlap.venn_region] += 1

        # Calculate totals by cohort
        arivale_total = sum(1 for o in enriched_overlaps if o.measurement.cohort == 'Arivale')
        ukbb_total = sum(1 for o in enriched_overlaps if o.measurement.cohort == 'UKBB')
        hpp_total = sum(1 for o in enriched_overlaps if o.measurement.cohort == 'HPP')

        return {
            'regions': regions,
            'totals': {
                'total': len(enriched_overlaps),
                'arivale': arivale_total,
                'ukbb': ukbb_total,
                'hpp': hpp_total
            }
        }


class NonDeduplicatedVennCalculator:
    """Main pipeline for non-deduplicated Venn analysis."""

    def __init__(self):
        self.extractor = SourceMeasurementExtractor()
        self.enricher = OverlapEnricher()
        self.aggregator = VennAggregator()

    def calculate_entity(self, entity_type: str) -> Dict:
        """Calculate non-deduplicated Venn counts for one entity type."""

        print(f"\nProcessing {entity_type}...")

        # Extract measurements from source files
        arivale_m = self.extractor.extract_measurements(entity_type, 'Arivale')
        ukbb_m = self.extractor.extract_measurements(entity_type, 'UKBB')
        hpp_m = self.extractor.extract_measurements(entity_type, 'HPP')

        # Enrich with overlap information
        enriched = self.enricher.enrich_measurements(arivale_m, ukbb_m, hpp_m)

        # Aggregate to Venn counts
        venn_counts = self.aggregator.aggregate_to_venn(enriched)

        # Add entity metadata
        venn_counts['entity_type'] = entity_type
        venn_counts['measurement_count'] = len(enriched)

        return venn_counts

    def calculate_all_entities(self) -> Dict:
        """Calculate non-deduplicated Venn counts for all entity types."""

        print("\n" + "=" * 70)
        print("NON-DEDUPLICATED VENN ANALYSIS")
        print("=" * 70)

        entity_types = [
            'proteins',
            'metabolites',
            'chemistry',
            'demographics',
            'questionnaires_loinc',
            'questionnaires_mondo'
        ]

        results = {}

        for entity_type in entity_types:
            results[entity_type] = self.calculate_entity(entity_type)

        return results

    def load_deduplicated_counts(self) -> Dict:
        """Load the existing deduplicated counts from master TSV."""

        tsv_file = Path("/home/ubuntu/biomapper/data/harmonization/analysis_results/venn_intersection_counts_master.tsv")

        if not tsv_file.exists():
            print(f"WARNING: Deduplicated counts file not found: {tsv_file}")
            return {}

        df = pd.read_csv(tsv_file, sep='\t')

        results = {}
        for _, row in df.iterrows():
            entity_type = row['entity_type']
            results[entity_type] = {
                'regions': {
                    'arivale_only': int(row['arivale_only']),
                    'ukbb_only': int(row['ukbb_only']),
                    'hpp_only': int(row['hpp_only']),
                    'arivale_ukbb_only': int(row['arivale_ukbb_only']),
                    'arivale_hpp_only': int(row['arivale_hpp_only']),
                    'ukbb_hpp_only': int(row['ukbb_hpp_only']),
                    'all_three': int(row['all_three'])
                },
                'totals': {
                    'total': int(row['total_entities']),
                    'arivale': int(row['arivale_total']),
                    'ukbb': int(row['ukbb_total']),
                    'hpp': int(row['hpp_total'])
                }
            }

        return results

    def generate_dual_count_tsv(self, non_dedup_results: Dict, dedup_results: Dict):
        """Generate master TSV with both deduplicated and non-deduplicated counts."""

        print("\n" + "=" * 70)
        print("GENERATING DUAL-COUNT MASTER TSV")
        print("=" * 70)

        rows = []

        entity_display_names = {
            'proteins': 'Proteins',
            'metabolites': 'Metabolites',
            'chemistry': 'Chemistry',
            'demographics': 'Demographics',
            'questionnaires_loinc': 'Questionnaires→LOINC',
            'questionnaires_mondo': 'Questionnaires→MONDO'
        }

        for entity_type, display_name in entity_display_names.items():
            non_dedup = non_dedup_results.get(entity_type, {})
            dedup = dedup_results.get(entity_type, {})

            # Calculate expansion factors
            total_expansion = (non_dedup.get('totals', {}).get('total', 0) /
                             dedup.get('totals', {}).get('total', 1)) if dedup.get('totals', {}).get('total', 0) > 0 else 1.0

            # Main summary row
            rows.append({
                'entity_type': entity_type,
                'display_name': display_name,
                'region': 'TOTAL',
                'dedup_count': dedup.get('totals', {}).get('total', 0),
                'non_dedup_count': non_dedup.get('totals', {}).get('total', 0),
                'expansion_factor': f"{total_expansion:.2f}x",
                'arivale_dedup': dedup.get('totals', {}).get('arivale', 0),
                'arivale_non_dedup': non_dedup.get('totals', {}).get('arivale', 0),
                'ukbb_dedup': dedup.get('totals', {}).get('ukbb', 0),
                'ukbb_non_dedup': non_dedup.get('totals', {}).get('ukbb', 0),
                'hpp_dedup': dedup.get('totals', {}).get('hpp', 0),
                'hpp_non_dedup': non_dedup.get('totals', {}).get('hpp', 0)
            })

            # Region-specific rows
            for region in ['arivale_only', 'ukbb_only', 'hpp_only', 'arivale_ukbb_only',
                          'arivale_hpp_only', 'ukbb_hpp_only', 'all_three']:

                dedup_count = dedup.get('regions', {}).get(region, 0)
                non_dedup_count = non_dedup.get('regions', {}).get(region, 0)

                expansion = non_dedup_count / dedup_count if dedup_count > 0 else 1.0

                rows.append({
                    'entity_type': entity_type,
                    'display_name': display_name,
                    'region': region,
                    'dedup_count': dedup_count,
                    'non_dedup_count': non_dedup_count,
                    'expansion_factor': f"{expansion:.2f}x",
                    'arivale_dedup': '',
                    'arivale_non_dedup': '',
                    'ukbb_dedup': '',
                    'ukbb_non_dedup': '',
                    'hpp_dedup': '',
                    'hpp_non_dedup': ''
                })

        # Create dataframe and save
        df = pd.DataFrame(rows)
        output_file = Path("/home/ubuntu/biomapper/data/harmonization/analysis_results/venn_dual_count_master.tsv")
        df.to_csv(output_file, sep='\t', index=False)

        print(f"Saved dual-count master to: {output_file}")

        # Print summary
        print("\nSummary by entity type:")
        summary_df = df[df['region'] == 'TOTAL'][['display_name', 'dedup_count', 'non_dedup_count', 'expansion_factor']]
        print(summary_df.to_string(index=False))

        return df


def main():
    """Main execution."""

    # Calculate non-deduplicated counts
    calculator = NonDeduplicatedVennCalculator()
    non_dedup_results = calculator.calculate_all_entities()

    # Load existing deduplicated counts
    dedup_results = calculator.load_deduplicated_counts()

    # Generate dual-count master TSV
    dual_count_df = calculator.generate_dual_count_tsv(non_dedup_results, dedup_results)

    # Save raw results to JSON for debugging
    output_json = Path("/home/ubuntu/biomapper/data/harmonization/analysis_results/non_dedup_venn_results.json")
    with open(output_json, 'w') as f:
        json.dump(non_dedup_results, f, indent=2)

    print(f"\nRaw results saved to: {output_json}")
    print("\n✅ Non-deduplicated Venn analysis complete!")

    return non_dedup_results, dedup_results, dual_count_df


if __name__ == "__main__":
    main()