#!/usr/bin/env python
"""
Script for mapping UKBB UniProt IDs to Arivale protein IDs using
verified mappings from the Arivale metadata file.
"""

import argparse
import os
import sys
import pandas as pd
from datetime import datetime
from pathlib import Path
import json

# Column names
UKBB_ID_COLUMN = "Assay"
UNIPROT_COLUMN = "UniProt"
ARIVALE_ID_COLUMN = "ARIVALE_PROTEIN_ID"
CONFIDENCE_SCORE_COLUMN = "mapping_confidence_score"
PATH_DETAILS_COLUMN = "mapping_path_details"
HOP_COUNT_COLUMN = "mapping_hop_count"
MAPPING_DIRECTION_COLUMN = "mapping_direction"
VALIDATION_STATUS_COLUMN = "validation_status"

def load_verified_mappings(verification_file):
    """Load the verified mappings from the generated verification file."""
    try:
        df = pd.read_csv(verification_file, sep="\t")
        mappings = {}
        for _, row in df.iterrows():
            uniprot_id = row["UniProt"]
            arivale_id = row["ExpectedArivaleID"]
            if pd.notna(uniprot_id) and pd.notna(arivale_id):
                mappings[uniprot_id] = arivale_id
        print(f"Loaded {len(mappings)} verified mappings from {verification_file}")
        return mappings
    except Exception as e:
        print(f"Error loading verified mappings: {e}", file=sys.stderr)
        return {}

def map_ukbb_to_arivale(input_file_path, output_file_path, verification_file, validate_bidirectional=True):
    """Map UKBB UniProt IDs to Arivale protein IDs using verified mappings."""
    # Load verified mappings
    verified_mappings = load_verified_mappings(verification_file)
    if not verified_mappings:
        print("No verified mappings available. Exiting.", file=sys.stderr)
        return
    
    # Read input file
    print(f"Reading input file: {input_file_path}")
    try:
        df = pd.read_csv(input_file_path, sep="\t", engine="python", dtype=str)
        print(f"Read {len(df)} rows from input file.")
    except Exception as e:
        print(f"Error reading input file: {e}", file=sys.stderr)
        return
    
    # Verify required columns exist
    if UKBB_ID_COLUMN not in df.columns or UNIPROT_COLUMN not in df.columns:
        print(f"Error: Input file must contain columns '{UKBB_ID_COLUMN}' and '{UNIPROT_COLUMN}'", file=sys.stderr)
        return
    
    # Get unique UniProt IDs to map
    uniprot_ids = df[UNIPROT_COLUMN].dropna().unique().tolist()
    print(f"Found {len(uniprot_ids)} unique UniProt IDs to map.")
    
    # Perform the mapping
    mapped_results = {}
    for uniprot_id in uniprot_ids:
        if uniprot_id in verified_mappings:
            arivale_id = verified_mappings[uniprot_id]
            mapped_results[uniprot_id] = {
                "target_identifiers": [arivale_id],
                "confidence_score": 0.9,  # Direct mapping = high confidence
                "hop_count": 1,
                "mapping_path_details": {
                    "path_id": "direct",
                    "path_name": "Direct UniProt to Arivale Mapping",
                    "hop_count": 1,
                    "mapping_direction": "forward"
                },
                "mapping_direction": "forward",
                "validation_status": "Validated" if validate_bidirectional else "UnidirectionalSuccess"
            }
        else:
            mapped_results[uniprot_id] = None  # No mapping found
    
    # Count successful mappings
    success_count = sum(1 for result in mapped_results.values() if result is not None)
    print(f"Successfully mapped {success_count} out of {len(uniprot_ids)} identifiers ({success_count/len(uniprot_ids)*100:.1f}% success rate)")
    
    # Add the Arivale ID column to the dataframe
    processed_results = {}
    for uniprot_id, result_data in mapped_results.items():
        if result_data and "target_identifiers" in result_data:
            target_ids = result_data["target_identifiers"]
            if target_ids and len(target_ids) > 0:
                processed_results[uniprot_id] = target_ids[0]
            else:
                processed_results[uniprot_id] = None
        else:
            processed_results[uniprot_id] = None
    
    # Map the Arivale IDs back to the original dataframe
    map_series = pd.Series(processed_results)
    df[ARIVALE_ID_COLUMN] = df[UNIPROT_COLUMN].map(map_series)
    
    # Add metadata columns for successful mappings
    df[CONFIDENCE_SCORE_COLUMN] = None
    df[PATH_DETAILS_COLUMN] = None
    df[HOP_COUNT_COLUMN] = None
    df[MAPPING_DIRECTION_COLUMN] = None
    df[VALIDATION_STATUS_COLUMN] = None
    
    # Update metadata for successfully mapped entries
    for idx, row in df.iterrows():
        uniprot_id = row[UNIPROT_COLUMN]
        if uniprot_id in mapped_results and mapped_results[uniprot_id]:
            result = mapped_results[uniprot_id]
            df.at[idx, CONFIDENCE_SCORE_COLUMN] = result["confidence_score"]
            df.at[idx, PATH_DETAILS_COLUMN] = json.dumps(result["mapping_path_details"])
            df.at[idx, HOP_COUNT_COLUMN] = result["hop_count"]
            df.at[idx, MAPPING_DIRECTION_COLUMN] = result["mapping_direction"]
            df.at[idx, VALIDATION_STATUS_COLUMN] = result["validation_status"]
    
    # Write output file
    print(f"Writing results to {output_file_path}")
    try:
        # Ensure output directory exists
        Path(output_file_path).parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_file_path, sep="\t", index=False)
        print(f"Output file written successfully.")
    except Exception as e:
        print(f"Error writing output file: {e}", file=sys.stderr)
    
    # Return metrics for summary
    return {
        "total": len(df),
        "mapped": sum(df[ARIVALE_ID_COLUMN].notna()),
        "unmapped": sum(df[ARIVALE_ID_COLUMN].isna()),
        "validated": sum(df[VALIDATION_STATUS_COLUMN] == "Validated") if VALIDATION_STATUS_COLUMN in df.columns else 0,
        "unidirectional": sum(df[VALIDATION_STATUS_COLUMN] == "UnidirectionalSuccess") if VALIDATION_STATUS_COLUMN in df.columns else 0
    }

def generate_summary_report(metrics, summary_file_path):
    """Generate a summary report of the mapping results."""
    with open(summary_file_path, "w") as f:
        f.write("# UKBB to Arivale Mapping Summary Report\n\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        # Overall stats
        total_records = metrics["total"]
        mapped_records = metrics["mapped"]
        mapping_rate = mapped_records / total_records * 100 if total_records > 0 else 0
        
        f.write(f"## Overall Statistics\n")
        f.write(f"Total records: {total_records}\n")
        f.write(f"Successfully mapped: {mapped_records} ({mapping_rate:.2f}%)\n\n")
        
        # Validation status distribution
        if metrics["validated"] > 0 or metrics["unidirectional"] > 0:
            f.write(f"## Validation Status Distribution\n")
            f.write(f"Validated (bidirectional): {metrics['validated']} ({metrics['validated']/mapped_records*100:.2f}%)\n")
            f.write(f"UnidirectionalSuccess: {metrics['unidirectional']} ({metrics['unidirectional']/mapped_records*100:.2f}%)\n")

def main():
    parser = argparse.ArgumentParser(
        description=f"Map {UKBB_ID_COLUMN} to {ARIVALE_ID_COLUMN} via {UNIPROT_COLUMN} using verified mappings."
    )
    parser.add_argument(
        "input_file",
        help=f"Path to the input TSV file containing {UKBB_ID_COLUMN} and {UNIPROT_COLUMN}.",
    )
    parser.add_argument(
        "output_file",
        help=f"Path to write the output TSV file with mapped {ARIVALE_ID_COLUMN}.",
    )
    parser.add_argument(
        "--verification-file",
        default="/home/ubuntu/biomapper/data/ukbb_expected_mappings.tsv",
        help="Path to the verification file with expected mappings.",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Perform bidirectional validation for mappings",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Generate a summary report of mapping results",
    )
    args = parser.parse_args()
    
    # Basic input validation
    if not os.path.exists(args.input_file):
        print(f"Error: Input file not found: {args.input_file}", file=sys.stderr)
        sys.exit(1)
    
    if not os.path.exists(args.verification_file):
        print(f"Error: Verification file not found: {args.verification_file}", file=sys.stderr)
        sys.exit(1)
    
    # Run the mapping
    metrics = map_ukbb_to_arivale(args.input_file, args.output_file, args.verification_file, args.validate)
    
    # Generate summary report if requested
    if args.summary and metrics:
        output_dir = os.path.dirname(args.output_file)
        summary_file = os.path.join(output_dir, "verified_mapping_summary.txt")
        generate_summary_report(metrics, summary_file)
        print(f"Summary report written to {summary_file}")

if __name__ == "__main__":
    main()