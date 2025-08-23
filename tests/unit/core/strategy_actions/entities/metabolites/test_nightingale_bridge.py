"""
TDD test suite for METABOLITE_NIGHTINGALE_BRIDGE action.
Tests both ID-based entries (45) and name-only entries (205) from Nightingale.
"""

import pytest
import pandas as pd
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, List

from actions.typed_base import TypedStrategyAction
from core.models.execution_context import StrategyExecutionContext


class TestMetaboliteNightingaleBridge:
    """Test suite for Nightingale metabolite bridge action following TDD principles."""
    
    @pytest.fixture
    def mock_context(self):
        """Create a mock execution context."""
        context = Mock(spec=StrategyExecutionContext)
        context.get_action_data = Mock(return_value={})
        context.set_action_data = Mock()
        return context
    
    @pytest.fixture
    def nightingale_csv_path(self):
        """Path to Nightingale CSV file."""
        return Path("/home/ubuntu/biomapper/data/nightingale/Nightingale-Health-CoreMetabolomics-Blood-CVs-PubChemIDs.csv")
    
    @pytest.fixture
    def sample_nightingale_data(self):
        """Sample data mimicking Nightingale CSV structure."""
        return pd.DataFrame({
            'CSV_column_name': [
                'Total_FC', 'Glucose', 'Lactate', 'DHA', 'Total_C',
                'HDL_C', 'LDL_C', 'VLDL_C', 'Omega_3', 'ApoB'
            ],
            'Biomarker_name': [
                'Total free cholesterol', 'Glucose', 'Lactate', 
                'Docosahexaenoic acid', 'Total cholesterol',
                'HDL cholesterol', 'LDL cholesterol', 'VLDL cholesterol',
                'Omega-3 fatty acids', 'Apolipoprotein B'
            ],
            'PubChem_ID': [
                '5997', '5793', '91435', '445580', '',
                '', '', '', '', ''
            ],
            'CAS_CHEBI_or_Uniprot_ID': [
                'CHEBI: 16113', '', '', '', 'CHEBI: 50404',
                'CHEBI: 47775', 'CHEBI: 47774', 'CHEBI: 47773',
                'CHEBI: 25681', 'Uniprot: P04114'
            ]
        })
    
    # Test Stage 1: Metabolites with IDs (45 entries)
    
    def test_stage1_pubchem_id_extraction(self, sample_nightingale_data):
        """Test extraction of PubChem IDs with confidence 0.98."""
        # RED: Test fails because action doesn't exist yet
        from actions.entities.metabolites.identification.nightingale_bridge import (
            MetaboliteNightingaleBridge, NightingaleBridgeParams
        )
        
        params = NightingaleBridgeParams(
            csv_file_path="/home/ubuntu/biomapper/data/nightingale/Nightingale-Health-CoreMetabolomics-Blood-CVs-PubChemIDs.csv",
            output_key="nightingale_matched",
            unmapped_key="nightingale_unmapped"
        )
        
        action = MetaboliteNightingaleBridge()
        
        # Mock file reading
        with patch('pandas.read_csv', return_value=sample_nightingale_data):
            result = action.extract_pubchem_ids(sample_nightingale_data)
        
        # Assertions
        assert len(result) == 4  # 4 entries have PubChem IDs
        assert all(m['confidence'] == 0.98 for m in result)
        assert result[0]['pubchem_id'] == '5997'
        assert result[0]['name'] == 'Total free cholesterol'
    
    def test_stage1_chebi_id_extraction(self, sample_nightingale_data):
        """Test extraction of CHEBI IDs with confidence 0.95."""
        from actions.entities.metabolites.identification.nightingale_bridge import (
            MetaboliteNightingaleBridge
        )
        
        action = MetaboliteNightingaleBridge()
        result = action.extract_chebi_ids(sample_nightingale_data)
        
        # Should extract CHEBI IDs and parse format
        assert len(result) == 5  # 5 CHEBI entries (excluding Uniprot)
        assert all(m['confidence'] == 0.95 for m in result)
        assert result[0]['chebi_id'] == '16113'  # Parsed from "CHEBI: 16113"
        assert result[0]['name'] == 'Total free cholesterol'
    
    def test_stage1_combined_id_extraction(self, sample_nightingale_data):
        """Test that PubChem takes priority over CHEBI when both exist."""
        from actions.entities.metabolites.identification.nightingale_bridge import (
            MetaboliteNightingaleBridge
        )
        
        action = MetaboliteNightingaleBridge()
        result = action.extract_all_ids(sample_nightingale_data)
        
        # Total_FC has both PubChem (5997) and CHEBI (16113)
        total_fc = [m for m in result if m['name'] == 'Total free cholesterol'][0]
        assert total_fc['pubchem_id'] == '5997'
        assert total_fc['chebi_id'] == '16113'
        assert total_fc['confidence'] == 0.98  # PubChem confidence takes priority
    
    # Test Stage 1: Name-only entries (205 entries)
    
    def test_stage1_name_only_extraction(self, sample_nightingale_data):
        """Test extraction of name-only entries for Stage 2 processing."""
        from actions.entities.metabolites.identification.nightingale_bridge import (
            MetaboliteNightingaleBridge
        )
        
        action = MetaboliteNightingaleBridge()
        matched, unmapped = action.process_nightingale_data(sample_nightingale_data)
        
        # Omega_3 has no PubChem ID but has CHEBI
        # ApoB has Uniprot (not metabolite) - should be unmapped
        assert 'Apolipoprotein B' in [m['name'] for m in unmapped]
        assert len(unmapped) == 1  # Only ApoB should be unmapped at this stage
    
    def test_stage1_name_standardization(self):
        """Test standardization of metabolite names for semantic matching."""
        from actions.entities.metabolites.identification.nightingale_bridge import (
            MetaboliteNightingaleBridge
        )
        
        action = MetaboliteNightingaleBridge()
        
        # Test various name formats
        assert action.standardize_name('HDL_C') == 'HDL cholesterol'
        assert action.standardize_name('Total-C') == 'Total cholesterol'
        assert action.standardize_name('Omega_3_pct') == 'Omega-3 percentage'
        assert action.standardize_name('bOHbutyrate') == 'beta-hydroxybutyrate'
    
    # Test confidence scoring
    
    def test_confidence_scoring_hierarchy(self):
        """Test that confidence scores follow the defined hierarchy."""
        from actions.entities.metabolites.identification.nightingale_bridge import (
            MetaboliteNightingaleBridge
        )
        
        action = MetaboliteNightingaleBridge()
        
        # Defined hierarchy
        assert action.PUBCHEM_CONFIDENCE == 0.98
        assert action.CHEBI_CONFIDENCE == 0.95
        assert action.NAME_EXACT_CONFIDENCE == 0.90
        assert action.NAME_FUZZY_CONFIDENCE == 0.80
    
    # Test edge cases
    
    def test_edge_case_empty_csv(self):
        """Test handling of empty CSV file."""
        from actions.entities.metabolites.identification.nightingale_bridge import (
            MetaboliteNightingaleBridge
        )
        
        action = MetaboliteNightingaleBridge()
        empty_df = pd.DataFrame()
        
        matched, unmapped = action.process_nightingale_data(empty_df)
        assert len(matched) == 0
        assert len(unmapped) == 0
    
    def test_edge_case_malformed_chebi(self):
        """Test handling of malformed CHEBI identifiers."""
        from actions.entities.metabolites.identification.nightingale_bridge import (
            MetaboliteNightingaleBridge
        )
        
        action = MetaboliteNightingaleBridge()
        
        # Various CHEBI formats
        assert action.parse_chebi_id('CHEBI: 12345') == '12345'
        assert action.parse_chebi_id('CHEBI:12345') == '12345'
        assert action.parse_chebi_id('chebi:12345') == '12345'
        assert action.parse_chebi_id('12345') == '12345'
        assert action.parse_chebi_id('invalid') is None
    
    def test_edge_case_duplicate_entries(self):
        """Test handling of duplicate metabolite entries."""
        from actions.entities.metabolites.identification.nightingale_bridge import (
            MetaboliteNightingaleBridge
        )
        
        df_with_duplicates = pd.DataFrame({
            'CSV_column_name': ['Glucose', 'Glucose', 'Glucose'],
            'Biomarker_name': ['Glucose', 'Glucose', 'D-Glucose'],
            'PubChem_ID': ['5793', '5793', ''],
            'CAS_CHEBI_or_Uniprot_ID': ['', 'CHEBI: 17234', 'CHEBI: 17234']
        })
        
        action = MetaboliteNightingaleBridge()
        matched, unmapped = action.process_nightingale_data(df_with_duplicates)
        
        # Should deduplicate and keep highest confidence
        glucose_matches = [m for m in matched if 'Glucose' in m['name']]
        assert len(glucose_matches) == 1
        assert glucose_matches[0]['confidence'] == 0.98  # PubChem confidence
    
    # Test performance requirements
    
    def test_performance_250_metabolites(self, nightingale_csv_path):
        """Test that processing 250 metabolites completes in <1 second."""
        import time
        from actions.entities.metabolites.identification.nightingale_bridge import (
            MetaboliteNightingaleBridge
        )
        
        action = MetaboliteNightingaleBridge()
        
        # Use actual Nightingale CSV if it exists
        if nightingale_csv_path.exists():
            start_time = time.time()
            df = pd.read_csv(nightingale_csv_path)
            matched, unmapped = action.process_nightingale_data(df)
            elapsed = time.time() - start_time
            
            assert elapsed < 1.0, f"Processing took {elapsed:.2f}s, should be <1s"
            assert len(matched) + len(unmapped) == len(df)
    
    # Test integration with execution context
    
    @pytest.mark.asyncio
    async def test_execute_typed_integration(self, mock_context):
        """Test full execution within the typed action framework."""
        from actions.entities.metabolites.identification.nightingale_bridge import (
            MetaboliteNightingaleBridge, NightingaleBridgeParams, NightingaleBridgeResult
        )
        
        params = NightingaleBridgeParams(
            csv_file_path="/home/ubuntu/biomapper/data/nightingale/test.csv",
            output_key="nightingale_matched",
            unmapped_key="nightingale_unmapped"
        )
        
        action = MetaboliteNightingaleBridge()
        
        # Mock CSV reading
        mock_df = pd.DataFrame({
            'CSV_column_name': ['Glucose'],
            'Biomarker_name': ['Glucose'],
            'PubChem_ID': ['5793'],
            'CAS_CHEBI_or_Uniprot_ID': ['']
        })
        
        with patch('pandas.read_csv', return_value=mock_df):
            result = await action.execute_typed(
                current_identifiers=[],
                current_ontology_type='metabolite',
                params=params,
                source_endpoint=None,
                target_endpoint=None,
                context=mock_context
            )
        
        assert isinstance(result, NightingaleBridgeResult)
        assert result.success
        assert result.total_processed == 1
        assert result.matched_with_ids == 1
        assert result.name_only_for_stage2 == 0
    
    # Test statistics tracking
    
    @pytest.mark.asyncio
    async def test_statistics_tracking(self, mock_context, sample_nightingale_data):
        """Test that statistics are properly tracked for progressive framework."""
        from actions.entities.metabolites.identification.nightingale_bridge import (
            MetaboliteNightingaleBridge, NightingaleBridgeParams
        )
        
        params = NightingaleBridgeParams(
            csv_file_path="test.csv",
            output_key="matched",
            unmapped_key="unmapped",
            track_statistics=True
        )
        
        action = MetaboliteNightingaleBridge()
        
        with patch('pandas.read_csv', return_value=sample_nightingale_data):
            result = await action.execute_typed(
                current_identifiers=[],
                current_ontology_type='metabolite',
                params=params,
                source_endpoint=None,
                target_endpoint=None,
                context=mock_context
            )
        
        # Check statistics were set in context
        mock_context.set_action_data.assert_called()
        call_args = mock_context.set_action_data.call_args_list
        
        # Find the statistics call
        stats_call = [c for c in call_args if c[0][0] == 'statistics']
        assert len(stats_call) > 0
        
        stats = stats_call[0][0][1]
        assert 'nightingale_bridge' in stats
        assert stats['nightingale_bridge']['stage'] == 1
        assert stats['nightingale_bridge']['coverage'] > 0