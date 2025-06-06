#!/bin/bash

# Test script for the enhanced phase3_bidirectional_reconciliation.py
# This script tests the enhanced version with dynamic column names and one-to-many support

# Set paths
SCRIPT_DIR=$(dirname "$(readlink -f "$0")")
OUTPUT_DIR="$SCRIPT_DIR/../output/test_phase3_enhanced_$(date +%Y%m%d_%H%M%S)"
PHASE1_FILE="$SCRIPT_DIR/../output/ukbb_to_arivale_path_fix_20250507_182543.tsv"
PHASE2_FILE="$SCRIPT_DIR/../output/ukbb_to_arivale_with_reverse_20250507_183627.tsv"

# Create output directory
mkdir -p "$OUTPUT_DIR"

echo "Testing enhanced phase3_bidirectional_reconciliation.py with dynamic column names..."
echo "Phase 1 input: $PHASE1_FILE"
echo "Phase 2 input: $PHASE2_FILE"
echo "Output directory: $OUTPUT_DIR"
echo

# Run the script with explicit column name arguments
python "$SCRIPT_DIR/phase3_bidirectional_reconciliation.py" \
    --phase1_results "$PHASE1_FILE" \
    --phase2_results "$PHASE2_FILE" \
    --output_dir "$OUTPUT_DIR" \
    --phase1_source_id_col "Assay" \
    --phase1_source_ontology_col "UniProt" \
    --phase1_mapped_id_col "ARIVALE_PROTEIN_ID" \
    --phase2_source_id_col "ARIVALE_PROTEIN_ID" \
    --phase2_source_ontology_col "UniProt" \
    --phase2_mapped_id_col "Assay"

# Check if the reconciliation succeeded
if [ $? -eq 0 ]; then
    echo
    echo "Reconciliation completed successfully!"
    
    # Check if the output file was created
    OUTPUT_FILE="$OUTPUT_DIR/phase3_bidirectional_reconciliation_results.tsv"
    if [ -f "$OUTPUT_FILE" ]; then
        echo "Output file created: $OUTPUT_FILE"
        
        # Display the header of the output file to verify columns
        echo
        echo "Output file column headers:"
        head -n 1 "$OUTPUT_FILE" | grep -v "^#" | tr '\t' '\n' | nl
        
        # Check for the new columns
        echo
        echo "Checking for new columns..."
        if grep -q "all_forward_mapped_target_ids" "$OUTPUT_FILE"; then
            echo "✓ all_forward_mapped_target_ids column found!"
        else
            echo "✗ all_forward_mapped_target_ids column not found!"
        fi
        
        if grep -q "all_reverse_mapped_source_ids" "$OUTPUT_FILE"; then
            echo "✓ all_reverse_mapped_source_ids column found!"
        else
            echo "✗ all_reverse_mapped_source_ids column not found!"
        fi
        
        # Count rows with multiple mappings
        echo
        echo "Checking for one-to-many relationships..."
        FORWARD_MULTIPLE=$(grep -v "^#" "$OUTPUT_FILE" | awk -F'\t' '{print $0}' | grep -c ";")
        echo "Rows with potential multiple mappings: $FORWARD_MULTIPLE"
        
        # Examine a sample of rows with multiple mappings
        echo
        echo "Sample of rows with multiple mappings:"
        grep -v "^#" "$OUTPUT_FILE" | grep ";" | head -n 3
    else
        echo "Error: Output file was not created!"
    fi
else
    echo "Error: Reconciliation failed!"
fi

echo
echo "Test completed."