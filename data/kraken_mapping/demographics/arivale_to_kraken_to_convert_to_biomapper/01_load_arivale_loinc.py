#!/usr/bin/env python3
"""
Proto-action: Load Arivale demographics with LOINC mappings
This is a STANDALONE script, not a biomapper action
"""
import pandas as pd
from pathlib import Path

# Direct file paths - Updated to use completed file with LLM reasoning
INPUT_FILE = "/home/ubuntu/biomapper/data/harmonization/demographics/loinc_demographics_to_convert_to_biomapper/results/arivale_demographics_loinc_final.tsv"
OUTPUT_DIR = Path(__file__).parent / "data"

def assign_demographic_category(field_name, description):
    """Assign demographic category based on field name and description"""
    field_lower = field_name.lower()
    desc_lower = description.lower() if description else ""

    # Age-related
    if 'age' in field_lower:
        return 'age'

    # Sex/Gender
    if any(term in field_lower for term in ['sex', 'gender']):
        return 'sex'

    # Race/Ethnicity
    if any(term in field_lower for term in ['race', 'ethnic', 'ancestry']):
        if 'ethnic' in field_lower:
            return 'ethnicity'
        return 'race'

    # Genetic ancestry
    if any(term in field_lower for term in ['pc1', 'pc2', 'pc3', 'genetic_ancestry', 'genome_id']):
        return 'genetic_ancestry'

    # Geographic
    if any(term in field_lower for term in ['country', 'region', 'location']):
        return 'geography'

    # Consent/Legal
    if any(term in field_lower for term in ['consent', 'agreement', 'permission']):
        return 'consent'

    # Identifiers
    if any(term in field_lower for term in ['id', 'identifier', 'client', 'user', 'participant']):
        return 'identifier'

    # Program/Study related
    if any(term in field_lower for term in ['program', 'study', 'enterprise', 'coach']):
        return 'program'

    # Default
    return 'other'

def main():
    print("Loading Arivale demographics with LOINC mappings...")

    # Load the Arivale demographics TSV file
    try:
        df = pd.read_csv(INPUT_FILE, sep='\t')
        print(f"Loaded {len(df)} demographic fields")
    except FileNotFoundError:
        print(f"Error: Input file not found: {INPUT_FILE}")
        return
    except Exception as e:
        print(f"Error loading file: {e}")
        return

    # Show basic info about the data
    print("\nData overview:")
    print(f"Columns: {list(df.columns)}")
    print(f"Shape: {df.shape}")

    # Check for required columns
    required_columns = ['field_name', 'loinc_code', 'confidence_score']
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        print(f"Warning: Missing required columns: {missing_columns}")

    # Filter for successfully mapped fields (confidence > 0.7 and not NO_MATCH)
    print(f"\nBefore filtering: {len(df)} fields")

    # Filter conditions
    high_confidence = df['confidence_score'] > 0.7
    has_loinc = df['loinc_code'] != 'NO_MATCH'
    valid_loinc = df['loinc_code'].notna()

    filtered_df = df[high_confidence & has_loinc & valid_loinc].copy()
    print(f"After filtering (confidence > 0.7, has LOINC): {len(filtered_df)} fields")

    # Add demographic categories
    print("\nAdding demographic categories...")
    filtered_df['demographic_category'] = filtered_df.apply(
        lambda row: assign_demographic_category(row['field_name'], row.get('description', '')),
        axis=1
    )

    # Show category distribution
    print("\nDemographic category distribution:")
    category_counts = filtered_df['demographic_category'].value_counts()
    for category, count in category_counts.items():
        print(f"  {category}: {count}")

    # Show some examples of LOINC mappings by category
    print("\nExample mappings by category:")
    for category in category_counts.head(5).index:
        example = filtered_df[filtered_df['demographic_category'] == category].iloc[0]
        print(f"  {category}: {example['field_name']} -> {example['loinc_code']} ({example['loinc_name']})")

    # Save filtered results
    output_file = OUTPUT_DIR / "arivale_loinc_filtered.tsv"
    filtered_df.to_csv(output_file, sep='\t', index=False)
    print(f"\nSaved {len(filtered_df)} filtered fields to {output_file}")

    # Summary statistics
    print("\nSummary:")
    print(f"  Total input fields: {len(df)}")
    print(f"  Successfully mapped fields: {len(filtered_df)}")
    print(f"  Mapping rate: {100 * len(filtered_df) / len(df):.1f}%")
    print(f"  Average confidence: {filtered_df['confidence_score'].mean():.3f}")

    return filtered_df

if __name__ == "__main__":
    main()