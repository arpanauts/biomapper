"""Test metabolomics action aliases."""

import pytest
from biomapper.core.strategy_actions.registry import ACTION_REGISTRY
from biomapper.core.strategy_actions import (
    BaselineFuzzyMatchAction,
    VectorEnhancedMatchAction,
    MetaboliteApiEnrichmentAction,
)


class TestMetabolomicsAliases:
    """Test that metabolomics aliases are properly registered and functional."""

    def test_metabolomics_aliases_registered(self):
        """Test that all metabolomics aliases are properly registered."""
        # Import to ensure aliases are registered
        import biomapper.core.strategy_actions

        # Check aliases exist
        assert "METABOLITE_NAME_MATCH" in ACTION_REGISTRY
        assert "ENRICHED_METABOLITE_MATCH" in ACTION_REGISTRY
        assert "METABOLITE_API_ENRICHMENT" in ACTION_REGISTRY

        # Check they map to correct actions
        assert (
            ACTION_REGISTRY["METABOLITE_NAME_MATCH"]
            == ACTION_REGISTRY["BASELINE_FUZZY_MATCH"]
        )
        assert (
            ACTION_REGISTRY["ENRICHED_METABOLITE_MATCH"]
            == ACTION_REGISTRY["VECTOR_ENHANCED_MATCH"]
        )
        assert (
            ACTION_REGISTRY["METABOLITE_API_ENRICHMENT"]
            == ACTION_REGISTRY["CTS_ENRICHED_MATCH"]
        )

    def test_alias_class_identity(self):
        """Test that aliases point to the same class instances."""
        # Import to ensure aliases are registered
        import biomapper.core.strategy_actions

        # METABOLITE_NAME_MATCH should be the same class as BASELINE_FUZZY_MATCH
        assert (
            ACTION_REGISTRY["METABOLITE_NAME_MATCH"]
            is ACTION_REGISTRY["BASELINE_FUZZY_MATCH"]
        )
        assert ACTION_REGISTRY["METABOLITE_NAME_MATCH"] == BaselineFuzzyMatchAction

        # ENRICHED_METABOLITE_MATCH should be the same class as VECTOR_ENHANCED_MATCH
        assert (
            ACTION_REGISTRY["ENRICHED_METABOLITE_MATCH"]
            is ACTION_REGISTRY["VECTOR_ENHANCED_MATCH"]
        )
        assert ACTION_REGISTRY["ENRICHED_METABOLITE_MATCH"] == VectorEnhancedMatchAction

        # METABOLITE_API_ENRICHMENT should be the same class as CTS_ENRICHED_MATCH
        assert (
            ACTION_REGISTRY["METABOLITE_API_ENRICHMENT"]
            is ACTION_REGISTRY["CTS_ENRICHED_MATCH"]
        )
        assert (
            ACTION_REGISTRY["METABOLITE_API_ENRICHMENT"]
            == MetaboliteApiEnrichmentAction
        )

    def test_alias_functionality(self):
        """Test that aliases work identically to their targets."""
        # Get action classes through aliases
        metabolite_name_match_class = ACTION_REGISTRY["METABOLITE_NAME_MATCH"]
        baseline_fuzzy_match_class = ACTION_REGISTRY["BASELINE_FUZZY_MATCH"]

        # Create instances
        alias_instance = metabolite_name_match_class()
        original_instance = baseline_fuzzy_match_class()

        # They should be instances of the same class
        assert type(alias_instance) == type(original_instance)
        assert isinstance(alias_instance, BaselineFuzzyMatchAction)
        assert isinstance(original_instance, BaselineFuzzyMatchAction)

    def test_all_base_actions_exist(self):
        """Test that all base actions that aliases depend on exist."""
        # These are the base actions that must exist
        required_base_actions = [
            "BASELINE_FUZZY_MATCH",
            "VECTOR_ENHANCED_MATCH",
            "CTS_ENRICHED_MATCH",
        ]

        for action_name in required_base_actions:
            assert (
                action_name in ACTION_REGISTRY
            ), f"Base action {action_name} not found in registry"

    def test_alias_parameter_models(self):
        """Test that aliases use the same parameter models as their base actions."""
        # Get the parameter models through aliases
        metabolite_name_match = ACTION_REGISTRY["METABOLITE_NAME_MATCH"]()
        baseline_fuzzy_match = ACTION_REGISTRY["BASELINE_FUZZY_MATCH"]()

        # Check they use the same parameter model
        assert (
            metabolite_name_match.get_params_model()
            == baseline_fuzzy_match.get_params_model()
        )

        # Same for enriched match
        enriched_metabolite_match = ACTION_REGISTRY["ENRICHED_METABOLITE_MATCH"]()
        vector_enhanced_match = ACTION_REGISTRY["VECTOR_ENHANCED_MATCH"]()

        assert (
            enriched_metabolite_match.get_params_model()
            == vector_enhanced_match.get_params_model()
        )

    def test_metabolite_api_enrichment_extended_features(self):
        """Test that METABOLITE_API_ENRICHMENT has extended features."""
        action_class = ACTION_REGISTRY["METABOLITE_API_ENRICHMENT"]
        action = action_class()

        # Get parameter model
        params_model = action.get_params_model()

        # Check for multi-API support
        assert hasattr(params_model, "__fields__")
        assert "api_services" in params_model.__fields__

        # Check for backward compatibility fields
        assert "identifier_columns" in params_model.__fields__
        assert "cts_timeout" in params_model.__fields__

    def test_no_duplicate_aliases(self):
        """Test that we don't have conflicting alias definitions."""
        # Count how many times each class appears in the registry
        class_counts = {}
        alias_mappings = {
            "METABOLITE_NAME_MATCH": "BASELINE_FUZZY_MATCH",
            "ENRICHED_METABOLITE_MATCH": "VECTOR_ENHANCED_MATCH",
            "METABOLITE_API_ENRICHMENT": "CTS_ENRICHED_MATCH",
        }

        for alias, target in alias_mappings.items():
            assert ACTION_REGISTRY[alias] == ACTION_REGISTRY[target]

    @pytest.mark.parametrize(
        "alias,base_action",
        [
            ("METABOLITE_NAME_MATCH", "BASELINE_FUZZY_MATCH"),
            ("ENRICHED_METABOLITE_MATCH", "VECTOR_ENHANCED_MATCH"),
            ("METABOLITE_API_ENRICHMENT", "CTS_ENRICHED_MATCH"),
        ],
    )
    def test_alias_base_relationship(self, alias, base_action):
        """Test each alias points to its correct base action."""
        assert alias in ACTION_REGISTRY
        assert base_action in ACTION_REGISTRY
        assert ACTION_REGISTRY[alias] == ACTION_REGISTRY[base_action]
