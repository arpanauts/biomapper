import pytest
from biomapper.core.strategy_actions.build_nightingale_reference import (
    BuildNightingaleReferenceAction,
    BuildNightingaleReferenceParams
)
from biomapper.core.strategy_actions.nightingale_nmr_match import (
    NightingaleNmrMatchAction,
    NightingaleNmrMatchParams
)

@pytest.mark.integration
class TestReferenceIntegration:
    """Integration tests for reference building."""
    
    @pytest.mark.asyncio
    @pytest.mark.requires_external_services
    async def test_end_to_end_reference_creation(self):
        """Test complete reference creation workflow."""
        # First run NIGHTINGALE_NMR_MATCH
        match_action = NightingaleNmrMatchAction()
        match_params = NightingaleNmrMatchParams(
            source_dataset_key="israeli10k",
            target_dataset_key="ukbb",
            source_nightingale_column="nightingale_metabolomics_original_name",
            target_title_column="title",
            match_strategy="fuzzy",
            confidence_threshold=0.80,
            output_key="matches",
            unmatched_source_key="unmatched_source",
            unmatched_target_key="unmatched_target"
        )
        
        # Sample data
        context = {
            'datasets': {
                'israeli10k': [
                    {
                        'tabular_field_name': 'total_c',
                        'nightingale_metabolomics_original_name': 'Total_C',
                        'description': 'Total cholesterol'
                    }
                ],
                'ukbb': [
                    {
                        'field_id': '23400',
                        'title': 'Total cholesterol',
                        'category': 'Cholesterol'
                    }
                ]
            }
        }
        
        # Run matching
        await match_action.execute_typed(match_params, context)
        
        # Now build reference
        ref_action = BuildNightingaleReferenceAction()
        ref_params = BuildNightingaleReferenceParams(
            israeli10k_data="israeli10k",
            ukbb_data="ukbb",
            matched_pairs="matches",
            output_key="reference",
            export_csv=False
        )
        
        result = await ref_action.execute_typed(ref_params, context)
        
        assert result.success
        reference = context['datasets']['reference']
        assert len(reference) == 1
        assert reference[0]['unified_name'] == 'Total cholesterol'
        # This test should FAIL initially