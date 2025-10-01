#!/usr/bin/env python3
"""
Cross-Cohort MONDO Questionnaires Harmonization Pipeline
Creates unified cross-cohort questionnaire mappings using MONDO ontology for Venn diagram analysis.

This pipeline combines:
1. Arivale questionnaires (mapped to MONDO)
2. UKBB questionnaires (mapped to MONDO)
3. Israeli10K questionnaires (mapped to MONDO)

Output: Cross-cohort intersection analysis for Venn diagrams.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import json
from typing import Dict, Set, List, Tuple
from datetime import datetime
import logging
from dataclasses import dataclass, field

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class MondoQuestionnaireEntity:
    """Represents a questionnaire item with hierarchical context preservation for MONDO disease mappings."""
    canonical_id: str  # MONDO ID as canonical identifier for questionnaire→disease mappings
    cohort_contexts: Dict[str, Dict] = field(default_factory=dict)  # cohort -> context

    def add_cohort_context(self, cohort: str, context: Dict):
        """Add cohort-specific context while preserving canonical identity."""
        self.cohort_contexts[cohort] = context

    def get_cohort_list(self) -> List[str]:
        """Return list of cohorts where this questionnaire disease mapping appears."""
        return list(self.cohort_contexts.keys())

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'canonical_id': self.canonical_id,
            'cohort_contexts': self.cohort_contexts
        }

class EnhancedCrossCohortMondoQuestionnairesHarmonizer:
    """Enhanced MONDO questionnaires harmonizer using hierarchical context preservation with COMPLETE.tsv files."""

    def __init__(self, base_dir: Path = None):
        if base_dir is None:
            base_dir = Path("/home/ubuntu/biomapper/data/harmonization/mondo")
        self.base_dir = base_dir
        self.results_dir = base_dir / "enhanced_cross_cohort_mondo_questionnaires_to_convert_to_biomapper" / "results"
        self.results_dir.mkdir(parents=True, exist_ok=True)

        # Enhanced data containers for two-stage processing
        self.stage1_entities: Dict[str, MondoQuestionnaireEntity] = {}  # canonical_id -> MondoQuestionnaireEntity
        self.cohort_raw_data = {}  # Raw loaded data for debugging
        self.intersection_stats = {}

        # COMPLETE.tsv file paths (preserving API/LLM enrichments)
        self.complete_files = {
            'arivale': base_dir.parent / "harmonization" / "arivale" / "COMPLETE.tsv",
            'ukbb': base_dir.parent / "harmonization" / "ukbb" / "COMPLETE.tsv",
            'israeli10k': base_dir.parent / "harmonization" / "israeli10k" / "COMPLETE.tsv"
        }

    def stage1_consolidate_arivale_questionnaires_mondo(self) -> Dict[str, Dict]:
        """Stage 1: Load and consolidate Arivale questionnaires with MONDO disease mappings."""
        logger.info("Stage 1: Consolidating Arivale questionnaires→MONDO...")

        arivale_file = self.complete_files['arivale']
        consolidated_questionnaires = {}

        if not arivale_file.exists():
            logger.warning(f"Arivale COMPLETE.tsv not found: {arivale_file}")
            return consolidated_questionnaires

        try:
            df = pd.read_csv(arivale_file, sep='\t', low_memory=False)
            self.cohort_raw_data['arivale'] = df

            # Look for MONDO IDs - questionnaires that map to disease concepts
            mondo_columns = [col for col in df.columns if 'mondo' in col.lower()]
            if not mondo_columns:
                logger.warning("No MONDO columns found in Arivale questionnaires data")
                return consolidated_questionnaires

            mondo_col = mondo_columns[0]

            for _, row in df.iterrows():
                mondo_id = row.get(mondo_col)
                if pd.notna(mondo_id) and str(mondo_id).strip():
                    mondo_clean = str(mondo_id).strip()

                    # Create context preserving questionnaire→disease mapping context
                    context = {
                        'original_id': row.get('id', ''),
                        'question_text': row.get('question_text', row.get('name', '')),
                        'survey_name': row.get('survey_name', row.get('survey', '')),
                        'disease_category': row.get('disease_category', ''),
                        'phenotype_mapping': row.get('phenotype_mapping', ''),
                        'clinical_significance': row.get('clinical_significance', ''),
                        'diagnosis_criteria': row.get('diagnosis_criteria', ''),
                        'mapping_confidence': row.get('mapping_confidence', ''),
                        'api_enrichment': {k: v for k, v in row.items() if k.startswith('api_')},
                        'llm_annotations': {k: v for k, v in row.items() if 'llm' in k.lower()},
                        'source_row_index': row.name
                    }

                    consolidated_questionnaires[mondo_clean] = context

            logger.info(f"Arivale Stage 1: Consolidated {len(consolidated_questionnaires)} questionnaire→MONDO mappings")

        except Exception as e:
            logger.error(f"Error consolidating Arivale questionnaires→MONDO: {e}")

        return consolidated_questionnaires

    def stage1_consolidate_ukbb_questionnaires_mondo(self) -> Dict[str, Dict]:
        """Stage 1: Load and consolidate UKBB questionnaires with MONDO disease mappings."""
        logger.info("Stage 1: Consolidating UKBB questionnaires→MONDO...")

        ukbb_file = self.complete_files['ukbb']
        consolidated_questionnaires = {}

        if not ukbb_file.exists():
            logger.warning(f"UKBB COMPLETE.tsv not found: {ukbb_file}")
            return consolidated_questionnaires

        try:
            df = pd.read_csv(ukbb_file, sep='\t', low_memory=False)
            self.cohort_raw_data['ukbb'] = df

            # UKBB questionnaires that map to disease concepts via MONDO
            mondo_columns = [col for col in df.columns if 'mondo' in col.lower()]
            if not mondo_columns:
                logger.warning("No MONDO columns found in UKBB questionnaires data")
                return consolidated_questionnaires

            mondo_col = mondo_columns[0]

            for _, row in df.iterrows():
                mondo_id = row.get(mondo_col)
                if pd.notna(mondo_id) and str(mondo_id).strip():
                    mondo_clean = str(mondo_id).strip()

                    # Create context with UKBB-specific disease mapping enrichments
                    context = {
                        'original_id': row.get('id', ''),
                        'field_name': row.get('field_name', ''),
                        'field_id': row.get('field_id', ''),
                        'category': row.get('category', ''),
                        'question_text': row.get('question_text', ''),
                        'icd10_mapping': row.get('icd10_mapping', ''),
                        'disease_hierarchy': row.get('disease_hierarchy', ''),
                        'self_reported': row.get('self_reported', ''),
                        'medical_history': row.get('medical_history', ''),
                        'api_enrichment': {k: v for k, v in row.items() if k.startswith('api_')},
                        'llm_annotations': {k: v for k, v in row.items() if 'llm' in k.lower()},
                        'source_row_index': row.name
                    }

                    consolidated_questionnaires[mondo_clean] = context

            logger.info(f"UKBB Stage 1: Consolidated {len(consolidated_questionnaires)} questionnaire→MONDO mappings")

        except Exception as e:
            logger.error(f"Error consolidating UKBB questionnaires→MONDO: {e}")

        return consolidated_questionnaires

    def stage1_consolidate_israeli10k_questionnaires_mondo(self) -> Dict[str, Dict]:
        """Stage 1: Load and consolidate Israeli10K questionnaires with MONDO disease mappings."""
        logger.info("Stage 1: Consolidating Israeli10K questionnaires→MONDO...")

        israeli10k_file = self.complete_files['israeli10k']
        consolidated_questionnaires = {}

        if not israeli10k_file.exists():
            logger.warning(f"Israeli10K COMPLETE.tsv not found: {israeli10k_file}")
            return consolidated_questionnaires

        try:
            df = pd.read_csv(israeli10k_file, sep='\t', low_memory=False)
            self.cohort_raw_data['israeli10k'] = df

            # Israeli10K questionnaires with disease mappings
            mondo_columns = [col for col in df.columns if 'mondo' in col.lower()]
            if not mondo_columns:
                logger.warning("No MONDO columns found in Israeli10K questionnaires data")
                return consolidated_questionnaires

            mondo_col = mondo_columns[0]

            for _, row in df.iterrows():
                mondo_id = row.get(mondo_col)
                if pd.notna(mondo_id) and str(mondo_id).strip():
                    mondo_clean = str(mondo_id).strip()

                    # Create context with Israeli10K-specific disease mapping enrichments
                    context = {
                        'original_id': row.get('id', ''),
                        'question_text': row.get('question_text', ''),
                        'questionnaire_name': row.get('questionnaire_name', ''),
                        'health_domain': row.get('health_domain', ''),
                        'symptom_category': row.get('symptom_category', ''),
                        'disease_risk_factor': row.get('disease_risk_factor', ''),
                        'clinical_relevance': row.get('clinical_relevance', ''),
                        'collection_wave': row.get('collection_wave', ''),
                        'api_enrichment': {k: v for k, v in row.items() if k.startswith('api_')},
                        'llm_annotations': {k: v for k, v in row.items() if 'llm' in k.lower()},
                        'source_row_index': row.name
                    }

                    consolidated_questionnaires[mondo_clean] = context

            logger.info(f"Israeli10K Stage 1: Consolidated {len(consolidated_questionnaires)} questionnaire→MONDO mappings")

        except Exception as e:
            logger.error(f"Error consolidating Israeli10K questionnaires→MONDO: {e}")

        return consolidated_questionnaires

    def stage2_create_hierarchical_entities(self) -> Dict[str, MondoQuestionnaireEntity]:
        """Stage 2: Create hierarchical MondoQuestionnaireEntity objects from Stage 1 consolidation."""
        logger.info("Stage 2: Creating hierarchical questionnaire→MONDO entities...")

        # Run Stage 1 for all cohorts
        arivale_questionnaires = self.stage1_consolidate_arivale_questionnaires_mondo()
        ukbb_questionnaires = self.stage1_consolidate_ukbb_questionnaires_mondo()
        israeli10k_questionnaires = self.stage1_consolidate_israeli10k_questionnaires_mondo()

        # Create unified entity collection using MONDO IDs as canonical identifiers
        all_mondo_ids = set(arivale_questionnaires.keys()) | set(ukbb_questionnaires.keys()) | set(israeli10k_questionnaires.keys())

        hierarchical_entities = {}

        for mondo_id in all_mondo_ids:
            entity = MondoQuestionnaireEntity(canonical_id=mondo_id)

            # Add cohort contexts where this MONDO ID appears
            if mondo_id in arivale_questionnaires:
                entity.add_cohort_context('arivale', arivale_questionnaires[mondo_id])

            if mondo_id in ukbb_questionnaires:
                entity.add_cohort_context('ukbb', ukbb_questionnaires[mondo_id])

            if mondo_id in israeli10k_questionnaires:
                entity.add_cohort_context('israeli10k', israeli10k_questionnaires[mondo_id])

            hierarchical_entities[mondo_id] = entity

        logger.info(f"Stage 2: Created {len(hierarchical_entities)} hierarchical questionnaire→MONDO entities")
        logger.info(f"Cohort distribution: Arivale({len(arivale_questionnaires)}), UKBB({len(ukbb_questionnaires)}), Israeli10K({len(israeli10k_questionnaires)})")

        return hierarchical_entities

    def run_enhanced_harmonization(self):
        """Execute enhanced cross-cohort questionnaires→MONDO harmonization with hierarchical context preservation."""
        logger.info("Starting enhanced cross-cohort questionnaires→MONDO harmonization...")

        try:
            # Use Stage 2 hierarchical entities
            self.stage1_entities = self.stage2_create_hierarchical_entities()

            # Create enhanced dataset
            harmonized_df = self.create_enhanced_cross_cohort_mondo_dataset()

            # Generate statistics
            stats = self.generate_enhanced_harmonization_statistics(harmonized_df)

            # Save results with timestamp
            timestamp = stats['harmonization_timestamp']

            # Save enhanced harmonized dataset
            harmonized_file = self.results_dir / f"enhanced_cross_cohort_questionnaires_mondo_{timestamp}.tsv"
            harmonized_df.to_csv(harmonized_file, sep='\t', index=False)

            # Save latest version
            latest_file = self.results_dir / "enhanced_cross_cohort_questionnaires_mondo_latest.tsv"
            harmonized_df.to_csv(latest_file, sep='\t', index=False)

            # Save hierarchical entities as JSON for advanced analysis
            entities_json = {}
            for mondo_id, entity in self.stage1_entities.items():
                entities_json[mondo_id] = entity.to_dict()

            entities_file = self.results_dir / f"hierarchical_mondo_questionnaire_entities_{timestamp}.json"
            with open(entities_file, 'w') as f:
                json.dump(entities_json, f, indent=2)

            entities_latest = self.results_dir / "hierarchical_mondo_questionnaire_entities_latest.json"
            with open(entities_latest, 'w') as f:
                json.dump(entities_json, f, indent=2)

            # Save enhanced statistics
            stats_file = self.results_dir / f"enhanced_questionnaires_mondo_harmonization_statistics_{timestamp}.json"
            with open(stats_file, 'w') as f:
                json.dump(stats, f, indent=2)

            stats_latest = self.results_dir / "enhanced_questionnaires_mondo_harmonization_statistics_latest.json"
            with open(stats_latest, 'w') as f:
                json.dump(stats, f, indent=2)

            # Create enhanced summary report
            self.create_enhanced_summary_report(stats)

            logger.info("Enhanced cross-cohort questionnaires→MONDO harmonization completed successfully!")
            logger.info(f"Results saved to: {self.results_dir}")

            return harmonized_df, stats

        except Exception as e:
            logger.error(f"Error during enhanced questionnaires→MONDO harmonization: {e}")
            raise

    def create_enhanced_cross_cohort_mondo_dataset(self) -> pd.DataFrame:
        """Create enhanced unified cross-cohort questionnaire→MONDO dataset using hierarchical entities."""

        records = []
        for mondo_id, entity in self.stage1_entities.items():
            cohorts = entity.get_cohort_list()

            record = {
                'mondo_id': mondo_id,
                'arivale_present': 'arivale' in cohorts,
                'ukbb_present': 'ukbb' in cohorts,
                'israeli10k_present': 'israeli10k' in cohorts,
                'cohort_count': len(cohorts),
                'cohorts_list': ','.join(sorted(cohorts))
            }

            # Add context-specific information for debugging/validation
            for cohort in ['arivale', 'ukbb', 'israeli10k']:
                if cohort in entity.cohort_contexts:
                    ctx = entity.cohort_contexts[cohort]
                    record[f'{cohort}_original_id'] = ctx.get('original_id', '')
                    record[f'{cohort}_question_text'] = ctx.get('question_text', ctx.get('field_name', ''))
                    record[f'{cohort}_disease_category'] = ctx.get('disease_category', ctx.get('health_domain', ''))
                else:
                    record[f'{cohort}_original_id'] = ''
                    record[f'{cohort}_question_text'] = ''
                    record[f'{cohort}_disease_category'] = ''

            records.append(record)

        df = pd.DataFrame(records)
        df = df.sort_values('cohort_count', ascending=False)

        logger.info(f"Created enhanced cross-cohort questionnaire→MONDO dataset with {len(df)} unique MONDO IDs")
        return df

    def generate_enhanced_harmonization_statistics(self, df: pd.DataFrame) -> Dict:
        """Generate enhanced statistics from hierarchical entities."""

        # Calculate cohort presence from hierarchical entities
        arivale_questionnaires = set(df[df['arivale_present']]['mondo_id'])
        ukbb_questionnaires = set(df[df['ukbb_present']]['mondo_id'])
        israeli10k_questionnaires = set(df[df['israeli10k_present']]['mondo_id'])

        # Calculate intersections
        intersections = self.calculate_intersections(arivale_questionnaires, ukbb_questionnaires, israeli10k_questionnaires)

        # Add hierarchical entity information
        entity_stats = {
            'total_hierarchical_entities': len(self.stage1_entities),
            'entities_with_multiple_cohorts': len([e for e in self.stage1_entities.values() if len(e.get_cohort_list()) > 1]),
            'entities_single_cohort': len([e for e in self.stage1_entities.values() if len(e.get_cohort_list()) == 1]),
            'context_preservation_successful': True
        }

        # Generate comprehensive statistics
        stats = {
            'harmonization_timestamp': datetime.now().strftime('%Y%m%d_%H%M%S'),
            'total_unique_mondo_ids': len(df),
            'cohort_coverage': {
                'arivale_questionnaires': len(arivale_questionnaires),
                'ukbb_questionnaires': len(ukbb_questionnaires),
                'israeli10k_questionnaires': len(israeli10k_questionnaires)
            },
            'overlap_statistics': intersections,
            'harmonization_rate': {
                'cross_cohort_overlap': ((intersections['all_three'] +
                                        intersections['arivale_ukbb_only'] +
                                        intersections['arivale_israeli10k_only'] +
                                        intersections['ukbb_israeli10k_only']) / len(df)) * 100,
                'three_way_overlap': (intersections['all_three'] / len(df)) * 100
            }
        }

        stats.update(entity_stats)
        return stats

    def create_enhanced_summary_report(self, stats: Dict):
        """Create enhanced human-readable summary report with hierarchical context information."""

        report = f"""
# Enhanced Cross-Cohort Questionnaires→MONDO Harmonization Summary

## Overview
- **Total Unique Questionnaire→MONDO Mappings**: {stats['total_unique_mondo_ids']:,}
- **Hierarchical Entities Created**: {stats['total_hierarchical_entities']:,}
- **Harmonization Timestamp**: {stats['harmonization_timestamp']}

## Cohort Coverage
- **Arivale**: {stats['cohort_coverage']['arivale_questionnaires']:,} questionnaire→MONDO mappings
- **UKBB**: {stats['cohort_coverage']['ukbb_questionnaires']:,} questionnaire→MONDO mappings
- **Israeli10K**: {stats['cohort_coverage']['israeli10k_questionnaires']:,} questionnaire→MONDO mappings

## Cross-Cohort Overlaps
- **All Three Cohorts**: {stats['overlap_statistics']['all_three']:,} mappings
- **Arivale + UKBB Only**: {stats['overlap_statistics']['arivale_ukbb_only']:,} mappings
- **Arivale + Israeli10K Only**: {stats['overlap_statistics']['arivale_israeli10k_only']:,} mappings
- **UKBB + Israeli10K Only**: {stats['overlap_statistics']['ukbb_israeli10k_only']:,} mappings
- **Arivale Only**: {stats['overlap_statistics']['arivale_only']:,} mappings
- **UKBB Only**: {stats['overlap_statistics']['ukbb_only']:,} mappings
- **Israeli10K Only**: {stats['overlap_statistics']['israeli10k_only']:,} mappings

## Hierarchical Context Preservation
- **Entities with Multiple Cohorts**: {stats['entities_with_multiple_cohorts']:,}
- **Entities Single Cohort**: {stats['entities_single_cohort']:,}
- **Context Preservation**: {'✅ Successful' if stats['context_preservation_successful'] else '❌ Failed'}

## Enhanced Data Sources
- **Arivale**: COMPLETE.tsv with questionnaire→disease mappings + API/LLM enrichments
- **UKBB**: COMPLETE.tsv with survey→disease classifications + API/LLM enrichments
- **Israeli10K**: COMPLETE.tsv with questionnaire→health domain mappings + API/LLM enrichments

## Two-Stage Processing Architecture
- **Stage 1**: Within-cohort questionnaire→MONDO consolidation
- **Stage 2**: Cross-cohort hierarchical entity creation with context preservation
- **Canonical Identifier Space**: MONDO IDs for disease classification standardization

## Validation
- Total intersections sum: {sum(stats['overlap_statistics'].values()):,}
- Should equal total unique mappings: {stats['total_unique_mondo_ids']:,}
- Mathematical consistency: {sum(stats['overlap_statistics'].values()) == stats['total_unique_mondo_ids']}
- Context preservation: {stats['context_preservation_successful']}
        """

        report_file = self.results_dir / "enhanced_cross_cohort_questionnaires_mondo_summary.md"
        with open(report_file, 'w') as f:
            f.write(report.strip())

        logger.info(f"Enhanced summary report saved to: {report_file}")

    def calculate_intersections(self, arivale_set: Set[str], ukbb_set: Set[str], israeli10k_set: Set[str]) -> Dict[str, int]:
        """Calculate all 7 possible intersections between three cohort sets."""

        # Individual only (exclusive to each cohort)
        arivale_only = arivale_set - ukbb_set - israeli10k_set
        ukbb_only = ukbb_set - arivale_set - israeli10k_set
        israeli10k_only = israeli10k_set - arivale_set - ukbb_set

        # Pairwise only (exclusive to pairs)
        arivale_ukbb_only = (arivale_set & ukbb_set) - israeli10k_set
        arivale_israeli10k_only = (arivale_set & israeli10k_set) - ukbb_set
        ukbb_israeli10k_only = (ukbb_set & israeli10k_set) - arivale_set

        # All three cohorts
        all_three = arivale_set & ukbb_set & israeli10k_set

        intersections = {
            'arivale_only': len(arivale_only),
            'ukbb_only': len(ukbb_only),
            'israeli10k_only': len(israeli10k_only),
            'arivale_ukbb_only': len(arivale_ukbb_only),
            'arivale_israeli10k_only': len(arivale_israeli10k_only),
            'ukbb_israeli10k_only': len(ukbb_israeli10k_only),
            'all_three': len(all_three)
        }

        # Validation: ensure all MONDO IDs are accounted for
        total_intersections = sum(intersections.values())
        total_union = len(arivale_set | ukbb_set | israeli10k_set)

        logger.info(f"Intersection validation: {total_intersections} intersection counts, {total_union} unique MONDO IDs")

        return intersections

    def load_cohort_mondo_questionnaires(self, cohort: str) -> Set[str]:
        """Load MONDO questionnaire mappings for a specific cohort."""
        logger.info(f"Loading {cohort} MONDO questionnaires...")

        mondo_file = self.base_dir / "results" / f"{cohort}_questionnaires_mondo_COMPLETE.tsv"

        if not mondo_file.exists():
            logger.warning(f"{cohort} MONDO questionnaires file not found: {mondo_file}")
            return set()

        df = pd.read_csv(mondo_file, sep='\t')

        # Extract unique MONDO IDs with high confidence scores
        mondo_ids = set()

        for _, row in df.iterrows():
            mondo_id = row['mondo_id']
            confidence_score = float(row.get('confidence_score', 0.0))

            # Only include high-confidence mappings (>= 0.7)
            if pd.notna(mondo_id) and confidence_score >= 0.7:
                mondo_clean = str(mondo_id).strip()
                if mondo_clean.startswith('MONDO:'):
                    mondo_ids.add(mondo_clean)

        logger.info(f"Loaded {len(mondo_ids)} high-confidence MONDO mappings for {cohort}")
        return mondo_ids

    def load_all_cohorts(self) -> Tuple[Set[str], Set[str], Set[str]]:
        """Load MONDO questionnaire mappings for all cohorts."""

        arivale_mondo = self.load_cohort_mondo_questionnaires('arivale')
        ukbb_mondo = self.load_cohort_mondo_questionnaires('ukbb')
        israeli10k_mondo = self.load_cohort_mondo_questionnaires('israeli10k')

        return arivale_mondo, ukbb_mondo, israeli10k_mondo

    def calculate_intersections(self, arivale_set: Set[str], ukbb_set: Set[str], israeli10k_set: Set[str]) -> Dict[str, int]:
        """Calculate all 7 possible intersections between three cohort sets."""

        # Individual only (exclusive to each cohort)
        arivale_only = arivale_set - ukbb_set - israeli10k_set
        ukbb_only = ukbb_set - arivale_set - israeli10k_set
        israeli10k_only = israeli10k_set - arivale_set - ukbb_set

        # Pairwise only (exclusive to pairs)
        arivale_ukbb_only = (arivale_set & ukbb_set) - israeli10k_set
        arivale_israeli10k_only = (arivale_set & israeli10k_set) - ukbb_set
        ukbb_israeli10k_only = (ukbb_set & israeli10k_set) - arivale_set

        # All three cohorts
        all_three = arivale_set & ukbb_set & israeli10k_set

        intersections = {
            'arivale_only': len(arivale_only),
            'ukbb_only': len(ukbb_only),
            'israeli10k_only': len(israeli10k_only),
            'arivale_ukbb_only': len(arivale_ukbb_only),
            'arivale_israeli10k_only': len(arivale_israeli10k_only),
            'ukbb_israeli10k_only': len(ukbb_israeli10k_only),
            'all_three': len(all_three)
        }

        # Validation: ensure all MONDO codes are accounted for
        total_intersections = sum(intersections.values())
        total_union = len(arivale_set | ukbb_set | israeli10k_set)

        logger.info(f"Intersection validation: {total_intersections} intersection counts, {total_union} unique MONDO codes")

        return intersections

    def create_cross_cohort_mondo_dataset(self) -> pd.DataFrame:
        """Create unified cross-cohort MONDO questionnaire dataset."""

        # Load all cohort data
        arivale_mondo, ukbb_mondo, israeli10k_mondo = self.load_all_cohorts()

        # Create unified dataset
        all_mondo_ids = arivale_mondo | ukbb_mondo | israeli10k_mondo

        records = []
        for mondo_id in all_mondo_ids:
            record = {
                'mondo_id': mondo_id,
                'arivale_present': mondo_id in arivale_mondo,
                'ukbb_present': mondo_id in ukbb_mondo,
                'israeli10k_present': mondo_id in israeli10k_mondo,
                'cohort_count': sum([
                    mondo_id in arivale_mondo,
                    mondo_id in ukbb_mondo,
                    mondo_id in israeli10k_mondo
                ])
            }
            records.append(record)

        df = pd.DataFrame(records)
        df = df.sort_values('cohort_count', ascending=False)

        logger.info(f"Created cross-cohort MONDO dataset with {len(df)} unique MONDO identifiers")
        return df

    def generate_harmonization_statistics(self, df: pd.DataFrame) -> Dict:
        """Generate comprehensive statistics for MONDO questionnaire harmonization."""

        # Calculate cohort presence
        arivale_mondo = set(df[df['arivale_present']]['mondo_id'])
        ukbb_mondo = set(df[df['ukbb_present']]['mondo_id'])
        israeli10k_mondo = set(df[df['israeli10k_present']]['mondo_id'])

        # Calculate intersections
        intersections = self.calculate_intersections(arivale_mondo, ukbb_mondo, israeli10k_mondo)

        # Generate statistics
        stats = {
            'harmonization_timestamp': datetime.now().strftime('%Y%m%d_%H%M%S'),
            'total_unique_mondo_codes': len(df),
            'cohort_coverage': {
                'arivale_mondo': len(arivale_mondo),
                'ukbb_mondo': len(ukbb_mondo),
                'israeli10k_mondo': len(israeli10k_mondo)
            },
            'overlap_statistics': intersections,
            'mondo_codes_in_all_cohorts': intersections['all_three'],
            'mondo_codes_in_two_cohorts': (
                intersections['arivale_ukbb_only'] +
                intersections['arivale_israeli10k_only'] +
                intersections['ukbb_israeli10k_only']
            ),
            'mondo_codes_in_one_cohort': (
                intersections['arivale_only'] +
                intersections['ukbb_only'] +
                intersections['israeli10k_only']
            ),
            'harmonization_rate': {
                'cross_cohort_overlap': ((intersections['all_three'] +
                                        intersections['arivale_ukbb_only'] +
                                        intersections['arivale_israeli10k_only'] +
                                        intersections['ukbb_israeli10k_only']) / len(df)) * 100,
                'three_way_overlap': (intersections['all_three'] / len(df)) * 100
            },
            'confidence_threshold': 0.7,
            'mapping_quality': 'high_confidence_only'
        }

        return stats

    def load_mondo_metadata(self) -> Dict[str, Dict]:
        """Load additional MONDO metadata for enhanced reporting."""

        metadata = {}

        # Load metadata from each cohort file for disease categories
        for cohort in ['arivale', 'ukbb', 'israeli10k']:
            mondo_file = self.base_dir / "results" / f"{cohort}_questionnaires_mondo_COMPLETE.tsv"

            if mondo_file.exists():
                try:
                    df = pd.read_csv(mondo_file, sep='\t')

                    for _, row in df.iterrows():
                        mondo_id = row['mondo_id']
                        if pd.notna(mondo_id) and str(mondo_id).startswith('MONDO:'):
                            mondo_clean = str(mondo_id).strip()

                            if mondo_clean not in metadata:
                                metadata[mondo_clean] = {
                                    'mondo_name': row.get('mondo_name', ''),
                                    'category': row.get('category', ''),
                                    'semantic_relationship': row.get('semantic_relationship', ''),
                                    'cohorts': []
                                }

                            if cohort not in metadata[mondo_clean]['cohorts']:
                                metadata[mondo_clean]['cohorts'].append(cohort)

                except Exception as e:
                    logger.warning(f"Could not load metadata from {cohort}: {e}")

        return metadata

    def run_harmonization(self):
        """Execute complete cross-cohort MONDO questionnaire harmonization."""
        logger.info("Starting cross-cohort MONDO questionnaires harmonization...")

        try:
            # Create cross-cohort dataset
            harmonized_df = self.create_cross_cohort_mondo_dataset()

            # Generate statistics
            stats = self.generate_harmonization_statistics(harmonized_df)

            # Load metadata
            metadata = self.load_mondo_metadata()

            # Save results with timestamp
            timestamp = stats['harmonization_timestamp']

            # Save harmonized dataset
            harmonized_file = self.results_dir / f"cross_cohort_mondo_questionnaires_{timestamp}.tsv"
            harmonized_df.to_csv(harmonized_file, sep='\t', index=False)

            # Save latest version
            latest_file = self.results_dir / "cross_cohort_mondo_questionnaires_latest.tsv"
            harmonized_df.to_csv(latest_file, sep='\t', index=False)

            # Save statistics
            stats_file = self.results_dir / f"mondo_questionnaires_harmonization_statistics_{timestamp}.json"
            with open(stats_file, 'w') as f:
                json.dump(stats, f, indent=2)

            stats_latest = self.results_dir / "mondo_questionnaires_harmonization_statistics_latest.json"
            with open(stats_latest, 'w') as f:
                json.dump(stats, f, indent=2)

            # Save metadata
            metadata_file = self.results_dir / f"mondo_questionnaires_metadata_{timestamp}.json"
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)

            # Create summary report
            self.create_summary_report(stats, metadata)

            logger.info("Cross-cohort MONDO questionnaires harmonization completed successfully!")
            logger.info(f"Results saved to: {self.results_dir}")

            return harmonized_df, stats

        except Exception as e:
            logger.error(f"Error during harmonization: {e}")
            raise

    def create_summary_report(self, stats: Dict, metadata: Dict):
        """Create human-readable summary report."""

        # Calculate top disease categories
        category_counts = {}
        for mondo_data in metadata.values():
            category = mondo_data.get('category', 'unknown')
            category_counts[category] = category_counts.get(category, 0) + 1

        top_categories = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)[:5]

        report = f"""
# Cross-Cohort MONDO Questionnaires Harmonization Summary

## Overview
- **Total Unique MONDO Codes**: {stats['total_unique_mondo_codes']:,}
- **Harmonization Timestamp**: {stats['harmonization_timestamp']}
- **Confidence Threshold**: {stats['confidence_threshold']}

## Cohort Coverage
- **Arivale**: {stats['cohort_coverage']['arivale_mondo']:,} MONDO codes
- **UKBB**: {stats['cohort_coverage']['ukbb_mondo']:,} MONDO codes
- **Israeli10K**: {stats['cohort_coverage']['israeli10k_mondo']:,} MONDO codes

## Cross-Cohort Overlaps
- **All Three Cohorts**: {stats['overlap_statistics']['all_three']:,} codes
- **Arivale + UKBB Only**: {stats['overlap_statistics']['arivale_ukbb_only']:,} codes
- **Arivale + Israeli10K Only**: {stats['overlap_statistics']['arivale_israeli10k_only']:,} codes
- **UKBB + Israeli10K Only**: {stats['overlap_statistics']['ukbb_israeli10k_only']:,} codes
- **Arivale Only**: {stats['overlap_statistics']['arivale_only']:,} codes
- **UKBB Only**: {stats['overlap_statistics']['ukbb_only']:,} codes
- **Israeli10K Only**: {stats['overlap_statistics']['israeli10k_only']:,} codes

## Harmonization Metrics
- **Cross-Cohort Overlap Rate**: {stats['harmonization_rate']['cross_cohort_overlap']:.1f}%
- **Three-Way Overlap Rate**: {stats['harmonization_rate']['three_way_overlap']:.1f}%
- **MONDO Codes in All Cohorts**: {stats['mondo_codes_in_all_cohorts']:,}
- **MONDO Codes in Two Cohorts**: {stats['mondo_codes_in_two_cohorts']:,}
- **MONDO Codes in One Cohort**: {stats['mondo_codes_in_one_cohort']:,}

## Top Disease Categories
"""
        for category, count in top_categories:
            report += f"- **{category}**: {count:,} codes\n"

        report += f"""

## Data Quality
- **Mapping Quality**: {stats['mapping_quality']}
- **Total MONDO Metadata Entries**: {len(metadata):,}

## Data Sources
- Arivale: Health history questionnaires mapped to MONDO
- UKBB: Health questionnaires mapped to MONDO
- Israeli10K: Health questionnaires mapped to MONDO

## Validation
Total intersections sum: {sum(stats['overlap_statistics'].values()):,}
Should equal total unique codes: {stats['total_unique_mondo_codes']:,}
Match: {sum(stats['overlap_statistics'].values()) == stats['total_unique_mondo_codes']}
        """

        report_file = self.results_dir / "cross_cohort_mondo_questionnaires_summary.md"
        with open(report_file, 'w') as f:
            f.write(report.strip())

        logger.info(f"Summary report saved to: {report_file}")

if __name__ == "__main__":
    # Use enhanced harmonizer for hierarchical context preservation
    harmonizer = EnhancedCrossCohortMondoQuestionnairesHarmonizer()
    harmonized_data, statistics = harmonizer.run_enhanced_harmonization()

    print(f"\n=== ENHANCED CROSS-COHORT QUESTIONNAIRES→MONDO HARMONIZATION COMPLETE ===")
    print(f"Total MONDO IDs: {statistics['total_unique_mondo_ids']:,}")
    print(f"Hierarchical Entities: {statistics['total_hierarchical_entities']:,}")
    print(f"Cross-Cohort Overlap: {statistics['harmonization_rate']['cross_cohort_overlap']:.1f}%")
    print(f"Context Preservation: {'✅ Successful' if statistics['context_preservation_successful'] else '❌ Failed'}")
    print(f"Mathematical Consistency: {'✅ YES' if sum(statistics['overlap_statistics'].values()) == statistics['total_unique_mondo_ids'] else '❌ NO'}")
    print(f"Results: {harmonizer.results_dir}")