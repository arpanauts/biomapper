"""
Test script for the enhanced bidirectional reconciliation implementation.

This script tests the bidirectional reconciliation functionality in phase3_bidirectional_reconciliation.py,
with a focus on verifying one-to-many mapping support in both directions.

Key test cases:
1. One UKBB entity mapping to multiple Arivale entities
2. One Arivale entity mapping to multiple UKBB entities 
3. Many-to-many mapping relationships
4. Edge cases and validation logic
"""

import os
import tempfile
import json
import pandas as pd
import unittest
from phase3_bidirectional_reconciliation import (
    create_mapping_indexes,
    perform_bidirectional_validation,
    get_dynamic_column_names,
    calculate_mapping_stats,
    VALIDATION_STATUS
)

class TestBidirectionalReconciliation(unittest.TestCase):
    """Test cases for bidirectional reconciliation with one-to-many support."""
    
    def setUp(self):
        """Set up test data for bidirectional reconciliation tests."""
        # Create temporary test directory
        self.test_dir = tempfile.mkdtemp()
        
        # Get column names
        self.column_names = get_dynamic_column_names("UKBB_Protein", "Arivale_Protein")
        
        # Create sample forward mapping data (UKBB -> Arivale)
        # Case 1: UKBB ID "IL18" maps to multiple Arivale IDs (CVD2_Q14116, INF_Q14116)
        # Case 2: UKBB ID "PTEN" maps to Arivale ID "CVD2_P60484"
        # Case 3: UKBB ID "TP53" has no mapping
        self.forward_data = {
            self.column_names['source_id']: ["IL18", "IL18", "PTEN", "TP53"],
            self.column_names['source_primary_ontology']: ["Q14116", "Q14116", "P60484", "P04637"],
            self.column_names['source_secondary_ontology']: ["IL18", "IL18", "PTEN", "TP53"],
            self.column_names['target_id']: ["CVD2_Q14116", "INF_Q14116", "CVD2_P60484", None],
            self.column_names['target_primary_ontology']: ["Q14116", "Q14116", "P60484", None],
            self.column_names['target_secondary_ontology']: ["IL18", "IL18", "PTEN", None],
            self.column_names['target_description']: [
                "interleukin 18 (interferon-gamma-inducing factor)",
                "interleukin 18 (interferon-gamma-inducing factor)",
                "phosphatase and tensin homolog",
                None
            ],
            self.column_names['mapping_method']: [
                "Direct Primary: UKBB UniProt -> Arivale Protein ID via Arivale Metadata",
                "Direct Primary: UKBB UniProt -> Arivale Protein ID via Arivale Metadata",
                "Direct Primary: UKBB UniProt -> Arivale Protein ID via Arivale Metadata",
                "No mapping found"
            ],
            self.column_names['mapping_path_details']: [
                json.dumps({"step": "Direct lookup in Arivale metadata using UKBB UniProt AC"}),
                json.dumps({"step": "Direct lookup in Arivale metadata using UKBB UniProt AC"}),
                json.dumps({"step": "Direct lookup in Arivale metadata using UKBB UniProt AC"}),
                None
            ],
            self.column_names['confidence_score']: [1.0, 1.0, 1.0, 0.0],
            self.column_names['hop_count']: [1, 1, 1, 0],
            self.column_names['notes']: [
                "Successfully mapped via direct UniProt AC match",
                "Successfully mapped via direct UniProt AC match",
                "Successfully mapped via direct UniProt AC match",
                "No Arivale match for UniProt AC P04637"
            ]
        }
        self.forward_df = pd.DataFrame(self.forward_data)
        
        # Create sample reverse mapping data (Arivale -> UKBB)
        # Case 1: Arivale ID "CVD2_Q14116" maps to UKBB ID "IL18"
        # Case 2: Arivale ID "INF_Q14116" maps to UKBB ID "IL18"
        # Case 3: Arivale ID "CVD2_P60484" maps to multiple UKBB IDs ("PTEN", "PTEN_alt")
        # Case 4: Arivale ID "INF_P60484" has no mapping
        self.reverse_data = {
            'arivale_protein_id': ["CVD2_Q14116", "INF_Q14116", "CVD2_P60484", "CVD2_P60484", "INF_P60484"],
            'arivale_uniprot_ac': ["Q14116", "Q14116", "P60484", "P60484", "P60484"],
            'arivale_gene_symbol': ["IL18", "IL18", "PTEN", "PTEN", "PTEN"],
            'arivale_protein_name': [
                "interleukin 18 (interferon-gamma-inducing factor)",
                "interleukin 18 (interferon-gamma-inducing factor)",
                "phosphatase and tensin homolog",
                "phosphatase and tensin homolog",
                "phosphatase and tensin homolog"
            ],
            'mapping_step_1_target_ukbb_assay': ["IL18", "IL18", "PTEN", "PTEN_alt", None],
            'mapping_method': [
                "Direct Primary: Arivale UniProt -> UKBB UniProt",
                "Direct Primary: Arivale UniProt -> UKBB UniProt",
                "Direct Primary: Arivale UniProt -> UKBB UniProt",
                "Direct Primary: Arivale UniProt -> UKBB UniProt",
                "No mapping found"
            ],
            'mapping_path_details_json': [
                json.dumps({"step": "Direct lookup using Arivale UniProt AC"}),
                json.dumps({"step": "Direct lookup using Arivale UniProt AC"}),
                json.dumps({"step": "Direct lookup using Arivale UniProt AC"}),
                json.dumps({"step": "Direct lookup using Arivale UniProt AC"}),
                None
            ],
            'confidence_score': [1.0, 1.0, 1.0, 1.0, 0.0],
            'hop_count': [1, 1, 1, 1, 0],
            'notes': [
                "Successfully mapped via direct UniProt AC match",
                "Successfully mapped via direct UniProt AC match",
                "Successfully mapped via direct UniProt AC match",
                "Successfully mapped via direct UniProt AC match",
                "No UKBB match for Arivale UniProt AC P60484"
            ]
        }
        self.reverse_df = pd.DataFrame(self.reverse_data)
    
    def test_create_mapping_indexes_one_to_many(self):
        """Test creation of mapping indexes with one-to-many support."""
        # Create mapping indexes with one-to-many support
        ukbb_to_arivale_index, arivale_to_ukbb_index = create_mapping_indexes(
            self.forward_df, self.reverse_df, self.column_names, support_one_to_many=True
        )
        
        # Verify UKBB -> Arivale index for one-to-many relationships
        self.assertIn("IL18", ukbb_to_arivale_index)
        self.assertIsInstance(ukbb_to_arivale_index["IL18"], list)
        self.assertEqual(len(ukbb_to_arivale_index["IL18"]), 2)
        
        # Verify that both Arivale targets are included for IL18
        arivale_ids = [mapping["arivale_id"] for mapping in ukbb_to_arivale_index["IL18"]]
        self.assertIn("CVD2_Q14116", arivale_ids)
        self.assertIn("INF_Q14116", arivale_ids)
        
        # Verify Arivale -> UKBB index for one-to-many relationships
        self.assertIn("CVD2_P60484", arivale_to_ukbb_index)
        self.assertIsInstance(arivale_to_ukbb_index["CVD2_P60484"], list)
        self.assertEqual(len(arivale_to_ukbb_index["CVD2_P60484"]), 2)
        
        # Verify that both UKBB targets are included for CVD2_P60484
        ukbb_ids = [mapping["ukbb_id"] for mapping in arivale_to_ukbb_index["CVD2_P60484"]]
        self.assertIn("PTEN", ukbb_ids)
        self.assertIn("PTEN_alt", ukbb_ids)
    
    def test_create_mapping_indexes_one_to_one(self):
        """Test creation of mapping indexes with one-to-one support (for backward compatibility)."""
        # Create mapping indexes with one-to-one support
        ukbb_to_arivale_index, arivale_to_ukbb_index = create_mapping_indexes(
            self.forward_df, self.reverse_df, self.column_names, support_one_to_many=False
        )
        
        # Verify UKBB -> Arivale index for one-to-one relationships
        self.assertIn("IL18", ukbb_to_arivale_index)
        self.assertIsInstance(ukbb_to_arivale_index["IL18"], dict)
        
        # Verify Arivale -> UKBB index for one-to-one relationships
        self.assertIn("CVD2_P60484", arivale_to_ukbb_index)
        self.assertIsInstance(arivale_to_ukbb_index["CVD2_P60484"], dict)
    
    def test_bidirectional_validation_one_to_many(self):
        """Test bidirectional validation with one-to-many support."""
        # Create mapping indexes with one-to-many support
        ukbb_to_arivale_index, arivale_to_ukbb_index = create_mapping_indexes(
            self.forward_df, self.reverse_df, self.column_names, support_one_to_many=True
        )
        
        # Perform bidirectional validation
        reconciled_df = perform_bidirectional_validation(
            self.forward_df, self.reverse_df, ukbb_to_arivale_index, arivale_to_ukbb_index, 
            self.column_names, support_one_to_many=True
        )
        
        # Test Case 1: Verify both mappings from IL18 are marked as bidirectional matches
        il18_rows = reconciled_df[reconciled_df[self.column_names['source_id']] == "IL18"]
        self.assertEqual(len(il18_rows), 2)
        
        for _, row in il18_rows.iterrows():
            self.assertEqual(
                row[self.column_names['validation_status']], 
                VALIDATION_STATUS['VALIDATED_BIDIRECTIONAL_EXACT']
            )
        
        # Test Case 2: Verify PTEN mapping is marked as bidirectional match
        pten_rows = reconciled_df[reconciled_df[self.column_names['source_id']] == "PTEN"]
        self.assertEqual(len(pten_rows), 1)
        self.assertEqual(
            pten_rows.iloc[0][self.column_names['validation_status']], 
            VALIDATION_STATUS['VALIDATED_BIDIRECTIONAL_EXACT']
        )
        
        # Test Case 3: Verify TP53 is marked as unmapped
        tp53_rows = reconciled_df[reconciled_df[self.column_names['source_id']] == "TP53"]
        self.assertEqual(len(tp53_rows), 1)
        self.assertEqual(
            tp53_rows.iloc[0][self.column_names['validation_status']], 
            VALIDATION_STATUS['UNMAPPED']
        )
        
        # Test Case 4: Verify PTEN_alt appears via reverse-only mapping
        pten_alt_rows = reconciled_df[reconciled_df[self.column_names['reverse_mapping_id']] == "PTEN_alt"]
        self.assertGreaterEqual(len(pten_alt_rows), 1)
        
        # Test Case 5: Verify INF_P60484 is included as unmapped Arivale entry
        inf_p60484_rows = reconciled_df[reconciled_df[self.column_names['target_id']] == "INF_P60484"]
        self.assertEqual(len(inf_p60484_rows), 1)
        self.assertEqual(
            inf_p60484_rows.iloc[0][self.column_names['validation_status']], 
            VALIDATION_STATUS['UNMAPPED']
        )
    
    def test_one_to_many_flags(self):
        """Test one-to-many relationship flags."""
        # Create mapping indexes with one-to-many support
        ukbb_to_arivale_index, arivale_to_ukbb_index = create_mapping_indexes(
            self.forward_df, self.reverse_df, self.column_names, support_one_to_many=True
        )
        
        # Perform bidirectional validation
        reconciled_df = perform_bidirectional_validation(
            self.forward_df, self.reverse_df, ukbb_to_arivale_index, arivale_to_ukbb_index, 
            self.column_names, support_one_to_many=True
        )
        
        # Verify one-to-many source flag for IL18
        il18_rows = reconciled_df[reconciled_df[self.column_names['source_id']] == "IL18"]
        for _, row in il18_rows.iterrows():
            self.assertTrue(row[self.column_names['is_one_to_many_source']])
        
        # Verify canonical mapping flag (should mark exactly one IL18 mapping as canonical)
        canonical_il18 = reconciled_df[
            (reconciled_df[self.column_names['source_id']] == "IL18") & 
            (reconciled_df[self.column_names['is_canonical_mapping']] == True)
        ]
        self.assertEqual(len(canonical_il18), 1)
    
    def test_mapping_stats(self):
        """Test calculation of mapping statistics."""
        # Create mapping indexes with one-to-many support
        ukbb_to_arivale_index, arivale_to_ukbb_index = create_mapping_indexes(
            self.forward_df, self.reverse_df, self.column_names, support_one_to_many=True
        )
        
        # Perform bidirectional validation
        reconciled_df = perform_bidirectional_validation(
            self.forward_df, self.reverse_df, ukbb_to_arivale_index, arivale_to_ukbb_index, 
            self.column_names, support_one_to_many=True
        )
        
        # Calculate mapping statistics
        mapping_stats = calculate_mapping_stats(reconciled_df, self.column_names)
        
        # Verify stats include expected metrics
        self.assertIn('total_mappings', mapping_stats)
        self.assertIn('unique_source_entities', mapping_stats)
        self.assertIn('unique_target_entities', mapping_stats)
        self.assertIn('validation_status_counts', mapping_stats)
        self.assertIn('one_to_many_source_mappings', mapping_stats)
        self.assertIn('one_to_many_target_mappings', mapping_stats)
        self.assertIn('canonical_mappings', mapping_stats)
        
        # Verify stats are calculated correctly
        self.assertEqual(mapping_stats['unique_source_entities'], 3)  # IL18, PTEN, TP53
        self.assertGreaterEqual(mapping_stats['canonical_mappings'], 3)  # At least one canonical mapping per source
    
    def test_real_world_example_il18(self):
        """Test the specific IL18/Q14116 example from the problem statement."""
        # Create a minimal dataset specifically for the IL18 example
        forward_data = {
            self.column_names['source_id']: ["IL18"],
            self.column_names['source_primary_ontology']: ["Q14116"],
            self.column_names['source_secondary_ontology']: ["IL18"],
            self.column_names['target_id']: ["CVD2_Q14116"],
            self.column_names['target_primary_ontology']: ["Q14116"],
            self.column_names['target_secondary_ontology']: ["IL18"],
            self.column_names['target_description']: ["interleukin 18 (interferon-gamma-inducing factor)"],
            self.column_names['mapping_method']: ["Direct Primary: UKBB UniProt -> Arivale Protein ID via Arivale Metadata"],
            self.column_names['mapping_path_details']: [json.dumps({"step": "Direct lookup in Arivale metadata using UKBB UniProt AC"})],
            self.column_names['confidence_score']: [1.0],
            self.column_names['hop_count']: [1],
            self.column_names['notes']: ["Successfully mapped via direct UniProt AC match"]
        }
        forward_df = pd.DataFrame(forward_data)
        
        reverse_data = {
            'arivale_protein_id': ["CVD2_Q14116", "INF_Q14116"],
            'arivale_uniprot_ac': ["Q14116", "Q14116"],
            'arivale_gene_symbol': ["IL18", "IL18"],
            'arivale_protein_name': [
                "interleukin 18 (interferon-gamma-inducing factor)",
                "interleukin 18 (interferon-gamma-inducing factor)"
            ],
            'mapping_step_1_target_ukbb_assay': ["IL18", "IL18"],
            'mapping_method': [
                "Direct Primary: Arivale UniProt -> UKBB UniProt",
                "Direct Primary: Arivale UniProt -> UKBB UniProt"
            ],
            'mapping_path_details_json': [
                json.dumps({"step": "Direct lookup using Arivale UniProt AC"}),
                json.dumps({"step": "Direct lookup using Arivale UniProt AC"})
            ],
            'confidence_score': [1.0, 1.0],
            'hop_count': [1, 1],
            'notes': [
                "Successfully mapped via direct UniProt AC match",
                "Successfully mapped via direct UniProt AC match"
            ]
        }
        reverse_df = pd.DataFrame(reverse_data)
        
        # Create mapping indexes with one-to-many support
        ukbb_to_arivale_index, arivale_to_ukbb_index = create_mapping_indexes(
            forward_df, reverse_df, self.column_names, support_one_to_many=True
        )
        
        # Verify INF_Q14116 appears in arivale_to_ukbb_index
        self.assertIn("INF_Q14116", arivale_to_ukbb_index)
        
        # Perform bidirectional validation
        reconciled_df = perform_bidirectional_validation(
            forward_df, reverse_df, ukbb_to_arivale_index, arivale_to_ukbb_index, 
            self.column_names, support_one_to_many=True
        )
        
        # Verify both CVD2_Q14116 and INF_Q14116 appear in the results
        targets = reconciled_df[self.column_names['target_id']].tolist()
        self.assertIn("CVD2_Q14116", targets)
        self.assertIn("INF_Q14116", targets)
        
        # Verify both are marked as bidirectional exact matches
        for _, row in reconciled_df.iterrows():
            if row[self.column_names['target_id']] == "INF_Q14116":
                self.assertEqual(
                    row[self.column_names['validation_status']], 
                    VALIDATION_STATUS['VALIDATED_BIDIRECTIONAL_EXACT']
                )

if __name__ == "__main__":
    unittest.main()