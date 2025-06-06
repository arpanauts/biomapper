#!/bin/bash
# Test the fixed phase3 script with real data

set -e

echo "Testing phase3 with existing phase1 and phase2 outputs..."
echo "=================================================="

# Use existing test data
PHASE1_OUTPUT="/home/ubuntu/biomapper/scripts/test_output/one_to_many_fix_test_20250513_175053/phase1_ukbb_to_arivale_results.tsv"
PHASE2_OUTPUT="/home/ubuntu/biomapper/scripts/test_output/one_to_many_fix_test_20250513_175053/phase2_arivale_to_ukbb_results.tsv"
OUTPUT_DIR="/home/ubuntu/biomapper/scripts/test_output/fixed_flags_test_$(date +%Y%m%d_%H%M%S)"

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Run phase3 with the fixed script
echo "Running phase3 reconciliation with fixed flags..."
python /home/ubuntu/biomapper/scripts/phase3_bidirectional_reconciliation.py \
    --phase1_results "$PHASE1_OUTPUT" \
    --phase2_results "$PHASE2_OUTPUT" \
    --output_dir "$OUTPUT_DIR" \
    --phase1_source_id_col source_ukbb_raw_ukbb_id \
    --phase1_mapped_id_col arivale_protein_id \
    --phase1_source_ontology_col uniprot_ac \
    --phase2_source_id_col arivale_protein_id \
    --phase2_mapped_id_col ukbb_id \
    --phase2_source_ontology_col uniprot_ac

echo ""
echo "Checking flag distributions in the output..."
echo "============================================"

# Check the is_one_to_many_target distribution
echo ""
echo "is_one_to_many_target distribution:"
tail -n +4 "$OUTPUT_DIR/phase3_bidirectional_reconciliation_results.tsv" | \
    awk -F'\t' '{print $25}' | sort | uniq -c

echo ""
echo "is_one_to_many_source distribution:"
tail -n +4 "$OUTPUT_DIR/phase3_bidirectional_reconciliation_results.tsv" | \
    awk -F'\t' '{print $24}' | sort | uniq -c

echo ""
echo "Comparison with original buggy output:"
echo "Original: 2157 True, 766 False for is_one_to_many_target (73.8% True)"
echo "Fixed: See above (should be much more balanced)"

echo ""
echo "Output saved to: $OUTPUT_DIR"