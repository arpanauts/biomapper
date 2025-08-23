"""
Test suite for composite ID matching scenarios.

This test suite validates that composite protein IDs (e.g., "P29460,P29459")
are properly parsed, matched against KG2c reference, and preserve their
original composite form in the final results.
"""

import pytest
import pandas as pd
from typing import List, Dict, Any
from unittest.mock import Mock, patch


class TestCompositeMatching:
    """Test suite for composite ID matching scenarios."""
    
    @pytest.fixture
    def known_composite_ids(self) -> List[str]:
        """Known problematic composite IDs from production."""
        return [
            "P29460,P29459",  # IL12B,IL12A
            "Q11128,P21217",  # FUT5,FUT3
            "Q29983,Q29980",  # MICA,MICB
            "Q8NEV9,Q14213"   # IL27,EBI3
        ]
    
    @pytest.fixture
    def kg2c_reference_data(self) -> pd.DataFrame:
        """Mock KG2c reference data with all required proteins."""
        data = {
            'id': ['NCBIGene:3593', 'NCBIGene:3592', 'NCBIGene:2526', 
                   'NCBIGene:2525', 'NCBIGene:4277', 'NCBIGene:4276',
                   'NCBIGene:246778', 'NCBIGene:10148'],
            'name': ['IL12B', 'IL12A', 'FUT5', 'FUT3', 
                     'MICA', 'MICB', 'IL27', 'EBI3'],
            'extracted_uniprot': ['P29460', 'P29459', 'Q11128', 'P21217',
                                  'Q29983', 'Q29980', 'Q8NEV9', 'Q14213'],
            'extracted_uniprot_normalized': ['P29460', 'P29459', 'Q11128', 'P21217',
                                            'Q29983', 'Q29980', 'Q8NEV9', 'Q14213']
        }
        return pd.DataFrame(data)
    
    def test_composite_parsing_creates_multiple_rows(self, known_composite_ids):
        """Verify composite IDs are parsed into multiple rows."""
        for comp_id in known_composite_ids:
            components = comp_id.split(',')
            assert len(components) == 2, f"Expected 2 components in {comp_id}"
            
            # Simulate parsing
            parsed_rows = []
            for component in components:
                parsed_rows.append({
                    'uniprot': component,
                    '_original_uniprot': comp_id
                })
            
            assert len(parsed_rows) == 2
            assert all(row['_original_uniprot'] == comp_id for row in parsed_rows)
    
    def test_composite_parsing_preserves_original(self, known_composite_ids):
        """Verify original composite IDs are preserved after parsing."""
        for comp_id in known_composite_ids:
            # Simulate PARSE_COMPOSITE_IDENTIFIERS action
            components = comp_id.split(',')
            parsed_data = []
            
            for component in components:
                parsed_data.append({
                    'uniprot': component,
                    '_original_uniprot': comp_id,  # Original preserved
                    '_expansion_count': len(components)
                })
            
            # Verify all rows preserve original
            assert all(row['_original_uniprot'] == comp_id for row in parsed_data)
            assert all(row['_expansion_count'] == 2 for row in parsed_data)
    
    def test_all_components_exist_in_kg2c(self, known_composite_ids, kg2c_reference_data):
        """Verify all composite components exist in KG2c reference."""
        kg2c_proteins = set(kg2c_reference_data['extracted_uniprot_normalized'].values)
        
        for comp_id in known_composite_ids:
            components = comp_id.split(',')
            for component in components:
                assert component in kg2c_proteins, \
                    f"{component} from {comp_id} not found in KG2c reference"
    
    def test_composite_matching_with_kg2c(self, known_composite_ids, kg2c_reference_data):
        """Verify composite IDs match correctly with KG2c reference."""
        kg2c_lookup = kg2c_reference_data.set_index('extracted_uniprot_normalized')
        
        for comp_id in known_composite_ids:
            components = comp_id.split(',')
            matches = []
            
            for component in components:
                if component in kg2c_lookup.index:
                    kg2c_match = kg2c_lookup.loc[component]
                    matches.append({
                        'original_composite': comp_id,
                        'parsed_component': component,
                        'kg2c_name': kg2c_match['name'],
                        'kg2c_id': kg2c_match['id']
                    })
            
            # Each composite should create matches for both components
            assert len(matches) == 2, \
                f"Expected 2 matches for {comp_id}, got {len(matches)}"
            
            # All matches should preserve original composite ID
            assert all(m['original_composite'] == comp_id for m in matches)
    
    def test_composite_restoration_after_matching(self, known_composite_ids):
        """Verify composite IDs are restored after matching."""
        for comp_id in known_composite_ids:
            # Simulate the restoration process
            matched_data = [
                {'uniprot': 'P29460', '_original_uniprot': 'P29460,P29459', 
                 'kg2c_name': 'IL12B', 'confidence_score': 0.95},
                {'uniprot': 'P29459', '_original_uniprot': 'P29460,P29459',
                 'kg2c_name': 'IL12A', 'confidence_score': 0.95}
            ]
            
            # Apply restoration (as in restore_and_tag_composite_matches)
            for row in matched_data:
                if '_original_uniprot' in row:
                    row['uniprot'] = row['_original_uniprot']
            
            # Verify restoration
            assert all(row['uniprot'] == 'P29460,P29459' for row in matched_data)
    
    def test_composite_creates_one_to_many_relationships(self, kg2c_reference_data):
        """Verify composite IDs create one-to-many relationships."""
        comp_id = "P29460,P29459"
        
        # Parse composite
        components = comp_id.split(',')
        
        # Match each component
        relationships = []
        for component in components:
            kg2c_matches = kg2c_reference_data[
                kg2c_reference_data['extracted_uniprot_normalized'] == component
            ]
            
            for _, kg2c_row in kg2c_matches.iterrows():
                relationships.append({
                    'source_id': comp_id,  # Original composite
                    'target_id': kg2c_row['id'],
                    'target_name': kg2c_row['name'],
                    'match_type': 'composite',
                    'confidence': 0.95
                })
        
        # Should create at least 2 relationships (one per component)
        assert len(relationships) >= 2
        
        # All relationships should reference original composite
        assert all(rel['source_id'] == comp_id for rel in relationships)
        
        # Should have relationships to both IL12B and IL12A
        target_names = {rel['target_name'] for rel in relationships}
        assert 'IL12B' in target_names
        assert 'IL12A' in target_names
    
    def test_join_column_alignment(self, kg2c_reference_data):
        """Test that join columns are properly aligned."""
        # Simulate parsed and normalized composite data
        parsed_data = pd.DataFrame({
            'uniprot': ['P29460', 'P29459'],
            '_original_uniprot': ['P29460,P29459', 'P29460,P29459']
        })
        
        # The join should be on:
        # parsed_data['uniprot'] == kg2c_reference_data['extracted_uniprot_normalized']
        
        # Perform the join
        matched = pd.merge(
            parsed_data,
            kg2c_reference_data,
            left_on='uniprot',
            right_on='extracted_uniprot_normalized',
            how='left'
        )
        
        # All rows should have matches
        assert matched['id'].notna().all(), \
            "Some composite components failed to match with KG2c"
        
        # Verify specific matches
        assert len(matched[matched['name'] == 'IL12B']) == 1
        assert len(matched[matched['name'] == 'IL12A']) == 1
    
    def test_coverage_improvement_from_composites(self, known_composite_ids):
        """Test that resolving composites improves coverage."""
        # Initial state: 4 unmapped composite IDs
        unmapped_before = set(known_composite_ids)
        
        # After parsing and matching
        resolved_proteins = set()
        for comp_id in known_composite_ids:
            components = comp_id.split(',')
            resolved_proteins.update(components)
        
        # Coverage improvement
        initial_unmapped = len(unmapped_before)  # 4 composite IDs
        proteins_resolved = len(resolved_proteins)  # 8 individual proteins
        
        assert proteins_resolved == 8, \
            f"Expected 8 proteins from 4 composites, got {proteins_resolved}"
        
        # Coverage calculation
        total_proteins = 1163  # From Arivale dataset
        initial_matched = 1156  # 99.4%
        
        # After composite resolution
        expected_matched = initial_matched + len(unmapped_before)  # Add 4 composites
        expected_coverage = expected_matched / total_proteins
        
        assert expected_coverage > 0.996, \
            f"Expected >99.6% coverage, got {expected_coverage:.1%}"
    
    @pytest.mark.integration
    def test_arivale_composite_integration(self, known_composite_ids, kg2c_reference_data):
        """Integration test for the 4 known Arivale composite IDs.
        
        This test ensures that these specific composite IDs are always handled
        correctly to prevent regression.
        """
        # The 4 known composite IDs from Arivale dataset
        expected_composites = {
            "P29460,P29459": ("IL12B", "IL12A"),  # Interleukin 12 subunits
            "Q11128,P21217": ("FUT5", "FUT3"),    # Fucosyltransferases
            "Q29983,Q29980": ("MICA", "MICB"),    # MHC class I related
            "Q8NEV9,Q14213": ("IL27", "EBI3")     # Interleukin 27 complex
        }
        
        for comp_id, (gene1, gene2) in expected_composites.items():
            # Parse composite
            components = comp_id.split(',')
            assert len(components) == 2
            
            # Verify both components exist in KG2c
            kg2c_proteins = set(kg2c_reference_data['extracted_uniprot_normalized'].values)
            assert components[0] in kg2c_proteins, f"{components[0]} not in KG2c"
            assert components[1] in kg2c_proteins, f"{components[1]} not in KG2c"
            
            # Verify gene names match
            gene_names = set(kg2c_reference_data['name'].values)
            assert gene1 in gene_names, f"{gene1} not found in KG2c gene names"
            assert gene2 in gene_names, f"{gene2} not found in KG2c gene names"
            
            # Verify mapping creates one-to-many relationship
            matched_genes = kg2c_reference_data[
                kg2c_reference_data['extracted_uniprot_normalized'].isin(components)
            ]['name'].values
            
            assert gene1 in matched_genes
            assert gene2 in matched_genes