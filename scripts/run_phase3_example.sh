#!/bin/bash

# Example command to run the phase3_bidirectional_reconciliation.py script with dynamic column names
# This uses sample files from the output directory

PHASE1_FILE="/home/ubuntu/biomapper/output/ukbb_to_arivale_path_fix_20250507_182543.tsv"
PHASE2_FILE="/home/ubuntu/biomapper/output/ukbb_to_arivale_with_reverse_20250507_183627.tsv"
OUTPUT_DIR="/home/ubuntu/biomapper/output/test_phase3_$(date +%Y%m%d_%H%M%S)"

# Create output directory
mkdir -p $OUTPUT_DIR

# Run the script with explicit column name arguments
python /home/ubuntu/biomapper/scripts/phase3_bidirectional_reconciliation.py \
    --phase1_results "$PHASE1_FILE" \
    --phase2_results "$PHASE2_FILE" \
    --output_dir "$OUTPUT_DIR" \
    --phase1_source_id_col "Assay" \
    --phase1_source_ontology_col "UniProt" \
    --phase1_mapped_id_col "ARIVALE_PROTEIN_ID" \
    --phase2_source_id_col "ARIVALE_PROTEIN_ID" \
    --phase2_source_ontology_col "UniProt" \
    --phase2_mapped_id_col "Assay"

echo "Results written to $OUTPUT_DIR"