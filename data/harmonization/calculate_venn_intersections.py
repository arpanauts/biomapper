#!/usr/bin/env python3
"""
Calculate Venn Diagram Intersections for All Entity Types
Generates master TSV file with 7-region intersection counts for visualization.
"""

import pandas as pd
import json
from pathlib import Path
from typing import Dict, Set, Tuple
from datetime import datetime

class VennIntersectionCalculator:
    """Calculate 7-region Venn intersections for cross-cohort harmonization."""

    def __init__(self, base_dir: Path = None):
        if base_dir is None:
            base_dir = Path("/home/ubuntu/biomapper/data/harmonization")
        self.base_dir = base_dir
        self.results = {}

    def calculate_7_region_intersections(self,
                                        arivale_set: Set,
                                        ukbb_set: Set,
                                        hpp_set: Set) -> Dict[str, int]:
        """Calculate all 7 Venn diagram regions."""

        # Individual exclusive regions
        arivale_only = arivale_set - ukbb_set - hpp_set
        ukbb_only = ukbb_set - arivale_set - hpp_set
        hpp_only = hpp_set - arivale_set - ukbb_set

        # Pairwise exclusive regions
        arivale_ukbb_only = (arivale_set & ukbb_set) - hpp_set
        arivale_hpp_only = (arivale_set & hpp_set) - ukbb_set
        ukbb_hpp_only = (ukbb_set & hpp_set) - arivale_set

        # Three-way intersection
        all_three = arivale_set & ukbb_set & hpp_set

        # Total unique entities
        total_unique = len(arivale_set | ukbb_set | hpp_set)

        return {
            'total_entities': total_unique,
            'arivale_only': len(arivale_only),
            'ukbb_only': len(ukbb_only),
            'hpp_only': len(hpp_only),
            'arivale_ukbb_only': len(arivale_ukbb_only),
            'arivale_hpp_only': len(arivale_hpp_only),
            'ukbb_hpp_only': len(ukbb_hpp_only),
            'all_three': len(all_three),
            'arivale_total': len(arivale_set),
            'ukbb_total': len(ukbb_set),
            'hpp_total': len(hpp_set)
        }

    def process_proteins(self) -> Dict:
        """Process proteins from hierarchical JSON."""
        print("\n" + "=" * 70)
        print("PROCESSING: Proteins")
        print("=" * 70)

        json_file = self.base_dir / "proteins/hierarchical_protein_entities_latest.json"

        with open(json_file, 'r') as f:
            data = json.load(f)

        arivale_set = set()
        ukbb_set = set()
        hpp_set = set()

        for canonical_id, entity_data in data.items():
            cohorts = entity_data.get('cohort_contexts', {})

            if cohorts.get('arivale'):
                arivale_set.add(canonical_id)
            if cohorts.get('ukbb'):
                ukbb_set.add(canonical_id)
            if cohorts.get('israeli10k'):
                hpp_set.add(canonical_id)

        result = self.calculate_7_region_intersections(arivale_set, ukbb_set, hpp_set)

        print(f"Arivale proteins: {len(arivale_set)}")
        print(f"UKBB proteins: {len(ukbb_set)}")
        print(f"HPP proteins: {len(hpp_set)}")
        print(f"Total unique: {result['total_entities']}")
        print(f"Arivale-only: {result['arivale_only']}")

        return result

    def process_metabolites(self) -> Dict:
        """Process metabolites from hierarchical JSON."""
        print("\n" + "=" * 70)
        print("PROCESSING: Metabolites")
        print("=" * 70)

        json_file = self.base_dir / "metabolites/hierarchical_metabolite_entities_latest.json"

        with open(json_file, 'r') as f:
            data = json.load(f)

        arivale_set = set()
        ukbb_set = set()
        hpp_set = set()

        for canonical_id, entity_data in data.items():
            cohorts = entity_data.get('cohort_contexts', {})

            if cohorts.get('arivale'):
                arivale_set.add(canonical_id)
            if cohorts.get('ukbb'):
                ukbb_set.add(canonical_id)
            if cohorts.get('israeli10k'):
                hpp_set.add(canonical_id)

        result = self.calculate_7_region_intersections(arivale_set, ukbb_set, hpp_set)

        print(f"Total unique: {result['total_entities']}")

        return result

    def process_chemistry(self) -> Dict:
        """Process chemistry from hierarchical JSON."""
        print("\n" + "=" * 70)
        print("PROCESSING: Chemistry")
        print("=" * 70)

        json_file = self.base_dir / "chemistry/hierarchical_chemistry_entities_latest.json"

        with open(json_file, 'r') as f:
            data = json.load(f)

        arivale_set = set()
        ukbb_set = set()
        hpp_set = set()

        for canonical_id, entity_data in data.items():
            cohorts = entity_data.get('cohort_contexts', {})

            if cohorts.get('arivale'):
                arivale_set.add(canonical_id)
            if cohorts.get('ukbb'):
                ukbb_set.add(canonical_id)
            if cohorts.get('israeli10k'):
                hpp_set.add(canonical_id)

        result = self.calculate_7_region_intersections(arivale_set, ukbb_set, hpp_set)

        print(f"Total unique: {result['total_entities']}")

        return result

    def process_demographics(self) -> Dict:
        """Process demographics from hierarchical JSON."""
        print("\n" + "=" * 70)
        print("PROCESSING: Demographics")
        print("=" * 70)

        json_file = self.base_dir / "demographics/hierarchical_demographics_entities_latest.json"

        with open(json_file, 'r') as f:
            data = json.load(f)

        arivale_set = set()
        ukbb_set = set()
        hpp_set = set()

        for canonical_id, entity_data in data.items():
            cohorts = entity_data.get('cohort_contexts', {})

            if cohorts.get('arivale'):
                arivale_set.add(canonical_id)
            if cohorts.get('ukbb'):
                ukbb_set.add(canonical_id)
            if cohorts.get('israeli10k'):
                hpp_set.add(canonical_id)

        result = self.calculate_7_region_intersections(arivale_set, ukbb_set, hpp_set)

        print(f"Total unique: {result['total_entities']}")

        return result

    def process_questionnaires_loinc(self) -> Dict:
        """Process questionnaires→LOINC from NEW Arivale TSV + existing UKBB/HPP JSON."""
        print("\n" + "=" * 70)
        print("PROCESSING: Questionnaires→LOINC")
        print("=" * 70)

        # Load NEW Arivale LOINC data from TSV
        arivale_tsv = self.base_dir / "analysis_results/arivale_questionnaires_loinc_v1.0.tsv"
        arivale_df = pd.read_csv(arivale_tsv, sep='\t')
        arivale_set = set(arivale_df[arivale_df['loinc_code'] != 'NO_MATCH']['loinc_code'].unique())

        print(f"Loaded Arivale LOINC from new TSV: {len(arivale_set)} codes")

        # Load existing UKBB/HPP from JSON
        json_file = self.base_dir / "questionnaires/hierarchical_loinc_questionnaire_entities_latest.json"

        with open(json_file, 'r') as f:
            data = json.load(f)

        ukbb_set = set()
        hpp_set = set()

        for canonical_id, entity_data in data.items():
            cohorts = entity_data.get('cohort_contexts', {})

            if cohorts.get('ukbb'):
                ukbb_set.add(canonical_id)
            if cohorts.get('israeli10k'):
                hpp_set.add(canonical_id)

        print(f"UKBB LOINC from JSON: {len(ukbb_set)} codes")
        print(f"HPP LOINC from JSON: {len(hpp_set)} codes")

        result = self.calculate_7_region_intersections(arivale_set, ukbb_set, hpp_set)

        print(f"Total unique: {result['total_entities']}")
        print(f"Arivale-only: {result['arivale_only']}")

        return result

    def process_questionnaires_mondo(self) -> Dict:
        """Process questionnaires→MONDO from NEW Arivale TSV + existing UKBB/HPP JSON."""
        print("\n" + "=" * 70)
        print("PROCESSING: Questionnaires→MONDO")
        print("=" * 70)

        # Load NEW Arivale MONDO data from TSV
        arivale_tsv = self.base_dir / "analysis_results/arivale_questionnaires_mondo_v1.0.tsv"
        arivale_df = pd.read_csv(arivale_tsv, sep='\t')
        arivale_set = set(arivale_df[arivale_df['mondo_id'] != 'NO_MATCH']['mondo_id'].unique())

        print(f"Loaded Arivale MONDO from new TSV: {len(arivale_set)} IDs")

        # Load existing UKBB/HPP from JSON
        json_file = self.base_dir / "mondo/hierarchical_mondo_questionnaire_entities_latest.json"

        with open(json_file, 'r') as f:
            data = json.load(f)

        ukbb_set = set()
        hpp_set = set()

        for canonical_id, entity_data in data.items():
            cohorts = entity_data.get('cohort_contexts', {})

            if cohorts.get('ukbb'):
                ukbb_set.add(canonical_id)
            if cohorts.get('israeli10k'):
                hpp_set.add(canonical_id)

        print(f"UKBB MONDO from JSON: {len(ukbb_set)} IDs")
        print(f"HPP MONDO from JSON: {len(hpp_set)} IDs")

        result = self.calculate_7_region_intersections(arivale_set, ukbb_set, hpp_set)

        print(f"Total unique: {result['total_entities']}")
        print(f"Arivale-only: {result['arivale_only']}")

        return result

    def generate_master_table(self) -> pd.DataFrame:
        """Generate master intersection table for all entity types."""

        print("\n" + "=" * 70)
        print("CALCULATING ALL INTERSECTIONS")
        print("=" * 70)

        # Calculate intersections for all entity types
        self.results['proteins'] = self.process_proteins()
        self.results['metabolites'] = self.process_metabolites()
        self.results['chemistry'] = self.process_chemistry()
        self.results['demographics'] = self.process_demographics()
        self.results['questionnaires_loinc'] = self.process_questionnaires_loinc()
        self.results['questionnaires_mondo'] = self.process_questionnaires_mondo()

        # Create master table
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
            data = self.results[entity_type]

            rows.append({
                'entity_type': entity_type,
                'display_name': display_name,
                'total_entities': data['total_entities'],
                'arivale_only': data['arivale_only'],
                'ukbb_only': data['ukbb_only'],
                'hpp_only': data['hpp_only'],
                'arivale_ukbb_only': data['arivale_ukbb_only'],
                'arivale_hpp_only': data['arivale_hpp_only'],
                'ukbb_hpp_only': data['ukbb_hpp_only'],
                'all_three': data['all_three'],
                'arivale_total': data['arivale_total'],
                'ukbb_total': data['ukbb_total'],
                'hpp_total': data['hpp_total'],
                'generated_timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })

        df = pd.DataFrame(rows)

        # Save to TSV
        output_file = self.base_dir / "analysis_results/venn_intersection_counts_master.tsv"
        df.to_csv(output_file, sep='\t', index=False)

        print("\n" + "=" * 70)
        print("MASTER TABLE GENERATED")
        print("=" * 70)
        print(f"Saved to: {output_file}")
        print(f"\nSummary:")
        print(df[['display_name', 'total_entities', 'arivale_only', 'ukbb_only', 'hpp_only', 'all_three']].to_string(index=False))

        return df

def main():
    """Main execution."""
    calculator = VennIntersectionCalculator()
    df = calculator.generate_master_table()

    print("\n✅ Intersection calculation complete!")
    return df

if __name__ == "__main__":
    main()
