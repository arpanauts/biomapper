"""
Integration tests for biological validation framework components.

Tests the interaction between gold standard curator, threshold optimizer,
and expert review flagger in a realistic workflow.
"""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path
import json
from unittest.mock import patch, MagicMock

from src.validation.gold_standard_curator import (
    GoldStandardCurator, MetaboliteClass, DifficultyLevel, GoldStandardDataset
)
from src.validation.threshold_optimizer import ConfidenceThresholdOptimizer, ThresholdResult
from src.validation.flagging_logic import ExpertReviewFlagger, FlaggingCategory
from src.validation.pipeline_modes import PipelineModeFactory, ValidationConfig


class TestValidationFrameworkIntegration:
    """Test integration of validation framework components."""
    
    @pytest.fixture
    def temp_validation_dir(self, tmp_path):
        """Create temporary validation directory."""
        validation_dir = tmp_path / "validation"
        validation_dir.mkdir()
        return str(validation_dir)
    
    @pytest.fixture
    def sample_gold_standard(self, temp_validation_dir):
        """Create sample gold standard dataset."""
        curator = GoldStandardCurator(output_dir=temp_validation_dir)
        
        # Create minimal gold standard for testing
        test_entries = [
            {
                "metabolite_id": "TEST_001",
                "primary_name": "Test Glucose",
                "alternative_names": ["glucose", "dextrose"],
                "hmdb_id": "HMDB0000122",
                "metabolite_class": MetaboliteClass.CLINICAL_MARKERS,
                "difficulty_level": DifficultyLevel.EASY,
                "expected_confidence": 0.95
            },
            {
                "metabolite_id": "TEST_002", 
                "primary_name": "Test Cholesterol",
                "alternative_names": ["cholesterol", "chol"],
                "hmdb_id": "HMDB0000067",
                "metabolite_class": MetaboliteClass.CLINICAL_MARKERS,
                "difficulty_level": DifficultyLevel.EASY,
                "expected_confidence": 0.90
            },
            {
                "metabolite_id": "TEST_003",
                "primary_name": "Test Complex Lipid",
                "alternative_names": ["complex_lipid"],
                "hmdb_id": "HMDB0001234",
                "metabolite_class": MetaboliteClass.LIPIDS,
                "difficulty_level": DifficultyLevel.DIFFICULT,
                "expected_confidence": 0.70
            }
        ]
        
        # Create mock gold standard dataset
        dataset = GoldStandardDataset(
            version="test_v1.0",
            creation_date="2024-01-01",
            total_entries=len(test_entries),
            class_distribution={"clinical_markers": 2, "lipids": 1},
            difficulty_distribution={"easy": 2, "difficult": 1},
            entries=[],
            curation_methodology="Test methodology"
        )
        
        # Convert enums to strings for JSON serialization
        serializable_entries = []
        for entry in test_entries:
            serializable_entry = entry.copy()
            serializable_entry["metabolite_class"] = entry["metabolite_class"].value
            serializable_entry["difficulty_level"] = entry["difficulty_level"].value
            serializable_entries.append(serializable_entry)
        
        # Save as JSON for testing
        gold_standard_file = Path(temp_validation_dir) / "test_gold_standard.json"
        with open(gold_standard_file, 'w') as f:
            json.dump({
                "version": dataset.version,
                "creation_date": dataset.creation_date, 
                "total_entries": dataset.total_entries,
                "class_distribution": dataset.class_distribution,
                "difficulty_distribution": dataset.difficulty_distribution,
                "curation_methodology": dataset.curation_methodology,
                "entries": serializable_entries
            }, f, indent=2)
        
        return str(gold_standard_file)
    
    @pytest.fixture
    def sample_pipeline_results(self):
        """Create sample pipeline results for testing."""
        return pd.DataFrame({
            "metabolite_id": ["TEST_001", "TEST_002", "TEST_003", "TEST_004"],
            "matched_name": ["Test Glucose", "Test Cholesterol", "Test Complex Lipid", "Unknown Compound"],
            "confidence_score": [0.95, 0.88, 0.72, 0.60],
            "matched_stage": ["nightingale", "fuzzy", "rampdb", "semantic"],
            "molecular_formula": ["C6H12O6", "C27H46O", "C45H87O8P", "C10H20O"],
            "alternative_matches": ["", "total cholesterol", "phospholipid", "compound1, compound2"]
        })
    
    def test_gold_standard_curator_basic_functionality(self, temp_validation_dir):
        """Test basic gold standard curator functionality."""
        curator = GoldStandardCurator(output_dir=temp_validation_dir)
        
        # Test that curator initializes correctly
        assert curator.output_dir.exists()
        assert curator.class_targets[MetaboliteClass.CLINICAL_MARKERS] == 200
        assert curator.difficulty_targets[DifficultyLevel.EASY] == 300
        
        # Test metabolite generation methods exist
        clinical_entries = curator._create_clinical_markers()
        assert len(clinical_entries) == 200
        assert all(entry.metabolite_class == MetaboliteClass.CLINICAL_MARKERS for entry in clinical_entries)
        
        amino_entries = curator._create_amino_acids()
        assert len(amino_entries) == 125
        assert all(entry.metabolite_class == MetaboliteClass.AMINO_ACIDS for entry in amino_entries)
    
    def test_threshold_optimizer_basic_functionality(self, temp_validation_dir):
        """Test basic threshold optimizer functionality."""
        optimizer = ConfidenceThresholdOptimizer(output_dir=temp_validation_dir)
        
        # Create mock validation data
        validation_data = pd.DataFrame({
            "confidence_score": [0.95, 0.88, 0.72, 0.60, 0.45],
            "is_correct_match": [1, 1, 1, 0, 0],  # First 3 correct, last 2 incorrect
            "metabolite_class": ["clinical", "clinical", "lipid", "other", "other"]
        })
        
        # Test threshold optimization
        try:
            results = optimizer.optimize_thresholds_for_dataset(validation_data)
            
            # Should return results dictionary
            assert isinstance(results, dict)
            assert "overall" in results
            
            overall_result = results["overall"]
            assert isinstance(overall_result, ThresholdResult)
            assert 0.0 <= overall_result.optimal_threshold <= 1.0
            assert 0.0 <= overall_result.precision <= 1.0
            assert 0.0 <= overall_result.recall <= 1.0
            
        except ImportError:
            # If scikit-learn not available, test fallback
            pytest.skip("scikit-learn not available, threshold optimization requires sklearn")
    
    def test_expert_review_flagger_basic_functionality(self):
        """Test basic expert review flagger functionality.""" 
        flagger = ExpertReviewFlagger(
            auto_accept_threshold=0.85,
            auto_reject_threshold=0.75,
            max_flagging_rate=0.15
        )
        
        # Create test data (avoid names that trigger edge case detection)
        pipeline_results = pd.DataFrame({
            "metabolite_id": ["MET_001", "MET_002", "MET_003", "MET_004"],
            "matched_name": ["High Conf Metabolite", "Medium Conf Metabolite", "Low Conf Metabolite", "Ambiguous Metabolite"],
            "confidence_score": [0.95, 0.80, 0.65, 0.82],
            "alternative_matches": ["", "", "", "alt1, alt2, alt3"]
        })
        
        # Test flagging
        flagged_results = flagger.flag_results_for_review(pipeline_results)
        
        # Verify flagging columns added
        expected_columns = [
            "expert_review_flag", "flagging_category", "flagging_reason",
            "review_priority", "estimated_review_time_minutes"
        ]
        for col in expected_columns:
            assert col in flagged_results.columns
        
        # Verify decisions are reasonable - check by actual confidence values
        # High confidence (0.95) should be auto-accepted
        auto_accept_rows = flagged_results[flagged_results["flagging_category"] == "auto_accept"]
        assert len(auto_accept_rows) >= 1
        assert not any(auto_accept_rows["expert_review_flag"])
        
        # Low confidence (0.65) should be auto-rejected
        auto_reject_rows = flagged_results[flagged_results["flagging_category"] == "auto_reject"]
        assert len(auto_reject_rows) >= 1
    
    def test_pipeline_mode_factory(self):
        """Test pipeline mode factory configurations."""
        
        # Test production config
        prod_config = PipelineModeFactory.create_production_config()
        assert prod_config.enable_expert_flagging is True
        assert prod_config.auto_accept_threshold == 0.85
        assert prod_config.max_total_cost == 25.0
        
        # Test validation config
        test_path = "/tmp/test_gold_standard.json"
        val_config = PipelineModeFactory.create_validation_config(test_path)
        assert val_config.gold_standard_enabled is True
        assert val_config.gold_standard_path == test_path
        assert val_config.validation_sample_size == 250
        
        # Test cost optimized config
        cost_config = PipelineModeFactory.create_cost_optimized_config()
        assert cost_config.llm_semantic_match.enabled is False
        assert cost_config.max_total_cost == 5.0
    
    @patch('src.validation.threshold_optimizer.SKLEARN_AVAILABLE', False)
    def test_threshold_optimizer_fallback(self, temp_validation_dir):
        """Test threshold optimizer fallback when scikit-learn unavailable."""
        optimizer = ConfidenceThresholdOptimizer(output_dir=temp_validation_dir)
        
        validation_data = pd.DataFrame({
            "confidence_score": [0.95, 0.88, 0.72, 0.60],
            "is_correct_match": [1, 1, 0, 0]
        })
        
        results = optimizer.optimize_thresholds_for_dataset(validation_data)
        
        # Should still return results using fallback method
        assert isinstance(results, dict)
        assert "overall" in results
        assert isinstance(results["overall"], ThresholdResult)
    
    def test_end_to_end_validation_workflow(self, temp_validation_dir, sample_gold_standard, sample_pipeline_results):
        """Test complete validation workflow integration."""
        
        # Step 1: Initialize components
        optimizer = ConfidenceThresholdOptimizer(output_dir=temp_validation_dir)
        flagger = ExpertReviewFlagger(max_flagging_rate=0.25)  # Higher rate for testing
        
        # Step 2: Create validation dataset (mock pipeline results)
        mock_pipeline_results = [
            {"metabolite_id": "TEST_001", "confidence_score": 0.92, "matched_name": "Test Glucose"},
            {"metabolite_id": "TEST_002", "confidence_score": 0.85, "matched_name": "Test Cholesterol"}, 
            {"metabolite_id": "TEST_003", "confidence_score": 0.68, "matched_name": "Test Complex Lipid"}
        ]
        
        validation_data = optimizer.generate_validation_dataset_from_gold_standard(
            sample_gold_standard, mock_pipeline_results
        )
        
        # Verify validation dataset created
        assert isinstance(validation_data, pd.DataFrame)
        assert len(validation_data) > 0
        assert "confidence_score" in validation_data.columns
        assert "is_correct_match" in validation_data.columns
        
        # Step 3: Apply expert review flagging
        flagged_results = flagger.flag_results_for_review(sample_pipeline_results)
        
        # Verify flagging applied
        assert "expert_review_flag" in flagged_results.columns
        assert "flagging_category" in flagged_results.columns
        
        # Step 4: Create review batches
        review_batches = flagger.create_expert_review_batch(flagged_results, batch_size=2)
        
        # Should create batches only if there are items flagged for review
        flagged_count = flagged_results["expert_review_flag"].sum()
        if flagged_count > 0:
            assert len(review_batches) > 0
            assert all(batch.total_flagged <= 2 for batch in review_batches)
    
    def test_validation_framework_error_handling(self, temp_validation_dir):
        """Test error handling in validation framework."""
        
        # Test with empty dataframes
        flagger = ExpertReviewFlagger()
        empty_df = pd.DataFrame()
        
        flagged_empty = flagger.flag_results_for_review(empty_df)
        assert len(flagged_empty) == 0
        
        # Test with missing columns
        incomplete_df = pd.DataFrame({"some_column": [1, 2, 3]})
        flagged_incomplete = flagger.flag_results_for_review(incomplete_df)
        
        # Should handle gracefully
        assert len(flagged_incomplete) == len(incomplete_df)
        
        # Test threshold optimizer with insufficient data
        optimizer = ConfidenceThresholdOptimizer(output_dir=temp_validation_dir)
        
        small_data = pd.DataFrame({
            "confidence_score": [0.8],
            "is_correct_match": [1]
        })
        
        # Should handle small datasets gracefully
        try:
            results = optimizer.optimize_thresholds_for_dataset(small_data)
            assert isinstance(results, dict)
        except ImportError:
            pytest.skip("scikit-learn not available")
    
    def test_flagging_rate_limiting(self):
        """Test that flagging respects rate limiting constraints."""
        
        # Create flagger with low rate limit
        flagger = ExpertReviewFlagger(
            auto_accept_threshold=0.95,  # Very high threshold
            auto_reject_threshold=0.90,  # High threshold  
            max_flagging_rate=0.10       # Only 10% can be flagged
        )
        
        # Create data where most items would normally be flagged
        test_data = pd.DataFrame({
            "metabolite_id": [f"MET_{i:03d}" for i in range(100)],
            "matched_name": [f"Compound {i}" for i in range(100)],
            "confidence_score": [0.80] * 100  # All in medium confidence range
        })
        
        flagged_results = flagger.flag_results_for_review(test_data)
        
        # Count items flagged for review
        review_count = flagged_results["expert_review_flag"].sum()
        
        # Should respect 10% rate limit (allow some tolerance)
        assert review_count <= 15  # 10% of 100 = 10, allow some tolerance
        
        # Verify remaining items were converted to auto decisions
        auto_decisions = flagged_results[
            flagged_results["flagging_category"].isin(["auto_accept", "auto_reject"])
        ]
        assert len(auto_decisions) >= 85  # Most should be auto decisions
    
    def test_production_threshold_recommendations(self, temp_validation_dir):
        """Test production threshold recommendations generation."""
        
        optimizer = ConfidenceThresholdOptimizer(output_dir=temp_validation_dir)
        
        # Create mock optimization results
        mock_results = {
            "overall": ThresholdResult(
                optimal_threshold=0.82,
                precision=0.91,
                recall=0.87,
                f1_score=0.89,
                false_positive_rate=0.05,
                true_positive_rate=0.87,
                auc_score=0.92,
                validation_confidence=0.88,
                sample_size=250
            ),
            "clinical_markers": ThresholdResult(
                optimal_threshold=0.85,
                precision=0.94,
                recall=0.89,
                f1_score=0.91,
                false_positive_rate=0.03,
                true_positive_rate=0.89,
                auc_score=0.95,
                validation_confidence=0.92,
                sample_size=100
            )
        }
        
        recommendations = optimizer.recommend_production_thresholds(mock_results)
        
        # Verify recommendations structure
        assert isinstance(recommendations, dict)
        assert "overall" in recommendations
        assert "nightingale_bridge_threshold" in recommendations
        assert "semantic_threshold" in recommendations
        
        # Verify recommendations are reasonable  
        assert 0.0 <= recommendations["overall"] <= 1.0
        assert recommendations["nightingale_bridge_threshold"] >= recommendations["semantic_threshold"]
        
        # Verify production thresholds are more conservative than optimization results
        assert recommendations["overall"] >= mock_results["overall"].optimal_threshold


class TestValidationFrameworkPerformance:
    """Test performance aspects of validation framework."""
    
    def test_large_dataset_flagging_performance(self):
        """Test flagging performance with large datasets."""
        
        flagger = ExpertReviewFlagger()
        
        # Create large test dataset
        large_data = pd.DataFrame({
            "metabolite_id": [f"MET_{i:06d}" for i in range(10000)],
            "matched_name": [f"Compound {i}" for i in range(10000)],
            "confidence_score": np.random.uniform(0.5, 1.0, 10000)
        })
        
        import time
        start_time = time.time()
        
        flagged_results = flagger.flag_results_for_review(large_data)
        
        execution_time = time.time() - start_time
        
        # Should complete within reasonable time (< 10 seconds for 10k items)
        assert execution_time < 10.0
        
        # Verify all rows processed
        assert len(flagged_results) == len(large_data)
        
        # Verify flagging columns added
        assert "expert_review_flag" in flagged_results.columns
        assert "flagging_category" in flagged_results.columns
    
    def test_batch_creation_efficiency(self):
        """Test efficiency of review batch creation."""
        
        flagger = ExpertReviewFlagger()
        
        # Create data with many items requiring review
        review_data = pd.DataFrame({
            "metabolite_id": [f"REV_{i:04d}" for i in range(1000)],
            "matched_name": [f"Review Compound {i}" for i in range(1000)],
            "confidence_score": [0.80] * 1000,  # All in review range
            "expert_review_flag": [True] * 1000,
            "requires_expert_action": [True] * 1000,
            "review_priority": [2] * 1000,
            "flagging_category": ["expert_review"] * 1000,
            "flagging_reason": ["Medium confidence"] * 1000,
            "estimated_review_time_minutes": [5] * 1000,
            "alternative_matches_flagged": [""] * 1000
        })
        
        import time
        start_time = time.time()
        
        batches = flagger.create_expert_review_batch(review_data, batch_size=50)
        
        execution_time = time.time() - start_time
        
        # Should create batches efficiently (< 1 second)
        assert execution_time < 1.0
        
        # Verify correct number of batches created
        expected_batches = (1000 + 49) // 50  # Ceiling division
        assert len(batches) == expected_batches
        
        # Verify total items across all batches
        total_items = sum(batch.total_flagged for batch in batches)
        assert total_items == 1000