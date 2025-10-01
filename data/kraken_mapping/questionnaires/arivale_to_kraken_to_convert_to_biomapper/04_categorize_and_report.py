#!/usr/bin/env python3
"""
Proto-strategy: Categorize questionnaire domains and generate final report
This is a STANDALONE script for domain categorization and final output generation
"""
import pandas as pd
from pathlib import Path
import re

# Input file from previous step
DATA_DIR = Path(__file__).parent / "data"
MAPPED_FILE = DATA_DIR / "arivale_kraken_mapped.tsv"

# Output directory
RESULTS_DIR = Path(__file__).parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)

def categorize_questionnaire_domain(field_name, category):
    """
    Categorize questionnaire fields into domains based on field name and category
    """
    field_lower = str(field_name).lower()
    cat_lower = str(category).lower()

    # Lifestyle domains
    if any(term in field_lower for term in ['diet', 'food', 'nutrition', 'eating', 'meal', 'breakfast', 'lunch', 'dinner']):
        return 'lifestyle_diet'
    elif any(term in field_lower for term in ['exercise', 'physical', 'activity', 'sport', 'fitness', 'workout']):
        return 'lifestyle_physical_activity'
    elif any(term in field_lower for term in ['sleep', 'rest', 'bedtime', 'wake']):
        return 'lifestyle_sleep'
    elif any(term in field_lower for term in ['smoke', 'tobacco', 'cigarette', 'alcohol', 'drink', 'substance']):
        return 'lifestyle_substance_use'

    # Medical domains
    elif any(term in field_lower for term in ['pain', 'ache', 'symptom', 'medical', 'health', 'condition', 'disease']):
        return 'medical_symptoms'
    elif any(term in field_lower for term in ['medication', 'drug', 'prescription', 'supplement', 'vitamin']):
        return 'medical_medications'
    elif any(term in field_lower for term in ['family', 'history', 'genetic', 'hereditary']):
        return 'medical_family_history'

    # Psychological domains
    elif any(term in field_lower for term in ['stress', 'anxiety', 'depression', 'mood', 'mental', 'emotional']):
        return 'psychological_mental_health'
    elif any(term in field_lower for term in ['wellbeing', 'quality', 'satisfaction', 'happiness']):
        return 'psychological_wellbeing'

    # Demographic domains
    elif any(term in field_lower for term in ['age', 'gender', 'sex', 'race', 'ethnicity', 'education', 'income']):
        return 'demographic_personal'
    elif any(term in field_lower for term in ['work', 'job', 'occupation', 'employment', 'career']):
        return 'demographic_occupational'

    # Check category for additional hints
    elif 'diet' in cat_lower:
        return 'lifestyle_diet'
    elif any(term in cat_lower for term in ['lifestyle', 'behavior']):
        return 'lifestyle_general'
    elif any(term in cat_lower for term in ['medical', 'health', 'clinical']):
        return 'medical_general'
    elif any(term in cat_lower for term in ['psychological', 'mental']):
        return 'psychological_general'
    elif any(term in cat_lower for term in ['demographic', 'personal']):
        return 'demographic_general'

    # Default
    return 'other_questionnaire'

def identify_survey_instrument(field_name, loinc_code):
    """
    Identify standard survey instruments based on field names and LOINC codes
    """
    field_lower = str(field_name).lower()
    loinc_str = str(loinc_code).lower()

    # Standard validated instruments
    if any(term in field_lower for term in ['phq', 'phq-9', 'phq9']):
        return 'PHQ-9 (Depression)'
    elif any(term in field_lower for term in ['gad', 'gad-7', 'gad7']):
        return 'GAD-7 (Anxiety)'
    elif any(term in field_lower for term in ['pss', 'perceived stress']):
        return 'PSS (Perceived Stress Scale)'
    elif any(term in field_lower for term in ['sf-36', 'sf36']):
        return 'SF-36 (Quality of Life)'
    elif any(term in field_lower for term in ['promis']):
        return 'PROMIS (Patient-Reported Outcomes)'
    elif any(term in field_lower for term in ['eq-5d', 'eq5d']):
        return 'EQ-5D (Health Status)'
    elif any(term in field_lower for term in ['beck', 'bdi']):
        return 'Beck Depression Inventory'
    elif any(term in field_lower for term in ['mini', 'mental state']):
        return 'Mini-Mental State Exam'

    # Diet/nutrition instruments
    elif any(term in field_lower for term in ['ffq', 'food frequency']):
        return 'FFQ (Food Frequency Questionnaire)'
    elif any(term in field_lower for term in ['dietary', 'nutrition', 'eating habits']):
        return 'Dietary Assessment Tool'

    # Physical activity instruments
    elif any(term in field_lower for term in ['ipaq']):
        return 'IPAQ (Physical Activity)'
    elif any(term in field_lower for term in ['physical activity questionnaire']):
        return 'Physical Activity Assessment'

    # Sleep instruments
    elif any(term in field_lower for term in ['pittsburgh', 'psqi']):
        return 'PSQI (Sleep Quality)'
    elif any(term in field_lower for term in ['epworth']):
        return 'Epworth Sleepiness Scale'

    return None

def main():
    print("Categorizing questionnaire domains and generating final report...")

    # Load the mapped data
    try:
        df = pd.read_csv(MAPPED_FILE, sep='\t')
        print(f"Loaded {len(df)} mapped questionnaire fields")
    except FileNotFoundError:
        print(f"ERROR: Mapped file not found: {MAPPED_FILE}")
        print("Please run 03_direct_loinc_mapping.py first")
        return
    except Exception as e:
        print(f"ERROR loading mapped file: {e}")
        return

    print(f"\n=== APPLYING CATEGORIZATION ===")

    # Apply domain categorization
    df['questionnaire_domain'] = df.apply(
        lambda row: categorize_questionnaire_domain(row.get('field_name', ''), row.get('category', '')),
        axis=1
    )

    # Identify survey instruments
    df['survey_instrument'] = df.apply(
        lambda row: identify_survey_instrument(row.get('field_name', ''), row.get('loinc_code', '')),
        axis=1
    )

    # Show categorization results
    print(f"\n=== DOMAIN CATEGORIZATION RESULTS ===")
    domain_counts = df['questionnaire_domain'].value_counts()
    for domain, count in domain_counts.items():
        print(f"  {domain}: {count} fields")

    # Show survey instrument identification
    instruments = df[df['survey_instrument'].notna()]['survey_instrument'].value_counts()
    print(f"\n=== IDENTIFIED SURVEY INSTRUMENTS ===")
    if len(instruments) > 0:
        for instrument, count in instruments.items():
            print(f"  {instrument}: {count} fields")
    else:
        print("  No standard survey instruments automatically identified")

    # Create final output with required fields
    print(f"\n=== GENERATING FINAL OUTPUT ===")

    # Prepare the final output dataframe with required columns
    final_df = pd.DataFrame()

    # Required fields from instructions
    final_df['arivale_field'] = df['field_name']
    final_df['arivale_category'] = df['category']
    final_df['matched_loinc_code'] = df['loinc_code']
    final_df['loinc_name'] = df.get('loinc_name', df.get('kraken_name', ''))

    # Use Kraken fields (treating as KG2C equivalent)
    final_df['kg2c_node_id'] = df['kraken_node_id']
    final_df['kg2c_name'] = df['kraken_name']
    final_df['kg2c_category'] = df['kraken_category']

    # Add our derived fields
    final_df['questionnaire_domain'] = df['questionnaire_domain']
    final_df['survey_instrument'] = df['survey_instrument']
    final_df['mapping_confidence'] = df['mapping_confidence']

    # Add metadata
    final_df['mapping_status'] = df['mapping_status']
    final_df['mapping_method'] = df['mapping_method']
    final_df['cohort'] = 'arivale'
    final_df['target_kg'] = 'kraken_1.0.0'

    # Save main results
    main_output = RESULTS_DIR / "arivale_to_kraken_mappings.tsv"
    final_df.to_csv(main_output, sep='\t', index=False)
    print(f"Saved main results to {main_output}")

    # Save matched-only results
    matched_final = final_df[final_df['mapping_status'] == 'matched'].copy()
    matched_output = RESULTS_DIR / "arivale_kraken_matched_questionnaires.tsv"
    matched_final.to_csv(matched_output, sep='\t', index=False)
    print(f"Saved matched questionnaires to {matched_output}")

    # Save unmatched for review
    unmatched_final = final_df[final_df['mapping_status'] == 'unmatched'].copy()
    unmatched_output = RESULTS_DIR / "arivale_kraken_unmatched_questionnaires.tsv"
    unmatched_final.to_csv(unmatched_output, sep='\t', index=False)
    print(f"Saved unmatched questionnaires to {unmatched_output}")

    # Generate summary statistics
    total_fields = len(final_df)
    matched_fields = len(matched_final)
    unmatched_fields = len(unmatched_final)

    # Create a summary report
    summary_report = f"""# Arivale Questionnaires to Kraken 1.0.0 Mapping Report

## Overview
- **Total questionnaire fields processed**: {total_fields:,}
- **Successfully mapped to Kraken**: {matched_fields:,} ({100*matched_fields/total_fields:.1f}%)
- **Unmatched fields**: {unmatched_fields:,} ({100*unmatched_fields/total_fields:.1f}%)

## Domain Categorization
"""

    for domain, count in domain_counts.items():
        summary_report += f"- **{domain}**: {count:,} fields\n"

    summary_report += f"\n## Survey Instruments Identified\n"
    if len(instruments) > 0:
        for instrument, count in instruments.items():
            summary_report += f"- **{instrument}**: {count:,} fields\n"
    else:
        summary_report += "- No standard survey instruments automatically identified\n"

    summary_report += f"""
## Files Generated
- `arivale_to_kraken_mappings.tsv`: Complete mapping results ({total_fields:,} records)
- `arivale_kraken_matched_questionnaires.tsv`: Successfully mapped fields ({matched_fields:,} records)
- `arivale_kraken_unmatched_questionnaires.tsv`: Unmatched fields for review ({unmatched_fields:,} records)

## Mapping Method
- **Direct LOINC code matching** between Arivale questionnaire fields and Kraken 1.0.0 clinical findings
- **High-confidence threshold**: Confidence score ≥ 0.7 for LOINC mappings
- **Target knowledge graph**: Kraken 1.0.0 clinical findings ({len(df)} total entries processed)

## Data Quality
- All mappings are based on standardized LOINC codes
- Confidence scores reflect original LLM-based LOINC mapping quality
- Domain categorization applied using field name and category analysis
- Survey instrument identification based on standard naming patterns
"""

    # Save summary report
    report_file = RESULTS_DIR / "mapping_summary_report.md"
    with open(report_file, 'w') as f:
        f.write(summary_report)
    print(f"Saved summary report to {report_file}")

    # Display final statistics
    print(f"\n=== FINAL RESULTS ===")
    print(f"Total questionnaire fields: {total_fields:,}")
    print(f"Successfully mapped: {matched_fields:,} ({100*matched_fields/total_fields:.1f}%)")
    print(f"Unmatched: {unmatched_fields:,} ({100*unmatched_fields/total_fields:.1f}%)")
    print(f"Unique domains: {len(domain_counts)}")
    print(f"Survey instruments identified: {len(instruments)}")

    print(f"\n✅ Successfully completed questionnaire categorization and reporting")
    print(f"   Main output: {main_output}")
    print(f"   Summary report: {report_file}")

if __name__ == "__main__":
    main()