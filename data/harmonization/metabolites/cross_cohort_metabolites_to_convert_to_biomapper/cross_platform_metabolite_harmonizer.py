#!/usr/bin/env python3
"""
Cross-Platform Metabolite Harmonization
Agent 6: Priority 1 Implementation

Harmonizes metabolomics data across:
- Arivale: ~1,000 mass spectrometry metabolites
- UKBB: ~250 Nightingale NMR biomarkers
- Israeli10K: ~250 Nightingale NMR biomarkers

Creates unified cross-platform mappings identifying common metabolites.
"""

import pandas as pd
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Set
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CrossPlatformMetaboliteHarmonizer:
    """Harmonizes metabolite data across mass spec and NMR platforms"""

    def __init__(self, base_dir="/home/ubuntu/biomapper/data"):
        self.base_dir = Path(base_dir)
        self.results_dir = self.base_dir / "harmonization/metabolites/cross_cohort_metabolites_to_convert_to_biomapper/results"
        self.data_dir = self.base_dir / "harmonization/metabolites/cross_cohort_metabolites_to_convert_to_biomapper/data"

        # Create directories
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Data paths
        self.arivale_path = self.base_dir / "kraken_mapping/metabolites/arivale_to_kraken_to_convert_to_biomapper/results/arivale_metabolites_production_standardized.tsv"
        self.ukbb_path = self.base_dir / "kraken_mapping/metabolites/ukbb_to_kraken_to_convert_to_biomapper/results/ukbb_nightingale_to_kraken_mapping.tsv"
        self.israeli10k_path = self.base_dir / "kraken_mapping/metabolites/israeli10k_to_kraken_to_convert_to_biomapper/results/israeli10k_nightingale_to_kraken_mapping.tsv"

    def load_arivale_metabolites(self) -> pd.DataFrame:
        """Load Arivale mass spec metabolites"""
        logger.info("Loading Arivale mass spec metabolites...")

        df = pd.read_csv(self.arivale_path, sep='\t')
        logger.info(f"Loaded {len(df)} Arivale metabolites")

        # Standardize columns for harmonization
        df_std = df.copy()
        df_std['platform'] = 'mass_spectrometry'
        df_std['cohort'] = 'Arivale'
        df_std['method'] = 'LC-MS/MS'
        df_std['unit'] = 'relative_intensity'  # Typical for Arivale

        # Normalize identifiers
        df_std['chebi_id'] = None  # Arivale doesn't have direct ChEBI
        df_std['hmdb_id'] = df_std['hmdb_normalized']
        df_std['pubchem_id'] = df_std['pubchem_normalized']

        return df_std

    def load_ukbb_metabolites(self) -> pd.DataFrame:
        """Load UKBB Nightingale NMR biomarkers"""
        logger.info("Loading UKBB Nightingale NMR biomarkers...")

        df = pd.read_csv(self.ukbb_path, sep='\t')
        logger.info(f"Loaded {len(df)} UKBB biomarkers")

        # Standardize columns
        df_std = df.copy()
        df_std['platform'] = 'nmr'
        df_std['cohort'] = 'UKBB'
        df_std['method'] = 'Nightingale_NMR'
        df_std['unit'] = 'mmol/L'  # Typical for Nightingale
        df_std['metabolite_name'] = df_std['nightingale_name']

        # Extract ChEBI ID (clean format)
        df_std['chebi_id'] = df_std['source_chebi_id'].str.replace('CHEBI:', '', regex=False)
        df_std['hmdb_id'] = df_std['source_hmdb_id']
        df_std['pubchem_id'] = df_std['source_pubchem_id']

        return df_std

    def load_israeli10k_metabolites(self) -> pd.DataFrame:
        """Load Israeli10K Nightingale NMR biomarkers"""
        logger.info("Loading Israeli10K Nightingale NMR biomarkers...")

        df = pd.read_csv(self.israeli10k_path, sep='\t')
        logger.info(f"Loaded {len(df)} Israeli10K biomarkers")

        # Standardize columns
        df_std = df.copy()
        df_std['platform'] = 'nmr'
        df_std['cohort'] = 'Israeli10K'
        df_std['method'] = 'Nightingale_NMR'
        df_std['unit'] = df_std['unit'] if 'unit' in df_std.columns else 'mmol/L'
        df_std['metabolite_name'] = df_std['nightingale_name']

        # Extract ChEBI ID
        df_std['chebi_id'] = df_std['mapped_chebi_id'].astype(str)
        df_std['hmdb_id'] = None  # Not present in Israeli10K data
        df_std['pubchem_id'] = None  # Not present in Israeli10K data

        return df_std

    def find_cross_platform_matches(self, arivale_df: pd.DataFrame,
                                   ukbb_df: pd.DataFrame,
                                   israeli10k_df: pd.DataFrame) -> pd.DataFrame:
        """Find common metabolites across platforms using multiple identifier systems"""
        logger.info("Finding cross-platform metabolite matches...")

        harmonized_metabolites = []

        # Method 1: Direct ChEBI matching between NMR platforms
        logger.info("Method 1: Matching UKBB and Israeli10K via ChEBI IDs...")
        nmr_matches = self._match_nmr_platforms(ukbb_df, israeli10k_df)

        # Method 2: HMDB-based matching (Arivale to NMR via HMDB)
        logger.info("Method 2: Matching Arivale to NMR via HMDB IDs...")
        arivale_nmr_matches = self._match_arivale_to_nmr(arivale_df, ukbb_df, israeli10k_df)

        # Method 3: Name-based fuzzy matching
        logger.info("Method 3: Name-based fuzzy matching...")
        name_matches = self._fuzzy_name_matching(arivale_df, ukbb_df, israeli10k_df)

        # Combine all matches
        all_matches = nmr_matches + arivale_nmr_matches + name_matches

        # Create final harmonized dataset
        harmonized_df = pd.DataFrame(all_matches)

        # Deduplicate based on metabolite combinations
        if not harmonized_df.empty:
            harmonized_df = harmonized_df.drop_duplicates(
                subset=['metabolite_name', 'arivale_present', 'ukbb_present', 'israeli10k_present']
            )

        logger.info(f"Found {len(harmonized_df)} harmonized metabolites")
        return harmonized_df

    def _match_nmr_platforms(self, ukbb_df: pd.DataFrame, israeli10k_df: pd.DataFrame) -> List[Dict]:
        """Match UKBB and Israeli10K NMR platforms via ChEBI IDs"""
        matches = []

        # Direct ChEBI matching
        ukbb_chebi = set(ukbb_df['chebi_id'].dropna())
        israeli10k_chebi = set(israeli10k_df['chebi_id'].dropna())
        common_chebi = ukbb_chebi.intersection(israeli10k_chebi)

        logger.info(f"Found {len(common_chebi)} common ChEBI IDs between UKBB and Israeli10K")

        for chebi_id in common_chebi:
            ukbb_row = ukbb_df[ukbb_df['chebi_id'] == chebi_id].iloc[0]
            israeli10k_row = israeli10k_df[israeli10k_df['chebi_id'] == chebi_id].iloc[0]

            match = {
                'metabolite_id': f'CHEBI:{chebi_id}',
                'metabolite_name': ukbb_row['metabolite_name'],
                'metabolite_class': ukbb_row.get('chemical_class', 'unknown'),
                'arivale_id': None,
                'arivale_method': None,
                'arivale_unit': None,
                'ukbb_id': ukbb_row['nightingale_biomarker_id'],
                'ukbb_method': 'Nightingale_NMR',
                'ukbb_unit': 'mmol/L',
                'israeli10k_id': israeli10k_row['nightingale_biomarker_id'],
                'israeli10k_method': 'Nightingale_NMR',
                'israeli10k_unit': israeli10k_row['unit'],
                'arivale_present': False,
                'ukbb_present': True,
                'israeli10k_present': True,
                'cohorts_present': 'ukbb,israeli10k',
                'match_confidence': 1.0,
                'cross_platform_compatible': 'partial',
                'matching_method': 'direct_chebi',
                'chebi_id': chebi_id,
                'platform_notes': 'NMR_compatible_both_cohorts'
            }
            matches.append(match)

        return matches

    def _match_arivale_to_nmr(self, arivale_df: pd.DataFrame,
                             ukbb_df: pd.DataFrame,
                             israeli10k_df: pd.DataFrame) -> List[Dict]:
        """Match Arivale to NMR platforms via HMDB and chemical name mapping"""
        matches = []

        # Create HMDB lookup for NMR data
        ukbb_hmdb = {row['hmdb_id']: row for _, row in ukbb_df.iterrows()
                     if pd.notna(row.get('hmdb_id'))}

        logger.info(f"UKBB has {len(ukbb_hmdb)} metabolites with HMDB IDs")

        # Match Arivale to UKBB via HMDB
        for _, arivale_row in arivale_df.iterrows():
            hmdb_id = arivale_row.get('hmdb_id')
            if pd.notna(hmdb_id) and hmdb_id in ukbb_hmdb:
                ukbb_match = ukbb_hmdb[hmdb_id]

                # Check if Israeli10K also has this metabolite
                israeli10k_match = None
                israeli10k_present = False

                # Look for Israeli10K match by ChEBI
                ukbb_chebi = ukbb_match.get('chebi_id')
                if ukbb_chebi:
                    israeli10k_candidates = israeli10k_df[israeli10k_df['chebi_id'] == ukbb_chebi]
                    if not israeli10k_candidates.empty:
                        israeli10k_match = israeli10k_candidates.iloc[0]
                        israeli10k_present = True

                # Determine platform compatibility
                platform_compatibility = 'no'
                if arivale_row['metabolite_name'].lower() in ukbb_match['metabolite_name'].lower():
                    platform_compatibility = 'partial'

                cohorts = ['arivale', 'ukbb']
                if israeli10k_present:
                    cohorts.append('israeli10k')

                match = {
                    'metabolite_id': hmdb_id,
                    'metabolite_name': arivale_row['metabolite_name'],
                    'metabolite_class': arivale_row.get('super_pathway', 'unknown'),
                    'arivale_id': arivale_row['arivale_metabolite_id'],
                    'arivale_method': 'LC-MS/MS',
                    'arivale_unit': 'relative_intensity',
                    'ukbb_id': ukbb_match['nightingale_biomarker_id'],
                    'ukbb_method': 'Nightingale_NMR',
                    'ukbb_unit': 'mmol/L',
                    'israeli10k_id': israeli10k_match['nightingale_biomarker_id'] if israeli10k_match is not None else None,
                    'israeli10k_method': 'Nightingale_NMR' if israeli10k_present else None,
                    'israeli10k_unit': israeli10k_match['unit'] if israeli10k_match is not None else None,
                    'arivale_present': True,
                    'ukbb_present': True,
                    'israeli10k_present': israeli10k_present,
                    'cohorts_present': ','.join(cohorts),
                    'match_confidence': 0.9,
                    'cross_platform_compatible': platform_compatibility,
                    'matching_method': 'hmdb_bridge',
                    'hmdb_id': hmdb_id,
                    'chebi_id': ukbb_chebi,
                    'platform_notes': 'mass_spec_to_nmr_via_hmdb'
                }
                matches.append(match)

        logger.info(f"Found {len(matches)} Arivale-NMR matches via HMDB")
        return matches

    def _fuzzy_name_matching(self, arivale_df: pd.DataFrame,
                           ukbb_df: pd.DataFrame,
                           israeli10k_df: pd.DataFrame) -> List[Dict]:
        """Fuzzy matching based on metabolite names"""
        matches = []

        # Common metabolite name patterns
        common_names = {
            'glucose': ['glucose', 'glc'],
            'lactate': ['lactate', 'lactic acid'],
            'pyruvate': ['pyruvate', 'pyruvic acid'],
            'alanine': ['alanine', 'ala'],
            'glycine': ['glycine', 'gly'],
            'valine': ['valine', 'val'],
            'leucine': ['leucine', 'leu'],
            'isoleucine': ['isoleucine', 'ile'],
            'phenylalanine': ['phenylalanine', 'phe'],
            'tyrosine': ['tyrosine', 'tyr'],
            'histidine': ['histidine', 'his'],
            'glutamine': ['glutamine', 'gln'],
            'creatinine': ['creatinine'],
            'acetate': ['acetate', 'acetic acid'],
            'cholesterol': ['cholesterol', 'total_fc', 'total_c'],
            'triglyceride': ['triglyceride', 'total_tg'],
            'linoleic': ['linoleic', 'la', 'linoleate']
        }

        logger.info("Performing fuzzy name matching for common metabolites...")

        for standard_name, name_variants in common_names.items():
            # Find matches in each cohort
            arivale_matches = []
            ukbb_matches = []
            israeli10k_matches = []

            for variant in name_variants:
                arivale_candidates = arivale_df[arivale_df['metabolite_name'].str.lower().str.contains(variant.lower(), na=False)]
                ukbb_candidates = ukbb_df[ukbb_df['metabolite_name'].str.lower().str.contains(variant.lower(), na=False)]
                israeli10k_candidates = israeli10k_df[israeli10k_df['metabolite_name'].str.lower().str.contains(variant.lower(), na=False)]

                arivale_matches.extend(arivale_candidates.to_dict('records'))
                ukbb_matches.extend(ukbb_candidates.to_dict('records'))
                israeli10k_matches.extend(israeli10k_candidates.to_dict('records'))

            # Create harmonized entry if matches found
            if arivale_matches or ukbb_matches or israeli10k_matches:
                cohorts = []
                if arivale_matches: cohorts.append('arivale')
                if ukbb_matches: cohorts.append('ukbb')
                if israeli10k_matches: cohorts.append('israeli10k')

                # Take first match from each cohort
                arivale_match = arivale_matches[0] if arivale_matches else None
                ukbb_match = ukbb_matches[0] if ukbb_matches else None
                israeli10k_match = israeli10k_matches[0] if israeli10k_matches else None

                match = {
                    'metabolite_id': f'COMMON_{standard_name.upper()}',
                    'metabolite_name': standard_name.title(),
                    'metabolite_class': arivale_match.get('super_pathway', 'unknown') if arivale_match else 'unknown',
                    'arivale_id': arivale_match['arivale_metabolite_id'] if arivale_match else None,
                    'arivale_method': 'LC-MS/MS' if arivale_match else None,
                    'arivale_unit': 'relative_intensity' if arivale_match else None,
                    'ukbb_id': ukbb_match['nightingale_biomarker_id'] if ukbb_match else None,
                    'ukbb_method': 'Nightingale_NMR' if ukbb_match else None,
                    'ukbb_unit': 'mmol/L' if ukbb_match else None,
                    'israeli10k_id': israeli10k_match['nightingale_biomarker_id'] if israeli10k_match else None,
                    'israeli10k_method': 'Nightingale_NMR' if israeli10k_match else None,
                    'israeli10k_unit': israeli10k_match.get('unit', 'mmol/L') if israeli10k_match else None,
                    'arivale_present': bool(arivale_match),
                    'ukbb_present': bool(ukbb_match),
                    'israeli10k_present': bool(israeli10k_match),
                    'cohorts_present': ','.join(cohorts),
                    'match_confidence': 0.7,
                    'cross_platform_compatible': 'partial' if len(cohorts) > 1 else 'no',
                    'matching_method': 'fuzzy_name',
                    'platform_notes': 'common_metabolite_name_based'
                }
                matches.append(match)

        logger.info(f"Found {len(matches)} fuzzy name matches")
        return matches

    def generate_compatibility_matrix(self, harmonized_df: pd.DataFrame) -> pd.DataFrame:
        """Generate platform compatibility matrix"""
        logger.info("Generating platform compatibility matrix...")

        # Count metabolites by platform presence
        platform_stats = {
            'Total_Harmonized': len(harmonized_df),
            'Arivale_Only': len(harmonized_df[
                (harmonized_df['arivale_present'] == True) &
                (harmonized_df['ukbb_present'] == False) &
                (harmonized_df['israeli10k_present'] == False)
            ]),
            'UKBB_Only': len(harmonized_df[
                (harmonized_df['arivale_present'] == False) &
                (harmonized_df['ukbb_present'] == True) &
                (harmonized_df['israeli10k_present'] == False)
            ]),
            'Israeli10K_Only': len(harmonized_df[
                (harmonized_df['arivale_present'] == False) &
                (harmonized_df['ukbb_present'] == False) &
                (harmonized_df['israeli10k_present'] == True)
            ]),
            'Arivale_UKBB': len(harmonized_df[
                (harmonized_df['arivale_present'] == True) &
                (harmonized_df['ukbb_present'] == True) &
                (harmonized_df['israeli10k_present'] == False)
            ]),
            'UKBB_Israeli10K': len(harmonized_df[
                (harmonized_df['arivale_present'] == False) &
                (harmonized_df['ukbb_present'] == True) &
                (harmonized_df['israeli10k_present'] == True)
            ]),
            'Arivale_Israeli10K': len(harmonized_df[
                (harmonized_df['arivale_present'] == True) &
                (harmonized_df['ukbb_present'] == False) &
                (harmonized_df['israeli10k_present'] == True)
            ]),
            'All_Three_Cohorts': len(harmonized_df[
                (harmonized_df['arivale_present'] == True) &
                (harmonized_df['ukbb_present'] == True) &
                (harmonized_df['israeli10k_present'] == True)
            ])
        }

        matrix_df = pd.DataFrame(list(platform_stats.items()),
                               columns=['Platform_Combination', 'Metabolite_Count'])

        return matrix_df

    def save_results(self, harmonized_df: pd.DataFrame, matrix_df: pd.DataFrame):
        """Save harmonization results"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Save main harmonized results
        harmonized_path = self.results_dir / f"cross_platform_metabolites_harmonized_{timestamp}.tsv"
        harmonized_df.to_csv(harmonized_path, sep='\t', index=False)
        logger.info(f"Saved harmonized metabolites: {harmonized_path}")

        # Save compatibility matrix
        matrix_path = self.results_dir / f"platform_compatibility_matrix_{timestamp}.tsv"
        matrix_df.to_csv(matrix_path, sep='\t', index=False)
        logger.info(f"Saved compatibility matrix: {matrix_path}")

        # Save summary statistics
        summary = {
            'harmonization_timestamp': timestamp,
            'total_harmonized_metabolites': len(harmonized_df),
            'arivale_metabolites_matched': int(harmonized_df['arivale_present'].sum()),
            'ukbb_metabolites_matched': int(harmonized_df['ukbb_present'].sum()),
            'israeli10k_metabolites_matched': int(harmonized_df['israeli10k_present'].sum()),
            'three_way_matches': int((harmonized_df['arivale_present'] &
                                    harmonized_df['ukbb_present'] &
                                    harmonized_df['israeli10k_present']).sum()),
            'nmr_only_matches': int((~harmonized_df['arivale_present'] &
                                   harmonized_df['ukbb_present'] &
                                   harmonized_df['israeli10k_present']).sum()),
            'mass_spec_coverage': f"{(harmonized_df['arivale_present'].sum() / len(harmonized_df) * 100):.1f}%",
            'nmr_coverage_ukbb': f"{(harmonized_df['ukbb_present'].sum() / len(harmonized_df) * 100):.1f}%",
            'nmr_coverage_israeli10k': f"{(harmonized_df['israeli10k_present'].sum() / len(harmonized_df) * 100):.1f}%"
        }

        summary_path = self.results_dir / f"harmonization_summary_{timestamp}.json"
        with open(summary_path, 'w') as f:
            json.dump(summary, f, indent=2)
        logger.info(f"Saved summary: {summary_path}")

        # Create symlinks to latest results
        latest_harmonized = self.results_dir / "cross_platform_metabolites_latest.tsv"
        latest_matrix = self.results_dir / "platform_compatibility_matrix_latest.tsv"
        latest_summary = self.results_dir / "harmonization_summary_latest.json"

        # Remove old symlinks if they exist
        for symlink in [latest_harmonized, latest_matrix, latest_summary]:
            if symlink.is_symlink():
                symlink.unlink()

        # Create new symlinks
        latest_harmonized.symlink_to(harmonized_path.name)
        latest_matrix.symlink_to(matrix_path.name)
        latest_summary.symlink_to(summary_path.name)

        return {
            'harmonized_file': harmonized_path,
            'matrix_file': matrix_path,
            'summary_file': summary_path,
            'summary_stats': summary
        }

    def run_harmonization(self) -> Dict:
        """Run complete cross-platform metabolite harmonization"""
        logger.info("Starting cross-platform metabolite harmonization...")

        # Load data from all cohorts
        arivale_df = self.load_arivale_metabolites()
        ukbb_df = self.load_ukbb_metabolites()
        israeli10k_df = self.load_israeli10k_metabolites()

        # Find cross-platform matches
        harmonized_df = self.find_cross_platform_matches(arivale_df, ukbb_df, israeli10k_df)

        # Generate compatibility matrix
        matrix_df = self.generate_compatibility_matrix(harmonized_df)

        # Save results
        results = self.save_results(harmonized_df, matrix_df)

        logger.info("Cross-platform metabolite harmonization completed successfully!")
        logger.info(f"Total harmonized metabolites: {len(harmonized_df)}")

        return results

def main():
    """Main execution function"""
    harmonizer = CrossPlatformMetaboliteHarmonizer()
    results = harmonizer.run_harmonization()

    print("\n" + "="*60)
    print("CROSS-PLATFORM METABOLITE HARMONIZATION COMPLETE")
    print("="*60)
    print(f"Results saved to: {results['harmonized_file']}")
    print(f"Summary: {results['summary_stats']}")
    print("="*60)

if __name__ == "__main__":
    main()