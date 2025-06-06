#!/usr/bin/env python
"""
Test the phase3_bidirectional_reconciliation.py script's enhanced bidirectional validation
capabilities that handle missing primary source identifiers by using parsed gene names as fallbacks.

This script creates synthetic test data with rows that:
1. Have a valid source ID and target ID (normal case)
2. Have a missing source ID but valid gene name and target ID (test case for fallback)
3. Have missing source ID and gene name (negative control)

Then it runs the reconciliation script on this data and verifies:
- Rows with valid source IDs are properly validated
- Rows with missing source IDs but valid gene names are properly validated using the fallback
- Rows with missing source IDs and gene names remain unmapped or unidirectional
"""

import os
import sys
import pandas as pd
import tempfile
import subprocess
import json
import argparse

def create_test_files():
    """Create synthetic test files for testing the bidirectional validation enhancement."""
    
    # Create a temporary directory for our test files
    temp_dir = tempfile.mkdtemp(prefix="bidirectional_validation_fallback_test_")
    
    # Phase 1 (forward) mapping test data
    phase1_data = {
        "source_ukbb_assay_raw": ["ID1", "ID2", None, None],
        "source_ukbb_uniprot_ac": ["P12345", "P67890", "P11111", None],
        "source_ukbb_parsed_gene_name": ["GENE1", "GENE2", "GENE3", None],
        "mapping_step_1_target_arivale_protein_id": ["ARIVALE1", "ARIVALE2", "ARIVALE3", "ARIVALE4"],
        "mapping_method": ["Direct", "Direct", "Direct", "Direct"],
        "confidence_score": [0.9, 0.8, 0.7, 0.6],
        "hop_count": [0, 0, 0, 0],
        "notes": ["", "", "", ""],
        "mapping_path_details_json": [None, None, None, None]
    }
    
    # Phase 2 (reverse) mapping test data
    phase2_data = {
        "mapping_step_1_target_arivale_protein_id": ["ARIVALE1", "ARIVALE2", "ARIVALE3", "ARIVALE4"],
        "arivale_uniprot_ac": ["P12345", "P67890", "P11111", "P99999"],
        "arivale_gene_symbol": ["GENE1", "GENE2", "GENE3", "GENE4"],
        "source_ukbb_assay_raw": ["ID1", "ID2", "GENE3", "ID4"],
        "mapping_method": ["Direct", "Direct", "Gene Name Match", "Direct"],
        "confidence_score": [0.9, 0.8, 0.7, 0.6],
        "hop_count": [0, 0, 0, 0],
        "notes": ["", "", "Matched by gene name", ""],
        "mapping_path_details_json": [None, None, None, None]
    }
    
    # Convert to DataFrames
    phase1_df = pd.DataFrame(phase1_data)
    phase2_df = pd.DataFrame(phase2_data)
    
    # Save to TSV files
    phase1_path = os.path.join(temp_dir, "phase1_results.tsv")
    phase2_path = os.path.join(temp_dir, "phase2_results.tsv")
    
    phase1_df.to_csv(phase1_path, sep='\t', index=False)
    phase2_df.to_csv(phase2_path, sep='\t', index=False)
    
    return temp_dir, phase1_path, phase2_path

def run_reconciliation(temp_dir, phase1_path, phase2_path):
    """Run the bidirectional reconciliation script on our test files."""
    
    # Construct the command
    cmd = [
        "python",
        "/home/ubuntu/biomapper/scripts/phase3_bidirectional_reconciliation.py",
        "--phase1_results", phase1_path,
        "--phase2_results", phase2_path,
        "--output_dir", temp_dir,
        "--phase1_source_id_col", "source_ukbb_assay_raw",
        "--phase1_source_ontology_col", "source_ukbb_uniprot_ac",
        "--phase1_mapped_id_col", "mapping_step_1_target_arivale_protein_id",
        "--phase2_source_id_col", "mapping_step_1_target_arivale_protein_id",
        "--phase2_source_ontology_col", "arivale_uniprot_ac",
        "--phase2_mapped_id_col", "source_ukbb_assay_raw"
    ]
    
    # Run the command
    try:
        result = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(f"Reconciliation completed successfully: {result.returncode}")
        print(f"Output saved to: {temp_dir}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error running reconciliation: {e}")
        print(f"STDOUT: {e.stdout.decode('utf-8')}")
        print(f"STDERR: {e.stderr.decode('utf-8')}")
        return False

def verify_results(temp_dir):
    """Verify that the reconciliation results match our expectations."""
    
    # Load reconciliation results
    results_path = os.path.join(temp_dir, "phase3_bidirectional_reconciliation_results.tsv")
    if not os.path.exists(results_path):
        print(f"ERROR: Results file not found: {results_path}")
        return False

    # Read the file content first to inspect
    with open(results_path, 'r') as f:
        content = f.readlines()

    # Skip the comment lines at the top (they start with #)
    data_lines = [line for line in content if not line.startswith('#')]
    header = data_lines[0]

    # Write only the data part to a temporary file
    temp_results_path = os.path.join(temp_dir, "temp_results.tsv")
    with open(temp_results_path, 'w') as f:
        f.writelines(data_lines)

    # Now read the cleaned file
    results_df = pd.read_csv(temp_results_path, sep='\t')
    
    # Print summary of results
    print("\nReconciliation Results Summary:")
    print(f"Total entries: {len(results_df)}")
    
    # Print status counts
    status_counts = results_df["bidirectional_validation_status"].value_counts()
    for status, count in status_counts.items():
        print(f"{status}: {count}")
    
    # Verify key test cases
    
    # Test case 1: Normal rows with source IDs should match properly
    id1_rows = results_df[results_df["source_ukbb_assay_raw"] == "ID1"]
    if len(id1_rows) == 0:
        print("ERROR: Test case 1 - ID1 row not found in results")
        return False
    
    id1_status = id1_rows.iloc[0]["bidirectional_validation_status"]
    if "Bidirectional" not in id1_status:
        print(f"ERROR: Test case 1 - ID1 has incorrect validation status: {id1_status}")
        return False
    print(f"PASS: Test case 1 - ID1 has expected bidirectional validation status: {id1_status}")
    
    # Test case 2: Rows with missing source ID but valid gene name should use fallback
    gene3_rows = results_df[results_df["source_ukbb_parsed_gene_name"] == "GENE3"]
    if len(gene3_rows) == 0:
        print("ERROR: Test case 2 - GENE3 row not found in results")
        return False
    
    gene3_status = gene3_rows.iloc[0]["bidirectional_validation_status"]
    if "Bidirectional" not in gene3_status:
        print(f"ERROR: Test case 2 - GENE3 has incorrect validation status: {gene3_status}")
        return False
    
    # Check validation details for gene name match evidence
    gene3_details = json.loads(gene3_rows.iloc[0]["bidirectional_validation_details"])
    if "gene_name_match" not in gene3_details or gene3_details.get("gene_name") != "GENE3":
        print(f"ERROR: Test case 2 - GENE3 validation details missing gene name match evidence: {gene3_details}")
        return False
    
    print(f"PASS: Test case 2 - GENE3 row correctly validated using gene name as fallback")
    print(f"  Validation status: {gene3_status}")
    print(f"  Validation details: {json.dumps(gene3_details, indent=2)}")
    
    # Test case 3: Row with missing source ID and no gene name should NOT be bidirectional
    arivale4_rows = results_df[results_df["mapping_step_1_target_arivale_protein_id"] == "ARIVALE4"]
    if len(arivale4_rows) == 0:
        print("ERROR: Test case 3 - ARIVALE4 row not found in results")
        return False
    
    arivale4_status = arivale4_rows.iloc[0]["bidirectional_validation_status"]
    if "Bidirectional" in arivale4_status:
        print(f"ERROR: Test case 3 - ARIVALE4 should not have bidirectional status, but has: {arivale4_status}")
        return False
    
    print(f"PASS: Test case 3 - ARIVALE4 correctly not identified as bidirectional")
    print(f"  Validation status: {arivale4_status}")
    
    return True

def cleanup(temp_dir):
    """Clean up test files."""
    # Keep files for inspection during testing
    print(f"Test files are available for inspection at: {temp_dir}")
    print("Files are not automatically deleted for debugging purposes.")

def main():
    parser = argparse.ArgumentParser(description="Test bidirectional validation enhancements.")
    parser.add_argument("--keep-files", action="store_true", help="Keep test files after running")
    args = parser.parse_args()
    
    print("Creating test files...")
    temp_dir, phase1_path, phase2_path = create_test_files()
    
    print("\nRunning bidirectional reconciliation...")
    if not run_reconciliation(temp_dir, phase1_path, phase2_path):
        sys.exit(1)
    
    print("\nVerifying results...")
    if not verify_results(temp_dir):
        sys.exit(1)
    
    print("\nAll tests passed successfully!")
    
    if not args.keep_files:
        cleanup(temp_dir)

if __name__ == "__main__":
    main()