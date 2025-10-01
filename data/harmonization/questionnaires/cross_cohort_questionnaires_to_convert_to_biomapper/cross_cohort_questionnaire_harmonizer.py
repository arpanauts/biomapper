#!/usr/bin/env python3
"""
Cross-Cohort Questionnaire LOINC Harmonization
Agent 6: Priority 3 Implementation

Harmonizes questionnaire items across Arivale, UKBB, and Israeli10K cohorts
through direct LOINC code matching to establish unified survey instrument mappings.

This is a "meta-harmonization" - harmonizing already-harmonized data where
all inputs have LOINC codes from LLM validation.
"""

import pandas as pd
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Set, Tuple
import logging
from collections import defaultdict, Counter

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CrossCohortQuestionnaireHarmonizer:
    """Harmonizes questionnaire LOINC mappings across cohorts"""

    def __init__(self, base_dir="/home/ubuntu/biomapper/data"):
        self.base_dir = Path(base_dir)
        self.results_dir = self.base_dir / "harmonization/questionnaires/cross_cohort_questionnaires_to_convert_to_biomapper/results"
        self.data_dir = self.base_dir / "harmonization/questionnaires/cross_cohort_questionnaires_to_convert_to_biomapper/data"

        # Create directories
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Input file paths - use the complete LOINC mappings
        loinc_base = self.base_dir / "harmonization/questionnaires/loinc_questionnaires_to_convert_to_biomapper/results"
        self.arivale_path = loinc_base / "arivale_questionnaires_weighted_loinc_COMPLETE.tsv"
        self.ukbb_path = loinc_base / "ukbb_questionnaires_weighted_loinc_COMPLETE.tsv"
        self.israeli10k_path = loinc_base / "israeli10k_questionnaires_weighted_loinc_COMPLETE.tsv"

    def load_cohort_questionnaires(self, cohort: str, file_path: Path) -> pd.DataFrame:
        """Load questionnaire LOINC mappings for a specific cohort"""
        logger.info(f"Loading {cohort} questionnaire LOINC mappings...")

        try:
            df = pd.read_csv(file_path, sep='\t', encoding='utf-8')

            # Handle different column naming conventions
            loinc_cols = [col for col in df.columns if 'loinc' in col.lower() and 'code' in col.lower()]
            if not loinc_cols:
                loinc_cols = [col for col in df.columns if 'loinc' in col.lower()]

            if loinc_cols:
                df['loinc_code'] = df[loinc_cols[0]]
            elif 'loinc_code' not in df.columns:
                logger.warning(f"No LOINC code column found in {cohort} data")
                return pd.DataFrame()

            # Standardize columns
            df['cohort'] = cohort

            # Clean LOINC codes
            if 'loinc_code' in df.columns:
                df['loinc_code'] = df['loinc_code'].astype(str).str.strip()
                df = df[df['loinc_code'].notna() & (df['loinc_code'] != '') & (df['loinc_code'] != 'nan')]

            logger.info(f"Loaded {len(df)} {cohort} questionnaire items with LOINC codes")
            return df

        except Exception as e:
            logger.error(f"Error loading {cohort} questionnaires: {e}")
            return pd.DataFrame()

    def identify_common_loinc_codes(self, arivale_df: pd.DataFrame,
                                   ukbb_df: pd.DataFrame,
                                   israeli10k_df: pd.DataFrame) -> Dict:
        """Identify common LOINC codes across cohorts"""
        logger.info("Identifying common LOINC codes across cohorts...")

        # Extract LOINC codes from each cohort
        arivale_loinc = set(arivale_df['loinc_code'].dropna().astype(str))
        ukbb_loinc = set(ukbb_df['loinc_code'].dropna().astype(str))
        israeli10k_loinc = set(israeli10k_df['loinc_code'].dropna().astype(str))

        logger.info(f"LOINC codes found - Arivale: {len(arivale_loinc)}, UKBB: {len(ukbb_loinc)}, Israeli10K: {len(israeli10k_loinc)}")

        # Find overlaps
        all_three = arivale_loinc & ukbb_loinc & israeli10k_loinc
        arivale_ukbb = (arivale_loinc & ukbb_loinc) - israeli10k_loinc
        arivale_israeli10k = (arivale_loinc & israeli10k_loinc) - ukbb_loinc
        ukbb_israeli10k = (ukbb_loinc & israeli10k_loinc) - arivale_loinc
        arivale_only = arivale_loinc - ukbb_loinc - israeli10k_loinc
        ukbb_only = ukbb_loinc - arivale_loinc - israeli10k_loinc
        israeli10k_only = israeli10k_loinc - arivale_loinc - ukbb_loinc

        overlaps = {
            'all_three_cohorts': all_three,
            'arivale_ukbb_only': arivale_ukbb,
            'arivale_israeli10k_only': arivale_israeli10k,
            'ukbb_israeli10k_only': ukbb_israeli10k,
            'arivale_only': arivale_only,
            'ukbb_only': ukbb_only,
            'israeli10k_only': israeli10k_only
        }

        # Log overlap statistics
        logger.info(f"LOINC code overlaps:")
        logger.info(f"  All three cohorts: {len(all_three)}")
        logger.info(f"  Arivale + UKBB only: {len(arivale_ukbb)}")
        logger.info(f"  Arivale + Israeli10K only: {len(arivale_israeli10k)}")
        logger.info(f"  UKBB + Israeli10K only: {len(ukbb_israeli10k)}")
        logger.info(f"  Arivale only: {len(arivale_only)}")
        logger.info(f"  UKBB only: {len(ukbb_only)}")
        logger.info(f"  Israeli10K only: {len(israeli10k_only)}")

        return overlaps

    def categorize_by_domains(self, harmonized_df: pd.DataFrame) -> pd.DataFrame:
        """Categorize questions by health domains using LOINC hierarchy"""
        logger.info("Categorizing questions by health domains...")

        # Domain mapping based on common LOINC patterns and question content
        domain_keywords = {
            'mental_health': ['depression', 'anxiety', 'mood', 'phq', 'gad', 'mental', 'stress', 'worry'],
            'lifestyle': ['exercise', 'physical activity', 'smoking', 'alcohol', 'sleep', 'diet', 'nutrition'],
            'medical_history': ['disease', 'condition', 'diagnosis', 'medication', 'treatment', 'surgery'],
            'demographics': ['age', 'sex', 'race', 'ethnicity', 'education', 'income', 'marital'],
            'family_history': ['family', 'parent', 'mother', 'father', 'sibling', 'relative'],
            'symptoms': ['pain', 'fatigue', 'symptom', 'complaint', 'discomfort'],
            'social': ['social', 'relationship', 'support', 'work', 'employment'],
            'reproductive': ['pregnancy', 'menstrual', 'reproductive', 'contraception'],
            'cardiovascular': ['heart', 'blood pressure', 'cardiovascular', 'cardiac'],
            'other': []  # Default category
        }

        def assign_domain(question_text: str) -> str:
            """Assign domain based on question text"""
            if pd.isna(question_text):
                return 'other'

            question_lower = question_text.lower()

            for domain, keywords in domain_keywords.items():
                if domain == 'other':
                    continue
                for keyword in keywords:
                    if keyword in question_lower:
                        return domain

            return 'other'

        # Assign domains
        harmonized_df['domain'] = harmonized_df['question_text'].apply(assign_domain)

        # Domain statistics
        domain_counts = harmonized_df['domain'].value_counts()
        logger.info(f"Domain distribution: {domain_counts.to_dict()}")

        return harmonized_df

    def create_unified_questionnaire_schema(self, arivale_df: pd.DataFrame,
                                          ukbb_df: pd.DataFrame,
                                          israeli10k_df: pd.DataFrame,
                                          overlaps: Dict) -> pd.DataFrame:
        """Create unified questionnaire schema with cross-cohort mappings"""
        logger.info("Creating unified questionnaire schema...")

        harmonized_questions = []

        # Process each LOINC code in the overlaps
        all_loinc_codes = set()
        for overlap_set in overlaps.values():
            all_loinc_codes.update(overlap_set)

        for loinc_code in all_loinc_codes:
            # Find questions for this LOINC code in each cohort
            arivale_questions = arivale_df[arivale_df['loinc_code'] == loinc_code]
            ukbb_questions = ukbb_df[ukbb_df['loinc_code'] == loinc_code]
            israeli10k_questions = israeli10k_df[israeli10k_df['loinc_code'] == loinc_code]

            # Determine which cohorts have this LOINC code
            cohorts_present = []
            if not arivale_questions.empty: cohorts_present.append('arivale')
            if not ukbb_questions.empty: cohorts_present.append('ukbb')
            if not israeli10k_questions.empty: cohorts_present.append('israeli10k')

            # Get representative question text (prefer Arivale, then UKBB, then Israeli10K)
            question_text = None
            if not arivale_questions.empty:
                question_text = arivale_questions.iloc[0].get('question_text',
                                                            arivale_questions.iloc[0].get('question',
                                                            arivale_questions.iloc[0].get('item_text', '')))
            elif not ukbb_questions.empty:
                question_text = ukbb_questions.iloc[0].get('question_text',
                                                         ukbb_questions.iloc[0].get('question',
                                                         ukbb_questions.iloc[0].get('item_text', '')))
            elif not israeli10k_questions.empty:
                question_text = israeli10k_questions.iloc[0].get('question_text',
                                                               israeli10k_questions.iloc[0].get('question',
                                                               israeli10k_questions.iloc[0].get('item_text', '')))

            # Create harmonized entry
            harmonized_entry = {
                'loinc_code': loinc_code,
                'question_text': question_text or f'LOINC_{loinc_code}',
                'cohorts_present': ','.join(cohorts_present),
                'num_cohorts': len(cohorts_present),
                'arivale_present': 'arivale' in cohorts_present,
                'ukbb_present': 'ukbb' in cohorts_present,
                'israeli10k_present': 'israeli10k' in cohorts_present,
                'arivale_count': len(arivale_questions),
                'ukbb_count': len(ukbb_questions),
                'israeli10k_count': len(israeli10k_questions),
                'total_questions': len(arivale_questions) + len(ukbb_questions) + len(israeli10k_questions)
            }

            # Add cohort-specific details
            if not arivale_questions.empty:
                harmonized_entry['arivale_question_text'] = harmonized_entry['question_text']
                harmonized_entry['arivale_confidence'] = arivale_questions.iloc[0].get('confidence_score',
                                                                                       arivale_questions.iloc[0].get('weighted_score', 1.0))
            else:
                harmonized_entry['arivale_question_text'] = None
                harmonized_entry['arivale_confidence'] = 0.0

            if not ukbb_questions.empty:
                harmonized_entry['ukbb_question_text'] = ukbb_questions.iloc[0].get('question_text',
                                                                                   ukbb_questions.iloc[0].get('question', ''))
                harmonized_entry['ukbb_confidence'] = ukbb_questions.iloc[0].get('confidence_score',
                                                                                ukbb_questions.iloc[0].get('weighted_score', 1.0))
            else:
                harmonized_entry['ukbb_question_text'] = None
                harmonized_entry['ukbb_confidence'] = 0.0

            if not israeli10k_questions.empty:
                harmonized_entry['israeli10k_question_text'] = israeli10k_questions.iloc[0].get('question_text',
                                                                                                israeli10k_questions.iloc[0].get('question', ''))
                harmonized_entry['israeli10k_confidence'] = israeli10k_questions.iloc[0].get('confidence_score',
                                                                                             israeli10k_questions.iloc[0].get('weighted_score', 1.0))
            else:
                harmonized_entry['israeli10k_question_text'] = None
                harmonized_entry['israeli10k_confidence'] = 0.0

            harmonized_questions.append(harmonized_entry)

        # Create DataFrame
        harmonized_df = pd.DataFrame(harmonized_questions)

        # Sort by number of cohorts (descending) and LOINC code
        harmonized_df = harmonized_df.sort_values(['num_cohorts', 'loinc_code'], ascending=[False, True])

        # Add domain categorization
        harmonized_df = self.categorize_by_domains(harmonized_df)

        logger.info(f"Created unified schema with {len(harmonized_df)} unique LOINC codes")

        return harmonized_df

    def generate_survey_instrument_mapping(self, harmonized_df: pd.DataFrame) -> pd.DataFrame:
        """Generate mapping of standard survey instruments"""
        logger.info("Generating standard survey instrument mapping...")

        # Common survey instruments and their LOINC patterns
        survey_instruments = {
            'PHQ-9': ['phq', 'depression', '44249-1', '44255-8'],
            'GAD-7': ['gad', 'anxiety', '69737-5', '70274-6'],
            'SF-36': ['sf-36', 'health survey', 'physical function'],
            'WHO-5': ['who-5', 'wellbeing', 'well-being'],
            'AUDIT': ['audit', 'alcohol use'],
            'PSS': ['perceived stress', 'stress scale'],
            'MOS': ['medical outcomes study'],
            'PROMIS': ['promis', 'patient-reported outcomes']
        }

        instrument_mappings = []

        for instrument, patterns in survey_instruments.items():
            matched_questions = harmonized_df[
                harmonized_df['question_text'].str.lower().str.contains('|'.join(patterns), na=False) |
                harmonized_df['loinc_code'].str.contains('|'.join([p for p in patterns if p.replace('-', '').isdigit()]), na=False)
            ]

            if not matched_questions.empty:
                instrument_mapping = {
                    'instrument_name': instrument,
                    'num_questions': len(matched_questions),
                    'loinc_codes': ','.join(matched_questions['loinc_code'].tolist()),
                    'cohorts_with_instrument': ','.join(matched_questions['cohorts_present'].str.split(',').explode().unique()),
                    'cross_cohort_coverage': matched_questions['num_cohorts'].mean()
                }
                instrument_mappings.append(instrument_mapping)

        instrument_df = pd.DataFrame(instrument_mappings)
        logger.info(f"Identified {len(instrument_df)} standard survey instruments")

        return instrument_df

    def save_results(self, harmonized_df: pd.DataFrame,
                    overlaps: Dict,
                    instrument_df: pd.DataFrame):
        """Save all harmonization results"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Save main harmonized questionnaires
        harmonized_path = self.results_dir / f"harmonized_questionnaires_{timestamp}.tsv"
        harmonized_df.to_csv(harmonized_path, sep='\t', index=False)
        logger.info(f"Saved harmonized questionnaires: {harmonized_path}")

        # Save domain categorization
        domain_path = self.results_dir / f"questionnaire_domains_{timestamp}.tsv"
        domain_summary = harmonized_df.groupby('domain').agg({
            'loinc_code': 'count',
            'num_cohorts': 'mean',
            'cohorts_present': lambda x: len(set(','.join(x).split(',')))
        }).reset_index()
        domain_summary.columns = ['domain', 'question_count', 'avg_cohort_coverage', 'unique_cohorts']
        domain_summary.to_csv(domain_path, sep='\t', index=False)
        logger.info(f"Saved domain categorization: {domain_path}")

        # Save cross-cohort survey map
        survey_map_path = self.results_dir / f"cross_cohort_survey_map_{timestamp}.tsv"
        survey_map = harmonized_df[['loinc_code', 'question_text', 'arivale_question_text',
                                   'ukbb_question_text', 'israeli10k_question_text',
                                   'cohorts_present', 'domain']].copy()
        survey_map.to_csv(survey_map_path, sep='\t', index=False)
        logger.info(f"Saved cross-cohort survey map: {survey_map_path}")

        # Save survey instruments
        instrument_path = self.results_dir / f"standard_survey_instruments_{timestamp}.tsv"
        instrument_df.to_csv(instrument_path, sep='\t', index=False)
        logger.info(f"Saved standard survey instruments: {instrument_path}")

        # Generate comprehensive statistics
        statistics = {
            'harmonization_timestamp': timestamp,
            'total_unique_loinc_codes': len(harmonized_df),
            'questions_in_all_cohorts': len(harmonized_df[harmonized_df['num_cohorts'] == 3]),
            'questions_in_two_cohorts': len(harmonized_df[harmonized_df['num_cohorts'] == 2]),
            'questions_in_one_cohort': len(harmonized_df[harmonized_df['num_cohorts'] == 1]),
            'cohort_coverage': {
                'arivale_questions': int(harmonized_df['arivale_present'].sum()),
                'ukbb_questions': int(harmonized_df['ukbb_present'].sum()),
                'israeli10k_questions': int(harmonized_df['israeli10k_present'].sum())
            },
            'overlap_statistics': {
                'all_three_cohorts': len(overlaps['all_three_cohorts']),
                'arivale_ukbb_only': len(overlaps['arivale_ukbb_only']),
                'arivale_israeli10k_only': len(overlaps['arivale_israeli10k_only']),
                'ukbb_israeli10k_only': len(overlaps['ukbb_israeli10k_only']),
                'arivale_only': len(overlaps['arivale_only']),
                'ukbb_only': len(overlaps['ukbb_only']),
                'israeli10k_only': len(overlaps['israeli10k_only'])
            },
            'domain_distribution': harmonized_df['domain'].value_counts().to_dict(),
            'standard_instruments_identified': len(instrument_df),
            'average_confidence_score': {
                'arivale': harmonized_df['arivale_confidence'].mean(),
                'ukbb': harmonized_df['ukbb_confidence'].mean(),
                'israeli10k': harmonized_df['israeli10k_confidence'].mean()
            }
        }

        # Save statistics
        stats_path = self.results_dir / f"harmonization_statistics_{timestamp}.json"
        with open(stats_path, 'w') as f:
            json.dump(statistics, f, indent=2, default=str)
        logger.info(f"Saved statistics: {stats_path}")

        # Create symlinks to latest results
        latest_files = {
            'harmonized_questionnaires_latest.tsv': harmonized_path,
            'questionnaire_domains_latest.tsv': domain_path,
            'cross_cohort_survey_map_latest.tsv': survey_map_path,
            'harmonization_statistics_latest.json': stats_path,
            'standard_survey_instruments_latest.tsv': instrument_path
        }

        for symlink_name, target_path in latest_files.items():
            symlink_path = self.results_dir / symlink_name
            if symlink_path.is_symlink():
                symlink_path.unlink()
            symlink_path.symlink_to(target_path.name)

        return {
            'harmonized_file': harmonized_path,
            'domain_file': domain_path,
            'survey_map_file': survey_map_path,
            'statistics_file': stats_path,
            'instruments_file': instrument_path,
            'statistics': statistics
        }

    def run_harmonization(self) -> Dict:
        """Run complete cross-cohort questionnaire harmonization"""
        logger.info("Starting cross-cohort questionnaire harmonization...")

        # Load questionnaire data from all cohorts
        arivale_df = self.load_cohort_questionnaires('Arivale', self.arivale_path)
        ukbb_df = self.load_cohort_questionnaires('UKBB', self.ukbb_path)
        israeli10k_df = self.load_cohort_questionnaires('Israeli10K', self.israeli10k_path)

        if arivale_df.empty and ukbb_df.empty and israeli10k_df.empty:
            logger.error("No questionnaire data could be loaded!")
            return {}

        # Identify common LOINC codes
        overlaps = self.identify_common_loinc_codes(arivale_df, ukbb_df, israeli10k_df)

        # Create unified questionnaire schema
        harmonized_df = self.create_unified_questionnaire_schema(arivale_df, ukbb_df, israeli10k_df, overlaps)

        # Generate survey instrument mapping
        instrument_df = self.generate_survey_instrument_mapping(harmonized_df)

        # Save results
        results = self.save_results(harmonized_df, overlaps, instrument_df)

        logger.info("Cross-cohort questionnaire harmonization completed successfully!")
        logger.info(f"Total unique LOINC codes: {len(harmonized_df)}")
        logger.info(f"Questions in all three cohorts: {len(harmonized_df[harmonized_df['num_cohorts'] == 3])}")

        return results

def main():
    """Main execution function"""
    harmonizer = CrossCohortQuestionnaireHarmonizer()
    results = harmonizer.run_harmonization()

    if results:
        print("\n" + "="*70)
        print("CROSS-COHORT QUESTIONNAIRE HARMONIZATION COMPLETE")
        print("="*70)
        print(f"Results saved to: {results['harmonized_file']}")
        print(f"Statistics: {results['statistics']}")
        print("="*70)
    else:
        print("Harmonization failed - check logs for details")

if __name__ == "__main__":
    main()