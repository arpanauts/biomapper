import pytest
from biomapper.core.strategy_actions.baseline_fuzzy_match import (
    BaselineFuzzyMatchAction,
    BaselineFuzzyMatchParams,
    FuzzyAlgorithm
)

@pytest.mark.integration
class TestBaselineIntegration:
    """Integration tests for baseline matching with real metabolite names."""
    
    @pytest.mark.asyncio
    async def test_arivale_to_nightingale_matching(self):
        """Test matching Arivale metabolites to Nightingale reference."""
        # Real Arivale metabolite names
        arivale_data = [
            {'BIOCHEMICAL_NAME': 'spermidine'},
            {'BIOCHEMICAL_NAME': '12,13-DiHOME'},
            {'BIOCHEMICAL_NAME': 'S-1-pyrroline-5-carboxylate'},
            {'BIOCHEMICAL_NAME': '1-methylnicotinamide'},
            {'BIOCHEMICAL_NAME': 'cholesterol'},
            {'BIOCHEMICAL_NAME': 'glucose'},
            {'BIOCHEMICAL_NAME': 'alanine'}
        ]
        
        # Simulated Nightingale reference
        nightingale_ref = [
            {'unified_name': 'Total cholesterol'},
            {'unified_name': 'Glucose'},
            {'unified_name': 'Alanine'},
            {'unified_name': 'Spermidine'},
            {'unified_name': 'HDL cholesterol'},
            {'unified_name': 'LDL cholesterol'}
        ]
        
        action = BaselineFuzzyMatchAction()
        params = BaselineFuzzyMatchParams(
            source_dataset_key="arivale",
            target_dataset_key="nightingale",
            source_column="BIOCHEMICAL_NAME",
            target_column="unified_name",
            threshold=0.80,
            algorithm=FuzzyAlgorithm.TOKEN_SET_RATIO,
            output_key="matches",
            track_metrics=True
        )
        
        context = {
            'datasets': {
                'arivale': arivale_data,
                'nightingale': nightingale_ref
            }
        }
        
        result = await action.execute(params, context)
        
        matches = context['datasets']['matches']
        metrics = context['metrics']['baseline']
        
        # Should match simple cases
        matched_names = {m['source']['BIOCHEMICAL_NAME'] for m in matches}
        assert 'cholesterol' in matched_names
        assert 'glucose' in matched_names
        assert 'alanine' in matched_names
        assert 'spermidine' in matched_names
        
        # Check recall (expect ~45-60% for baseline)
        assert 0.4 <= metrics['recall'] <= 0.7
        
        # Complex names like '12,13-DiHOME' should be unmatched
        unmatched = context['datasets']['unmatched.baseline.arivale']
        unmatched_names = {u['BIOCHEMICAL_NAME'] for u in unmatched}
        assert '12,13-DiHOME' in unmatched_names
        # This test should FAIL initially