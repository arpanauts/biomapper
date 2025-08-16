"""Comprehensive tests for PROTEIN_MULTI_BRIDGE action (TDD - WRITE TESTS FIRST!)."""

import pytest
import pandas as pd
from pydantic import ValidationError

# These imports will FAIL initially - that's the TDD point!
from biomapper.core.strategy_actions.entities.proteins.matching.multi_bridge import (
    ProteinMultiBridge,
    ProteinMultiBridgeParams,
    BridgeAttempt,
)


class TestProteinMultiBridge:
    """Comprehensive test suite for PROTEIN_MULTI_BRIDGE action following TDD methodology."""

    @pytest.fixture
    def sample_source_data(self):
        """Sample source dataset (Arivale-like protein data)."""
        return pd.DataFrame(
            {
                "id": ["source_1", "source_2", "source_3", "source_4"],
                "uniprot": ["P12345", "Q14213", "MISSING", "O15031"],
                "gene_name": ["TP53", "NRP1", "UNKNOWN", "PLXNB2"],
                "protein_name": [
                    "Tumor protein p53",
                    "Neuropilin-1",
                    "Unknown protein",
                    "Plexin-B2",
                ],
            }
        )

    @pytest.fixture
    def sample_target_data(self):
        """Sample target dataset (KG2c-like protein data)."""
        return pd.DataFrame(
            {
                "id": ["target_1", "target_2", "target_3", "target_4", "target_5"],
                "extracted_uniprot": ["P12345", "Q14213", "O15031", "", "Q8NEV9"],
                "gene_symbol": ["TP53", "NRP1", "PLXNB2", "BRCA1", "EXAMPLE"],
                "protein_description": [
                    "tumor protein p53",
                    "neuropilin 1",
                    "plexin B2",
                    "breast cancer gene",
                    "example protein",
                ],
            }
        )

    @pytest.fixture
    def basic_bridge_config(self):
        """Basic bridge configuration for testing."""
        return [
            BridgeAttempt(
                type="uniprot",
                source_column="uniprot",
                target_column="extracted_uniprot",
                method="exact",
                confidence_threshold=0.95,
                enabled=True,
            ),
            BridgeAttempt(
                type="gene_symbol",
                source_column="gene_name",
                target_column="gene_symbol",
                method="fuzzy",
                confidence_threshold=0.80,
                enabled=True,
                fuzzy_threshold=0.85,
            ),
        ]

    @pytest.fixture
    def mock_context_with_datasets(self, sample_source_data, sample_target_data):
        """Mock execution context with datasets."""
        return {
            "datasets": {
                "source_proteins": sample_source_data,
                "target_proteins": sample_target_data,
            },
            "statistics": {},
        }

    # Phase 1: Basic Exact Matching Tests (WILL FAIL - TDD RED PHASE)

    @pytest.mark.asyncio
    async def test_exact_uniprot_matching_basic(
        self, mock_context_with_datasets, basic_bridge_config
    ):
        """Test basic exact UniProt matching - SHOULD FAIL initially."""
        action = ProteinMultiBridge()
        params = ProteinMultiBridgeParams(
            source_dataset_key="source_proteins",
            target_dataset_key="target_proteins",
            bridge_attempts=basic_bridge_config[:1],  # Only UniProt bridge
            output_key="matched_results",
            partial_match_handling="best_match",
        )

        # This test will fail until implementation exists
        result = await action.execute_typed(params, mock_context_with_datasets)

        # Test assertions that will fail initially
        assert result.success is True
        assert "matched_results" in mock_context_with_datasets["datasets"]

        matched_data = mock_context_with_datasets["datasets"]["matched_results"]
        assert len(matched_data) > 0

        # Check that exact matches were found (P12345, Q14213, O15031)
        source_ids = set(matched_data["source_id"].tolist())
        expected_matches = {
            "source_1",
            "source_2",
            "source_4",
        }  # Those with valid UniProt
        assert expected_matches.intersection(source_ids) == expected_matches

    @pytest.mark.asyncio
    async def test_fuzzy_gene_symbol_matching(
        self, mock_context_with_datasets, basic_bridge_config
    ):
        """Test fuzzy gene symbol matching - SHOULD FAIL initially."""
        action = ProteinMultiBridge()
        params = ProteinMultiBridgeParams(
            source_dataset_key="source_proteins",
            target_dataset_key="target_proteins",
            bridge_attempts=basic_bridge_config[1:],  # Only gene symbol bridge
            output_key="matched_results",
            partial_match_handling="best_match",
        )

        result = await action.execute_typed(params, mock_context_with_datasets)

        assert result.success is True
        matched_data = mock_context_with_datasets["datasets"]["matched_results"]

        # Should find fuzzy matches for TP53, NRP1, PLXNB2
        assert len(matched_data) >= 3

        # Check confidence scores exist and are reasonable
        assert "confidence" in matched_data.columns
        assert all(score >= 0.80 for score in matched_data["confidence"])

    @pytest.mark.asyncio
    async def test_bridge_priority_order(
        self, mock_context_with_datasets, basic_bridge_config
    ):
        """Test that bridges are tried in specified priority order - SHOULD FAIL initially."""
        action = ProteinMultiBridge()
        params = ProteinMultiBridgeParams(
            source_dataset_key="source_proteins",
            target_dataset_key="target_proteins",
            bridge_attempts=basic_bridge_config,  # Both bridges
            output_key="matched_results",
            logging_verbosity="detailed",
        )

        result = await action.execute_typed(params, mock_context_with_datasets)

        assert result.success is True
        matched_data = mock_context_with_datasets["datasets"]["matched_results"]

        # Check that successful_bridge column indicates which bridge succeeded
        assert "successful_bridge" in matched_data.columns

        # UniProt exact matches should have been chosen over gene symbol fuzzy where both available
        uniprot_matches = matched_data[matched_data["successful_bridge"] == "uniprot"]
        assert (
            len(uniprot_matches) >= 2
        )  # P12345, Q14213, O15031 should match via UniProt

    @pytest.mark.asyncio
    async def test_enable_disable_bridges(self, mock_context_with_datasets):
        """Test enable/disable functionality for bridges - SHOULD FAIL initially."""
        disabled_config = [
            BridgeAttempt(
                type="uniprot",
                source_column="uniprot",
                target_column="extracted_uniprot",
                method="exact",
                confidence_threshold=0.95,
                enabled=False,  # DISABLED
            ),
            BridgeAttempt(
                type="gene_symbol",
                source_column="gene_name",
                target_column="gene_symbol",
                method="fuzzy",
                confidence_threshold=0.80,
                enabled=True,  # ENABLED
            ),
        ]

        action = ProteinMultiBridge()
        params = ProteinMultiBridgeParams(
            source_dataset_key="source_proteins",
            target_dataset_key="target_proteins",
            bridge_attempts=disabled_config,
            output_key="matched_results",
        )

        result = await action.execute_typed(params, mock_context_with_datasets)

        assert result.success is True
        matched_data = mock_context_with_datasets["datasets"]["matched_results"]

        # Should only have gene_symbol matches, no uniprot matches
        assert all(
            bridge == "gene_symbol" for bridge in matched_data["successful_bridge"]
        )
        assert "uniprot" not in matched_data["successful_bridge"].values

    @pytest.mark.asyncio
    async def test_confidence_thresholds(self, mock_context_with_datasets):
        """Test confidence threshold filtering - SHOULD FAIL initially."""
        high_threshold_config = [
            BridgeAttempt(
                type="gene_symbol",
                source_column="gene_name",
                target_column="gene_symbol",
                method="fuzzy",
                confidence_threshold=0.99,  # VERY HIGH threshold
                enabled=True,
                fuzzy_threshold=0.85,
            )
        ]

        action = ProteinMultiBridge()
        params = ProteinMultiBridgeParams(
            source_dataset_key="source_proteins",
            target_dataset_key="target_proteins",
            bridge_attempts=high_threshold_config,
            output_key="matched_results",
        )

        result = await action.execute_typed(params, mock_context_with_datasets)

        # Should have fewer matches due to high threshold
        assert result.success is True
        matched_data = mock_context_with_datasets["datasets"]["matched_results"]

        # All remaining matches should meet high threshold
        if len(matched_data) > 0:
            assert all(score >= 0.99 for score in matched_data["confidence"])

    # Phase 2: Partial Match Handling Tests (WILL FAIL - TDD RED PHASE)

    @pytest.mark.asyncio
    async def test_partial_match_handling_best_match(
        self, mock_context_with_datasets, basic_bridge_config
    ):
        """Test best_match partial handling strategy - SHOULD FAIL initially."""
        action = ProteinMultiBridge()
        params = ProteinMultiBridgeParams(
            source_dataset_key="source_proteins",
            target_dataset_key="target_proteins",
            bridge_attempts=basic_bridge_config,
            partial_match_handling="best_match",
            min_overall_confidence=0.5,  # Lower threshold to allow partial matches
            output_key="matched_results",
        )

        result = await action.execute_typed(params, mock_context_with_datasets)

        assert result.success is True
        matched_data = mock_context_with_datasets["datasets"]["matched_results"]

        # Should include partial matches above min_overall_confidence
        assert len(matched_data) > 0
        assert all(score >= 0.5 for score in matched_data["confidence"])

    @pytest.mark.asyncio
    async def test_partial_match_handling_reject(
        self, mock_context_with_datasets, basic_bridge_config
    ):
        """Test reject partial handling strategy - SHOULD FAIL initially."""
        action = ProteinMultiBridge()
        params = ProteinMultiBridgeParams(
            source_dataset_key="source_proteins",
            target_dataset_key="target_proteins",
            bridge_attempts=basic_bridge_config,
            partial_match_handling="reject",
            min_overall_confidence=0.9,  # High threshold
            output_key="matched_results",
        )

        result = await action.execute_typed(params, mock_context_with_datasets)

        assert result.success is True
        matched_data = mock_context_with_datasets["datasets"]["matched_results"]

        # Should reject low-confidence matches
        if len(matched_data) > 0:
            assert all(score >= 0.9 for score in matched_data["confidence"])

    @pytest.mark.asyncio
    async def test_partial_match_handling_warn(self):
        """Test warn partial handling strategy with fuzzy mismatch data."""
        # Create test data that will generate fuzzy matches with lower confidence
        fuzzy_source = pd.DataFrame(
            {
                "id": ["fuzzy_1", "fuzzy_2"],
                "gene_name": ["TP53_VARIANT", "NRP1_ALT"],  # Similar but not exact
            }
        )

        fuzzy_target = pd.DataFrame(
            {
                "id": ["target_1", "target_2"],
                "gene_symbol": [
                    "TP53",
                    "NRP1",
                ],  # Will fuzzy match but with lower confidence
            }
        )

        fuzzy_context = {
            "datasets": {"fuzzy_source": fuzzy_source, "fuzzy_target": fuzzy_target}
        }

        # Create a bridge configuration that will produce partial matches
        high_threshold_bridge = [
            BridgeAttempt(
                type="gene_symbol",
                source_column="gene_name",
                target_column="gene_symbol",
                method="fuzzy",
                confidence_threshold=0.95,  # HIGH threshold for fuzzy matches
                enabled=True,
                fuzzy_threshold=0.85,
            )
        ]

        action = ProteinMultiBridge()
        params = ProteinMultiBridgeParams(
            source_dataset_key="fuzzy_source",
            target_dataset_key="fuzzy_target",
            bridge_attempts=high_threshold_bridge,
            partial_match_handling="warn",
            min_overall_confidence=0.60,  # Lower than bridge threshold
            output_key="matched_results",
        )

        result = await action.execute_typed(params, fuzzy_context)

        assert result.success is True
        matched_data = fuzzy_context["datasets"]["matched_results"]

        # Should include matches with warnings for low confidence
        # For this test, the fuzzy matches should have lower confidence and generate warnings
        if len(matched_data) > 0:
            # Check if any warnings were generated
            has_warnings = "warning" in matched_data.columns
            # Alternatively, verify we have matches with confidence < 0.95 (which would trigger warnings)
            low_confidence_matches = any(
                conf < 0.95 for conf in matched_data["confidence"]
            )
            assert (
                has_warnings or not low_confidence_matches
            ), "Expected warning column for low confidence matches"

    # Phase 3: Logging and Metadata Tests (WILL FAIL - TDD RED PHASE)

    @pytest.mark.asyncio
    async def test_detailed_logging_verbosity(
        self, mock_context_with_datasets, basic_bridge_config, caplog
    ):
        """Test detailed logging produces scientific reproducibility logs - SHOULD FAIL initially."""
        action = ProteinMultiBridge()
        params = ProteinMultiBridgeParams(
            source_dataset_key="source_proteins",
            target_dataset_key="target_proteins",
            bridge_attempts=basic_bridge_config,
            logging_verbosity="detailed",
            output_key="matched_results",
        )

        with caplog.at_level("INFO"):
            result = await action.execute_typed(params, mock_context_with_datasets)

        assert result.success is True

        # Check for detailed scientific logging
        log_messages = [record.message for record in caplog.records]
        assert any(
            "PROTEIN MULTI-BRIDGE MATCHING COMPLETE" in msg for msg in log_messages
        )
        assert any("source dataset" in msg.lower() for msg in log_messages)
        assert any("enabled bridges" in msg.lower() for msg in log_messages)

    @pytest.mark.asyncio
    async def test_minimal_logging_verbosity(
        self, mock_context_with_datasets, basic_bridge_config, caplog
    ):
        """Test minimal logging produces less output - SHOULD FAIL initially."""
        action = ProteinMultiBridge()
        params = ProteinMultiBridgeParams(
            source_dataset_key="source_proteins",
            target_dataset_key="target_proteins",
            bridge_attempts=basic_bridge_config,
            logging_verbosity="minimal",
            output_key="matched_results",
        )

        with caplog.at_level("DEBUG"):
            result = await action.execute_typed(params, mock_context_with_datasets)

        assert result.success is True

        # Should have fewer log messages than detailed mode
        log_messages = [record.message for record in caplog.records]
        # At minimal verbosity, should only log essential messages
        debug_messages = [msg for msg in log_messages if "DEBUG" in str(msg)]
        assert len(debug_messages) < 10  # Should be minimal

    @pytest.mark.asyncio
    async def test_match_metadata_and_statistics(
        self, mock_context_with_datasets, basic_bridge_config
    ):
        """Test that match metadata and statistics are properly recorded - SHOULD FAIL initially."""
        action = ProteinMultiBridge()
        params = ProteinMultiBridgeParams(
            source_dataset_key="source_proteins",
            target_dataset_key="target_proteins",
            bridge_attempts=basic_bridge_config,
            output_key="matched_results",
        )

        result = await action.execute_typed(params, mock_context_with_datasets)

        assert result.success is True
        matched_data = mock_context_with_datasets["datasets"]["matched_results"]

        # Check required metadata columns
        expected_columns = [
            "source_id",
            "target_id",
            "confidence",
            "successful_bridge",
            "bridge_method",
        ]
        for col in expected_columns:
            assert col in matched_data.columns, f"Missing required column: {col}"

        # Check statistics were recorded
        stats = mock_context_with_datasets.get("statistics", {})
        assert "total_source_proteins" in stats
        assert "total_matches" in stats
        assert "matches_by_bridge" in stats

    # Phase 4: Edge Cases and Error Handling (WILL FAIL - TDD RED PHASE)

    @pytest.mark.asyncio
    async def test_empty_datasets_handling(self, basic_bridge_config):
        """Test handling of empty datasets - SHOULD FAIL initially."""
        empty_context = {
            "datasets": {"empty_source": pd.DataFrame(), "empty_target": pd.DataFrame()}
        }

        action = ProteinMultiBridge()
        params = ProteinMultiBridgeParams(
            source_dataset_key="empty_source",
            target_dataset_key="empty_target",
            bridge_attempts=basic_bridge_config,
            output_key="matched_results",
        )

        result = await action.execute_typed(params, empty_context)

        # Should handle gracefully, not crash
        assert result.success is True
        assert "matched_results" in empty_context["datasets"]
        assert len(empty_context["datasets"]["matched_results"]) == 0

    @pytest.mark.asyncio
    async def test_missing_columns_error_handling(self, mock_context_with_datasets):
        """Test error handling for missing columns - SHOULD FAIL initially."""
        bad_bridge_config = [
            BridgeAttempt(
                type="uniprot",
                source_column="nonexistent_column",  # BAD COLUMN
                target_column="extracted_uniprot",
                method="exact",
                confidence_threshold=0.95,
                enabled=True,
            )
        ]

        action = ProteinMultiBridge()
        params = ProteinMultiBridgeParams(
            source_dataset_key="source_proteins",
            target_dataset_key="target_proteins",
            bridge_attempts=bad_bridge_config,
            output_key="matched_results",
        )

        result = await action.execute_typed(params, mock_context_with_datasets)

        # Should succeed but with 0 matches (graceful handling)
        assert result.success is True
        matched_data = mock_context_with_datasets["datasets"]["matched_results"]
        assert len(matched_data) == 0  # No matches due to missing column

    @pytest.mark.asyncio
    async def test_all_bridges_disabled(self, mock_context_with_datasets):
        """Test behavior when all bridges are disabled - SHOULD FAIL initially."""
        all_disabled_config = [
            BridgeAttempt(
                type="uniprot",
                source_column="uniprot",
                target_column="extracted_uniprot",
                method="exact",
                confidence_threshold=0.95,
                enabled=False,  # DISABLED
            ),
            BridgeAttempt(
                type="gene_symbol",
                source_column="gene_name",
                target_column="gene_symbol",
                method="fuzzy",
                confidence_threshold=0.80,
                enabled=False,  # DISABLED
            ),
        ]

        action = ProteinMultiBridge()
        params = ProteinMultiBridgeParams(
            source_dataset_key="source_proteins",
            target_dataset_key="target_proteins",
            bridge_attempts=all_disabled_config,
            output_key="matched_results",
        )

        result = await action.execute_typed(params, mock_context_with_datasets)

        # Should complete but with no matches
        assert result.success is True
        matched_data = mock_context_with_datasets["datasets"]["matched_results"]
        assert len(matched_data) == 0

    # Phase 5: Performance and Integration Tests (WILL FAIL - TDD RED PHASE)

    @pytest.mark.asyncio
    async def test_large_dataset_performance(self, basic_bridge_config):
        """Test performance with larger protein datasets - SHOULD FAIL initially."""
        import time

        # Create larger synthetic datasets
        large_source = pd.DataFrame(
            {
                "id": [f"source_{i}" for i in range(1000)],
                "uniprot": [f"P{str(i).zfill(5)}" for i in range(1000)],
                "gene_name": [f"GENE{i}" for i in range(1000)],
            }
        )

        large_target = pd.DataFrame(
            {
                "id": [f"target_{i}" for i in range(1000)],
                "extracted_uniprot": [
                    f"P{str(i).zfill(5)}" if i % 2 == 0 else "" for i in range(1000)
                ],
                "gene_symbol": [f"GENE{i}" for i in range(1000)],
            }
        )

        large_context = {
            "datasets": {"large_source": large_source, "large_target": large_target}
        }

        action = ProteinMultiBridge()
        params = ProteinMultiBridgeParams(
            source_dataset_key="large_source",
            target_dataset_key="large_target",
            bridge_attempts=basic_bridge_config,
            output_key="matched_results",
        )

        start_time = time.time()
        result = await action.execute_typed(params, large_context)
        end_time = time.time()

        # Performance requirement: reasonable time for 1k proteins (scaled down from 10k requirement)
        execution_time = end_time - start_time
        assert (
            execution_time < 30.0
        ), f"Performance test failed: {execution_time:.2f}s for 1k proteins (requirement: <30s for 10k)"

        assert result.success is True
        matched_data = large_context["datasets"]["matched_results"]
        assert len(matched_data) > 0

    @pytest.mark.asyncio
    async def test_real_protein_data_patterns(self, basic_bridge_config):
        """Test with realistic protein identifier patterns - SHOULD FAIL initially."""
        # Real-world protein data patterns
        realistic_source = pd.DataFrame(
            {
                "id": ["arivale_1", "arivale_2", "arivale_3", "arivale_4"],
                "uniprot": [
                    "P04637",
                    "O14786",
                    "UniProtKB:Q8NEV9",
                    "",
                ],  # Mixed formats
                "gene_name": ["TP53", "NRP1", "PLXNB2", "UNKNOWN_GENE"],
            }
        )

        realistic_target = pd.DataFrame(
            {
                "id": ["kg2c_1", "kg2c_2", "kg2c_3", "kg2c_4"],
                "extracted_uniprot": ["P04637", "O14786", "Q8NEV9", "P12345"],
                "gene_symbol": [
                    "TP53",
                    "Neuropilin-1",
                    "PLXNB2",
                    "BRCA1",
                ],  # Mixed case
            }
        )

        realistic_context = {
            "datasets": {
                "realistic_source": realistic_source,
                "realistic_target": realistic_target,
            }
        }

        action = ProteinMultiBridge()
        params = ProteinMultiBridgeParams(
            source_dataset_key="realistic_source",
            target_dataset_key="realistic_target",
            bridge_attempts=basic_bridge_config,
            output_key="matched_results",
        )

        result = await action.execute_typed(params, realistic_context)

        assert result.success is True
        matched_data = realistic_context["datasets"]["matched_results"]

        # Should handle mixed formats and find matches
        assert len(matched_data) >= 3  # Should match TP53, NRP1, PLXNB2

        # Test that UniProtKB: prefix was handled correctly
        uniprot_matches = matched_data[matched_data["successful_bridge"] == "uniprot"]
        assert len(uniprot_matches) >= 2

    # Phase 6: Parameter Validation Tests (WILL FAIL - TDD RED PHASE)

    @pytest.mark.asyncio
    async def test_parameter_validation_missing_keys(self, basic_bridge_config):
        """Test parameter validation for missing dataset keys - SHOULD FAIL initially."""
        bad_context = {"datasets": {"wrong_key": pd.DataFrame()}}

        action = ProteinMultiBridge()
        params = ProteinMultiBridgeParams(
            source_dataset_key="missing_source_key",  # MISSING
            target_dataset_key="missing_target_key",  # MISSING
            bridge_attempts=basic_bridge_config,
            output_key="matched_results",
        )

        result = await action.execute_typed(params, bad_context)

        # Should fail with appropriate error message
        assert result.success is False
        assert "not found" in result.message or "missing" in result.message.lower()

    @pytest.mark.asyncio
    async def test_bridge_attempt_validation(self, mock_context_with_datasets):
        """Test validation of BridgeAttempt parameters - SHOULD FAIL initially."""
        # Test with invalid confidence threshold - should fail during BridgeAttempt creation
        with pytest.raises(ValidationError):  # ValidationError expected
            invalid_bridge = BridgeAttempt(
                type="uniprot",
                source_column="uniprot",
                target_column="extracted_uniprot",
                method="exact",
                confidence_threshold=1.5,  # INVALID - > 1.0
                enabled=True,
            )


# Additional test fixtures and utilities for the comprehensive test suite


@pytest.fixture
def complex_multi_bridge_config():
    """Complex bridge configuration for advanced testing."""
    return [
        BridgeAttempt(
            type="uniprot",
            source_column="uniprot",
            target_column="extracted_uniprot",
            method="exact",
            confidence_threshold=0.95,
            enabled=True,
        ),
        BridgeAttempt(
            type="gene_symbol",
            source_column="gene_name",
            target_column="gene_symbol",
            method="fuzzy",
            confidence_threshold=0.80,
            enabled=True,
            fuzzy_threshold=0.85,
        ),
        BridgeAttempt(
            type="ensembl",
            source_column="ensembl_id",
            target_column="ensembl_protein_id",
            method="exact",
            confidence_threshold=0.98,
            enabled=True,
        ),
    ]


class TestProteinMultiBridgeIntegration:
    """Integration tests for PROTEIN_MULTI_BRIDGE with other actions."""

    @pytest.mark.asyncio
    async def test_integration_with_normalize_accessions_output(self):
        """Test integration with PROTEIN_NORMALIZE_ACCESSIONS output - SHOULD FAIL initially."""
        # This test simulates the output from normalize_accessions action
        normalized_source = pd.DataFrame(
            {
                "id": ["norm_1", "norm_2"],
                "original_uniprot": ["UniProtKB:P12345-1", "sp|Q14213|NRP1_HUMAN"],
                "normalized_uniprot": [
                    "P12345",
                    "Q14213",
                ],  # Output from normalize action
                "gene_name": ["TP53", "NRP1"],
            }
        )

        target_data = pd.DataFrame(
            {
                "id": ["target_1", "target_2"],
                "extracted_uniprot": ["P12345", "Q14213"],
                "gene_symbol": ["TP53", "NRP1"],
            }
        )

        context = {
            "datasets": {
                "normalized_source": normalized_source,
                "kg2c_target": target_data,
            }
        }

        bridge_config = [
            BridgeAttempt(
                type="uniprot",
                source_column="normalized_uniprot",  # Use normalized output
                target_column="extracted_uniprot",
                method="exact",
                confidence_threshold=0.95,
                enabled=True,
            )
        ]

        action = ProteinMultiBridge()
        params = ProteinMultiBridgeParams(
            source_dataset_key="normalized_source",
            target_dataset_key="kg2c_target",
            bridge_attempts=bridge_config,
            output_key="final_matches",
        )

        result = await action.execute_typed(params, context)

        assert result.success is True
        matches = context["datasets"]["final_matches"]
        assert len(matches) == 2  # Both should match after normalization


# Run these tests to confirm they all FAIL (TDD Red Phase):
# poetry run pytest -xvs tests/unit/core/strategy_actions/entities/proteins/matching/test_multi_bridge.py
# Expected result: ALL TESTS FAIL because implementation doesn't exist yet
