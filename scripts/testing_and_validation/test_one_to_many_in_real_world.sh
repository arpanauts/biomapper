#!/bin/bash
# Test script to verify the one-to-many mapping fix in a real-world scenario

# Create a test output directory
OUTPUT_DIR="test_output/one_to_many_fix_test_$(date +%Y%m%d_%H%M%S)"
mkdir -p $OUTPUT_DIR

echo "Testing one-to-many mapping fix with real data..."
echo "Output will be saved to: $OUTPUT_DIR"

# 1. First, run the mapping from UKBB to Arivale with a small test set
echo "1. Running Phase 1: UKBB -> Arivale mapping..."
python /home/ubuntu/biomapper/scripts/map_ukbb_to_arivale.py \
  /home/ubuntu/biomapper/data/UKBB_Protein_Meta.tsv \
  $OUTPUT_DIR/phase1_ukbb_to_arivale_results.tsv \
  --source_endpoint "UKBB_Protein" \
  --target_endpoint "Arivale_Protein" \
  --input_id_column_name "UniProt" \
  --input_primary_key_column_name "Assay" \
  --output_mapped_id_column_name "ARIVALE_PROTEIN_ID" \
  --source_ontology_name "UNIPROTKB_AC" \
  --target_ontology_name "ARIVALE_PROTEIN_ID" \
  --summary

if [[ $? -ne 0 ]]; then
  echo "Error: Phase 1 mapping failed!"
  exit 1
fi

# 2. Run reverse mapping from Arivale to UKBB
echo "2. Running Phase 2: Arivale -> UKBB mapping..."
python /home/ubuntu/biomapper/scripts/map_ukbb_to_arivale.py \
  /home/ubuntu/biomapper/data/arivale_proteomics_metadata.tsv \
  $OUTPUT_DIR/phase2_arivale_to_ukbb_results.tsv \
  --source_endpoint "Arivale_Protein" \
  --target_endpoint "UKBB_Protein" \
  --input_id_column_name "uniprot" \
  --input_primary_key_column_name "name" \
  --output_mapped_id_column_name "UKBB_ASSAY_ID" \
  --source_ontology_name "UNIPROTKB_AC" \
  --target_ontology_name "UKBB_PROTEIN_ID" \
  --summary

if [[ $? -ne 0 ]]; then
  echo "Error: Phase 2 mapping failed!"
  exit 1
fi

# 3. Run bidirectional reconciliation
echo "3. Running Phase 3: Bidirectional reconciliation..."
python /home/ubuntu/biomapper/scripts/phase3_bidirectional_reconciliation.py \
  --phase1_results $OUTPUT_DIR/phase1_ukbb_to_arivale_results.tsv \
  --phase2_results $OUTPUT_DIR/phase2_arivale_to_ukbb_results.tsv \
  --output_dir $OUTPUT_DIR \
  --phase1_source_id_col "Assay" \
  --phase1_source_ontology_col "UniProt" \
  --phase1_mapped_id_col "ARIVALE_PROTEIN_ID" \
  --phase2_source_id_col "name" \
  --phase2_source_ontology_col "uniprot" \
  --phase2_mapped_id_col "UKBB_ASSAY_ID"

if [[ $? -ne 0 ]]; then
  echo "Error: Phase 3 reconciliation failed!"
  exit 1
fi

# 4. Analyze the results
echo "4. Analyzing results..."

# Calculate file sizes
PHASE1_SIZE=$(stat -c %s $OUTPUT_DIR/phase1_ukbb_to_arivale_results.tsv)
PHASE3_SIZE=$(stat -c %s $OUTPUT_DIR/phase3_bidirectional_reconciliation_results.tsv)

echo "Phase 1 output file size: $(($PHASE1_SIZE / 1024)) KB"
echo "Phase 3 output file size: $(($PHASE3_SIZE / 1024)) KB"

# Count rows in each file
PHASE1_ROWS=$(wc -l < $OUTPUT_DIR/phase1_ukbb_to_arivale_results.tsv)
PHASE3_ROWS=$(wc -l < $OUTPUT_DIR/phase3_bidirectional_reconciliation_results.tsv)

echo "Phase 1 rows: $PHASE1_ROWS"
echo "Phase 3 rows: $PHASE3_ROWS"

# Check for abnormally large semicolon-separated strings in Phase 3 output
echo "Checking for abnormally large semicolon-separated strings in Phase 3 output..."
LONG_STRINGS=$(awk -F'\t' 'BEGIN{max=0;col=0} NR==1{for(i=1;i<=NF;i++){if($i=="all_forward_mapped_target_ids"){col=i;break}}} col>0 && NR>1 && length($col)>1000{print "Long string found in row " NR ", length=" length($col)}' $OUTPUT_DIR/phase3_bidirectional_reconciliation_results.tsv)

if [[ -z "$LONG_STRINGS" ]]; then
  echo " No abnormally large strings found in the all_forward_mapped_target_ids column."
else
  echo " Found abnormally large strings:"
  echo "$LONG_STRINGS"
fi

# Sample some rows to see if one-to-many relationships are properly represented
echo "Sampling rows with one-to-many relationships from Phase 1 output..."
grep -v "^#" $OUTPUT_DIR/phase1_ukbb_to_arivale_results.tsv | head -1
# Find rows with the same UniProt ID (indicating one-to-many)
awk -F'\t' 'NR>1{a[$2]++}END{for(i in a){if(a[i]>1)print i, a[i]}}' $OUTPUT_DIR/phase1_ukbb_to_arivale_results.tsv | head -5 | while read uniprot count; do
  echo "UniProt $uniprot appears in $count rows (one-to-many relationship)"
  grep -v "^#" $OUTPUT_DIR/phase1_ukbb_to_arivale_results.tsv | grep -w "$uniprot" | head -3
done

echo "Test completed successfully!"
echo "Results can be found in $OUTPUT_DIR"