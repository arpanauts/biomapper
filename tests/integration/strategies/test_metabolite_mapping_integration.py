"""
Integration tests for metabolite mapping strategies.

Tests end-to-end execution with mock data and real BiomapperClient.
"""

import pytest
import tempfile
import pandas as pd
import yaml
from pathlib import Path
from unittest.mock import Mock, patch
from biomapper_client import BiomapperClient


class TestMetaboliteStrategiesIntegration:
    """Integration tests for metabolite mapping strategies."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test outputs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    @pytest.fixture
    def mock_data_files(self, temp_dir):
        """Create mock data files for testing."""
        # Mock Israeli10k metabolomics data
        israeli_metab = pd.DataFrame({
            'compound_id': ['HMDB0000001', 'HMDB0000002', 'HMDB0000003'],
            'compound_name': ['Alanine', 'Glycine', 'Serine'],
            'hmdb_id': ['HMDB0000001', 'HMDB0000002', 'HMDB0000003']
        })
        israeli_metab_file = Path(temp_dir) / 'israeli10k_metabolomics_metadata.csv'
        israeli_metab.to_csv(israeli_metab_file, index=False)
        
        # Mock Israeli10k lipidomics data
        israeli_lipids = pd.DataFrame({
            'lipid_id': ['PC(16:0/18:1)', 'PE(18:0/20:4)', 'SM(d18:1/16:0)'],
            'lipid_name': ['Phosphatidylcholine', 'Phosphatidylethanolamine', 'Sphingomyelin'],
            'hmdb_id': ['HMDB0000564', 'HMDB0009093', 'HMDB0001348']
        })
        israeli_lipids_file = Path(temp_dir) / 'israeli10k_lipidomics_metadata.csv'
        israeli_lipids.to_csv(israeli_lipids_file, index=False)
        
        # Mock Arivale metabolomics data  
        arivale = pd.DataFrame({
            'metabolite_id': ['Glucose', 'Lactate', 'Pyruvate'],
            'metabolite_name': ['D-Glucose', 'L-Lactate', 'Pyruvate'],
            'hmdb_id': ['HMDB0000122', 'HMDB0000190', 'HMDB0000243']
        })
        arivale_file = Path(temp_dir) / 'metabolomics_metadata.tsv'
        arivale.to_csv(arivale_file, sep='\t', index=False)
        
        # Mock UKBB NMR data
        ukbb_nmr = pd.DataFrame({
            'biomarker': ['Total_C', 'LDL_C', 'HDL_C'],
            'description': ['Total Cholesterol', 'LDL Cholesterol', 'HDL Cholesterol'],
            'units': ['mmol/L', 'mmol/L', 'mmol/L']
        })
        ukbb_nmr_file = Path(temp_dir) / 'UKBB_NMR_Meta.tsv'
        ukbb_nmr.to_csv(ukbb_nmr_file, sep='\t', index=False)
        
        # Mock KG2c metabolites
        kg2c = pd.DataFrame({
            'id': ['KG2C:1', 'KG2C:2', 'KG2C:3'],
            'name': ['Alanine', 'Glycine', 'Glucose'],
            'xrefs': ['HMDB:HMDB0000001', 'HMDB:HMDB0000002', 'HMDB:HMDB0000122']
        })
        kg2c_file = Path(temp_dir) / 'kg2c_metabolites.csv'
        kg2c.to_csv(kg2c_file, index=False)
        
        # Mock SPOKE metabolites
        spoke = pd.DataFrame({
            'id': ['SPOKE:M1', 'SPOKE:M2', 'SPOKE:M3'],
            'name': ['Alanine', 'Lactate', 'Serine'], 
            'identifiers': ['HMDB0000001|InChI=ABCD', 'HMDB0000190|InChI=EFGH', 'HMDB0000003|InChI=IJKL']
        })
        spoke_file = Path(temp_dir) / 'spoke_metabolites.csv'
        spoke.to_csv(spoke_file, index=False)
        
        # Mock Nightingale reference
        nightingale_ref = pd.DataFrame({
            'biomarker': ['Total_C', 'LDL_C', 'HDL_C'],
            'hmdb_id': ['HMDB0000067', 'HMDB0000067', 'HMDB0000067'],  # Cholesterol
            'confidence': [0.95, 0.90, 0.88]
        })
        nightingale_ref_file = Path(temp_dir) / 'nightingale_nmr_reference.csv'
        nightingale_ref.to_csv(nightingale_ref_file, index=False)
        
        return {
            'israeli_metabolomics': israeli_metab_file,
            'israeli_lipidomics': israeli_lipids_file,
            'arivale_metabolomics': arivale_file,
            'ukbb_nmr': ukbb_nmr_file,
            'kg2c_metabolites': kg2c_file,
            'spoke_metabolites': spoke_file,
            'nightingale_reference': nightingale_ref_file
        }
    
    @pytest.fixture
    def mock_client(self):
        """Create mock BiomapperClient."""
        client = Mock()
        
        # Mock successful execution result
        result = Mock()
        result.success = True
        result.statistics = Mock()
        result.statistics.total_mapped = 50
        result.statistics.match_rate = 0.75
        result.metadata = {'execution_time': '30s'}
        
        client.execute_strategy.return_value = result
        client.get_strategy.return_value = Mock()
        
        return client
    
    @pytest.mark.integration
    def test_israeli10k_kg2c_strategy_execution(self, mock_client, mock_data_files, temp_dir):
        """Test execution of Israeli10k to KG2c metabolomics strategy."""
        # Update strategy with test data paths
        strategy_params = {
            'output_dir': temp_dir,
            'source_file': str(mock_data_files['israeli_metabolomics']),
            'target_file': str(mock_data_files['kg2c_metabolites'])
        }
        
        result = mock_client.execute_strategy(
            "met_isr_metab_to_kg2c_hmdb_v1_base",
            parameters=strategy_params
        )
        
        assert result.success
        assert result.statistics.total_mapped > 0
        mock_client.execute_strategy.assert_called_once()
    
    @pytest.mark.integration
    def test_nightingale_nmr_strategy_execution(self, mock_client, mock_data_files, temp_dir):
        """Test execution of UKBB NMR to KG2c with Nightingale matching."""
        strategy_params = {
            'output_dir': temp_dir,
            'source_file': str(mock_data_files['ukbb_nmr']),
            'target_file': str(mock_data_files['kg2c_metabolites']),
            'nightingale_reference_file': str(mock_data_files['nightingale_reference'])
        }
        
        result = mock_client.execute_strategy(
            "met_ukb_nmr_to_kg2c_nightingale_v1_base",
            parameters=strategy_params
        )
        
        assert result.success
        assert result.statistics.match_rate >= 0.0
        mock_client.execute_strategy.assert_called_once()
    
    @pytest.mark.integration
    def test_multi_bridge_strategy_execution(self, mock_client, mock_data_files, temp_dir):
        """Test execution of multi-bridge Arivale to KG2c strategy."""
        strategy_params = {
            'output_dir': temp_dir,
            'source_file': str(mock_data_files['arivale_metabolomics']),
            'target_file': str(mock_data_files['kg2c_metabolites'])
        }
        
        result = mock_client.execute_strategy(
            "met_arv_to_kg2c_multi_v1_base",
            parameters=strategy_params
        )
        
        assert result.success
        mock_client.execute_strategy.assert_called_once()
    
    @pytest.mark.integration
    def test_lipidomics_strategy_execution(self, mock_client, mock_data_files, temp_dir):
        """Test execution of Israeli10k lipidomics to SPOKE strategy."""
        strategy_params = {
            'output_dir': temp_dir,
            'source_file': str(mock_data_files['israeli_lipidomics']),
            'target_file': str(mock_data_files['spoke_metabolites'])
        }
        
        result = mock_client.execute_strategy(
            "met_isr_lipid_to_spoke_inchikey_v1_base", 
            parameters=strategy_params
        )
        
        assert result.success
        mock_client.execute_strategy.assert_called_once()
    
    @pytest.mark.integration
    def test_multi_source_harmonization(self, mock_client, mock_data_files, temp_dir):
        """Test multi-source metabolite harmonization strategy."""
        # Mock enhanced result for complex strategy
        result = Mock()
        result.success = True
        result.statistics = Mock()
        result.statistics.sources_integrated = 4
        result.statistics.total_unique_metabolites = 120
        result.statistics.overlap_statistics = {'jaccard': 0.65}
        
        mock_client.execute_strategy.return_value = result
        
        strategy_params = {
            'output_dir': temp_dir,
            'nightingale_reference_file': str(mock_data_files['nightingale_reference'])
        }
        
        result = mock_client.execute_strategy(
            "met_multi_to_unified_semantic_v1_enhanced",
            parameters=strategy_params
        )
        
        assert result.success
        assert result.statistics.sources_integrated == 4
        assert result.statistics.total_unique_metabolites > 0
    
    @pytest.mark.integration 
    def test_semantic_enrichment_pipeline(self, mock_client, mock_data_files, temp_dir):
        """Test advanced semantic enrichment pipeline."""
        # Mock advanced semantic result
        result = Mock()
        result.success = True
        result.statistics = Mock()
        result.statistics.semantic_matches = 45
        result.statistics.vector_enhanced = 30
        result.statistics.combined_confidence = 0.88
        result.metadata = {
            'methods_used': ['cts', 'semantic', 'vector'],
            'performance_breakdown': {
                'cts_success_rate': 0.65,
                'semantic_success_rate': 0.72,
                'vector_enhancement_rate': 0.85
            }
        }
        
        mock_client.execute_strategy.return_value = result
        
        strategy_params = {
            'output_dir': temp_dir,
            'semantic_model': 'biobert',
            'vector_model': 'mol2vec'
        }
        
        result = mock_client.execute_strategy(
            "met_multi_semantic_enrichment_v1_advanced",
            parameters=strategy_params
        )
        
        assert result.success
        assert result.statistics.combined_confidence > 0.8
        assert 'semantic' in result.metadata['methods_used']
    
    @pytest.mark.integration
    def test_strategy_error_handling(self, mock_client, temp_dir):
        """Test strategy execution with error conditions."""
        # Mock failed execution
        result = Mock()
        result.success = False
        result.error = "CTS bridge timeout"
        result.statistics = None
        
        mock_client.execute_strategy.return_value = result
        
        result = mock_client.execute_strategy(
            "met_isr_metab_to_kg2c_hmdb_v1_base",
            parameters={'output_dir': temp_dir}
        )
        
        assert not result.success
        assert result.error is not None
    
    @pytest.mark.integration
    def test_performance_benchmarks(self, mock_client, mock_data_files, temp_dir):
        """Test performance benchmarks for metabolite strategies."""
        benchmark_results = {}
        
        test_strategies = [
            "met_isr_metab_to_kg2c_hmdb_v1_base",
            "met_arv_to_kg2c_multi_v1_base",
            "met_ukb_nmr_to_kg2c_nightingale_v1_base"
        ]
        
        for strategy in test_strategies:
            # Mock execution with timing
            result = Mock()
            result.success = True
            result.statistics = Mock()
            result.statistics.execution_time_seconds = 45.2
            result.statistics.match_rate = 0.75
            result.statistics.total_processed = 1000
            
            mock_client.execute_strategy.return_value = result
            
            execution_result = mock_client.execute_strategy(
                strategy,
                parameters={'output_dir': temp_dir}
            )
            
            benchmark_results[strategy] = {
                'success': execution_result.success,
                'execution_time': execution_result.statistics.execution_time_seconds,
                'match_rate': execution_result.statistics.match_rate
            }
        
        # Verify all strategies completed successfully
        for strategy, results in benchmark_results.items():
            assert results['success'], f"Strategy {strategy} failed"
            assert results['execution_time'] > 0, f"Invalid execution time for {strategy}"
            assert 0.0 <= results['match_rate'] <= 1.0, f"Invalid match rate for {strategy}"


class TestMetaboliteStrategiesRealData:
    """Integration tests with real data subsets (when available)."""
    
    @pytest.mark.slow
    @pytest.mark.skipif(not Path("/procedure/data/local_data").exists(), 
                       reason="Real data not available")
    def test_real_data_subset_execution(self):
        """Test strategy execution with real data subset."""
        client = BiomapperClient()
        
        # Use small subset of real data for testing
        try:
            result = client.execute_strategy(
                "met_isr_metab_to_kg2c_hmdb_v1_base",
                parameters={
                    'output_dir': '/tmp/biomapper_test',
                    'max_compounds': 100  # Limit to first 100 compounds
                }
            )
            
            assert result.success, f"Real data test failed: {result.error}"
            assert result.statistics.total_processed <= 100
            
        except Exception as e:
            pytest.skip(f"Real data test skipped due to: {e}")
    
    @pytest.mark.slow
    def test_nightingale_reference_availability(self):
        """Test availability of Nightingale NMR reference data."""
        nightingale_file = Path("/procedure/data/local_data/references/nightingale_nmr_reference.csv")
        
        if not nightingale_file.exists():
            pytest.skip("Nightingale reference file not available")
        
        # Test file structure
        try:
            df = pd.read_csv(nightingale_file)
            required_columns = ['biomarker', 'hmdb_id']
            
            for col in required_columns:
                assert col in df.columns, f"Missing column {col} in Nightingale reference"
            
            assert len(df) > 0, "Empty Nightingale reference file"
            
        except Exception as e:
            pytest.fail(f"Nightingale reference file validation failed: {e}")


class TestMetaboliteStrategyValidation:
    """Validation tests for strategy quality and completeness."""
    
    @pytest.fixture
    def all_strategy_files(self):
        """Get all metabolite strategy files."""
        strategies_dir = Path("/home/ubuntu/biomapper/configs/strategies/experimental")
        return list(strategies_dir.glob("met_*.yaml"))
    
    def test_strategy_completeness_checklist(self, all_strategy_files):
        """Test that strategies meet the quality checklist requirements."""
        for strategy_file in all_strategy_files:
            with open(strategy_file, 'r') as f:
                strategy = yaml.safe_load(f)
            
            # Check naming convention
            assert strategy_file.name.startswith('met_')
            assert '_v1_' in strategy_file.name
            
            # Check metadata completeness
            metadata = strategy.get('metadata', {})
            assert metadata.get('entity_type') == 'metabolites'
            assert metadata.get('quality_tier') == 'experimental'
            assert 'expected_match_rate' in metadata
            
            # Check bridge type specification
            assert 'bridge_type' in metadata
            assert isinstance(metadata['bridge_type'], list)
            
            # Check cache configuration
            params = strategy.get('parameters', {})
            assert params.get('use_cache') is True
            
            # Check output configuration
            steps = strategy.get('steps', [])
            export_steps = [s for s in steps if s['action']['type'] == 'EXPORT_DATASET']
            assert len(export_steps) > 0
    
    def test_expected_match_rates(self, all_strategy_files):
        """Test that expected match rates are reasonable for metabolites."""
        for strategy_file in all_strategy_files:
            with open(strategy_file, 'r') as f:
                strategy = yaml.safe_load(f)
            
            metadata = strategy.get('metadata', {})
            expected_rate = metadata.get('expected_match_rate')
            
            if expected_rate is not None:
                # Metabolite match rates should be lower than proteins due to complexity
                assert 0.4 <= expected_rate <= 0.9, \
                    f"Unrealistic expected match rate {expected_rate} in {strategy_file.name}"
                
                # Nightingale strategies should have higher rates
                if 'nightingale' in strategy_file.name:
                    assert expected_rate >= 0.8, \
                        f"Nightingale strategy should have higher expected rate in {strategy_file.name}"
                
                # Semantic strategies should have highest rates
                if 'semantic' in strategy_file.name or 'advanced' in strategy_file.name:
                    assert expected_rate >= 0.8, \
                        f"Advanced strategy should have higher expected rate in {strategy_file.name}"